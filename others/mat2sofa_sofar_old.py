# write_srir_sofar.py — Convert AIR subset (M=1, R=2) to SOFA (SingleRoomSRIR) using sofar
import numpy as np
from scipy.io import loadmat
import sofar as sf
from datetime import datetime

MAT_PATH = "out/AIR_rirtype1_room11_head1_rirno3_az45_subset.mat"   # ← MATLABで作った中間.mat
OUT_SOFA = "AIR_room11_3m_az45_SRIR.sofa"

def as_scalar(x):
    return float(np.squeeze(x))

def get_first_key(mat, candidates, required=True, default=None):
    """mat(dict) から最初に見つかったキーを返す。required=False なら未発見時に default を返す。"""
    for k in candidates:
        if k in mat:
            return k
    if required:
        raise KeyError(f"Required key not found. Tried: {candidates}")
    return default

def strings_to_char_matrix(strings, with_M_dim=False, M=1):
    """
    ['left','right'] → (R,S) 文字配列（空白パディング）
    with_M_dim=True のときは (R,S,M)
    """
    S = max(len(s) for s in strings) if strings else 0
    arr = np.full((len(strings), S), ' ', dtype='<U1')
    for i, s in enumerate(strings):
        arr[i, :len(s)] = list(s)
    if with_M_dim:
        return arr[:, :, np.newaxis]  # (R,S,1)
    return arr

def main():
    # 1) .mat 読み込み（IR: (M,R,N)、fs、azimuth(deg)、distance(m)）
    mat = loadmat(MAT_PATH)

    IR = mat[get_first_key(mat, ["IR", "Data_IR", "h", "h_air"])]
    fs = as_scalar(mat[get_first_key(mat, ["fs", "Fs", "sampling_rate", "Data_SamplingRate"])])

    # 角度（deg）
    az_key = get_first_key(mat, ["angle_deg", "azimuth_deg", "azimuth", "theta_deg"])
    az_deg = as_scalar(mat[az_key])

    # 距離（m）
    dist_key = get_first_key(mat, ["dist_m", "distance_m", "rir_no", "r_m"])
    dist_m = as_scalar(mat[dist_key])

    M, R, N = IR.shape
    if (M, R) != (1, 2):
        raise ValueError(f"Expected (M,R)=(1,2), got {(M,R)} with N={N}")

    # 2) SRIRオブジェクト作成（ver 1.1）
    sofa = sf.Sofa("SingleRoomSRIR", version="1.0")

    # --- Data.*
    sofa.Data_IR = IR                              # (M,R,N)
    sofa.Data_SamplingRate = np.array([fs])        # I×M（I=1, M=1）として書かれる
    sofa.Data_SamplingRate_Units = "hertz"
    sofa.Data_Delay = np.zeros((M, R))             # (M,R)

    # --- Listener（MC: M×3）
    sofa.ListenerPosition = np.array([[0.0, 0.0, 0.0]])  # (1,3)
    sofa.ListenerPosition_Type  = "cartesian"
    sofa.ListenerPosition_Units = "metre"
    sofa.ListenerView = np.array([[1.0, 0.0, 0.0]])      # (M,3)
    sofa.ListenerUp   = np.array([[0.0, 0.0, 1.0]])      # (M,3)
    sofa.ListenerView_Type  = "cartesian"
    sofa.ListenerView_Units = "metre"

    # --- Receiver（RCM：R×3×M）
    # 左右マイクの位置（例：±9 cm）。実機寸法がわかれば置き換えてください。
    rcv_xyz = np.array([[-0.09, 0.0, 0.0],
                        [ 0.09, 0.0, 0.0]])              # (R,3)
    sofa.ReceiverPosition = rcv_xyz[:, :, np.newaxis]    # (R,3,M)
    # SRIR は receiver の座標表現種別の制約は緩い（離散も連続も可）
    sofa.ReceiverPosition_Type  = "cartesian"
    sofa.ReceiverPosition_Units = "metre"
    # 受波器の向き（RCM: R×3×M）
    receiver_view = np.tile(np.array([[1.0, 0.0, 0.0]]), (R, 1))[:, :, np.newaxis]
    receiver_up   = np.tile(np.array([[0.0, 0.0, 1.0]]), (R, 1))[:, :, np.newaxis]
    sofa.ReceiverView = receiver_view                  # (R,3,1)
    sofa.ReceiverUp   = receiver_up                    # (R,3,1)
    sofa.ReceiverView_Type  = "cartesian"
    sofa.ReceiverView_Units = "metre"
    # 説明（R×S 文字配列。必要に応じて R×S×M でも可）
    sofa.ReceiverDescriptions = ["left", "right"]

    # --- Source（MC: M×3）
    rad = np.deg2rad(az_deg)
    src_xyz = np.array([[dist_m*np.cos(rad), dist_m*np.sin(rad), 0.0]])  # (1,3)
    sofa.SourcePosition = src_xyz
    sofa.SourcePosition_Type  = "cartesian"
    sofa.SourcePosition_Units = "metre"
    sofa.SourceView = np.array([[1.0, 0.0, 0.0]])       # (M,3)
    sofa.SourceUp   = np.array([[0.0, 0.0, 1.0]])       # (M,3)
    sofa.SourceView_Type  = "cartesian"
    sofa.SourceView_Units = "metre"

    # --- Emitter（eCM：E×3×M；点音源 E=1）
    sofa.EmitterPosition = np.zeros((1, 3, M))
    sofa.EmitterPosition_Type  = "cartesian"
    sofa.EmitterPosition_Units = "metre"
    sofa.EmitterView = np.array([[1.0, 0.0, 0.0]])      # (E,3) or (E,3,M) でもよいが sofar 側で整形
    sofa.EmitterUp   = np.array([[0.0, 0.0, 1.0]])
    sofa.EmitterView_Type  = "cartesian"
    sofa.EmitterView_Units = "metre"

    # --- GLOBAL（必須メタ）
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sofa.GLOBAL_Title         = "AIR room=11 (Aula), 3 m, az=45°, binaural (SRIR)"
    sofa.GLOBAL_AuthorContact = "uesho131@keio.jp"
    sofa.GLOBAL_Organization  = "Takamichi Lab, Keio University"
    sofa.GLOBAL_License       = "Research use; RIRs from AIR DB"
    sofa.GLOBAL_Comment       = "Converted from AIR (Aachen Impulse Response DB)"
    sofa.GLOBAL_DatabaseName  = "Aachen Impulse Response (AIR)"
    # SRIRでは 'shoebox' or 'dae' のみが許容。実測RIRなら通常 'dae' を推奨。
    sofa.GLOBAL_RoomType      = "dae"
    sofa.GLOBAL_DateCreated   = now
    sofa.GLOBAL_DateModified  = now

    # （任意）測定日時（M依存）
    sofa.MeasurementDate = np.array([datetime.strptime(now, "%Y-%m-%d %H:%M:%S").timestamp()])

    # 3) 書き出し
    # sofa.inspect()  # 必要なら検査
    sf.write_sofa(OUT_SOFA, sofa)
    print(f"Wrote: {OUT_SOFA}")

if __name__ == "__main__":
    main()
