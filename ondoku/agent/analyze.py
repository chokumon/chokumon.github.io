"""録音を楽譜とくらべる（Azure の単語タイミング＋自前の声の高さの分析）
入力: wav（16kHz・モノラル）, 楽譜 x（chunks, nucleus, final）, words（Azure の単語: word, start, end, acc, err）
出力: 測った結果の dict（アドバイス文は feedback.py が作る）"""
import re
import numpy as np
import parselmouth

PAUSE_IN_CHUNK = 0.30   # かたまりの途中でこれ以上止まったら「途中で止まった」
PAUSE_AT_BOUND = 0.12   # 境目でこれ以上あいていれば「区切れている」

def norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower())

def chunk_of_words(x):
    """楽譜のかたまりごとに、何語目から何語目かを返す"""
    out, i = [], 0
    for c in x["say_chunks"]:
        n = len([w for w in c.split() if norm(w)])
        out.append((i, i + n - 1)); i += n
    return out

def align(ref_words, words):
    """楽譜の語と、Azure が聞き取った語を並べる（読み抜け・付け足しはずれる）"""
    ref = [norm(w) for w in ref_words]
    got = [w for w in words if w.get("err") != "Insertion"]
    m, j = [None] * len(ref), 0
    for i, r in enumerate(ref):
        k = j
        while k < len(got) and k < j + 3 and norm(got[k]["word"]) != r:
            k += 1
        if k < len(got) and norm(got[k]["word"]) == r and got[k].get("err") != "Omission":
            m[i] = got[k]; j = k + 1
    return m

def silences(path, min_len=0.25, drop=28):
    """声の大きさから、無音の区間（秒）を拾う。Azure が無音を単語の長さに含めてしまう場合への備え"""
    s = parselmouth.Sound(path)
    I = s.to_intensity(time_step=0.01)
    v, t = I.values[0], I.xs()
    sil = v < v.max() - drop
    on = np.where(~sil)[0]
    if not len(on): return []
    out, i = [], on[0]
    while i <= on[-1]:
        if sil[i]:
            j = i
            while j <= on[-1] and sil[j]: j += 1
            if t[j - 1] - t[i] >= min_len: out.append((float(t[i]), float(t[j - 1])))
            i = j
        else: i += 1
    return out

def pitch_track(path):
    s = parselmouth.Sound(path)
    p = s.to_pitch(time_step=0.01, pitch_floor=75, pitch_ceiling=500)
    f, t = p.selected_array["frequency"], p.xs()
    I = s.to_intensity(time_step=0.01)
    return t, f, I.xs(), I.values[0]

def span_stat(t, f, a, b):
    sel = f[(t >= a) & (t <= b) & (f > 0)]
    return float(np.median(sel)) if len(sel) else None

def final_dir(t, f, end, span=0.45):
    voiced = f > 0
    if voiced.sum() < 10: return None
    med = np.median(f[voiced])
    sel = (t >= end - span) & (t <= end + 0.05) & voiced
    st = 12 * np.log2(f[sel] / med)
    if len(st) < 6: return None
    k = max(3, len(st) // 4)
    return round(float(st[-k:].mean() - st[:k].mean()), 1)

def measure(path, x, words):
    ref_words = [w for w in x["say"].split() if norm(w)]
    m = align(ref_words, words)
    bounds = chunk_of_words(x)
    R = {"omitted": [ref_words[i].strip(",.;?!") for i, w in enumerate(m) if w is None],
         "inserted": [w["word"] for w in words if w.get("err") == "Insertion"],
         "mispronounced": [w["word"] for w in words if w.get("err") not in ("Omission", "Insertion") and (w.get("err") == "Mispronunciation" or (w.get("acc") is not None and w["acc"] < 60))],
         "mid_pauses": [], "bound_pauses": [], "nucleus": [], "final": None}
    # 止まった場所
    for ci, (a, b) in enumerate(bounds):
        for i in range(a, b):
            if m[i] and m[i + 1]:
                gap = m[i + 1]["start"] - m[i]["end"]
                if gap >= PAUSE_IN_CHUNK:
                    R["mid_pauses"].append({"after": ref_words[i].strip(",.;"), "before": ref_words[i + 1].strip(",.;"), "sec": round(gap, 2), "chunk": ci})
        if ci < len(bounds) - 1 and m[b] and m[b + 1]:
            R["bound_pauses"].append(round(m[b + 1]["start"] - m[b]["end"], 2))
    # 無音の区間からも止まった場所を拾う（単語の時間に無音が含まれていても見逃さない）
    inner = {(a + k, a + k + 1): ci for ci, (a, b) in enumerate(bounds) for k in range(b - a)}
    edges = {b: ci for ci, (a, b) in enumerate(bounds) if ci < len(bounds) - 1}
    seen = {(q["after"], q["before"]) for q in R["mid_pauses"]}
    for s0, s1 in silences(path):
        mid = (s0 + s1) / 2
        prev = [i for i, w in enumerate(m) if w and w["start"] < mid]
        if not prev: continue
        i = prev[-1]
        if i + 1 >= len(m) or not any(m[i + 1:]): continue
        if (i, i + 1) in inner:
            key = (ref_words[i].strip(",.;"), ref_words[i + 1].strip(",.;"))
            if key not in seen:
                R["mid_pauses"].append({"after": key[0], "before": key[1], "sec": round(s1 - s0, 2), "chunk": inner[(i, i + 1)], "by": "silence"}); seen.add(key)
        elif i in edges and edges[i] < len(R["bound_pauses"]):
            R["bound_pauses"][edges[i]] = max(R["bound_pauses"][edges[i]], round(s1 - s0, 2))
    # 強く読む語（かたまりの中で高さ・強さが目立っているか）
    t, f, ti, iv = pitch_track(path)
    for ci, (a, b) in enumerate(bounds):
        nuc = norm(x["nucleus"][ci])
        idx = [i for i in range(a, b + 1) if norm(ref_words[i]) == nuc]
        if not idx or not m[idx[-1]]: continue
        w = m[idx[-1]]
        others = [m[i] for i in range(a, b + 1) if i != idx[-1] and m[i]]
        if not others: continue
        p_n = span_stat(t, f, w["start"], w["end"])
        p_o = [span_stat(t, f, o["start"], o["end"]) for o in others]
        p_o = [p for p in p_o if p]
        i_n = span_stat(ti, iv, w["start"], w["end"])
        i_o = [span_stat(ti, iv, o["start"], o["end"]) for o in others]
        i_o = [p for p in i_o if p]
        if p_n and p_o and i_n and i_o:
            R["nucleus"].append({"word": x["nucleus"][ci], "pitch_st": round(12 * np.log2(p_n / np.median(p_o)), 1),
                                 "loud_db": round(i_n - float(np.median(i_o)), 1)})
    last = next((w for w in reversed(m) if w), None)
    if last: R["final"] = final_dir(t, f, last["end"])
    # 速さ（1分あたりの語数）
    got = [w for w in m if w]
    if len(got) >= 2:
        dur = got[-1]["end"] - got[0]["start"]
        R["wpm"] = round(len(ref_words) / dur * 60) if dur > 0 else None
    return R
