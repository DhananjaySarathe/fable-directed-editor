"""The 2026-10-10 evidence changes: SFX budget, quiet moments, reading holds in qa.py, the kit inlining evidence.js."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "kit/hf"))

from kit.audio.mix import quiet_env, thin  # noqa: E402


def test_small_cues_are_thinned_to_the_playbook_budget_but_story_and_keep_cues_stay():
    small = [{"name": "ui/ui__pop", "at": round(t, 2)} for t in np.arange(0, 60, 0.5)]        # 120 asked in a minute
    story = [{"name": "impact/impact__hit", "at": 20.1}, {"name": "whoosh/whoosh__cinematic", "at": 40.05}]
    keep = [{"name": "ui/ui__tone", "at": 30.2, "keep": True}]
    kept = thin(small + story + keep)
    n_small = sum(1 for c in kept if "ui__pop" in c["name"])
    assert 6 <= n_small <= 13                                   # EDITING.md §7: 6-12 a minute
    assert all(c in kept for c in story + keep)
    ats = sorted(c["at"] for c in kept if "ui__pop" in c["name"])
    assert min(np.diff(ats)) >= 0.8


def test_quiet_moment_takes_the_music_out_with_ramps_and_restores_it():
    g = quiet_env([{"a": 2.0, "b": 3.0, "depth": -60, "ramp": 0.35}], 5.0, sr=1000)
    assert g[1000] == pytest.approx(1.0)                        # 1 s: untouched
    assert g[2500] < 0.01                                       # inside: out
    assert 0.01 < g[1800] < 1.0                                 # ramping down before it starts
    assert g[4000] == pytest.approx(1.0)                        # back after


def test_vendor_inlines_evidence_and_the_brand():
    import vendor
    html = vendor.inline("<head><!--HF:KIT--></head>", stickman=False)
    assert "HF.focus = function" in html and "HF.scoreboard = function" in html
    assert "HF.HANDLES = HF.BRAND.end_card" in html


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_qa_treats_a_declared_reading_hold_as_a_hold(tmp_path):
    still = tmp_path / "still.mp4"                              # 1 s moving noise, 3 s of one still frame, 1 s moving noise
    noise = "nullsrc=s=320x180:r=30:d=1,geq=lum='random(1)*255':cb=128:cr=128,format=yuv420p"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", noise, "-f", "lavfi", "-i", "color=c=gray:s=320x180:r=30:d=3,format=yuv420p",
                    "-f", "lavfi", "-i", noise, "-f", "lavfi", "-i", "sine=f=440:r=48000:d=5",
                    "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]", "-map", "[v]", "-map", "3:a", "-c:v", "libx264", "-c:a", "aac", "-shortest", str(still)], check=True)
    holds = tmp_path / "holds.json"
    holds.write_text(json.dumps([{"a": 0.9, "b": 4.1, "need": 3.0, "why": "reading: test"}]))
    qa = [sys.executable, str(ROOT / "kit/qa/qa.py"), str(still)]
    subprocess.run(qa + [f"--json={tmp_path / 'a.json'}"], capture_output=True, text=True)
    subprocess.run(qa + [f"--holds={holds}", f"--json={tmp_path / 'b.json'}"], capture_output=True, text=True)
    plain, held = json.loads((tmp_path / "a.json").read_text()), json.loads((tmp_path / "b.json").read_text())
    assert any(i["id"].startswith("freeze@") for i in plain["issues"])
    assert not any(i["id"].startswith(("freeze@", "frozen-total")) for i in held["issues"])
    assert held["info"]["holds"]


def test_sound_cues_land_their_attack_or_peak_on_the_cue(tmp_path):
    """2026-10-11: a cue time is when the sound is heard. The library's check hits 100 ms into its file; the whoosh peaks
    ~1 s in. mix() shifts each file so the attack (UI, impacts) or the peak (whooshes) lands on the cue."""
    import contextlib
    import io
    from kit.audio import mix as M
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "4", "-c:a", "pcm_s16le", str(tmp_path / "vo.wav")], check=True)
    for name, at, what in [("ui/ui__modern-click-box-check__mixkit-1120", 2.0, "onset"),
                           ("whoosh/whoosh__cinematic-whoosh-fast-transition__mixkit-1492", 1.6, "peak")]:
        assert M.align_of(name) == what
        (tmp_path / "cues.json").write_text(json.dumps([{"name": name, "at": at, "gain_db": -18, "keep": True}]))
        with contextlib.redirect_stdout(io.StringIO()):
            M.mix(tmp_path, {"words": [], "talk_end": 4.0}, [], 4.0, out_name="m.wav")
        x = M.decode(tmp_path / "m.wav", ch=1)[:, 0]
        env = np.sqrt(np.convolve(x * x, np.ones(240) / 240, mode="same"))
        heard = env.argmax() / 48000 if what == "peak" else np.argmax(env > env.max() * 0.1) / 48000
        assert abs(heard - at) < 0.034                                  # within a frame at 30 fps
    assert M.align_of("riser/riser__cinematic-synth-riser__mixkit-645") == "start"   # a riser builds up from its cue


def test_vendor_inlines_the_paper_collage_kit():
    import vendor
    html = vendor.inline("<head><!--HF:KIT--></head>", stickman=False)
    assert "HF.paper = function" in html and "HF.annotate = function" in html
