# write_srir_sofar.py — Convert AIR subset (M=1, R=2) to SOFA (SingleRoomSRIR) using sofar
import numpy as np
from scipy.io import loadmat
import sofar as sf
from datetime import datetime

MAT_PATH = "out_intermediate\AIR_rirtype1_room11_head1_rirno3_az45_R2.mat"   # ← MATLABで作った中間.mat


def as_scalar(x):
    return float(np.squeeze(x))

_ROOM_RIRNO_TO_DIST = {
    1:  [0.5, 1.0, 1.5],                                  # booth
    2:  [1.0, 2.0, 3.0],                                  # office
    3:  [1.45, 1.7, 1.9, 2.25, 2.8],                      # meeting
    4:  [2.25, 4.0, 5.56, 7.1, 8.68, 10.2],               # lecture
    5:  [1.0, 2.0, 3.0],                                  # stairway
    # 6,7,8,9,10 は未記載のため未定義（必要になれば追記）
    11: [1.0, 2.0, 3.0, 5.0, 15.0, 20.0],                 # aula_carolina
}

# --- Title helper (room名のラベルとフォーマット) ---
_ROOM_NAMES = {
    1: "booth", 2: "office", 3: "meeting", 4: "lecture", 5: "stairway",
    6: "stairway1", 7: "stairway2", 8: "corridor", 9: "bathroom", 10: "lecture1", 11: "aula_carolina"
}

def _fmt_g(x):
    # 余計な0を付けずに短く表記（例: 3 -> "3", 3.0 -> "3", 3.50 -> "3.5", 15.0 -> "15"）
    try:
        return f"{float(x):g}"
    except Exception:
        return str(x)

def _rir_type_label(rt):
    rt = int(round(float(rt)))
    if rt == 1:
        return "binaural"
    elif rt == 2:
        return "phone"
    return f"type{rt}"
def rirno_to_distance(room_idx, rir_no):
    """room(1..11) と rir_no(1始まり) から距離[m]を返す"""
    if room_idx not in _ROOM_RIRNO_TO_DIST:
        raise ValueError(f"room={room_idx} の距離テーブルが未定義です。_ROOM_RIRNO_TO_DIST に追記してください。")
    table = _ROOM_RIRNO_TO_DIST[room_idx]
    if not (1 <= rir_no <= len(table)):
        raise ValueError(f"rir_no={rir_no} は room={room_idx} の範囲外です (1..{len(table)})")
    return float(table[rir_no - 1])

