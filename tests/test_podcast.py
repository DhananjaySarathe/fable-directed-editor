"""kit/podcast on synthetic data (no real podcast footage yet): speakers, trims, the edit list, the camera director, the
render path."""
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kit.podcast import camera, speakers, trims  # noqa: E402
from kit.podcast import edl as pedl  # noqa: E402


def conversation():
    """A talks 0-12 s, B 12.5-20 s, a 'haan' from A at 21 s, B again 22-40 s (a long answer)."""
    words, i = [], 0
    def say(who, a, b, n):
        nonlocal i
        for k in range(n):
            t = a + (b - a) * k / n
            words.append({"i": i, "text": f"w{i}", "start": round(t, 3), "end": round(t + (b - a) / n * 0.8, 3), "who": who}); i += 1
    say("A", 0.5, 12.0, 30); say("B", 12.5, 20.0, 20); say("A", 21.0, 21.4, 1); say("B", 22.0, 40.0, 50)
    return words


def marks_for(words, dur=41.0, rate=10):
    """Two faces (A left, B right); the speaker's mouth opens and closes, the listener's stays still."""
    M = []
    for k in range(int(dur * rate)):
        t = k / rate
        who = next((w["who"] for w in words if w["start"] - 0.1 <= t <= w["end"] + 0.1), None)
        f = lambda x, talking: {"x": x, "y": 0.3, "w": 0.12, "h": 0.2, "mouth": (0.08 + 0.06 * np.sin(t * 17)) if talking else 0.02, "pitch": 0, "yaw": 0, "eyes": 0.3}
        M.append({"t": t, "faces": [f(0.2, who == "A"), f(0.68, who == "B")]})
    return M


def test_speakers_follow_the_moving_mouth():
    W = conversation()
    M = marks_for(W)
    P = speakers.people(M, 2)
    assert [p["id"] for p in P] == ["A", "B"] and P[0]["cx"] < P[1]["cx"]
    t, act = speakers.activity(M, P)
    attr = speakers.attribute([dict(w) for w in W], t, act)
    right = sum(1 for a, w in zip(attr, W) if a["who"] == w["who"])
    assert right / len(W) > 0.95
    T = speakers.turns(attr)
    assert [x["who"] for x in T][:2] == ["A", "B"]


def test_trims_find_repeats_restarts_and_filler_runs():
    S = [{"id": 0, "start": 0, "end": 3, "text": "I think the agent should open the PR first"},
         {"id": 1, "start": 4, "end": 5, "text": "So the"},
         {"id": 2, "start": 5, "end": 8, "text": "So the agent opens it"},
         {"id": 3, "start": 20, "end": 23, "text": "I think the agent should open the PR first, right"}]
    assert any(x["kind"] == "repeat" and x["again"] == 3 for x in trims.repeats(S))
    assert any(x["kind"] == "restart" and x["sentence"] == 1 for x in trims.restarts(S))
    W = [{"i": k, "text": t, "start": k, "end": k + 0.5} for k, t in enumerate(["um", "uh", "so", "we", "ship"])]
    assert trims.fillers(W)[0]["text"] == "um uh so"


def test_edit_list_drops_cuts_and_shortens_pauses_in_quiet():
    W = conversation()
    W = [dict(w, t=w["start"], e=w["end"]) for w in W]
    env = np.full(int(45 * 100), -80.0)                       # silence everywhere except the words
    for w in W:
        env[int(w["t"] * 100):int(w["e"] * 100)] = -20.0
    P = SimpleNamespace(FPS=30, CUT=[(30, 39, "repeat")], GAP_MAX=0.6, GAP_KEEP=0.35)
    E = pedl.build(P, W, env, -44.0)
    kept = {w["i"] for w in E["words"]}
    assert not kept & set(range(30, 40)) and len(kept) == len(W) - 10
    assert E["total"] < 40.0 and E["cuts"]
    for a, b in zip(E["pieces"], E["pieces"][1:]):
        assert a["src_b"] <= b["src_a"] + 1e-6                # in order, no overlap


