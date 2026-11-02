"""新しい音読の文を足す：python3 ondoku/tools/add.py new.json
new.json は [{"cat": "C07", "chunks": ["英語のかたまり|前からの日本語", ...]}, ...]
チェック（形・長さ・かぶり）→ 見本音声（Kokoro）→ ondoku/dNN.m4a と sentences.json に追加"""
import json, os, re, sys, datetime, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import ondoku_lib as L
S = json.load(open(os.path.join(ROOT, "sentences.json")))
C = json.load(open(os.path.join(HERE, "categories.json")))
NUM = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine", "10": "ten"}

def grams(t, n=4):
    w = re.findall(r"[a-z']+", t.lower()); return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}

COMMON = set("""I Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May June July August September October November December Internet Web English Japanese""".split())

def txt(o):
    return o.get("text") or " ".join(o["chunks"])

def names(t):
    w = [re.sub(r"[^A-Za-z]", "", x) for x in t.split()[1:]]
    return {x for x in w if len(x) >= 4 and x[0].isupper() and x not in COMMON}

def check(x, others):
    E = []
    if x["cat"] not in C: E.append(f"カテゴリ {x['cat']} がない")
    w = len(x["text"].split())
    if not 10 <= w <= 26: E.append(f"語数 {w}（10〜26）")
    if not 3 <= len(x["chunks"]) <= 5: E.append(f"かたまり {len(x['chunks'])} 個（3〜5）")
    if re.search(r"\d", x["text"]): E.append("数字は英語のつづりで書く（例：twenty）")
    if not re.search(r"[.?!]$", x["text"]): E.append("文の終わりに . か ? がない")
    if any(not j.strip() for j in x["ja"]): E.append("日本語が空のかたまりがある")
    g = grams(x["text"])
    for o in others:
        if txt(o).lower() == x["text"].lower(): E.append(f"同じ文がある（{o['id']}）"); break
        og = grams(txt(o))
        if g and og and len(g & og) / len(g | og) >= 0.3: E.append(f"{o['id']} と言い回しが似すぎ：{txt(o)}"); break
    used = set().union(*[names(txt(o)) for o in others]) if others else set()
    dup = sorted(n for n in names(x["text"]) if n in used)
    if dup: E.append(f"人名・会社名がかぶり：{dup}")
    return E

def main(path):
    new = json.load(open(path)); today = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    stamp = today.strftime("%y%m%d"); done = []; errs = []
    for k, raw in enumerate(new, 1):
        ch = [c.split("|")[0].strip() for c in raw["chunks"]]; ja = [c.split("|")[1].strip() if "|" in c else "" for c in raw["chunks"]]
        text = " ".join(ch); q = text.endswith("?"); wh = re.match(r"(What|When|Where|Why|How|Who|Which)\b", text)
        x = {"id": f"g{stamp}{k}", "cat": raw["cat"], "chunks": ch, "ja": ja, "text": text,
             "nucleus": [L.last_content(c) for c in ch], "final": "↗" if q and not wh else "↘",
             "say": text.replace("e-mail", "email"), "say_chunks": [c.replace("e-mail", "email") for c in ch]}
        E = check(x, S + done)
        if E: errs.append((text, E)); continue
        with tempfile.TemporaryDirectory() as td:
            wav = os.path.join(td, "a.wav"); rep = L.make_model_audio(x, wav)
            x["ms"] = L.to_m4a(wav, os.path.join(ROOT, x["id"] + ".m4a"))
        x["check"] = "ok" if rep["ok"] else "要確認（見本音声が楽譜と合わない）"
        done.append(x); print("追加", x["id"], x["cat"], text, x["check"])
    for x in done:
        x["no"] = len(S) + 1; x["catname"] = C[x["cat"]]["name"]; x.pop("text"); S.append(x)
    json.dump(S, open(os.path.join(ROOT, "sentences.json"), "w"), ensure_ascii=False)
    for t, E in errs: print("はねた：", t, "→", "／".join(E))
    print(f"追加 {len(done)} 文、はねた {len(errs)} 文、全 {len(S)} 文")
    sys.exit(0 if done else 1)

if __name__ == "__main__":
    main(sys.argv[1])
