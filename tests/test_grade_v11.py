"""v11 picture (2026-10-22): grade hygiene (.part / .ok, passthrough, region), the 'clean' look's maths (pins, the wall
anchor, the shoulder, the skin-held key) and the zoom budget the cut writes (work/tracks.json)."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kit/look"))
import faces as FC  # noqa: E402
import ffio as FF  # noqa: E402
import scopes  # noqa: E402
import v2 as V2  # noqa: E402


def clip(path, frames=30, size="64x64", fps=30):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size={size}:rate={fps}", "-frames:v", str(frames),
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-f", "mp4", str(path)], check=True)
    return Path(path)


def decode(p, w, h):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), *FF.vf(), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3).astype(int)


# ------------------------------------------------------------------------------------------------ completeness
def test_finish_refuses_a_short_grade_and_keeps_the_part(tmp_path):
    cut = clip(tmp_path / "aroll.mp4", 30)
    out = tmp_path / "aroll_graded.mp4"
    part = clip(FF.part(out), 20)                                       # a grade that stopped 10 frames short
    with pytest.raises(SystemExit, match="20 frames graded, the source has 30"):
        FF.finish(part, out, cut, 20)
    assert not out.exists() and part.exists() and not FF.ok_path(out).exists()
    assert FF.status(cut, out) == (False, "aroll_graded.mp4 is missing (aroll_graded.mp4.part is an unfinished grade)")


def test_finish_renames_and_status_follows_the_cut(tmp_path):
    cut = clip(tmp_path / "aroll.mp4", 30)
    out = tmp_path / "aroll_graded.mp4"
    rec = FF.finish(clip(FF.part(out), 30), out, cut, 30, look=["clean"])
    assert out.exists() and not FF.part(out).exists() and rec["frames"] == rec["src_frames"] == 30
    assert FF.status(cut, out) == (True, None)
    clip(out, 24)                                                       # the graded file replaced / truncated afterwards
    ok, why = FF.status(cut, out)
    assert not ok and "changed after its grade" in why
    FF.finish(clip(FF.part(out), 30), out, cut, 30)
    time.sleep(0.01)
    clip(cut, 30)                                                       # a new cut (same length): the grade is stale
    ok, why = FF.status(cut, out)
    assert not ok and "graded from an older aroll.mp4" in why


def test_legacy_graded_file_is_counted_once(tmp_path):
    cut = clip(tmp_path / "aroll.mp4", 30)
    time.sleep(0.01)
    out = clip(tmp_path / "aroll_graded.mp4", 30)                       # a pre-v11 grade: no .ok
    assert FF.status(cut, out) == (True, None)
    assert json.loads(FF.ok_path(out).read_text())["legacy"] is True    # written, so the next look is a stat
    short = clip(tmp_path / "b_graded.mp4", 22)                         # ai-video-editor: newer, but short
    ok, why = FF.status(cut, short, write=False)
    assert not ok and why == "b_graded.mp4: 22 frames, the cut has 30" and not FF.ok_path(short).exists()


def test_settings_ignore_paths_and_normalise_numbers(tmp_path):
    plan = [{"t": 0.0, "look": "natural", "fade": 0.0}, {"t": 10.0, "look": None, "fade": 0.0}]
    pf = tmp_path / "room.looks.json"
    pf.write_text(json.dumps(plan))
    a = FF.settings(["--v2", "--look=natural", f"--track={tmp_path}/a.face.json", f"--matte={tmp_path}/m", f"--looks={pf}"], "vignette=0.0,wb_ref=white")
    b = FF.settings(["--look=natural", "--v2", "--track=/else/where.json", "--matte=/x/y", "--looks=/other/room.looks.json"], "vignette=0,wb_ref=white", plan)
    assert a == b and a["opts"]["matte"] == "on" and "track" not in a["opts"] and a["set"] == {"vignette": 0.0, "wb_ref": "white"}
    assert FF.looks_of(a) == {"natural"} and FF.looks_of(FF.settings(["--look=clean"])) == {"clean"} and FF.looks_of({}) == {"natural"}
    assert FF.settings(["--look=clean"]) != FF.settings(["--look=natural"])


def test_status_refuses_a_grade_made_with_other_settings(tmp_path):
    cut = clip(tmp_path / "aroll.mp4", 30)
    out = tmp_path / "aroll_graded.mp4"
    nat = FF.settings(["--v2", "--look=natural"], "vignette=0.0")
    FF.finish(clip(FF.part(out), 30), out, cut, 30, settings=nat)
    assert FF.status(cut, out) == (True, None)                          # no want: completeness only (as before)
    assert FF.status(cut, out, want=nat) == (True, None)
    ok, why = FF.status(cut, out, want=FF.settings(["--v2", "--look=clean"], "vignette=0.0"))
    assert not ok and "look natural -> clean" in why                    # GRADE look="clean": stale, re-grade
    ok, why = FF.status(cut, out, want=FF.settings(["--v2", "--look=natural", "--passthrough=0-1"], "vignette=0.0"))
    assert not ok and "passthrough (none) -> 0-1" in why                # kinds added (a screen recording passed through)


def test_status_compares_an_older_record_on_its_looks(tmp_path):
    cut = clip(tmp_path / "aroll.mp4", 30)
    time.sleep(0.01)
    out = clip(tmp_path / "aroll_graded.mp4", 30)                       # pre-v11: no .ok, a v2 .balance.json beside it
    Path(str(out) + ".balance.json").write_text(json.dumps([{"t0": 0, "t1": 1, "bal": {"natural": {}}}]))
    nat, cln = FF.settings(["--v2", "--look=natural", "--room=wardrobe"]), FF.settings(["--v2", "--look=clean"])
    assert FF.status(cut, out, want=nat) == (True, None)                # unchanged film: never re-graded for the upgrade
    ok, why = FF.status(cut, out, want=cln)
    assert not ok and why == "aroll_graded.mp4 was graded in natural; the grade now asks for clean: re-grade"
    Path(str(out) + ".balance.json").unlink()
    assert FF.status(cut, out, want=cln) == (True, None)                # nothing says what it was: trusted, as before


def test_ok_is_written_atomically_and_an_unreadable_one_is_recounted(tmp_path):
    cut = clip(tmp_path / "aroll.mp4", 30)
    out = tmp_path / "aroll_graded.mp4"
    FF.finish(clip(FF.part(out), 30), out, cut, 30)
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []
    FF.ok_path(out).write_text('{"frames": 30, "si')                    # a write cut off half way
    os.utime(out, (time.time() + 5, time.time() + 5))
    assert FF.status(cut, out) == (True, None)                          # counted again (30 = 30), not refused
    assert json.loads(FF.ok_path(out).read_text())["frames"] == 30      # and the record rewritten


def test_film_grade_want_follows_grade(tmp_path):
    from kit.film.grade import command, want
    Fm = _Film({"room": (3840, 2160)}, {"room": {"cam": "", "chrome": ""}})
    Fm.work, Fm.FACE_TRACK = tmp_path, "room"
    edl = {"total": 50.0, "pieces": [{"clip": 1, "kind": "cam", "out_a": 0.0}, {"clip": 1, "kind": "chrome", "out_a": 10.0}]}
    Fm.edl = lambda: edl
    Fm.GRADE = dict(look="natural")
    a = want(Fm, "room")
    args, v2set, plan = command(Fm, "room")
    assert a == FF.settings(args[2:], v2set, plan) and a["opts"]["look"] == "natural" and a["opts"]["shots"] == 10.0
    assert not (tmp_path / "room.looks.json").exists() and not (tmp_path / "room_matte").exists()   # nothing written / made
    Fm.GRADE = dict(look="clean")
    assert want(Fm, "room") != a
    Fm.GRADE = dict(look="natural", kinds={"cam": "clean", "chrome": None}, matte=True)
    b = want(Fm, "room")
    assert b["opts"]["passthrough"] == "10.000-50.000" and b["opts"]["matte"] == "on" and FF.looks_of(b) == {"clean", "natural"}
    assert not (tmp_path / "room.looks.json").exists() and not (tmp_path / "room_matte").exists()


def test_grade_py_records_what_kit_film_asks_for(tmp_path):
    """The settings grade.py writes into the .ok are the ones kit/film's want() works out from the same arguments."""
    src = clip(tmp_path / "c.mp4", 30, "160x90")
    out = tmp_path / "g.mp4"
    args = ["--v2", "--look=clean", "--room=wardrobe", "--shots=0.500"]
    env = dict(os.environ, GRADE_WORKERS="2", GRADE_PRESET="ultrafast", GRADE_V2_SET="vignette=0.0")
    r = subprocess.run([sys.executable, str(ROOT / "kit/look/grade.py"), str(src), str(out), *args], capture_output=True, text=True, env=env, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-2000:]
    assert FF.status(src, out, want=FF.settings(args, "vignette=0")) == (True, None)
    assert FF.status(src, out, want=FF.settings(args[:1] + ["--look=natural"] + args[2:], "vignette=0"))[0] is False


