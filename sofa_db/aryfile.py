from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
import numpy as np
import sofar as sf  # pip install sofar


def _round_tuple(arr: Iterable[float], ndigits: int = 3) -> Tuple[float, ...]:
    """Iterable[float] -> タプル化＆四捨五入。インデックス化の安定化に必須。"""
    return tuple(round(float(x), ndigits) for x in arr)


@dataclass
class AryFile:
    """
    1つの SOFA ファイル（= マイクアレイ単位）を検索用レコードに正規化するクラス。
    - srcpos: 代表 SourcePosition (3要素)
    - micpos: 各マイクの 3次元位置のタプル列（R x 3）
    - attrs : GLOBAL_* 等のシンプルな属性
    """
    path: Path
    srcpos: Tuple[float, float, float]
    micpos: Tuple[Tuple[float, float, float], ...]
    attrs: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_sofa(path: Path | str, ndigits: int = 3) -> "AryFile":
        """SOFA 読み込み→検索向けメタ抽出。丸め桁は ndigits で統一。"""
        p = Path(path)
        sofa = sf.read_sofa(str(p))

        # --- SourcePosition 抽出（M×3 or 1×3 を想定） ---
        sp = np.asarray(sofa.SourcePosition)
        sp = np.squeeze(sp)
        if sp.ndim == 1 and sp.size == 3:
            srcpos = _round_tuple(sp, ndigits)
        else:
            # 先頭を代表値として採用（必要ならポリシー変更可）
            srcpos = _round_tuple(sp[0], ndigits)

        # --- ReceiverPosition 抽出（R×3×M or R×3）→ R×3 に整形 ---
        rp = np.asarray(sofa.ReceiverPosition)
        if rp.ndim == 3:
            # M が複数なら先頭を採用（必要に応じて平均なども検討可）
            rp = rp[:, :, 0]
        if rp.ndim != 2 or rp.shape[1] != 3:
            raise ValueError(f"Unexpected ReceiverPosition shape: {rp.shape}")
        micpos = tuple(_round_tuple(row, ndigits) for row in rp)

        # --- GLOBAL_* 属性を抽出（スカラ/文字列のみを素直に保持） ---
        attrs: Dict[str, Any] = {}
        for k in dir(sofa):
            if k.startswith("GLOBAL_"):
                try:
                    v = getattr(sofa, k)
                except Exception:
                    continue
                # numpy/配列は扱い分け。配列は可読のため list 化するが
                # インデックスには使わない（database 側で扱う）
                if isinstance(v, np.ndarray):
                    v = np.squeeze(v)
                    v = v.tolist() if v.ndim > 0 else v.item()
                attrs[k] = v

        return AryFile(path=p, srcpos=srcpos, micpos=micpos, attrs=attrs)

    def as_index_items(self) -> List[Tuple[Tuple[str, Tuple[Any, ...]], None]]:
        """
        逆引きインデックスに載せる (field, key) の列挙。
        - srcpos: ('srcpos', (az,el,dist)) 等の1キー
        - micpos: 各マイク座標ごとに ('micpos', (x,y,z))
        - attrs : スカラ/文字列のみを ('attr:GLOBAL_*', (value,)) として登録
        """
        items: List[Tuple[Tuple[str, Tuple[Any, ...]], None]] = []
        items.append((('srcpos', self.srcpos), None))
        for m in self.micpos:
            items.append((('micpos', m), None))
        for k, v in self.attrs.items():
            if isinstance(v, (str, int, float, bool)):
                items.append(((f'attr:{k}', (v,)), None))
        return items
