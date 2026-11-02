"""測った結果 → 直問！の言葉でアドバイス（型から選ぶ。AIに自由に書かせない）。言うのは多くても3つ"""
FLAT_ST = 1.0      # 強く読む語が、まわりより半音1つ分も高くなっていなければ「平ら」
FLAT_DB = 1.0

def advise(x, R, az):
    good, fix = [], []
    # 1. 読み抜け・付け足し（いちばん大事）
    if R["omitted"]:
        w = "、".join(R["omitted"][:3])
        fix.append(f"「{w}」が抜けています。抜けると意味が変わることがあるので、1語ずつ目で追ってもう一度。")
    if R["inserted"]:
        fix.append(f"台本にない「{R['inserted'][0]}」が聞こえました。言い直しは止めて、そのまま最後まで読みきってOKです。")
    # 2. かたまりの途中で止まった
    if len(R["mid_pauses"]) >= 3:
        ch = x["chunks"][R["mid_pauses"][0]["chunk"]].rstrip(",.;?")
        fix.append(f"1語ずつ区切って読んでいます。止まるのは楽譜の ／ のところだけ。まず「{ch}」を一息で3回言ってから、全体へ。")
    elif R["mid_pauses"]:
        p = max(R["mid_pauses"], key=lambda q: q["sec"])
        ch = x["chunks"][p["chunk"]].rstrip(",.;?")
        fix.append(f"「{p['after']}」と「{p['before']}」の間で {p['sec']:.1f} 秒止まっています。ここは「{ch}」で1かたまり。かたまりの中は一息で。")
    elif R["bound_pauses"] and len(x["chunks"]) >= 3:
        good.append("止まる場所がかたまりの境目だけになっています。前から意味を取りながら読めている証拠です。")
    # 3. 文末の上げ下げ
    fd = R.get("final")
    if fd is not None:
        if x["final"] == "↗" and fd < 0.5:
            fix.append("質問の文なので、最後の語で声を上げて終わりましょう（↗）。")
        elif x["final"] == "↘" and fd > 0.5:
            fix.append("最後が上がっています。言い切る文なので、最後の語で下げて終わりましょう（↘）。")
        elif x["final"] == "↘" and fd <= -2:
            good.append("文の終わりをしっかり下げられています。")
    # 4. 強く読む語・平らな読み
    flat = [n for n in R["nucleus"] if n["pitch_st"] < FLAT_ST and n["loud_db"] < FLAT_DB]
    monotone = az.get("monotone")
    if monotone or (R["nucleus"] and len(flat) >= max(2, len(R["nucleus"]) // 2 + 1)):
        w = flat[0]["word"] if flat else x["nucleus"][0]
        fix.append(f"全体が平らに聞こえます。楽譜のオレンジの語（たとえば「{w}」）だけを、少し高く・少し長く。ほかの語は軽くでOK。")
    elif R["nucleus"] and not flat:
        good.append("オレンジの語にきちんと山ができています。")
    # 5. 発音（目立つものだけ、最大2語）
    if R["mispronounced"]:
        ws = "、".join(dict.fromkeys(R["mispronounced"]))
        ws = "、".join(ws.split("、")[:2])
        fix.append(f"「{ws}」の発音が聞き取りにくかったです。見本の音声でこの語だけ3回まねしてから、文に戻りましょう。")
    # 6. 速さ
    wpm = R.get("wpm")
    if wpm and wpm < 85 and not R["mid_pauses"]:
        fix.append("全体がゆっくりめです。かたまりの中は速く、境目で少し休む、のメリハリで。")
    head = good[0] if good else "提出ありがとう！"
    body = fix[:2] if fix else ["大きな直しはありません。次は見本の音声に重ねて（同時に）読んでみましょう。"]
    score = az.get("scores", {})
    tail = ""
    if score:
        tail = f"\n\n（参考）正確さ {score.get('acc', '-')}／なめらかさ {score.get('flu', '-')}／抑揚 {score.get('pro', '-')}"
    return head + "\n\n" + "\n".join(f"・{b}" for b in body) + tail + "\n\n違うと思ったら、そのまま質問してね。"