def test_grade_py_passthrough_mid_shot_without_shots(tmp_path):
    """A passthrough range across a shot's middle with no --shots (the direct CLI) crashed the pool (its shot had no
    balance) and left only the .part; the range edges are shot edges now."""
    src = clip(tmp_path / "c.mp4", 60, "320x180")
    out = tmp_path / "g.mp4"
    env = dict(os.environ, GRADE_WORKERS="2", GRADE_PRESET="ultrafast")
    r = subprocess.run([sys.executable, str(ROOT / "kit/look/grade.py"), str(src), str(out), "--v2", "--passthrough=0.5-1.5"],
                       capture_output=True, text=True, env=env, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-2000:]
    shots = json.loads(Path(str(out) + ".balance.json").read_text())
    assert [(s["t0"], s["t1"], s["bal"] is None) for s in shots] == [(0.0, 0.5, False), (0.5, 1.5, True), (1.5, 2.0, False)]
    a, b = decode(src, 320, 180), decode(out, 320, 180)
    d = np.abs(a - b).mean(axis=(1, 2, 3))
    assert d[15:45].max() < 2.5 and d[:15].min() > 5 and d[45:].min() > 5


def test_shot_cuts_split_at_every_range_edge():
    import grade as G                                                   # kit/look/grade.py (on the path above)
    assert G.shot_cuts(300, 30) == [0, 300]                             # frame indices: a shot is frames [f0, f1)
    assert G.shot_cuts(300, 30, ["4"], [2.0, 6.0, 0.0, 10.0, 4.0]) == [0, 60, 120, 180, 300]
    assert G.shot_cuts(300, 30, ["1.067"], [1.0667, 1.066]) == [0, 32, 300]   # three spellings of frame 32: one edge


