"""kit/reel on the v11 sound (S-M1, 2026-10-22): a single-take Reel made from V11_FROM mixes with V11_REEL through
kit/film/mix.py's planner (voice duck, gap under + 6, looping, SFX families and the Reel budget); SOUND="v10" or an
older Reel mixes exactly as before; music.json records the sound (sticky). Also precheck's report and ambition gate,
and the music map for a bed file outside the kit. Synthetic audio only."""
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from kit.audio import beats as BT
from kit.audio import mix as M
from kit.film import mix as MX
from kit.reel import build as B

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_audio_v11 import speech, wav, words  # noqa: E402

SR = M.SR
POP = "ui/ui__bubble-pop-up-alert-notification__mixkit-2357"       # a "pop" family file (kit/sfx/library.json)
OLD = 1792454400                                                   # 2026-10-20 00:00 UTC


def reel(tmp_path, music=(), sound=None, ambition=None, total=9.0, spans=((0.2, 2.5), (2.7, 5.0), (5.6, 8.0)), today=True):
    """A Reel folder (src/template.html, edl.json), its work dir (vo.wav, cues.json: four kept pops) and an R."""
    d, work = tmp_path / "reel", tmp_path / "work"
    (d / "src").mkdir(parents=True), work.mkdir()
    (d / "src/template.html").write_text("<html></html>")
    edl = {"words": words(spans), "talk_end": spans[-1][1], "total": total, "pieces": []}
    (d / "edl.json").write_text(json.dumps(edl))
    wav(work / "vo.wav", speech(spans, total))
    (work / "cues.json").write_text(json.dumps([{"name": POP, "at": t, "gain_db": -14, "keep": True} for t in (1.0, 3.0, 5.0, 7.0)]))
    if not today:
        for p in (d / "src/template.html", work / "vo.wav", d / "edl.json"):
            os.utime(p, (OLD, OLD))
    mod = SimpleNamespace(**({"SOUND": sound} if sound else {}), **({"AMBITION": ambition} if ambition is not None else {}))
    return SimpleNamespace(dir=d, work=work, mod=mod, MUSIC=list(music), W=1080, H=1920, SAMPLE=5.0)


@pytest.fixture
def lib(tmp_path, monkeypatch):
    """kit/music in tmp: one 20 s bed, no music map; the usage log in tmp."""
    music = tmp_path / "music"
    (music / "calm").mkdir(parents=True)
    wav(music / "calm/bed.wav", np.random.default_rng(4).normal(0, 0.05, (int(20 * SR), 2)))
    (music / "library.json").write_text(json.dumps([{"file": "music/calm/bed.wav", "mood": "calm", "longform": True}]))
    monkeypatch.setattr(MX, "MUSIC_DIR", music)
    monkeypatch.setattr(B, "MUSIC_DIR", music)
    monkeypatch.setattr(MX.BT, "entry", lambda f, tracks=None: None)
    monkeypatch.setattr(MX.BT, "load", lambda: {})
    monkeypatch.setattr(MX, "USAGE", tmp_path / "music_usage.json")
    monkeypatch.setattr(MX, "film_name", lambda d: Path(d).name)
    return music


def test_the_reel_sound_gate_follows_reel_py_then_music_json_then_the_day(tmp_path):
    R = reel(tmp_path)
    assert B.sound(R) == ("v11", B.sound(R)[1]) and "made on" in B.sound(R)[1]   # an untracked Reel made today
    R.mod.SOUND = "v10"
    assert B.sound(R) == ("v10", "SOUND in reel.py")
    R.mod.SOUND = "v12"
    with pytest.raises(SystemExit):
        B.sound(R)
    del R.mod.SOUND
    (R.work / "music.json").write_text(json.dumps({"sound": "v10"}))
    v, why = B.sound(R)
    assert v == "v10" and why.startswith("recorded")               # sticky: its last mix was v10
    old = reel(tmp_path / "old", today=False)
    assert B.sound(old)[0] == "v10"                                # made 2026-10-20: the v10 mix reproduces
    assert MX.made_on(B.sound_fm(old)) < MX.V11_FROM
    root = Path(__file__).resolve().parents[1]
    if (root / "films/claude-makes-claude/reel.py").exists():      # a delivered kit/reel Reel (git: 2026-10-19)
        cmc = SimpleNamespace(dir=root / "films/claude-makes-claude", work=tmp_path / "none", mod=SimpleNamespace(),
                              MUSIC=[], W=1080, H=1920)
        assert B.sound(cmc)[0] == "v10"


def test_made_on_reads_made_file_when_given(tmp_path):
    f = tmp_path / "x.html"
    f.write_text("")
    os.utime(f, (OLD, OLD))
    fm = SimpleNamespace(dir=tmp_path, reel="a", made_file=f)
    assert MX.made_on(fm) == "2026-10-20" or MX.made_on(fm) == "2026-10-19"   # (the local day of 00:00 UTC)
    assert MX.made_on(SimpleNamespace(dir=tmp_path, reel="a")) == MX.date.today().isoformat()   # no template.html there


def test_v11_reel_plan_ducks_on_the_voice_and_resolves_reel_times(tmp_path, lib):
    R = reel(tmp_path, music=[{"file": "calm/bed.wav", "a": "w2", "b": "end-1", "start": 1.0}])
    edl = B.edl_of(R)
    P = B.music_plan(R, edl, edl["total"], True)
    (bd,) = P["beds"]
    w2 = next(w["t"] for w in edl["words"] if w["i"] == 2)
    assert (bd.a, bd.b, bd.start) == pytest.approx((w2, edl["total"] - 1, 1.0))
    assert (bd.duck, bd.under, bd.gap, bd.loop) == ("voice", -12.0, -6.0, False)   # the track fits: no play list
    assert not B.music_plan(R, edl, 0.5, True)["beds"]           # a sample that ends before the bed starts has none
    assert B.music_plan(R, edl, edl["total"], False)["beds"] is None


