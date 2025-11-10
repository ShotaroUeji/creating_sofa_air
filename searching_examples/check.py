from pathlib import Path
from sofa_db import SofaDB

root = Path("out_sofa")  # 実データのあるフォルダに合わせて変更
db = SofaDB.from_dir(root, ndigits=3)

print(f"#files: {len(db.records)}")

# 実在する srcpos / micpos / GLOBAL_* の値を列挙
srcpos_set = set()
micpos_set = set()
titles = set()

for r in db.records:
    srcpos_set.add(r.srcpos)               # 代表 SourcePosition（丸め後）
    for m in r.micpos:
        micpos_set.add(m)                  # 各マイク位置（丸め後）
    t = r.attrs.get("GLOBAL_Title")
    if isinstance(t, str):
        titles.add(t)

print("unique srcpos (up to 30):", list(srcpos_set)[:30])
print("unique micpos (up to 30):", list(micpos_set)[:30])
print("some GLOBAL_Title values:", list(titles)[:10])
