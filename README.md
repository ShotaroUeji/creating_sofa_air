# AIR→SOFA 変換パイプライン README

最終更新: 2025-09-22

本リポジトリは、**Aachen Impulse Response (AIR) Database**　[https://www.iks.rwth-aachen.de/en/research/tools-downloads/databases/aachen-impulse-response-database/] の配布データを一括処理し、

1. MATLAB で公式 `load_air.m` を用いて **中間 .mat (マイクロフォンアレイごと)** を生成（`out_intermediate/`）
2. Python + **sofar** で **SOFA (SingleRoomSRIR)** へ変換（`out_sofa/`）

するための実装を提供します。

---

## 背景
- E:エミッターの数

- R:受信者の数

- M:1ファイルあたりの測定回数

- N:データのサンプル数または頻度ビン数

- C:座標の数（常に3）

- I:ユニティ次元（常に1）

- S:データに含まれる最長文字列の長さ（自動検出）
* AIR の元データでは、1 つの .mat に **1 チャンネル（R = 1）** の単一 IR とメタ情報 (`air_info`) を含みます。例えば、L/R の両耳収録は **左右で別ファイル** です。公式ローダー `load_air.m` は、与えたパラメータ（部屋、距離インデックス、方位、チャンネルなど）に応じて該当ファイルを返します。
* 
* SOFA への書き出しは **SingleRoomSRIR 1.0** [https://www.sofaconventions.org/mediawiki/index.php/SingleRoomSRIR] を採用し、`ReceiverPosition` は ±0.09 m を仮定（必要に応じて調整可）。

---

## ディレクトリ構成（例）

```
AIR_1_4/
├─ data/                 # AIR 純正の .mat 群（公式配布をそのまま配置）
├─ out_intermediate/     # 中間 .mat (M=1,R=2,N) の出力先
├─ out_sofa/             # 変換後の .sofa 出力先
├─ load_air.m            # 公式ローダー(参照パス名以外はそのまま)
├─ load_air_examples.m   # 公式サンプル(load_air.mの使い方)
├─ build_submats.m       # ★ 一括生成（ステレオ前提）
├─ build_submats_single.m# ★ 単一条件での生成（検証向け）
├─ mat2sofa_sofar_batch.py   # ★ 中間 .mat → SOFA を一括変換
├─ mat2sofa_sofar_single.py  # ★ 単一 .mat → SOFA 変換
├─ requirements.txt
└─ README.md（本ファイル）
```

> **重要:** `load_air.m` と **同じ階層に `data/` ディレクトリ**を置いてください（公式の相対パス仕様をそのまま使います）。

---

## セットアップ

### MATLAB 側

* MATLAB R2021a+（目安）
* `load_air.m` と `data/` をリポジトリ直下に配置
* （任意）`config.yaml` または `config.json` を `build_submats.m` の設定ファイルとして用意

### Python 側

* Python 3.9+ 推奨
* 依存関係をインストール:

  ```bash
  pip install -r requirements.txt
  ```

  > `sofar`, `numpy`, `scipy` などが含まれます。

---

## 1) 中間 .mat の一括生成（MATLAB）

### スクリプト

* `build_submats.m` … 指定レンジを**総当たり**して `out_intermediate/` に保存
* `build_submats_single.m` … 単一条件（デバッグ/検証用）

### 生成されるファイル

* 出力先: `out_intermediate/`
* 形式: `AIR_rirtype{d}_room{d}_head{d}_rirno{d}_az{d}_R{d}.mat`
* 中身の変数:

  * `IR` … **(M=1, R, N)**
  * `fs`, `rir_type`, `room`, `head`, `rir_no`, `azimuth`

### 実行例（設定ファイルなし = 既定値で実行）

MATLAB コマンドウィンドウで：

```matlab
>> build_submats
```

### 既定パラメータ（抜粋）

* `fs = 48000`
* `rir_type = 1`（**binaural** 固定）
* `rooms = [1 2 3 4 5 11]`
* `head_list = [0 1]`（ダミーヘッド有無の両方を試行）
* `chan_map = [1 0]`（左=1, 右=0 の順で R=2 を構成）
* `require_full_stereo = true`（L/R のどちらかが欠落したら保存しない）
* `az_list_override = []`（空なら実在パターンに従う）

### 実在パターン（方位）

* `room=5 (stairway)`: `0:15:180`
* `room=11 (aula_carolina) & rir_no=3`: `0:45:180`
* それ以外: `90`（= AIR で正面）
* `room=11` は `mic_type=3` を明示（実装内で設定）

---

## 2) SOFA への変換（Python + sofar）

### バッチ変換

```bash
python mat2sofa_sofar_batch.py \
  --in_dir out_intermediate \
  --out_dir out_sofa \
  --pattern "*.mat" \
```

### 単体変換（デバッグ）

```bash
python mat2sofa_sofar_single.py --in_path out_intermediate/XXXX.mat --out_dir out_sofa
```

### SOFA の中身（要点）

* Conventions: **SingleRoomSRIR 1.0**
* `Data.IR`: (M=1, R=2, N) ← 中間 .mat をそのまま格納
* `Data.SamplingRate`: Hz
* `ListenerPosition`: (M,3) = `[0,0,0]`[x, y, z]
* `ReceiverPosition`: (R,3,M) = `[-0.09,0,0]` / `[+0.09,0,0]`（仮定）[x, y, z]
* `SourcePosition`: (M,3) = `[az, 0, distance]` [degree, degree, metre] 

* タイトルや日付などの GLOBAL メタも自動付与

### 距離テーブル（`room` と `rir_no` の対応）

| room | name           | `rir_no`→距離 \[m]               |
| ---: | -------------- | ------------------------------ |
|    1 | booth          | 0.5, 1, 1.5                    |
|    2 | office         | 1, 2, 3                        |
|    3 | meeting        | 1.45, 1.7, 1.9, 2.25, 2.8      |
|    4 | lecture        | 2.25, 4, 5.56, 7.1, 8.68, 10.2 |
|    5 | stairway       | 1, 2, 3                        |
|   11 | aula\_carolina | 1, 2, 3, 5, 15, 20             |

---

## 典型ワークフロー（コピペ用）

1. **MATLAB**: 中間 .mat 生成

   ```matlab
   >> build_submats   % or: build_submats('config.yaml')
   ```
2. **Python**: SOFA 一括変換

   ```bash
   python mat2sofa_sofar_batch.py --in_dir out_intermediate --out_dir out_sofa
   ```
3. `out_sofa/` に `.sofa` が生成されていることを確認

---

了解。README.mdにそのまま貼れる追記案を用意しました。既存の「2) SOFA への変換」の後、あるいは「典型ワークフロー」の後あたりに入れる想定です。必要なら見出し番号だけ調整してください。

---

## 3) SOFA 検索ユーティリティ（`sofa_db/`）

AIR→SOFA 変換後に生成される `out_sofa/*.sofa` を**高速に検索**するためのミニユーティリティです。
`sofa_db/aryfile.py` と `sofa_db/database.py` から成り、以下の2段構えになっています。

### 構成と設計

* **AryFile**: 1つの SOFA ファイルを「検索用レコード」に正規化

  * 抽出フィールド

    * `srcpos`: 代表 SourcePosition（3要素）
    * `micpos`: 各マイクの3次元位置（R×3 → R×3 に整形して保持）
    * `attrs`: `GLOBAL_*` の**スカラ/文字列**など簡素な属性（配列は可読目的で list 化）
  * 丸めポリシー

    * 位置などの数値は**既定で小数第3位に四捨五入**してタプル化（インデックス安定化のため）。SOFA 読み込み時の丸め桁は `ndigits` で統一できます（既定=3）。
  * SourcePosition の代表値

    * `M×3` または `1×3` を想定し、`1×3` ならそのまま、`M×3` なら**先頭**を代表値として採用（必要ならポリシー変更可）。
  * 逆引きインデックスのキー化

    * `('srcpos',(az,el,dist))`, `('micpos',(x,y,z))`, `('attr:GLOBAL_XXX',(value,))` を列挙して登録します（`attrs`は**スカラ/文字列のみ**をキー化）。

* **SofaDB**: 複数 `AryFile` を束ねて**逆引きインデックス**を構築し、検索 API を提供

  * 機能：`from_dir`/`from_paths` で構築、`search()` で `srcpos` / `micpos` / `attrs` / `tol` / `predicate` を指定して検索できます。
  * `search()` の仕様

    * 丸めは**DB構築時のルール（`ndigits`）に従う**。
    * `attrs` は完全一致。`"GLOBAL_"` 接頭辞は**省略可**（内部で補完）。
    * `tol > 0` の場合、最終段で**各次元ごとの近傍（|a−b| ≤ tol）判定**を行います。
    * 結果は**パス文字列順**に安定ソートされます。

### インストール

Python 側の依存に `sofar` を利用しています（`pip install sofar`）。
本リポジトリのセットアップ手順は既存の「セットアップ > Python 側」を参照してください（`requirements.txt` に含まれます）。 

### 使い方（クイックスタート）
```python -m searching_examples.search_example```

```python
from pathlib import Path
from sofa_db import SofaDB

# out_sofa/ 以下の .sofa を走査して DB 構築（既定の丸め桁=3）
db = SofaDB.from_dir(Path("out_sofa"))

# 1) srcpos 完全一致（[方位角°, 仰角°, 距離m]）
results = db.search(srcpos=[45.0, 0.0, 1.0])
print(f"[srcpos=(45,0,1.0)] {len(results)}")
for r in results:
    print(r.path)

# 2) 別の距離で検索
results = db.search(srcpos=[45.0, 0.0, 3.0])
print(f"[srcpos=(45,0,3.0)] {len(results)}")
for r in results:
    print(r.path)

# 3) GLOBAL 属性で検索（'GLOBAL_'は省略可）
hits = db.search(attrs={"RoomShortName": "booth"})
print(f"[RoomShortName='booth'] {len(hits)}")
for r in hits:
    print(r.path)

# 4) 複合 AND：srcpos × room
hits = db.search(srcpos=[90.0, 0.0, 2.25], attrs={"RoomShortName": "lecture"})
print(f"[srcpos=(90,0,2.25) AND RoomShortName='lecture'] {len(hits)}")
for r in hits:
    print(r.path)

# 5) 近傍検索（±1e-2）と任意フィルタ（タイトルに 'Aula' を含む）
near = db.search(
    srcpos=[45.0, 0.0, 3.0],
    tol=1e-2,
    predicate=lambda rec: "Aula" in str(rec.attrs.get("GLOBAL_Title", ""))
)
for r in near:
    print("[near srcpos & Aula]", r.path)
```

> 参考: `searching_examples/search_example.py` にも実行例を置いてあります（micpos検索や predicate 例を含む）。

### 実装上の注意

* **SourcePosition の扱い**: `M×3` の場合は**先頭の測定**を代表値にします（必要なら平均化などへ変更可能）。
* **ReceiverPosition の整形**: `R×3×M` のときは `M` 次元の**先頭スライス**を採用し、`R×3` へ落としてから丸め・格納します。
* **属性の抽出**: `GLOBAL_*` の配列は `np.squeeze` してから list 変換（スカラは `item()`）し、**インデックスには使わない**方針です（検索キーはスカラ/文字列のみ）。
* **丸め一貫性**: インデックス安定化のため、**DB構築時**の `ndigits` に揃えて `_round_tuple` で丸めます。検索時のキーも同じ丸めに正規化されます。
* **近傍判定**: `tol` は各成分ごとの絶対差に適用します（例: `abs(a_i - b_i) ≤ tol`）。

---

必要があれば、このセクションを「目次」にも追加してください。文言や見出しのトーンは既存READMEに合わせてあります（セットアップ節やワークフロー節の記載形式に沿うよう配慮）。

## トラブルシュート

* **`load_air: file <...> does not exist`**

  * `data/` に必要なファイルが揃っているか、`load_air.m` と同階層か、パラメータ（`room`, `rir_no`, `azimuth`, `channel` など）が実在の組み合わせか確認。
* **ステレオ不足で保存されない**

  * `require_full_stereo: true` のため、L/R のどちらかが取得失敗するとスキップします。状況に応じて `false` にすると片チャンネルでも保存。
* **Aula Carolina (room=11) のみ変換されない**

  * `mic_type=3` を前提にしています。`data/` に該当ファイルがあるか確認。
* **SOFA 書き込み時の検証エラー**

  * `sofar` が要求する Conventions/Dimensions に合うよう、`IR` の次元（M=1,R=2）やサンプリング周波数が妥当かを確認。
  *  python others/inspect_air.pyでsofaファイルの中身を確認できます。
---

## 引用・ライセンス

* 元データ: RWTH Aachen University, AIR Database（Jeub et al., 2009; Jeub et al., 2010 ほか）
* 本スクリプトは研究目的の補助ツールです。元データのライセンス/クレジットに従ってください。

---

## 付記

* 角度基準の違い（AIR ↔ SOFA）はバグ源になりやすいので、**検証時は既知条件（正面/側方）で変換後の `SourcePosition` を必ず目視確認**してください。
* 受聴点・受音点の幾何（`ReceiverPosition` など）は計測セットアップに合わせて自由に書き換えられます（±0.09 m は暫定）。