# ------------------------------------------------------------------------------------------------ the frame grid
def test_edges_snap_to_the_frame_grid():
    """kit/film writes its frame edges to the millisecond; a frame k = 2 (mod 3) at 30 fps rounds UP past its own time
    (frame 1853 = 61.7667 s -> 61.767), and comparing i / fps against it put the stretch's first frame in the range
    before (oss-editor's chrome stretch). Ranges are frames round(a*fps) .. round(b*fps) - 1 now."""
    import grade as G
    assert G.edge_frame(61.767, 30) == 1853 and G.edge_frame(1.067, 30) == 32 and G.edge_frame(0.5, 30) == 15
    for k in range(1, 400):                                             # every frame, written as kit/film writes it
        a = float(f"{k / 30:.3f}")
        mode = G.frame_mode([(a, 20.0)], None, [], 30)
        assert mode(k - 1) == "full" and mode(k) == "pass", k
    mode = G.frame_mode([(1.067, 2.0)], [0, 0, 8, 8], [(0.1, 1.067)], 30)
    assert [i for i in range(60) if mode(i) == "pass"] == list(range(32, 60))
    assert [i for i in range(60) if mode(i) == "region"] == list(range(3, 32))
    assert G.frame_at(2.3, 30) == 69 and G.frame_at(61.77, 30) == 1853 and G.frame_at(1.0333, 30) == 30
    rows = [{"t0": 0, "t1": 61.767, "bal": None}, {"t0": 61.767, "t1": 70.0, "f0": 1853, "f1": 2100, "bal": {"natural": {}}}]
    shots = G.balance_shots(rows, 30)                                   # an older .balance.json (seconds) snaps on load
    assert [s[:2] for s in shots] == [(0, 1853), (1853, 2100)] and G.shot_of(shots, 1853)[2] == {"natural": {}}
    assert G.shot_of(shots, 1852)[2] is None and G.shot_of(shots, 5000) is shots[-1]


def test_decode_frame_is_the_frame_asked_for(tmp_path):
    """An -ss at a frame's .3f time returned the next frame for every k = 2 (mod 3); decode_frame seeks half a frame
    early and lands on it."""
    import grade as G
    src = tmp_path / "n.mp4"                                            # frame N carries luma 16 + N (lossless)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=black:s=32x32:r=30:d=3,geq=lum='16+N':cb=128:cr=128",
                    "-c:v", "libx264", "-qp", "0", "-g", "30", "-pix_fmt", "yuv420p", str(src)], check=True)
    full = decode(src, 32, 32)[:, 16, 16, 0]
    for i in (0, 1, 2, 31, 32, 33, 59, 62, 89):
        raw = G.decode_frame(src, i, 30, 32, 32)
        assert np.frombuffer(raw, np.uint8).reshape(32, 32, 3)[16, 16, 0] == full[i], i
    assert G.decode_frame(src, 90, 30, 32, 32) == b""                   # past the end