def test_v11_reel_loops_a_track_that_runs_out(tmp_path, lib, monkeypatch):
    e = {"duration": 10.0, "bpm": 120.0, "steady": True, "downbeats": [0.5 + 2 * i for i in range(5)], "sections": [], "beats": []}
    monkeypatch.setattr(MX.BT, "entry", lambda f, tracks=None: e)
    monkeypatch.setattr(MX.LP, "pcm", lambda p: p)
    monkeypatch.setattr(MX.LP, "audible_end", lambda x: 10.0)
    monkeypatch.setattr(MX.LP, "plan", lambda f, e, s, need, end=True, shift=True:
                        {"start": s, "segments": [(s, 8.5), (2.5, 10.0)], "how": "loops 1x (8.5->2.5)"})
    R = reel(tmp_path, music=[{"file": "calm/bed.wav", "a": 0, "b": "end", "start": 0.5, "snap": False}], total=14.0,
             spans=((0.2, 6.0), (6.5, 13.5)))
    edl = B.edl_of(R)
    (bd,) = B.music_plan(R, edl, edl["total"], True)["beds"]
    assert bd.loop and bd.segments == ((0.5, 8.5), (2.5, 10.0))
    Mm = MX.music_map(B.sound_fm(R), edl, bedlist=[bd])
    assert Mm["beds"][0]["seams"] == [8.0]                       # music.json lists the seam to listen to


def test_v11_reel_mix_end_to_end_records_its_sound_and_rotates_the_pops(tmp_path, lib):
    R = reel(tmp_path, music=[{"file": "calm/bed.wav", "a": 0, "b": "end", "start": 1.0}])
    r = B.mix(R, sample=True)                                      # a sample: music_sample.json, the gate not yet recorded
    assert (R.work / "mix_sample.wav").exists() and (R.work / "music_sample.json").exists()
    assert not (R.work / "music.json").exists()
    r = B.mix(R)
    Mj = json.loads((R.work / "music.json").read_text())
    assert Mj["sound"] == "v11" and r["under_db"] == pytest.approx(-12.0, abs=2.0)
    assert Mj["mix"]["variants"] == 2                              # the pop family plays both of its files in turn
    assert B.sound(R)[1].startswith("recorded")
    assert json.loads((tmp_path / "music_usage.json").read_text()) == [{"job": "reel", "file": "music/calm/bed.wav"}]


def test_a_v10_reel_mixes_exactly_as_before(tmp_path, lib):
    R = reel(tmp_path, music=[{"file": "calm/bed.wav", "a": 0, "b": "end", "start": 1.0, "gap": -5.0}], sound="v10")
    B.mix(R)
    edl = B.edl_of(R)
    # the pre-v11 kit/reel mix: kit.audio.mix with v10 Beds and no Sound
    M.mix(R.work, edl, [M.Bed(lib / "calm/bed.wav", 0.0, edl["total"], 1.0, -5.0, -12.0, 0.3, 0.3)], edl["total"], out_name="old.wav")
    a, b = M.decode(R.work / "mix.wav"), M.decode(R.work / "old.wav")
    assert a.shape == b.shape and np.array_equal(a, b)
    Mj = json.loads((R.work / "music.json").read_text())
    assert Mj["sound"] == "v10" and Mj["mix"]["variants"] == 1 and Mj["findings"] == []


def test_precheck_report_keeps_the_verdict_the_highs_and_the_closing_line():
    med = [f"  MEDIUM text      00:{i:02d}.0-00:{i:02d}.5 (x)  a long finding about a caption that is small" for i in range(60)]
    out = "\n".join(["holds: 3 (0 declared) -> holds.json", "FAIL: hf  60 s at 5 fps in 9 s: 2 HIGH, 60 MEDIUM",
                     "  HIGH   layout    00:01.0-00:02.0 (1.00-2.00 s)  overlap", "  HIGH   error     00:00.0-00:00.0  boom"]
                    + med + ["  density: p50 2", "precheck FAIL: 2 HIGH [layout 00:01.0, error 00:00.0], 60 MEDIUM"])
    rep = B.precheck_report(out)
    lines = rep.splitlines()
    assert lines[0].startswith("FAIL: hf") and lines[1].startswith("  HIGH   layout") and lines[2].startswith("  HIGH   error")
    assert lines[-1].startswith("precheck FAIL: 2 HIGH") and len(rep) < 2600
    assert B.precheck_report("PASS: hf 9 s\nprecheck PASS: 0 HIGH, 0 MEDIUM\n") == "PASS: hf 9 s\nprecheck PASS: 0 HIGH, 0 MEDIUM"


def test_precheck_ambition_is_on_for_new_reels_and_off_for_older_ones(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["kit.reel", "x", "render"])
    assert B.ambition(reel(tmp_path / "new"))[0] is True
    on, why = B.ambition(reel(tmp_path / "old", today=False))
    assert on is False and why.startswith("made on 2026-10-")
    assert B.ambition(reel(tmp_path / "pin", ambition=True, today=False)) == (True, "AMBITION in reel.py")
    monkeypatch.setattr(sys, "argv", ["kit.reel", "x", "render", "--no-ambition"])
    assert B.ambition(reel(tmp_path / "cli")) == (False, "--no-ambition")


def test_a_bed_file_outside_the_kit_has_no_music_map(tmp_path):
    f = tmp_path / "clip.mp4"
    f.write_bytes(b"\0" * 10)
    assert BT.entry(f) is None                                     # (raised ValueError: kit/reel's mix stopped on it)
