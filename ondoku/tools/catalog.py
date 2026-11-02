"""新しい文を作る前に必ず見る一覧：カテゴリごとの数と、これまでの全部の文（かぶり防止）
python3 ondoku/tools/catalog.py"""
import json, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "..", "sentences.json")))
C = json.load(open(os.path.join(HERE, "categories.json")))
cnt = collections.Counter(x["cat"] for x in S)
print(f"全 {len(S)} 文\n\n== カテゴリごとの数（少ない順）")
for k in sorted(C, key=lambda k: (cnt[k], k)):
    print(f"{k} {C[k]['name']}：{cnt[k]} 文 ― {C[k]['desc']}")
print("\n== これまでの文（カテゴリ別）")
for k in sorted(C):
    print(f"\n[{k} {C[k]['name']}]")
    for x in S:
        if x["cat"] == k: print(f"  No.{x['no']} {x['id']}: {' / '.join(x['chunks'])}")
