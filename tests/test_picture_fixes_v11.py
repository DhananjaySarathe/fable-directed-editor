"""v11 fix pass, the picture group (2026-10-22): a kit/film Reel writes its own work/tracks.json (Pi-M1), tracks.json's
per-kind entries are the lens's contract (tracks.json[name].kinds[kind] = {sharp_px, max_zoom, soft_zoom, soft}, read
by kit/hf/motion.js MO.lensBudget exactly as cut.py computes them), kit/reel's config defaults say what prep does
(Pi-S1), and a kit/reel cut never takes a stale or partial graded take (Pi-S2)."""
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
HF = ROOT / "kit/hf"
node = pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")

# v11-sample's speaker track (films/v11-sample/film.py): ONE native 3840 x 2160 track, his whole 4K selfie ("cam") and
# Framecast's 576 x 324 bubble strip ("chrome") scaled up to it by the cut
CAM, BUBBLE = "", "crop=576:324:3184:1632"


class _Film:
    """Just enough of FilmConfig for cut.track_info and reels.cut_one."""
    FPS, SR, TRACK_CRF, FACE_TRACK, FACE = 30, 48000, 12, "face", [960.0, 540.0, 300.0]

    def __init__(self, tracks, size=(3840, 2160), track_size=(3840, 2160), W=1920, H=1080, show=None, edl=None, work=None):
        self.W, self.H, self.TRACK_SHOW, self._ts, self._size = W, H, show or {}, track_size, size
        self.SOURCES = {1: {"tracks": tracks}}
        self.reel, self.parent, self.work, self._edl = None, None, work, edl

    def src(self, c):
        return {"tracks": self.SOURCES[c]["tracks"], "kind": "cam"}

    def tracks(self):
        return list(self.SOURCES[1]["tracks"])

    def track_size(self, name):
        return self._ts

    def size(self, c):
        return self._size

    def edl(self):
        return self._edl


class _Reel:
    """A kit/film Reel's config: its own 1080 x 1920 page, the film as parent (FilmConfig._as_reel)."""
    def __init__(self, parent, work, **spec):
        self.W, self.H, self.TAIL, self.TRACK_SHOW = 1080, 1920, 0.4, parent.TRACK_SHOW
        self.START_AT, self.END_AT, self.SENTENCES = spec.get("start_at", {}), spec.get("end_at", {}), spec.get("sentences", [])
        self.reel, self.parent, self.work, self.HOLD, self.VOICE_FX = "a", parent, work, {}, []

    @property
    def edl_path(self):
        return self.work / "edl.json"


FILM_EDL = {"total": 62.0, "tracks": {"face": [3840, 2160]},
            "pieces": [{"clip": 1, "kind": "cam", "out_a": 0.0, "face": [960.0, 500.0, 300.0]},
                       {"clip": 1, "kind": "chrome", "out_a": 36.0, "face": [1700.0, 900.0, 80.0]}]}


def _v11_sample():
    return _Film({"face": {"cam": CAM, "chrome": BUBBLE}, "screen": {"chrome": "delogo=x=590:y=180:w=1230:h=64"}}, edl=FILM_EDL)


# ------------------------------------------------------------------------------------------------ the per-kind contract
def test_kinds_entries_are_self_contained():
    """Every kinds entry carries the budget fields the top level has (sharp_px, max_zoom, soft_zoom, soft), each from
    the sharp_px written; the top level is the poorest kind's; a kind a track shows black for has no entry."""
    from kit.film.cut import SOFT, soft_budget, track_info, zoom_budget
    info = track_info(_v11_sample(), FILM_EDL)
    f = info["face"]
    assert f["kinds"]["cam"]["sharp_px"] == 1080.0 and f["kinds"]["chrome"]["sharp_px"] == 162.0
    for k, e in f["kinds"].items():
        assert {"src_w", "src_h", "sharp_px", "max_zoom", "soft_zoom", "soft", "share"} <= set(e), k
        assert e["soft"] == SOFT and e["max_zoom"] == zoom_budget(e["sharp_px"], f["ref_px"])
        assert e["soft_zoom"] == soft_budget(e["sharp_px"], f["ref_px"])
    worst = f["kinds"]["chrome"]
    assert (f["sharp_px"], f["max_zoom"], f["soft_zoom"]) == (worst["sharp_px"], worst["max_zoom"], worst["soft_zoom"])
    assert list(info["screen"]["kinds"]) == ["chrome"]                  # black while the selfie plays: no "cam" entry
    json.dumps(info, allow_nan=False)                                   # plain JSON numbers (no NaN / Infinity)


