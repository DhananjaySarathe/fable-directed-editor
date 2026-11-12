"""HLG -> SDR tone maps for prep's picture copy (kit/film/prep.py), chosen per film with TONEMAP in film.py
(2026-10-23, films/who-gonna-hire: the comparison sheet is output/temp/films/who-gonna-hire/quality/tonemap_sheet.jpg).

  "mobius"   (default, the v11 chain) zscale HLG -> display linear at npl=203, ffmpeg tonemap=mobius, zscale to BT.709,
             no dither. Linear to 0.3 of reference white (~60 nits), then every level up to the 1000-nit peak is squeezed
             into the top of the range: on a lit night scene (11 % of the who-gonna-hire take sits above HLG reference
             white) the walls, path and lamps flatten together and the sky bands
  "hable"    the same chain with tonemap=hable (peak 1000/203); bends the mid tones too
  "bt2390"   ITU-R BT.2390's EETF (the Hermite roll-off libplacebo uses), computed here into a 65^3 3D LUT from
             HLG-coded BT.2020 RGB to BT.1886-coded BT.709 RGB, then error-diffusion dither to 8 bit:
               HLG inverse OETF -> the BT.2100 OOTF at 1000 nits (gamma 1.2) -> BT.2020 -> BT.709 (out-of-gamut colours
               desaturated toward their own luminance, not clipped per channel) -> the EETF on max(R, G, B) in PQ
               (1000 nits -> 203; identity below its knee, ~95 nits, so skin and mid tones are exactly the mobius
               chain's) with the hue kept (RGB scaled by one ratio) -> / 203 -> BT.1886 (gamma 2.4, as zimg encodes
               display light)
  "bt2390c"  bt2390 plus a gentle S (+-2.4 % either side of mid grey on the coded signal): the contrast the roll-off takes out

This ffmpeg (7.1, Homebrew) has no libplacebo and no OpenCL, so tonemap=bt.2390 and peak detection are not available as
filters; the LUT is the same curve. Peak detection would not change it here: every sampled frame of the take reaches
the HLG peak (the lamps), so the static 1000-nit peak is the detected one.

    uv run python -m kit.film.tonemap bt2390            # prints the -vf chain (and writes the LUT once)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from kit.paths import CACHE

LUTS = CACHE / "luts"
LUT_N = 65
VERSION = 1

_ZIN = "zscale=tin=arib-std-b67:pin=bt2020:min=bt2020nc:t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,"
_ZOUT = ",zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
CHAINS = {
    "mobius": _ZIN + "tonemap=tonemap=mobius:desat=0" + _ZOUT,
    "hable": _ZIN + f"tonemap=tonemap=hable:desat=0:peak={1000 / 203:.4f}" + _ZOUT.replace("r=tv", "r=tv:d=error_diffusion"),
}
LUT_MAPS = {"bt2390": dict(contrast=0.0), "bt2390c": dict(contrast=0.25)}
NAMES = tuple(CHAINS) + tuple(LUT_MAPS)

# ---- the math (BT.2100 HLG and PQ, BT.2390 EETF)
_A, _B, _C = 0.17883277, 0.28466892, 0.55991073
_M1, _M2, _C1, _C2, _C3 = 2610 / 16384, 2523 / 4096 * 128, 3424 / 4096, 2413 / 4096 * 32, 2392 / 4096 * 32
_2020_TO_709 = np.array([[1.660491, -0.587641, -0.072850], [-0.124550, 1.132900, -0.008349], [-0.018151, -0.100579, 1.118730]])
_Y2020, _Y709 = np.array([0.2627, 0.6780, 0.0593]), np.array([0.2126, 0.7152, 0.0722])


def hlg_inverse_oetf(e):
    e = np.clip(e, 0, 1)
    return np.where(e <= 0.5, e * e / 3, (np.exp((e - _C) / _A) + _B) / 12)


def pq(nits):
    y = np.clip(nits / 10000, 0, 1) ** _M1
    return ((_C1 + _C2 * y) / (1 + _C3 * y)) ** _M2


def pq_inverse(e):
    p = np.clip(e, 0, 1) ** (1 / _M2)
    return 10000 * (np.maximum(p - _C1, 0) / (_C2 - _C3 * p)) ** (1 / _M1)


def eetf(nits, src_peak=1000.0, dst_peak=203.0):
    """BT.2390 EETF (black 0): source nits -> target nits, identity below the knee, a Hermite roll-off above."""
    span = pq(src_peak)
    e1 = pq(nits) / span
    mx = pq(dst_peak) / span
    ks = 1.5 * mx - 0.5
    t = np.clip((e1 - ks) / (1 - ks), 0, 1)
    p = (2 * t ** 3 - 3 * t ** 2 + 1) * ks + (t ** 3 - 2 * t ** 2 + t) * (1 - ks) + (-2 * t ** 3 + 3 * t ** 2) * mx
    return pq_inverse(np.where(e1 < ks, e1, p) * span)


def hlg_to_sdr(rgb, contrast=0.0, src_peak=1000.0, white=203.0):
    """HLG-coded BT.2020 RGB (..., 3) in [0, 1] -> BT.1886-coded BT.709 RGB in [0, 1]."""
    e = hlg_inverse_oetf(rgb)                                                   # scene light
    ys = np.maximum(e @ _Y2020, 1e-12)[..., None]
    d = src_peak * ys ** 0.2 * e                                                # OOTF (gamma 1.2 at 1000 nits): nits
    d = d @ _2020_TO_709.T
    y = np.maximum(d @ _Y709, 0)[..., None]
    lo = d.min(-1, keepdims=True)
    k = np.where(lo < 0, y / np.maximum(y - lo, 1e-12), 1.0)                    # into gamut toward its own luminance
    d = y + k * (d - y)
    m = np.maximum(d.max(-1, keepdims=True), 1e-9)
    d = d * (eetf(m, src_peak, white) / m)                                      # one ratio: the hue kept
    v = np.clip(d / white, 0, 1) ** (1 / 2.4)
    if contrast:
        v = np.clip(v + contrast * v * (1 - v) * (2 * v - 1), 0, 1)            # +-2.4 % at 0.21 / 0.79 for 0.25
    return v


def lut(name) -> Path:
    """The .cube for a LUT map (written once into output/temp/cache/luts)."""
    LUTS.mkdir(parents=True, exist_ok=True)
    out = LUTS / f"hlg_{name}_v{VERSION}_{LUT_N}.cube"
    if out.exists():
        return out
    g = np.linspace(0, 1, LUT_N)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")                              # red fastest (the .cube order)
    v = hlg_to_sdr(np.stack([r, gg, b], -1).reshape(-1, 3), **LUT_MAPS[name])
    tmp = out.with_suffix(".part")
    with open(tmp, "w") as f:
        f.write(f'TITLE "HLG BT.2020 -> SDR BT.709 ({name}, kit/film/tonemap.py v{VERSION})"\nLUT_3D_SIZE {LUT_N}\n')
        np.savetxt(f, v, fmt="%.6f")
    tmp.rename(out)
    return out


def chain(name="mobius") -> str:
    """The -vf chain from the original HLG take to SDR yuv420p (BT.709)."""
    if name in CHAINS:
        return CHAINS[name]
    if name in LUT_MAPS:
        return (f"zscale=min=bt2020nc:rin=tv:r=full,format=gbrpf32le,lut3d=file='{lut(name)}':interp=tetrahedral,"
                "zscale=tin=bt709:t=bt709:pin=bt709:p=bt709:rin=full:m=bt709:r=tv:d=error_diffusion,format=yuv420p")
    raise SystemExit(f"TONEMAP {name!r}: one of {', '.join(NAMES)}")


if __name__ == "__main__":
    print(chain(sys.argv[1] if len(sys.argv) > 1 else "mobius"))
