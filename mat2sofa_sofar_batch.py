# write_srir_batch.py
# Batch-convert AIR intermediate .mat (M=1,R=2) -> SOFA (SingleRoomSRIR) with sofar
import os, glob, argparse
import numpy as np
from datetime import datetime
from scipy.io import loadmat
import sofar as sf

# ---- helpers ---------------------------------------------------------------
def as_scalar(x): return float(np.squeeze(x))

def wrap_angle_pm180(x):
    """map degrees to [-180, 180)"""
    return ((float(x) + 180.0) % 360.0) - 180.0

_ROOM_RIRNO_TO_DIST = {
    1:  [0.5, 1.0, 1.5],             # booth
    2:  [1.0, 2.0, 3.0],             # office
    3:  [1.45, 1.7, 1.9, 2.25, 2.8], # meeting
    4:  [2.25, 4.0, 5.56, 7.1, 8.68, 10.2],  # lecture
    5:  [1.0, 2.0, 3.0],             # stairway
    11: [1.0, 2.0, 3.0, 5.0, 15.0, 20.0],    # aula_carolina
}
_ROOM_NAMES = {
    1:"booth",2:"office",3:"meeting",4:"lecture",5:"stairway",
    6:"stairway1",7:"stairway2",8:"corridor",9:"bathroom",10:"lecture1",11:"aula_carolina"
}
def fmt_g(x):
    try: return f"{float(x):g}"
    except: return str(x)

def rirno_to_distance(room_idx, rir_no):
    if room_idx not in _ROOM_RIRNO_TO_DIST:
        raise ValueError(f"room={room_idx} is not in distance table")
    table = _ROOM_RIRNO_TO_DIST[room_idx]
    if not (1 <= rir_no <= len(table)):
        raise ValueError(f"rir_no={rir_no} out of range for room={room_idx} (1..{len(table)})")
    return float(table[rir_no-1])

def rirtype_label(rt):
    rt = int(round(float(rt)))
    return "binaural" if rt==1 else ("phone" if rt==2 else f"type{rt}")

