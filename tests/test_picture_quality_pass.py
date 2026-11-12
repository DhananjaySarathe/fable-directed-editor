"""The picture quality pass of 2026-10-23 (films/who-gonna-hire): the selectable HLG tone map (kit/film/tonemap.py),
ZOOM_CAP in work/tracks.json (kit/film/cut.py track_info) and the trailing-comma frame count in kit/hf/render4k.py."""
import numpy as np
import pytest

from kit.film import tonemap as T


def test_eetf_identity_below_knee_and_peak_to_target():
    # BT.2390: below the knee (~95 nits for 1000 -> 203) the curve is the identity; the source peak lands on the target
    lo = np.array([0.5, 5.0, 40.0, 80.0])
    assert np.allclose(T.eetf(lo), lo, rtol=1e-6)
    assert T.eetf(np.array([1000.0]))[0] == pytest.approx(203.0, rel=1e-4)
    x = np.linspace(0, 1000, 2001)
    y = T.eetf(x)
    assert np.all(np.diff(y) >= -1e-9) and y.max() <= 203.0 + 1e-6      # monotonic, never past the target


def test_hlg_to_sdr_greys_hue_and_range():
    # HLG reference white (75 % signal, 203 nits) sits under SDR white (the roll-off leaves the highlights room) and a
    # neutral stays neutral; black stays black; everything lands in [0, 1]
    g = np.array([[0.0, 0.0, 0.0], [0.5, 0.5, 0.5], [0.75, 0.75, 0.75], [1.0, 1.0, 1.0]])
    v = T.hlg_to_sdr(g)
    assert np.allclose(v[:, 0], v[:, 1], atol=1e-6) and np.allclose(v[:, 1], v[:, 2], atol=1e-6)
    assert v[0, 0] == pytest.approx(0.0, abs=1e-6) and v[3, 0] == pytest.approx(1.0, abs=1e-4)
    assert 0.8 < v[2, 0] < 0.95 and v[1, 0] < v[2, 0]
    rng = np.random.default_rng(1).random((5000, 3))
    out = T.hlg_to_sdr(rng)
    assert out.min() >= 0 and out.max() <= 1
    c = T.hlg_to_sdr(g, contrast=0.25)                                       # the S keeps black, white and mid grey's order
    assert c[0, 0] == pytest.approx(0.0, abs=1e-6) and c[3, 0] == pytest.approx(1.0, abs=1e-4)


def test_chains_default_unchanged_and_unknown_refused():
    from kit.film import prep
    assert prep.TONEMAP == T.chain("mobius") and "tonemap=mobius" in prep.TONEMAP and "lut3d" not in prep.TONEMAP
    assert "tonemap=hable" in T.chain("hable") and "error_diffusion" in T.chain("hable")
    with pytest.raises(SystemExit, match="one of"):
        T.chain("reinhard")


def test_lut_file(tmp_path, monkeypatch):
    monkeypatch.setattr(T, "LUTS", tmp_path)
    monkeypatch.setattr(T, "LUT_N", 5)
    p = T.lut("bt2390")
    lines = p.read_text().splitlines()
    assert lines[1] == "LUT_3D_SIZE 5" and len(lines) == 2 + 125
    first, last = (list(map(float, lines[i].split())) for i in (2, -1))
    assert first == [0.0, 0.0, 0.0] and all(abs(x - 1) < 1e-4 for x in last)
    assert f"file='{p}'" in T.chain("bt2390") and "d=error_diffusion" in T.chain("bt2390")


class _Film:
    def __init__(self, W=1920, H=1080, cap=None, rs=None):
        self.W, self.H, self.TRACK_SHOW, self.ZOOM_CAP, self.RENDER_SCALE = W, H, {}, cap, rs
        self.SOURCES = {1: {"tracks": {"face": ""}}}

    def src(self, c):
        return {"tracks": self.SOURCES[c]["tracks"], "kind": "cam"}

    def tracks(self):
        return ["face"]

    def track_size(self, name):
        return (3840, 2160)

    def size(self, c):
        return (3840, 2160)


EDL = {"total": 10.0, "pieces": [{"clip": 1, "kind": "cam", "out_a": 0.0}]}


def test_zoom_cap_sets_the_budget():
    from kit.film.cut import track_info
    plain = track_info(_Film(), EDL)["face"]                          # a 4K take on a 4K render: no headroom
    assert plain["render_scale"] == 2.0 and plain["sharp_px"] == 1080.0 and plain["max_zoom"] == 1.0
    f = track_info(_Film(cap=1.3), EDL)["face"]                       # x1.3 over the full frame's cover, accepted at 4K
    assert f["render_scale"] == 2.0 and f["sharp_px"] == 1404.0 and f["max_zoom"] == 1.3 and f["soft_zoom"] == 1.3
    r = track_info(_Film(W=1080, H=1920, cap=1.3), EDL)["face"]       # a Reel's page: x1.3 over its own cover
    assert r["ref_px"] == 1920.0 and r["max_zoom"] == 1.3


def test_render4k_frames_reads_a_trailing_comma(monkeypatch):
    import subprocess
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "kit/hf"))
    import render4k
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="5826,\n", stderr=""))
    assert render4k.frames("x.mp4") == 5826