def test_grade_py_passthrough_starts_on_its_own_frame(tmp_path):
    """The review's case: --passthrough=1.067-2.000 (kit/film's .3f of a stretch starting on frame 32) passed 27 frames
    and graded frame 32 (a one-frame tone pop at the cut)."""
    src = clip(tmp_path / "c.mp4", 60, "320x180")
    out = tmp_path / "g.mp4"
    env = dict(os.environ, GRADE_WORKERS="2", GRADE_PRESET="ultrafast")
    r = subprocess.run([sys.executable, str(ROOT / "kit/look/grade.py"), str(src), str(out), "--v2", "--passthrough=1.067-2.000"],
                       capture_output=True, text=True, env=env, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-2000:]
    assert json.loads(FF.ok_path(out).read_text())["passthrough"] == 28  # frames 32 .. 59
    shots = json.loads(Path(str(out) + ".balance.json").read_text())
    assert [(s["f0"], s["f1"], s["bal"] is None) for s in shots] == [(0, 32, False), (32, 60, True)]
    d = np.abs(decode(src, 320, 180) - decode(out, 320, 180)).mean(axis=(1, 2, 3))
    assert d[32:].max() < 2.5 and d[:32].min() > 5


def test_grade_py_sheet_time_just_after_an_edge(tmp_path):
    """grade.run(oss-editor, sheet='61.77') exited 1 ('v2: no balance for the frame at 61.767s'): the sheet balanced
    the shot holding 61.77 s, then rendered frame 1853, which the time compare put in the skipped shot before it."""
    src = clip(tmp_path / "c.mp4", 60, "320x180")
    jpg = tmp_path / "sheet.jpg"
    env = dict(os.environ, GRADE_WORKERS="2", GRADE_PRESET="ultrafast")
    r = subprocess.run([sys.executable, str(ROOT / "kit/look/grade.py"), str(src), str(jpg), "--v2", "--shots=1.067", "--sheet=1.07",
                        "--sheet-looks=natural", "--stage=#FFFFFF"], capture_output=True, text=True, env=env, cwd=ROOT)
    assert r.returncode == 0, (r.stdout + r.stderr)[-2000:]
    rec = json.loads(jpg.with_suffix(".json").read_text())
    assert jpg.exists() and {x["frame"] for x in rec} == {32}
    shots = json.loads(Path(str(jpg) + ".balance.json").read_text())
    assert [(s["f0"], s["f1"], s["bal"] is None) for s in shots] == [(0, 32, True), (32, 60, False)]


def test_ok_is_written_before_the_rename(tmp_path, monkeypatch):
    """finish() used to drop the .ok, rename, then count and write the record: a build looking in between found no .ok,
    took the pre-v11 path and could write a record without settings over the grade's own."""
    cut = clip(tmp_path / "aroll.mp4", 30)
    out = tmp_path / "aroll_graded.mp4"
    old = FF.settings(["--v2", "--look=natural"])
    FF.finish(clip(FF.part(out), 30), out, cut, 30, settings=old)
    seen = []
    real_replace = Path.replace

    def spy(self, target):                                              # look at the moment of the rename
        if self == FF.part(out):
            seen.append((json.loads(FF.ok_path(out).read_text()).get("settings"), FF.status(cut, out, write=False)[0]))
        return real_replace(self, target)
    monkeypatch.setattr(Path, "replace", spy)
    new = FF.settings(["--v2", "--look=clean"])
    FF.finish(clip(FF.part(out), 30, "48x48"), out, cut, 30, settings=new)
    assert seen == [(new, False)]                                       # the new record is there; the old file reads stale
    assert FF.status(cut, out, want=new) == (True, None)


def test_legacy_record_never_replaces_a_grade_record(tmp_path, monkeypatch):
    """A build counting a pre-v11 file's frames while a grade finishes: the grade's record (with settings) stays."""
    cut = clip(tmp_path / "aroll.mp4", 30)
    time.sleep(0.01)
    out = clip(tmp_path / "aroll_graded.mp4", 30)                       # no .ok yet: status() takes the counting path
    S = FF.settings(["--v2", "--look=clean"])
    real, done = FF.frames, []

    def frames(p):                                                      # the grade finishes while status() counts
        if not done:
            done.append(1)
            FF.mark(out, cut, 30, settings=S)
        return real(p)
    monkeypatch.setattr(FF, "frames", frames)
    assert FF.status(cut, out, want=S) == (True, None)                  # judged by the grade's record
    assert json.loads(FF.ok_path(out).read_text()).get("settings") == S and "legacy" not in json.loads(FF.ok_path(out).read_text())
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


