from pathlib import Path
from sofa_db import SofaDB

db = SofaDB.from_dir(Path("out_sofa"))

# micpos 完全一致（DB構築時丸め後）
# results = db.search(micpos=[-0.09, 110.0, 0.0])
# for r in results:
#     print(r.path)

# # srcpos 近傍（±1e-2）かつタイトルに "Aula"
# results = db.search(
#     srcpos=[45.0, 0.0, 3.0],
#     tol=1e-2,
#     predicate=lambda rec: "Aula" in str(rec.attrs.get("GLOBAL_Title", "")),
# )
# for r in results:
#     print("[near srcpos & Aula]", r.path)

# 例: Room(=Aula Carolina)で検索（'GLOBAL_'は省略可）
hits = db.search(attrs={"RoomShortName": "booth"})
for r in hits:
    print(r.path)
# or タイトルに含まれる文字列で曖昧検索