@node
def test_lens_budget_reads_a_kind_entry_as_cut_py_computes_it():
    """MO.lensBudget(kinds[kind], Hc, cover, vs) == cut.py's zoom_budget / soft_budget(sharp_px, Hc) for every kind and
    shape: the numbers the engine's per-kind budget (E-M1) will cap at are the cut's. v11-sample's face track: the
    selfie in the 1680 x 945 frame card is sharp to x1.143 (1080 / 945), the bubble to x1.0 (soft 1 + 0.24 * 162 / 945),
    where the track's top level (the bubble's) would hold the selfie still."""
    from kit.film.cut import soft_budget, track_info, zoom_budget
    f = track_info(_v11_sample(), FILM_EDL)["face"]
    shapes = {"card": (1680, 945), "full": (1920, 1080), "circle": (460, 460)}
    js = (
        "const fs=require('fs'),vm=require('vm');const ctx=vm.createContext({console,Math});"
        f"vm.runInContext(fs.readFileSync({json.dumps(str(HF / 'motion.js'))},'utf8'),ctx);"
        f"const K={json.dumps(f['kinds'])},S={json.dumps(shapes)},T={json.dumps({k: v for k, v in f.items() if k != 'kinds'})},out={{}};"
        "for (const [k,e] of Object.entries(K)) for (const [s,[w,h]] of Object.entries(S)) {"
        "  const cover=Math.max(w/3840,h/2160), Hc=2160*cover;"
        "  out[k+'/'+s]={Hc, sharp: ctx.HF.motion.lensBudget(e,Hc,cover,cover).zoom, soft: ctx.HF.motion.lensBudget(e,Hc,cover,cover,'soft').zoom,"
        "    track: ctx.HF.motion.lensBudget(T,Hc,cover,cover).zoom};}"
        "process.stdout.write(JSON.stringify(out));"
    )
    r = subprocess.run(["node", "-e", js], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    for key, v in out.items():
        e = f["kinds"][key.split("/")[0]]
        assert round(v["sharp"], 3) == zoom_budget(e["sharp_px"], v["Hc"]), key
        assert round(v["soft"], 3) == soft_budget(e["sharp_px"], v["Hc"]), key
    assert round(out["cam/card"]["sharp"], 3) == 1.143 and out["cam/card"]["track"] == 1.0   # per kind vs the poorest
    assert out["chrome/card"]["sharp"] == 1.0 and round(out["chrome/card"]["soft"], 3) == round(1 + 0.24 * 162 / 945, 3)
    assert out["cam/full"]["sharp"] == 1.0 and round(out["cam/full"]["soft"], 3) == 1.24   # native 4K at full bleed


# ------------------------------------------------------------------------------------------------ Pi-M1: a Reel's tracks.json
def test_reel_save_tracks_writes_the_reels_own_budget(tmp_path, capsys):
    from kit.film.reels import save_tracks
    reel_edl = {"total": 20.0, "tracks": {"face": [3840, 2160]},
                "pieces": [{"clip": "film", "kind": "cam", "out_a": 0.0}, {"clip": "film", "kind": "chrome", "out_a": 15.0}]}
    R = _Reel(_v11_sample(), tmp_path)
    save_tracks(R, reel_edl)
    f = json.loads((tmp_path / "tracks.json").read_text())["face"]
    assert f["render_scale"] == 1.0 and f["ref_px"] == 1920.0               # its own page, rendered at its page
    assert f["kinds"]["cam"]["sharp_px"] == 2160.0 and f["kinds"]["cam"]["max_zoom"] == 1.125   # 2160 / 1920
    assert f["kinds"]["chrome"]["sharp_px"] == 324.0 and f["max_zoom"] == 1.0 and f["kinds"]["cam"]["share"] == 0.75
    assert "per kind: cam sharp 2160 px" in capsys.readouterr().out
    # can't be worked out (the film's edl is gone): the Reel is still cut, and the old file goes with a NOTE
    R.parent._edl = None
    R.parent.edl = lambda: (_ for _ in ()).throw(SystemExit("no edl.json: run cut"))
    assert save_tracks(R, reel_edl) is None and not (tmp_path / "tracks.json").exists()
    assert "NOTE: tracks.json: skipped (no edl.json: run cut)" in capsys.readouterr().out


def _lavfi(out, n, size="64x36", color="gray"):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s={size}:r=30", "-frames:v", str(n),
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(out)], check=True)