def test_grade_py_passthrough_and_region(tmp_path):
    src = clip(tmp_path / "c.mp4", 60, "320x180")
    out = tmp_path / "g.mp4"
    env = dict(os.environ, GRADE_WORKERS="2", GRADE_PRESET="ultrafast")
    r = subprocess.run([sys.executable, str(ROOT / "kit/look/grade.py"), str(src), str(out), "--v2", "--passthrough=0-0.5",
                        "--region=160,0,160,180", "--region-at=1.0-2.0"], capture_output=True, text=True, env=env, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-2000:]
    assert out.exists() and not FF.part(out).exists()
    ok = json.loads(FF.ok_path(out).read_text())
    assert ok["frames"] == ok["src_frames"] == 60 and ok["passthrough"] == 15
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer,color_primaries",
                            "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout.strip()
    assert probe == "bt709,bt709"                                       # tagged in the stream, not only the container
    a, b = decode(src, 320, 180), decode(out, 320, 180)
    d = np.abs(a - b)
    assert d[:15].mean() < 2.5                                          # passed through (one x264 generation)
    assert d[15:30].mean() > 10                                         # graded whole
    assert d[30:, :, :160].mean() < 2.5 and d[30:, :, 160:].mean() > 10   # only the region graded


# ------------------------------------------------------------------------------------------------ the clean look
def test_clean_keeps_its_identity_under_the_paper_room():
    P = V2.params("clean")                                              # no room = paper, whose "*" is warm
    assert P["split_hi"][0] == 0.0 and P["neutral_keep"] == 0.0 and P["vignette"] == 0.0
    assert P["wb_ref"] == "white" and P["room_white"] == 0.93 and P["shoulder"] == 0.92 and P["key_skin"] == 1.0
    assert P["skin_y"] == 0.60 and P["contrast"] == 1.3 and P["halation"] == 0.0 and P["grain"] == 0.004 and P["sharpen"] == 0.18
    nat = V2.params("natural")                                          # unchanged for every other look
    assert nat["split_hi"] == [0.035, 150.0] and nat["neutral_keep"] == 0.85 and nat["white"] == 2.0 and nat["key_skin"] == 0.0
    assert V2.params("natural", "wardrobe")["neutral_keep"] == 0.6 and V2.params("clean", "wardrobe")["neutral_keep"] == 0.0


def test_shoulder_is_identity_below_the_knee_and_never_clips():
    e = np.linspace(0, 1.6, 400, dtype=np.float32)
    s = V2.shoulder(e, 0.92)
    assert np.allclose(s[e <= 0.92], e[e <= 0.92])
    assert np.all(np.diff(s) >= 0) and s.max() <= 1.0 and s[np.searchsorted(e, 1.0)] < 0.985   # 1.0 = 8 % past the knee
    assert s[np.searchsorted(e, 1.05)] < 0.997                          # still a gradient where a plain clip is flat
    assert np.array_equal(V2.shoulder(e, 0.0), np.clip(e, 0, 1))


def test_key_held_to_skin_leaves_the_wall_alone():
    face = {"box": (150.0, 120.0, 100.0, 129.0)}
    P = dict(V2.params("natural"), vignette=0.0, key=0.3, fall=0.2)
    s0, _ = V2.light_field(face, 400, 400, P)
    s1, _ = V2.light_field(face, 400, 400, dict(P, key_skin=1.0), skin4=np.zeros((100, 100), np.float32))
    assert np.abs(s0).max() > 0.2 and np.abs(s1).max() < 1e-6       # no skin, no key: the wall is as shot
    s2, _ = V2.light_field(face, 400, 400, P, skin4=np.zeros((100, 100), np.float32))
    assert np.array_equal(s0, s2)                                       # key_skin 0 (every old look): unchanged


def _room(wall=(0.80, 0.81, 0.86)):
    """A 400 x 400 frame: a bluish-grey wall, a face (warm skin) and a light shirt below the chin."""
    img = np.zeros((400, 400, 3), np.float32) + np.array(wall, np.float32)
    face = {"box": (150.0, 110.0, 100.0, 129.0), "lm": [(180, 162), (220, 162), (200, 187), (184, 210), (216, 210)]}
    yy, xx = np.mgrid[0:400, 0:400]
    head = ((xx - 200) / 62.0) ** 2 + ((yy - 175) / 80.0) ** 2 < 1
    img[head] = (0.72, 0.50, 0.40)
    img[yy > 255] = (0.93, 0.93, 0.90)                                  # a light shirt: never the white anchor
    return img, face


def test_wall_mask_reads_beside_and_above_never_below_the_chin():
    img, face = _room()
    m = FC.wall_mask(img, face)
    assert m.any() and not m[255:].any()


