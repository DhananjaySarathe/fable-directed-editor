"""Room-echo removal for the office takes: WPE dereverberation (nara_wpe, weighted prediction error) on the iPhone's two
mic channels, before DeepFilterNet. WPE only predicts and subtracts the room's late reflections from the past signal,
so it never invents sound (unlike a generative "enhancer"). Two channels make the prediction much better than one.

Runs in its own venv (numpy 2 + nara_wpe), not the project's:
    uv venv ~/.venvs/wpe && uv pip install --python ~/.venvs/wpe/bin/python nara-wpe soundfile numpy scipy
    ~/.venvs/wpe/bin/python dereverb.py <in.wav (stereo, 48 kHz)> <out.wav (mono)> [--taps=10 --delay=3 --iters=3]
Processed in 20 s blocks with 2 s overlaps (crossfaded), so memory stays small.
"""
import sys

import numpy as np
import soundfile as sf
from nara_wpe.utils import istft, stft
from nara_wpe.wpe import wpe


def arg(name, default):
    return type(default)(next((a.split("=", 1)[1] for a in sys.argv if a.startswith(f"--{name}=")), default))


def main():
    src, out = sys.argv[1], sys.argv[2]
    taps, delay, iters = arg("taps", 10), arg("delay", 3), arg("iters", 3)
    x, sr = sf.read(src, always_2d=True)                 # (n, ch)
    x = x.T.astype(np.float64)
    size, shift = 1024, 256
    block, ov = 20 * sr, 2 * sr
    y = np.zeros(x.shape[1])
    wsum = np.zeros(x.shape[1])
    a = 0
    while a < x.shape[1]:
        b = min(x.shape[1], a + block + ov)
        if x.shape[1] - b < ov:                           # no sliver of a last block: this one runs to the end
            b = x.shape[1]
        seg = x[:, a:b]
        Y = stft(seg, size=size, shift=shift)            # (ch, frames, bins)
        Z = wpe(Y.transpose(2, 0, 1), taps=taps, delay=delay, iterations=iters, statistics_mode="full").transpose(1, 2, 0)
        z = istft(Z, size=size, shift=shift)[:, : seg.shape[1]].mean(axis=0)
        w = np.ones(len(z))
        k = min(ov, len(z))
        if a > 0:
            w[:k] = np.linspace(0, 1, k)
        if b < x.shape[1]:
            w[-k:] = np.linspace(1, 0, k)
        y[a:a + len(z)] += z * w
        wsum[a:a + len(z)] += w
        print(f"wpe {a / sr:6.1f}-{b / sr:6.1f} s", flush=True)
        if b >= x.shape[1]:
            break
        a += block
    y /= np.maximum(wsum, 1e-6)
    sf.write(out, (y / max(1e-9, np.abs(y).max()) * 0.9).astype(np.float32), sr)
    print("->", out)


if __name__ == "__main__":
    main()
