from __future__ import annotations
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from .aryfile import AryFile, _round_tuple


class SofaDB:
    """
    複数 AryFile を束ね、(field, key) -> [record_ids] の逆引きインデックスを提供。
    - from_dir / from_paths で構築
    - search() で srcpos / micpos / attrs / tol / predicate を指定して検索
    """
    def __init__(self) -> None:
        self.records: List[AryFile] = []
        self.inv: Dict[Tuple[str, Tuple[Any, ...]], List[int]] = {}

    @classmethod
    def from_paths(cls, paths: Iterable[Path | str], ndigits: int = 3) -> "SofaDB":
        db = cls()
        for p in paths:
            p = Path(p)
            if p.suffix.lower() != ".sofa":
                continue
            rec = AryFile.from_sofa(p, ndigits=ndigits)
            idx = len(db.records)
            db.records.append(rec)
            for (key, _none) in rec.as_index_items():
                db.inv.setdefault(key, []).append(idx)
        return db

    @classmethod
    def from_dir(cls, root: Path | str, ndigits: int = 3) -> "SofaDB":
        root = Path(root)
        return cls.from_paths(root.rglob("*.sofa"), ndigits=ndigits)

    def _lookup(self, field: str, key: Tuple[Any, ...]) -> List[int]:
        return self.inv.get((field, key), [])

    def search(
        self,
        srcpos: Optional[Iterable[float]] = None,
        micpos: Optional[Iterable[float]] = None,
        attrs: Optional[Dict[str, Any]] = None,
        tol: float = 0.0,
        predicate: Optional[Callable[[AryFile], bool]] = None,
    ) -> List[AryFile]:
        """
        条件に一致する AryFile を返す。
        - 丸めは DB 構築時（ndigits）のルールに従う
        - tol > 0 のときは最終段で数値近傍フィルタ
        - attrs は {'GLOBAL_Title': 'Aula', ...} のように完全一致。
          'GLOBAL_' を省略しても OK（内部で補完）
        """
        candidate_sets: List[set] = []

        if srcpos is not None:
            key = _round_tuple(srcpos)
            candidate_sets.append(set(self._lookup('srcpos', key)))

        if micpos is not None:
            key = _round_tuple(micpos)
            candidate_sets.append(set(self._lookup('micpos', key)))

        if attrs:
            for k, v in attrs.items():
                kk = k if k.startswith('GLOBAL_') else f'GLOBAL_{k}'
                candidate_sets.append(set(self._lookup(f'attr:{kk}', (v,))))

        # 候補の積集合
        if candidate_sets:
            cand_idx = set.intersection(*candidate_sets) if len(candidate_sets) > 1 else candidate_sets[0]
        else:
            cand_idx = set(range(len(self.records)))

        out = [self.records[i] for i in cand_idx]

        # tol 近傍フィルタ
        if tol > 0:
            def near(a: Tuple[float, ...], b: Tuple[float, ...]) -> bool:
                return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))

            if srcpos is not None:
                s = _round_tuple(srcpos)
                out = [r for r in out if near(r.srcpos, s)]
            if micpos is not None:
                m = _round_tuple(micpos)
                out = [r for r in out if any(near(mp, m) for mp in r.micpos)]

        if predicate:
            out = [r for r in out if predicate(r)]

        return sorted(out, key=lambda r: str(r.path))