# ---- core ------------------------------------------------------------------
def convert_one(mat_path, out_dir, overwrite=False, verbose=True):
    try:
        mat = loadmat(mat_path)
        IR   = mat["IR"]     # (M,R,N)
        fs   = as_scalar(mat["fs"])
        room = int(round(as_scalar(mat["room"])))
        rir_no = int(round(as_scalar(mat["rir_no"])))
        az_air = as_scalar(mat["azimuth"])    # AIR: 0=left, 90=front, 180=right
        head = int(round(as_scalar(mat["head"])))
        rir_type = int(round(as_scalar(mat["rir_type"])))
    except Exception as e:
        if verbose: print(f"[FAIL-load] {mat_path} | {e}")
        return False

    # shape checks
    if IR.ndim != 3:
        if verbose: print(f"[SKIP] {mat_path} | IR has ndim={IR.ndim}, expected 3 (M,R,N)")
        return False
    M,R,N = IR.shape
    if (M,R) != (1,2):
        if verbose: print(f"[SKIP] {mat_path} | (M,R)=({M},{R}) expected (1,2)")
        return False

    # distance and azimuth (SOFA)
    try:
        dist = rirno_to_distance(room, rir_no)
    except Exception as e:
        if verbose: print(f"[SKIP] {mat_path} | {e}")
        return False
    az_sofa = wrap_angle_pm180(90.0 - az_air)  # AIR→SOFA

    # build SRIR
    sofa = sf.Sofa("SingleRoomSRIR", version="1.0")

    # Data.*
    sofa.Data_IR = IR
    sofa.Data_SamplingRate = fs
    sofa.Data_SamplingRate_Units = "hertz"
    sofa.Data_Delay = np.zeros((M, R))

    # Listener (M=1)
    sofa.ListenerPosition = np.array([[0.0, 0.0, 0.0]])   # (M,3)
    sofa.ListenerPosition_Type  = "cartesian"
    sofa.ListenerPosition_Units = "metre"
    sofa.ListenerView = np.array([[1.0, 0.0, 0.0]])
    sofa.ListenerUp   = np.array([[0.0, 0.0, 1.0]])
    sofa.ListenerView_Type  = "cartesian"
    sofa.ListenerView_Units = "metre"

    # Receiver (R=2) — ±0.09 m (仮)
    rcv_xyz = np.array([[-0.09, 0.0, 0.0],
                        [ 0.09, 0.0, 0.0]])   # (R,3)
    sofa.ReceiverPosition = rcv_xyz[:, :, np.newaxis]  # (R,3,M)
    sofa.ReceiverPosition_Type  = "cartesian"
    sofa.ReceiverPosition_Units = "metre"
    rv = np.tile(np.array([[1.0, 0.0, 0.0]]), (R,1))
    ru = np.tile(np.array([[0.0, 0.0, 1.0]]), (R,1))
    sofa.ReceiverView = rv[:, :, np.newaxis]
    sofa.ReceiverUp   = ru[:, :, np.newaxis]
    sofa.ReceiverDescriptions = np.array(["left", "right"])

    # Source (M=1)
    sofa.SourcePosition_Type  = "spherical"
    sofa.SourcePosition_Units = "degree, degree, metre"
    sofa.SourcePosition = np.array([[az_sofa, 0.0, dist]])  # [az, el, dist]
    sofa.SourceView = np.array([[1.0, 0.0, 0.0]])
    sofa.SourceUp   = np.array([[0.0, 0.0, 1.0]])
    sofa.SourceView_Type  = "cartesian"
    sofa.SourceView_Units = "metre"

    # Emitter (point, optional)
    sofa.EmitterPosition = np.zeros((1,3,M))
    sofa.EmitterPosition_Type  = "cartesian"
    sofa.EmitterPosition_Units = "metre"

    # GLOBAL meta
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    room_name = _ROOM_NAMES.get(room, f"room{room}")
    title = f"AIR room={room} ({room_name}), {fmt_g(dist)} m, az={fmt_g(az_sofa)}°, {rirtype_label(rir_type)}{' +head' if head==1 else ''} (SRIR)"
    sofa.GLOBAL_Title = title
    sofa.GLOBAL_AuthorContact = "ueji shotaro <uesho131@keio.jp>"
    sofa.GLOBAL_Organization  = "Takamichi-lab"
    sofa.GLOBAL_License       = "Research use; RIRs from AIR DB"
    sofa.GLOBAL_Comment       = "Converted from AIR v1.4 (Aachen IR DB)"
    sofa.GLOBAL_DatabaseName  = "Aachen Impulse Response (AIR)"
    sofa.GLOBAL_DateCreated   = now
    sofa.GLOBAL_DateModified  = now

    # write
    os.makedirs(out_dir, exist_ok=True)
    out_name = f"AIR_room{room}_{room_name}_{fmt_g(dist)}m_az{fmt_g(az_sofa)}_{rirtype_label(rir_type)}{'_head' if head==1 else ''}.sofa"
    out_path = os.path.join(out_dir, out_name)
    if (not overwrite) and os.path.exists(out_path):
        if verbose: print(f"[EXISTS] {out_name}")
        return True

    try:
        sf.write_sofa(out_path, sofa)
        if verbose: print(f"[OK] {out_name}")
        return True
    except Exception as e:
        if verbose: print(f"[FAIL-write] {out_name} | {e}")
        return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_dir",  default="out_intermediate", help="dir containing *.mat")
    ap.add_argument("--out_dir", default="out_sofa",         help="dir to write *.sofa")
    ap.add_argument("--pattern", default="*.mat",            help="glob pattern inside in_dir")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--quiet",     action="store_true")
    args = ap.parse_args()

    mats = sorted(glob.glob(os.path.join(args.in_dir, args.pattern)))
    if not mats:
        print(f"[WARN] no .mat files in: {args.in_dir}/{args.pattern}")
        return

    ok = 0
    for p in mats:
        ok += bool(convert_one(p, args.out_dir, overwrite=args.overwrite, verbose=(not args.quiet)))
    print(f"Done. {ok}/{len(mats)} files converted.")

if __name__ == "__main__":
    main()
