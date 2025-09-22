# inspect_sofa.py
import os
import numpy as np
import sofar as sf
from scipy.io.wavfile import write as write_wav
import matplotlib.pyplot as plt

PATH = r"out_sofa\AIR_room5_stairway_3m_az0_binaural_head.sofa"  # ←確認したいSOFA

def main():
    sofa = sf.read_sofa(PATH)  # 読み込み
    ir = sofa.Data_IR          # shape: (M,R,N) 期待: (1,2,N)
    fs = float(np.squeeze(sofa.Data_SamplingRate))
    M, R, N = ir.shape
    print(f"Data_IR shape = (M,R,N) = {ir.shape}  fs = {fs:g} Hz")

    # 基本統計（chごと）
    peaks = ir.max(axis=2).squeeze(), np.abs(ir).max(axis=2).squeeze()
    rms = np.sqrt(np.mean(ir**2, axis=2)).squeeze()
    print(f"Peak (per ch)    : {np.abs(ir).max(axis=2).squeeze()}")
    print(f"RMS  (per ch)    : {rms}")
    print(f"Any nonzero?     : {bool(np.any(np.abs(ir) > 0))}")
    print(f"Length [samples] : {N}  ({N/fs:.3f} s)")

    # 可視化：先頭50 ms
    t_ms = 50
    n_show = min(N, int(fs * t_ms / 1000))
    xL = ir[0,0,:n_show]
    xR = ir[0,1,:n_show]
    tt = np.arange(n_show) / fs * 1000.0

    plt.figure()
    plt.plot(tt, xL, label="Left")
    plt.plot(tt, xR, label="Right", alpha=0.8)
    plt.xlabel("Time [ms]"); plt.ylabel("Amplitude")
    plt.title(f"IR (first {t_ms} ms)")
    plt.legend(); plt.grid(True)
    plt.tight_layout()
    plt.show()

    # 試聴用にWAVも出力（正規化し過ぎないよう -1..1 でclip）
    out_wav = os.path.splitext(os.path.basename(PATH))[0] + "_IR.wav"
    stereo = np.stack([ir[0,0,:], ir[0,1,:]], axis=1)
    # 16-bitに整形（ピーク基準で安全スケール）
    peak = np.max(np.abs(stereo)) + 1e-12
    gain = min(1.0/peak, 1.0)  # クリップしない範囲で最大化
    pcm16 = np.clip(stereo * gain, -1.0, 1.0)
    pcm16 = (pcm16 * 32767.0).astype(np.int16)
    write_wav(out_wav, int(fs), pcm16)
    print(f"Wrote WAV: {out_wav} (gain={gain:.3f})")

if __name__ == "__main__":
    main()