def test_white_anchor_neutralises_the_wall_and_lands_it_on_room_white():
    img, face = _room()
    P = V2.params("clean")
    bal = V2.analyse([(img, face)], P)
    assert bal["out"]["wb_ref"] == "white" and abs(bal["out"]["wall_y"] - 0.93) < 0.006 and bal["out"]["wall_c"] < 0.002
    assert "white" in bal and P["white_range"][0] <= bal["white"] <= P["white_range"][1]
    out = V2.grade((img * 255 + 0.5).astype(np.uint8), bal, P, face, None, 0).astype(np.float32) / 255
    w = scopes.wall(out, face)
    assert abs(w["wall_y"] - 0.93) < 0.015 and w["wall_c"] < 0.004     # the frame, graded, measures what was solved
    nat = V2.analyse([(img, face)], V2.params("natural"))
    assert "white" not in nat and "wall_y" not in nat["out"]           # natural: no anchor, the same balance as before


def test_clean_qa_flags_a_wall_that_steps_at_a_cut():
    rows = [("x 1.0s", {"wall_y": 0.93, "wall_c": 0.002}), ("x 5.0s", {"wall_y": 0.90, "wall_c": 0.012})]
    lines, misses = scopes.clean_qa(rows, [(0, 3), (3, 9)])
    assert misses == 2 and "WARN" in lines[-1]                          # the cast on frame 2, and the 0.03 step


def test_clean_profile_total_counts_the_frame_table_too():
    rows = [("x 2.0s", {"skin_y": 0.664, "skin_hue": 123.0, "black": 0.02}), ("x 9.0s", {"skin_y": 0.60, "black": 0.009})]
    assert scopes.table_misses(rows, "clean") == {"skin_y": 1, "black": 1}
    assert scopes.table_misses(rows) == {"skin_y": 2, "black": 1}         # the default targets: 0.60 is hot too


# ------------------------------------------------------------------------------------------------ zoom budget
def test_vf_size_tracks_the_source_pixels_behind_a_track():
    from kit.film.cut import vf_size
    assert vf_size((3840, 2160), "crop=2160:2160:820:0,scale=1080:1080:flags=lanczos") == ((1080, 1080), (1080, 1080))
    assert vf_size((3840, 2160), "crop=576:576:3184:1504,scale=1080:1080:flags=lanczos,scale=1080:1080") == ((1080, 1080), (576, 576))
    assert vf_size((3840, 2160), "crop=2160:2160:820:0") == ((2160, 2160), (2160, 2160))
    assert vf_size((3840, 2160), "delogo=x=590:y=180:w=1230:h=64,scale=1920:-2") == ((1920, 1080), (1920, 1080))
    assert vf_size((1920, 1080), "crop=iw/2:ih:0:0") == ((960, 1080), (960, 1080))
    # quoted expressions and functions (a comma inside min() is not a filter break), rotations
    assert vf_size((3840, 2160), "crop='min(iw,ih)':'min(iw,ih)'") == ((2160, 2160), (2160, 2160))
    assert vf_size((3840, 2160), "crop=w=ih*9/16:h=ih,scale=-2:1920") == ((1080, 1920), (1080, 1920))
    assert vf_size((3840, 2160), "transpose=1,crop=1080:1920") == ((1080, 1920), (1080, 1920))
    assert vf_size((1080, 1920), "transpose=dir=1:passthrough=portrait") == ((1080, 1920), (1080, 1920))
    assert vf_size((3840, 2160), "scale=w=oh*a:h=1080") == ((1920, 1080), (1920, 1080))
    assert vf_size((3840, 2160), "scale=trunc(iw/4)*2:-2") == ((1920, 1080), (1920, 1080))
    with pytest.raises(ValueError, match="can't evaluate"):
        vf_size((3840, 2160), "crop=iw*foo:ih")                          # never assumed to be the whole frame


class _Film:
    """Just enough of FilmConfig for cut.track_info / grade.kind_args."""
    def __init__(self, track_size, tracks, W=1920, H=1080, show=None):
        self.W, self.H, self.TRACK_SHOW, self._ts = W, H, show or {}, track_size
        self.SOURCES = {1: {"tracks": tracks}}
        self.work = None

    def src(self, c):
        return {"tracks": self.SOURCES[c]["tracks"], "kind": "cam"}

    def tracks(self):
        return list(self.SOURCES[1]["tracks"])

    def track_size(self, name):
        return self._ts[name]

    def size(self, c):
        return (3840, 2160)