def test_camera_director_holds_cuts_on_speakers_and_skips_interjections():
    W = conversation()
    W = [dict(w, ot=w["start"], oe=w["end"]) for w in W]
    E = {"words": W, "cuts": [], "pieces": [{"out_a": 0, "out_b": 41.0}]}
    shots, log, stats = camera.direct(E, ["A", "B"], 41.0)
    assert shots[0]["kind"] == "wide" and shots[-1]["kind"] == "wide"
    for s in shots[:-1]:
        assert s["b"] - s["a"] >= 2.5 - 1e-6                  # min hold
    singles = [s for s in shots if s["kind"] in ("single", "tight")]
    assert any(s["who"] == "B" and abs(s["a"] - (12.5 + 0.1)) < 0.05 for s in singles)   # 3 frames after B starts
    assert not any(20.9 < s["a"] < 21.6 for s in shots)       # A's "haan" doesn't cut
    long_b = [s for s in shots if 22 <= s["a"] < 40]
    assert len(long_b) >= 2                                    # an 18 s answer is varied, not one 18 s hold


def test_crops_stay_in_frame_and_warn_on_soft_upscales():
    P = [{"id": "A", "box": {"x": 0.2, "y": 0.3, "w": 0.06, "h": 0.1}}, {"id": "B", "box": {"x": 0.7, "y": 0.3, "w": 0.06, "h": 0.1}}]
    R, warn = camera.crops(P, 1920, 1080, 1080)
    for x, y, w, h in R.values():
        assert x >= 0 and y >= 0 and x + w <= 1920 and y + h <= 1080 and abs(w / h - 16 / 9) < 0.01
    assert warn                                               # a 1080p source cropped tight is soft at 1080p


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_render_path_crops_segments_and_keeps_sync(tmp_path):
    from kit.podcast import render
    src = tmp_path / "src.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=30:duration=8", "-f", "lavfi", "-i", "sine=f=300:d=8",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(src)], check=True)
    mix = tmp_path / "mix.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=440:d=6", "-ar", "48000", str(mix)], check=True)
    P = SimpleNamespace(RES=720, FPS=30, source=src, work=tmp_path, PEOPLE={"A": "Host", "B": "Guest"})
    E = {"pieces": [{"src_a": 0.0, "src_b": 3.0, "out_a": 0.0, "out_b": 3.0}, {"src_a": 5.0, "src_b": 8.0, "out_a": 3.0, "out_b": 6.0}]}
    shots = [{"a": 0.0, "b": 2.0, "kind": "wide", "who": None}, {"a": 2.0, "b": 6.0, "kind": "single", "who": "A"}]
    rects = {("wide", None): [0, 0, 1920, 1080], ("single", "A"): [200, 100, 960, 540]}
    out, n = render.render(P, E, shots, rects, "null", mix, tmp_path / "out.mp4", workers=2)
    assert n == 3                                             # wide, single in piece 1, single in piece 2
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout)
    assert abs(d - 6.0) < 0.1


def test_sequence_plays_a_later_part_in_the_middle():
    """SEQUENCE: a part recorded later (take 2) plays between two stretches of take 1; edges stay inside each source span."""
    W = conversation()
    W = [dict(w, t=w["start"], e=w["end"]) for w in W]
    env = np.full(int(45 * 100), -80.0)
    for w in W:
        env[int(w["t"] * 100):int(w["e"] * 100)] = -20.0
    P = SimpleNamespace(FPS=30, CUT=[], GAP_MAX=0.6, GAP_KEEP=0.35, SEQUENCE=[(0, 29), (51, 100), (30, 50)])
    E = pedl.build(P, W, env, -44.0)
    order = [w["i"] for w in E["words"]]
    assert order[:30] == list(range(30)) and order[30] == 51 and order[-1] == 50
    outs = [(p["out_a"], p["out_b"]) for p in E["pieces"]]
    assert all(b > a for a, b in outs) and all(abs(outs[k][1] - outs[k + 1][0]) < 1e-6 for k in range(len(outs) - 1))


def test_single_crop_keeps_the_other_face_out():
    """People sitting close: a single slides or tightens so the other person's face isn't cut in half."""
    P = [{"id": "A", "box": {"x": 0.285, "y": 0.375, "w": 0.068, "h": 0.12}}, {"id": "B", "box": {"x": 0.596, "y": 0.389, "w": 0.076, "h": 0.134}}]
    R, _ = camera.crops(P, 3840, 2160, 2160, {"single": 0.2, "tight": 0.24})
    for who, other in (("A", "B"), ("B", "A")):
        x, y, w, h = R[("single", who)]
        o = next(p["box"] for p in P if p["id"] == other)
        ox0, ox1 = o["x"] * 3840, (o["x"] + o["w"]) * 3840
        assert ox1 <= x or ox0 >= x + w                           # the other face is fully outside the single
        assert R[("tight", who)][3] < h * 0.9                     # the tight is a visible punch-in on it
