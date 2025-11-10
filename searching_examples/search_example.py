from pathlib import Path
from sofa_db import SofaDB

# SofaDBを指定ディレクトリから構築
db = SofaDB.from_dir(Path("out_sofa"))

# srcposがマイクから見て、[45.0, 0.0, 1.0]の位置にあるものを検索 [方位角、仰角、距離(m)]
results = db.search(
    srcpos=[45.0, 0.0, 1.0]
)
print(f"[srcpos = (45,0,1.0)] {len(results)}")
for r in results:
    print(r.path)    
# srcposがマイクから見て、[45.0, 0.0, 3.0]の位置にあるものを検索 [方位角、仰角、距離(m)]
results = db.search(
    srcpos=[45.0, 0.0, 3.0]
)
print(f"[srcpos = (45,0,3.0)] {len(results)}")
for r in results:
    print(r.path)


# 例: Room(=booth)で検索（'GLOBAL_'は省略可）
hits = db.search(attrs={"RoomShortName": "booth"})
print(f"[RoomShortName = 'booth'] {len(hits)}")
for r in hits:
    print(r.path)
# 例: Room(=lecture)で検索（'GLOBAL_'は省略可）
hits = db.search(attrs={"RoomShortName": "lecture"})
print(f"[RoomShortName = 'lecture'] {len(hits)}")
for r in hits:
    print(r.path)


# 例: srcposとrooomの複合 AND 検索
hits = db.search(
    srcpos=[90, 0.0, 2.25],
    attrs={"RoomShortName": "lecture"})
print(f"[srcpos=(90,0,2.25) AND RoomShortName='lecture'] {len(hits)}")
for r in hits:
    print(r.path)