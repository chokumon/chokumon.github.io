"""測った結果 → 直問！の言葉でアドバイス（型から選ぶ。AIに自由に書かせない）。言うのは多くても2つ
2026-11-02 テスト結果で調整：ゆっくり・区切りなしを指摘、平らの判定は Azure の抑揚の評価を主に、機能語の発音は言わない"""
FUNC = set("a an the and or but of to in on at by for with from as is are was were be been it its this that those these who which will would can could may might must shall should do does did has have had not no".split())
SLOW_WPM = 85          # 1分あたりの語数がこれより少なければ「ゆっくり」
PAUSE_OK = 0.15        # 境目でこれ以上あいていれば「区切れている」
RISE_ST = 2.0          # 言い切る文で、最後がこれ以上（半音）上がっていたら「上がっている」
FLAT_PRO = 70          # Azure の抑揚の点がこれより低ければ「平ら」の候補

def advise(x, R, az):
    good, fix = [], []
    mids, bps, wpm, fd = R["mid_pauses"], R.get("bound_pauses", []), R.get("wpm"), R.get("final")
    n_chunks = len(x["chunks"])
    # 1. 読み抜け・付け足し（いちばん大事）
    if R["omitted"]:
        fix.append(f"「{'、'.join(R['omitted'][:3])}」が抜けています。抜けると意味が変わることがあるので、1語ずつ目で追ってもう一度。")
    if R["inserted"]:
        fix.append(f"台本にない「{R['inserted'][0]}」が聞こえました。言い直しは止めて、そのまま最後まで読みきってOKです。")
    # 2. 区切り：1語ずつ／かたまりの途中で止まる／どこでも止まらない
    if len(mids) >= 3:
        ch = x["chunks"][mids[0]["chunk"]].rstrip(",.;?")
        fix.append(f"1語ずつ区切って読んでいます。止まるのは楽譜の ／ のところだけ。まず「{ch}」を一息で3回言ってから、全体へ。")
    elif mids:
        p = max(mids, key=lambda q: q["sec"])
        ch = x["chunks"][p["chunk"]].rstrip(",.;?")
        fix.append(f"「{p['after']}」と「{p['before']}」の間で {p['sec']:.1f} 秒止まっています。ここは「{ch}」で1かたまり。かたまりの中は一息で。")
    elif n_chunks >= 3 and bps and max(bps) < PAUSE_OK:
        fix.append("最後まで一気に読んでいます。楽譜の ／ のところで、ほんの少し（0.3秒くらい）間をあけると、かたまりごとに意味を取る練習になります。")
    elif bps and max(bps) >= PAUSE_OK:
        good.append("止まる場所がかたまりの境目だけになっています。前から意味を取りながら読めている証拠です。")
    # 3. 速さ（1語ずつのときは上で言っているので言わない）
    if wpm and wpm < SLOW_WPM and len(mids) < 3:
        fix.append("全体がゆっくりめです。かたまりの中は速く、境目で少し休む、のメリハリで。見本の音声と同じくらいの速さを目指しましょう。")
    # 4. 文末の上げ下げ
    if fd is not None:
        if x["final"] == "↗" and fd < 1.0:
            fix.append("質問の文なので、最後の語で声を上げて終わりましょう（↗）。")
        elif x["final"] == "↘" and fd > RISE_ST:
            fix.append("最後が上がっています。言い切る文なので、最後の語で下げて終わりましょう（↘）。")
        elif x["final"] == "↘" and fd <= -2:
            good.append("文の終わりをしっかり下げられています。")
    # 5. 平らな読み（Azure の判定を主にする）
    pro = (az.get("scores") or {}).get("pro")
    flat_words = [n for n in R["nucleus"] if n["pitch_st"] < 0 and n["loud_db"] < 0]
    if az.get("monotone") or (pro is not None and pro < FLAT_PRO and len(flat_words) >= 2):
        w = flat_words[0]["word"] if flat_words else x["nucleus"][0]
        fix.append(f"全体が平らに聞こえます。楽譜の大文字の語（たとえば「{w}」）だけを、少し高く・少し長く。ほかの語は軽くでOK。")
    # 6. 発音（中身の語だけ、最大2語）
    mis = [w for w in dict.fromkeys(R["mispronounced"]) if w.lower() not in FUNC]
    if mis:
        fix.append(f"「{'、'.join(mis[:2])}」の発音が聞き取りにくかったです。見本の音声でこの語だけ3回まねしてから、文に戻りましょう。")
    head = good[0] if good else "提出ありがとう！"
    body = fix[:2] if fix else ["大きな直しはありません。次は見本の音声に重ねて（同時に）読んでみましょう。"]
    s = az.get("scores") or {}
    tail = f"\n\n（参考）正確さ {s.get('acc', '-')}／なめらかさ {s.get('flu', '-')}／抑揚 {s.get('pro', '-')}" if s else ""
    return head + "\n\n" + "\n".join(f"・{b}" for b in body) + tail + "\n\n違うと思ったら、そのまま質問してね。"