def main():
    # 1) .mat 読み込み（IR: (M,R,N)、fs、angle_deg、dist_m）
    mat  = loadmat(MAT_PATH)
    IR   = mat["IR"]                            # (M,R,N) = (1,2,N)
    fs   = as_scalar(mat["fs"])
    az   = as_scalar(mat["azimuth"])         # deg
    room_idx = int(round(as_scalar(mat["room"])))
    rir_no   = int(round(as_scalar(mat["rir_no"])))
    dist     = rirno_to_distance(room_idx, rir_no)    
    head = as_scalar(mat["head"])
    rir_type = as_scalar(mat["rir_type"])
    M, R, N = IR.shape
    assert (M, R) == (1, 2), (M, R, N)

    # 2) SRIRオブジェクト作成（現行 1.1）
    sofa = sf.Sofa("SingleRoomSRIR", version="1.0")

    # --- Data.*
    sofa.Data_IR = IR                           # m r n
    sofa.Data_SamplingRate = fs                # I（書き込み時に (1,) へ）
    sofa.Data_SamplingRate_Units = "hertz"
    sofa.Data_Delay = np.zeros((M, R))         # MR=(1,2)

    # --- Listener（MC）---
    sofa.ListenerPosition = np.array([[0.0, 0.0, 0.0]])  # (M,3)=(1,3)
    sofa.ListenerPosition_Type  = "cartesian"
    sofa.ListenerPosition_Units = "metre"
    # 向きは (3,) で簡潔に
    sofa.ListenerView = np.array([1.0, 0.0, 0.0])
    sofa.ListenerUp   = np.array([0.0, 0.0, 1.0])
    sofa.ListenerView_Type  = "cartesian"
    sofa.ListenerView_Units = "metre"

    # --- Receiver（RCM）：左右マイクを ±0.09 m と仮定（必要なら修正）---
    rcv_xyz = np.array([[-0.09, 0.0, 0.0],
                        [ 0.09, 0.0, 0.0]])            # (R,3)
    sofa.ReceiverPosition = rcv_xyz[:, :, np.newaxis]   # -> (R,3,M)=(2,3,1)
    sofa.ReceiverPosition_Type  = "cartesian"          # SRIR既定はsphericalだがcartesian可
    sofa.ReceiverPosition_Units = "metre"

    # 受波器の向き（規約では R×3×M or R×3×I）
    receiver_view = np.tile(np.array([[1.0, 0.0, 0.0]]), (R, 1))  # (R,3)
    receiver_up   = np.tile(np.array([[0.0, 0.0, 1.0]]), (R, 1))  # (R,3)
    sofa.ReceiverView = receiver_view[:, :, np.newaxis]            # (R,3,1)
    sofa.ReceiverUp   = receiver_up[:,   :, np.newaxis]            # (R,3,1)
    # ① 念のため既存の変数を削除（optional なので消せます）


    # 説明文字列（ReceiverDescriptions）：(R,S[,M]) の文字マトリクスで与える            # (2,S)
    sofa.ReceiverDescriptions = np.array(["left", "right"])  
    # --- Source（MC）---
    sofa.SourcePosition_Type  = "spherical"
    sofa.SourcePosition_Units = "degree, degree, metre"
    sofa.SourcePosition = np.array([[dist, az, 0.0]])  # (M,3)=(1,3)
    sofa.SourceView = np.array([1.0, 0.0, 0.0])
    sofa.SourceUp   = np.array([0.0, 0.0, 1.0])
    sofa.SourceView_Type  = "cartesian"
    sofa.SourceView_Units = "metre"

    # --- Emitter（点音源想定 eCM）：E=1 → (1,3,1)
    sofa.EmitterPosition = np.zeros((1, 3, M))
    sofa.EmitterPosition_Type  = "cartesian"
    sofa.EmitterPosition_Units = "metre"
    sofa.EmitterView = np.array([1.0, 0.0, 0.0])
    sofa.EmitterUp   = np.array([0.0, 0.0, 1.0])
    sofa.EmitterView_Type  = "cartesian"
    sofa.EmitterView_Units = "metre"

    # --- GLOBAL 必須メタ ---
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    room_name = _ROOM_NAMES.get(room_idx, f"room{room_idx}")
    title = f"AIR room={room_idx} ({room_name}), {_fmt_g(dist)} m, az={_fmt_g(az)}°, {_rir_type_label(rir_type)}{' +head' if int(round(head))==1 else ''} (SRIR)"
    sofa.GLOBAL_Title = title
    sofa.GLOBAL_AuthorContact = "hello"
    sofa.GLOBAL_Organization  = "hello"
    sofa.GLOBAL_License       = "Research use; RIRs from AIR DB"
    sofa.GLOBAL_Comment       = "Converted from AIR v1.4 (Aachen IR DB)"
    sofa.GLOBAL_DatabaseName  = "Aachen Impulse Response (AIR)"
    sofa.GLOBAL_RoomType      = "dae"  # or 'shoebox' 等、実態に合わせて
    sofa.GLOBAL_DateCreated   = now
    sofa.GLOBAL_DateModified  = now
    
    OUT_DIR = "out_sofa"
    import os
    os.makedirs(OUT_DIR, exist_ok=True)
    OUT_SOFA = f"{OUT_DIR}/AIR_room{room_idx}_{_fmt_g(dist)}m_az{_fmt_g(az)}_{_rir_type_label(rir_type)}.sofa"
    # 3) 任意: 簡易点検 → 書き出し
    # sofa.inspect()  # 大きいデータで遅ければ省略可
    sf.write_sofa(OUT_SOFA, sofa)
    print(f"Wrote: {OUT_SOFA}")

if __name__ == "__main__":
    main()