EDL = {"total": 40.0, "pieces": [{"clip": 1, "kind": "cam", "out_a": 0.0}, {"clip": 1, "kind": "chrome", "out_a": 30.0}]}
SELFIE, BUBBLE = "crop=2160:2160:820:0,scale=1080:1080:flags=lanczos", "crop=576:576:3184:1504,scale=1080:1080:flags=lanczos"


def test_track_info_budget_per_kind_and_native_headroom():
    from kit.film.cut import track_info
    info = track_info(_Film({"face": (1080, 1080), "room": (3840, 2160)}, {"face": {"cam": SELFIE, "chrome": BUBBLE}, "room": {"cam": ""}}), EDL)
    f = info["face"]
    assert f["render_scale"] == 2.0 and f["kinds"]["cam"]["src_w"] == 1080 and f["kinds"]["chrome"]["src_w"] == 576
    assert f["kinds"]["cam"]["sharp_px"] == 540.0 and f["kinds"]["chrome"]["sharp_px"] == 288.0 and f["src_w"] == 576
    # the contract's max_zoom (source px / shown px, never under 1): no headroom at full height on a 4K render
    assert f["kinds"]["cam"]["max_zoom"] == 1.0 and f["max_zoom"] == 1.0 and f["kinds"]["cam"]["share"] == 0.75
    # the softer allowance, offered beside it: the bubble's is the track's (its poorest kind)
    assert f["kinds"]["cam"]["soft_zoom"] == 1.12 and f["soft_zoom"] == 1.064 and f["soft"] == 0.24
    assert info["room"]["max_zoom"] == 1.0 and info["room"]["soft_zoom"] == 1.24 and info["room"]["sharp_px"] == 1080.0
    assert list(info["room"]["kinds"]) == ["cam"]                       # (the contract's example: 3840 shown 1920 wide at 4K = 1.0)
    native = track_info(_Film({"face": (2160, 2160)}, {"face": {"cam": "crop=2160:2160:820:0"}}, show={"face": 540}), EDL)["face"]
    assert native["src_w"] == 2160 and native["sharp_px"] == 1080.0 and native["max_zoom"] == 2.0   # a 540 px card: 2x
    from kit.film.cut import soft_budget, zoom_budget
    assert zoom_budget(1080, 540) == 2.0 and zoom_budget(540, 1080) == 1.0 and zoom_budget(1080, 1080) == 1.0
    assert zoom_budget(540, 460) == round(540 / 460, 3)                  # a 460 px circle of a 1080 track at 4K
    assert soft_budget(1080, 540) == 2.0 and soft_budget(540, 1080) == 1.12 and soft_budget(1080, 1080) == 1.24


class _Reel(_Film):
    """A kit/film Reel's config: its own 1080 x 1920 page, the film as parent, pieces cut from the film's tracks."""
    def __init__(self, parent, show=None):
        super().__init__(parent._ts, parent.SOURCES[1]["tracks"], W=1080, H=1920)
        self.TRACK_SHOW = show if show is not None else parent.TRACK_SHOW   # inherited unless the Reel sets its own
        self.reel, self.parent = "a", parent


def test_track_info_for_a_reel_page():
    from kit.film.cut import track_info
    film = _Film({"face": (1080, 1080)}, {"face": {"cam": SELFIE, "chrome": BUBBLE}}, show={"face": 880})
    film.edl = lambda: EDL
    reel_edl = {"total": 20.0, "tracks": {"face": [1080, 1080]},
                "pieces": [{"clip": "film", "kind": "cam", "out_a": 0.0}, {"clip": "film", "kind": "cam", "out_a": 12.0}]}
    f = track_info(_Reel(film), reel_edl)["face"]
    # rendered at its page (1.0), referenced to its own height (the film's 880 is the film page's px), cam only
    assert f["render_scale"] == 1.0 and f["ref_px"] == 1920.0 and list(f["kinds"]) == ["cam"] and f["kinds"]["cam"]["share"] == 1.0
    assert f["sharp_px"] == 1080.0 and f["max_zoom"] == 1.0 and f["soft_zoom"] == round(1 + 0.24 * 1080 / 1920, 3)
    reel_edl["pieces"].append({"clip": "film", "kind": "chrome", "out_a": 15.0})
    g = track_info(_Reel(film, show={"face": 600}), reel_edl)["face"]
    assert g["ref_px"] == 600.0 and g["kinds"]["chrome"]["sharp_px"] == 576.0 and g["max_zoom"] == 1.0   # the bubble: 576 < 600
    assert g["kinds"]["cam"]["max_zoom"] == 1.8 and g["kinds"]["chrome"]["share"] == 0.25


