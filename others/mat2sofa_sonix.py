# mat2sofa.py — Convert AIR subset (1 point, 2 mics) to SOFA (SingleRoomDRIR) with SOFASonix
import numpy as np
from scipy.io import loadmat
from datetime import datetime
from SOFASonix import SOFAFile
from SOFASonix import TemplateGenerator
MAT_PATH = "out/AIR_room11_dist3_az45_subset.mat"  # 必要なら変更

def as_scalar(x):
    return float(np.squeeze(x).item())

def main():
    # ==== 1) .mat 読み込み ====
    mat  = loadmat(MAT_PATH)
    IR   = mat["IR"]   
                      # (M,R,N)=(1,2,N)
    fs   = as_scalar(mat["fs"])
    az   = as_scalar(mat["angle_deg"])
    dist = as_scalar(mat["dist_m"])

    M, R, N = IR.shape
    if not (M == 1 and R == 2):
        raise ValueError(f"Expected (M,R)=(1,2), got (M,R)=({M},{R})")
    TemplateGenerator("SingleRoomDRIR", sofaConventionsVersion=0.3, version=1.0)
    # ==== 2) SOFA: SingleRoomDRIR ====
    sofa = SOFAFile("SingleRoomDRIR", sofaConventionsVersion=0.3, version=1.0)
    sofa.view()  # 概要
    # ----- Data.* （テンプレと同じ“属性名”で設定）-----
    sofa.Data_IR                 = IR                  # mRn = (M,R,N)
    sofa.Data_SamplingRate       = np.array([fs])      # I = (1,)  ※スカラー不可
    sofa.Data_SamplingRate_Units = "hertz"
    sofa.Data_Delay              = np.zeros((M, R))    # MR = (1,2)

    # ----- 座標（DRIRは Cartesian/ metre が前提）-----
    # SourcePosition: (M,3)
    rad = np.deg2rad(az)
    src_xyz = np.array([[dist*np.cos(rad), dist*np.sin(rad), 0.0]])  # (1,3)
    sofa.SourcePosition        = src_xyz


    # ReceiverPosition: (R,3,M)
    rcv_xyz = np.array([[-0.09, 0.0, 0.0],
                        [ 0.09, 0.0, 0.0]])           # (2,3)
    rcv_xyz = rcv_xyz[:, :, np.newaxis]               # -> (2,3,1)
    sofa.ReceiverPosition       = rcv_xyz

    # Listener: (M,3) & View/Up: (M,3)
    sofa.ListenerPosition       = np.array([[0.0, 0.0, 0.0]])

    sofa.ListenerView           = np.array([[1.0, 0.0, 0.0]])
    sofa.ListenerView_Type      = "cartesian"
    sofa.ListenerUp             = np.array([[0.0, 0.0, 1.0]])
    sofa.ListenerUp_Type        = "cartesian"
    sofa.ListenerView_Units      = "meter"

    # Source の向き（未定なら既定方向でOK）: (M,3)
    sofa.SourceView             = np.array([[1.0, 0.0, 0.0]])

    sofa.SourceUp               = np.array([[0.0, 0.0, 1.0]])


    # Emitter: (E,3,M) — E=1 なら (1,3,1)
    sofa.EmitterPosition        = np.zeros((1, 3, M))

    # ----- GLOBAL（テンプレの必須を網羅）-----
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sofa.GLOBAL_AuthorContact   = "uesho131@keio.jp"
    sofa.GLOBAL_Comment         = "Converted from AIR v1.4"
    sofa.GLOBAL_License         = "Research use; RIRs from AIR DB"
    sofa.GLOBAL_Organization    = "Takamichi Lab, Keio University"
    sofa.GLOBAL_RoomType        = "reverberant"
    sofa.GLOBAL_RoomDescription = "a"
    sofa.GLOBAL_DateCreated     = now
    sofa.GLOBAL_DateModified    = now
    sofa.GLOBAL_Title           = "AIR room=11 (Aula), 3 m, az=45°, binaural (DRIR)"
    sofa.GLOBAL_DatabaseName    = "Aachen Impulse Response (AIR)"
    sofa.GLOBAL_Application     = "SOFASonix"
    sofa.GLOBAL_ApplicationName = "SOFASonix (https://github.com/sofa-framework/SOFASonix)"
    sofa.GLOBAL_ApplicationVersion = "0.5"
    sofa.GLOBAL_History         = f"Created by SOFASonix {sofa.GLOBAL_ApplicationVersion} on {now}"
    sofa.GLOBAL_References      = "https://zenodo.org/record/4277115"
    sofa.GLOBAL_Source = "a"
    sofa.GLOBAL_TimeCreated     = now
    sofa.GLOBAL_TimeModified    = now
    # 任意：著者名など
    sofa.GLOBAL_Author          = "Shotaro Ueji"

    # ==== 3) 確認（フィールド一覧） ====
    # テーブルで Required/Optional とか次元が見える
    sofa.view()

    # ==== 4) validate → export ====
    # ok, report = sofa.validate()
    # print(report)
    # if not ok:
    #     raise SystemExit("Validation failed. See report above.")
    sofa.export("AIR_room11_3m_az45_DRIR")
    print("Wrote AIR_room11_3m_az45_DRIR.sofa")


if __name__ == "__main__":
    main()