@ffmpeg
def test_cut_one_writes_the_reels_tracks_json(tmp_path, monkeypatch):
    """kit/film reels: the Reel's cut writes edl.json and, beside it, its own tracks.json (build.track_data loads it as
    D.tracks for HF.reel's lens and precheck)."""
    import kit.film.reels as RL
    fw, rw = tmp_path / "film", tmp_path / "reel"
    fw.mkdir(), rw.mkdir()
    film = _v11_sample()
    film.TRACK_CRF, film.work = 30, fw
    film.SOURCES[1]["tracks"].pop("screen")
    film._edl = dict(FILM_EDL, total=4.0, pieces=[dict(FILM_EDL["pieces"][0]), dict(FILM_EDL["pieces"][1], out_a=2.0)])
    _lavfi(fw / "face.mp4", 120)
    film.track_file = lambda name: (fw / f"{name}.mp4", None)
    film.dir = tmp_path
    R = _Reel(film, rw, sentences=[(0, 1)], start_at={0: 0.3}, end_at={1: 3.3})
    monkeypatch.setattr(RL, "FilmConfig", lambda p: R)
    words = [{"i": 0, "t": 0.5, "e": 0.9, "text": "Hello"}, {"i": 1, "t": 2.5, "e": 3.0, "text": "there."}]
    vo = np.zeros(4 * 48000, np.float32)
    RL.cut_one(film, "a", words, vo, RL.env_db(vo + 1e-4, 48000))
    edl = json.loads((rw / "edl.json").read_text())
    assert [p["kind"] for p in edl["pieces"]] == ["cam", "chrome"]
    f = json.loads((rw / "tracks.json").read_text())["face"]
    assert f["ref_px"] == 1920.0 and set(f["kinds"]) == {"cam", "chrome"} and f["kinds"]["cam"]["max_zoom"] == 1.125
    assert f["kinds"]["cam"]["share"] == round(1.7 / edl["total"], 3)


# ------------------------------------------------------------------------------------------------ Pi-S1: kit/reel config
def test_reel_config_defaults_say_what_prep_does():
    from kit.reel.config import DEFAULTS
    from kit.reel.prep import grade_args
    assert DEFAULTS["ROOM"] is None and DEFAULTS["ROOM_SET_BACK"] is False
    R = SimpleNamespace(ROOM=DEFAULTS["ROOM"], work=Path("/w"), mod=SimpleNamespace())
    assert grade_args(R) == (["--room=asshot"], "vignette=0")           # unset: his room as shot
    R.mod.ROOM_SET_BACK = True                                          # the set-back look keeps its old room, not None
    assert grade_args(R) == (["--room=woodoffice", "--matte=/w/matte"], "")
    R.ROOM = R.mod.ROOM = "shelf"
    assert grade_args(R) == (["--room=shelf", "--matte=/w/matte"], "")


# ------------------------------------------------------------------------------------------------ Pi-S2: the Reel's graded take
@ffmpeg
def test_reel_cut_takes_only_a_complete_current_grade(tmp_path, monkeypatch, capsys):
    from kit.look import ffio as FF
    from kit.reel.edl import graded_take
    from kit.reel.prep import grade_cmd
    monkeypatch.delenv("GRADE_V2_SET", raising=False)
    R = SimpleNamespace(work=tmp_path, mod=SimpleNamespace(), ROOM=None, LOOK="natural")
    take, graded = tmp_path / "take.mp4", tmp_path / "take_graded.mp4"
    with pytest.raises(SystemExit, match="missing .*take_graded.mp4: run prep"):
        graded_take(R)                                                  # prep never graded: stop, as before
    _lavfi(take, 10)
    cmd, v2 = grade_cmd(R)
    shutil.copy(take, graded)
    FF.mark(graded, take, 10, settings=FF.settings(cmd[2:], v2))
    assert graded_take(R) == graded and "NOTE" not in capsys.readouterr().out   # complete, these settings
    FF.mark(graded, take, 10, settings=FF.settings([*cmd[2:4], "--look=clean", *cmd[5:]], v2))
    assert graded_take(R) == take                                       # graded in another look: stale
    assert "graded with other settings (look clean -> natural)" in capsys.readouterr().out
    FF.ok_path(graded).unlink()
    _lavfi(graded, 6)                                                   # a grade that stopped short (no .ok, newer)
    assert graded_take(R) == take and "6 frames, the cut has 10" in capsys.readouterr().out
    graded.rename(FF.part(graded))                                      # only an unfinished .part
    assert graded_take(R) == take and "unfinished grade" in capsys.readouterr().out