def test_kind_args_passthrough_region_and_looks(tmp_path):
    from kit.film.grade import kind_args
    Fm = _Film({"room": (3840, 2160)}, {"room": {"cam": "", "chrome": "", "github": ""}})
    Fm.work = tmp_path
    edl = {"total": 50.0, "pieces": [{"clip": 1, "kind": "cam", "out_a": 0.0}, {"clip": 1, "kind": "chrome", "out_a": 10.0},
                                     {"clip": 1, "kind": "github", "out_a": 30.0}, {"clip": 1, "kind": "cam", "out_a": 40.0}]}
    g = {"look": "natural", "kinds": {"cam": "clean", "chrome": None, "github": None}, "regions": {"chrome": [3184, 1504, 576, 576]}}
    args = kind_args(Fm, g, edl, "room")
    assert "--passthrough=30.000-40.000" in args
    assert "--region=3184,1504,576,576" in args and "--region-at=10.000-30.000" in args
    plan = json.loads((tmp_path / "room.looks.json").read_text())
    assert [(p["t"], p["look"]) for p in plan] == [(0.0, "clean"), (10.0, "natural"), (40.0, "clean")]
    assert kind_args(Fm, {"look": "natural"}, edl, "room") == []        # no kinds: the grade's arguments as before


def test_regions_apply_only_to_a_track_whose_frame_holds_them(tmp_path, capsys):
    from kit.film.grade import kind_args, track_regions
    Fm = _Film({"room": (3840, 2160), "face": (1080, 1080)}, {"room": {"cam": "", "chrome": ""}, "face": {"cam": SELFIE, "chrome": BUBBLE}})
    Fm.work = tmp_path
    edl = {"total": 40.0, "pieces": [{"clip": 1, "kind": "cam", "out_a": 0.0}, {"clip": 1, "kind": "chrome", "out_a": 10.0}]}
    g = {"look": "natural", "regions": {"chrome": [3184, 1504, 576, 576]}}
    assert "--region=3184,1504,576,576" in kind_args(Fm, g, edl, "room")
    assert kind_args(Fm, g, edl, "face") == [] and "outside face's 1080x1080 frame" in capsys.readouterr().out
    per = {"look": "natural", "regions": {"face": {"chrome": [0, 0, 540, 540]}}}       # {track: {kind: rect}}
    assert track_regions(Fm, per, "room") == {} and "--region=0,0,540,540" in kind_args(Fm, per, edl, "face")


def test_reel_grade_keeps_the_room_as_shot():
    from kit.reel.prep import grade_args
    R = SimpleNamespace(ROOM="woodoffice", work=Path("/w"), mod=SimpleNamespace())
    assert grade_args(R) == (["--room=asshot"], "vignette=0")           # config's default room is not an opt-in
    R.mod.ROOM = "shelf"
    assert grade_args(R) == (["--room=shelf"], "vignette=0")
    R.mod.ROOM_SET_BACK = True
    assert grade_args(R) == (["--room=woodoffice", "--matte=/w/matte"], "")


def test_reel_default_room_is_neutral_not_the_cream_studio():
    """No ROOM in reel.py: not grade.py's default 'paper' (warm highlights, 85 % of the wall's cast kept), but a
    profile that keeps his room's colour as shot: the look's own split tone, about half the cast."""
    from kit.reel.prep import grade_args
    opts, _ = grade_args(SimpleNamespace(ROOM="woodoffice", work=Path("/w"), mod=SimpleNamespace()))
    room = opts[0].split("=", 1)[1]
    for look in ("natural", "cinematic", "bright"):
        P = V2.params(look, room, True)
        assert P["split_hi"] == V2.params(look, "nosuchroom")["split_hi"] and P["neutral_keep"] <= 0.6
        assert P["vignette"] == 0.0 and P["bg_stops"] == 0.0 and P["bg_blur"] == 0.0
    assert V2.params("natural", room)["split_hi"] == V2.V2["split_hi"]
    assert V2.params("clean", room)["neutral_keep"] == 0.0               # clean pins its own over any room
    img, face = _room((0.86, 0.84, 0.78))                               # a cream-cast white wall
    walls = {}
    for rm in ("paper", room):
        P = V2.params("natural", rm, True)
        out = V2.grade((img * 255 + 0.5).astype(np.uint8), V2.analyse([(img, face)], P), P, face, None, 0)
        walls[rm] = scopes.wall(out, face)["wall_c"]
    assert walls[room] < 0.8 * walls["paper"]                           # less cream than the studio's warmth leaves


def test_hlg_tonemap_puts_reference_white_at_one():
    from kit.film.prep import TONEMAP
    assert "npl=203" in TONEMAP and "tonemap=mobius" in TONEMAP and "hable" not in TONEMAP
