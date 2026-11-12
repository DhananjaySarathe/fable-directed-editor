"""The music map (kit/audio/beats.py) and how the film mix uses it (kit/film/mix.py), on hand-made maps: no model, no audio."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from kit.film import mix as MX

CORE = Path(__file__).resolve().parents[1] / "kit/hf/core.js"


def entry(bpm=120.0, dur=120.0, steady=True, sections=((16.0, 18.0), (48.0, -9.0), (64.0, 9.5))):
    beat = 60 / bpm
    beats = [round(0.03 + i * beat, 3) for i in range(int((dur - 0.1) / beat))]
    return {"size": 1, "duration": dur, "bpm": bpm, "agree": 1.0 if steady else 0.4, "steady": steady, "beats": beats,
            "downbeats": beats[::4], "sections": [{"t": t, "rise": r} for t, r in sections], "drops": []}


EDL = {"total": 60.0, "pieces": [{"out_a": 0.0, "tag": "one"}], "words": [{"i": 7, "t": 20.0, "e": 20.4}]}


def test_start_snaps_to_the_nearest_downbeat_within_half_a_bar():
    e = entry()                                                     # downbeats 0.03, 2.03, 4.03, ...
    assert MX.snap_start(e, 4.5) == pytest.approx(4.03)
    assert MX.snap_start(e, 5.2) == pytest.approx(6.03)           # 0.83 s away: still within half a bar (1 s)
    assert MX.snap_start(entry(steady=False), 4.5) == 4.5          # an ambient track (seeds disagree): never moved


def test_drop_auto_lands_the_biggest_rise_on_the_word(monkeypatch):
    monkeypatch.setattr(MX.BT, "entry", lambda f, tracks=None: entry())
    s, how = MX.resolve({"file": "x", "drop": "auto", "at": "w7"}, 10.0, 40.0, EDL, {})
    assert s == pytest.approx(16.0 - (20.0 - 10.0))               # the +18 dB section at 16 s plays at word 7 (20 s)
    s2, _ = MX.resolve({"file": "x", "drop": "section:3", "at": "w7"}, 10.0, 40.0, EDL, {})
    assert s2 == pytest.approx(64.0 - 10.0)


def test_drop_that_cannot_fit_says_so(monkeypatch):
    monkeypatch.setattr(MX.BT, "entry", lambda f, tracks=None: entry(dur=30.0, sections=((16.0, 18.0),)))
    with pytest.raises(SystemExit):
        MX.resolve({"file": "x", "drop": "auto", "at": "w7"}, 10.0, 59.0, EDL, {})   # 49 s of bed, 30 s of track


def test_end_on_track_end_starts_on_a_downbeat_that_still_fits(monkeypatch):
    e = entry()
    monkeypatch.setattr(MX.BT, "entry", lambda f, tracks=None: e)
    s, _ = MX.resolve({"file": "x", "end_on": "track_end"}, 30.0, 60.0, EDL, {})
    assert s in e["downbeats"] and s <= e["duration"] - 30.0 and e["duration"] - 30.0 - s < 2.0


def test_findings_flag_mid_bar_entries_and_unmotivated_turns(monkeypatch):
    e = entry()
    monkeypatch.setattr(MX.BT, "entry", lambda f, tracks=None: e)
    monkeypatch.setattr(MX.BT, "load", lambda: {})

    class Fm:
        MUSIC = [{"file": "x", "a": 0.0, "b": 60.0, "start": 1.0, "snap": False}]
    M = MX.music_map(Fm, EDL)
    assert M["beds"][0]["entry_ms"] == 970                          # 1.0 vs the downbeats 0.03 / 2.03
    cues = [{"name": "impact/impact__short-bass-hit__mixkit-2299", "at": 15.2}]          # a story sound at the first turn
    ids = [f["id"] for f in MX.findings(M, cues)]
    assert "music-entry@0.0" in ids
    assert "music-turn@15.0" not in ids                              # 16 - 1 = 15.0 s in film time: motivated
    assert "music-turn@47.0" in ids                                  # the -9 dB breakdown at 47 s: nothing happens


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_hf_music_snaps_within_lip_sync_and_is_inert_without_a_map():
    js = f"""
    globalThis.window = globalThis; require({json.dumps(str(CORE))});
    const none = [HF.music.snap(10), HF.music.near(10), HF.music.turns().length];
    globalThis.__music = {{ beats: [9.95, 10.5, 11.0], downbeats: [9.95], sections: [{{ t: 10.5, rise: 9 }}, {{ t: 30, rise: 2 }}] }};
    console.log(JSON.stringify({{ none, early: HF.music.snap(10.02), late: HF.music.snap(10.47), down: HF.music.snap(10.1, {{ kind: "downbeat", early: 0.2 }}),
      turns: HF.music.turns().map((s) => s.t), near: HF.music.near(10.4, "section", 0.2) }}));
    """
    r = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert r["none"] == [10, None, 0]
    assert r["early"] == 9.95                                        # 70 ms early: inside the 100 ms window
    assert r["late"] == 10.5                                         # the beat 30 ms after: inside the 40 ms window
    assert r["down"] == 9.95 and r["turns"] == [10.5] and r["near"] == 10.5
