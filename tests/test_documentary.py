"""The documentary preset is opt-in only (kit/presets/documentary, 2026-10-24): a film that does not say
PRESET = "documentary" gets the pipeline exactly as before, and the documentary settings are refused on it.
(The end-to-end proof, a normal film's cut and page byte-identical before and after, was run on kit/film/example.)"""
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from kit.film import build, doc, render
from kit.film.config import FilmConfig

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_output_dirs(monkeypatch, tmp_path):
    """FilmConfig's kit.paths.Film makes output/ folders for a film inside the repo: a stand-in keeps them in tmp_path."""
    import kit.film.config as cfg
    monkeypatch.setattr(cfg, "Film", lambda p: SimpleNamespace(work=tmp_path / "work", final=tmp_path / "final", hf=tmp_path / "hf"))


def film(tmp_path, body):
    (tmp_path / "film.py").write_text("SOURCES = {1: dict(job='x', tracks={'aroll': ''})}\n" + body)
    return tmp_path


def test_a_normal_film_is_not_a_documentary(tmp_path):
    Fm = FilmConfig(film(tmp_path, "KEEP = [(0, 4, 'a')]\n"))
    assert Fm.PRESET is None and Fm.DOC == {} and not doc.on(Fm)


@pytest.mark.parametrize("body", ["DOC = dict(chapters=[dict(at=0, title='x')])\n", "KEEP = [(0, 4, 'a', {'j': 0.5})]\n"])
def test_documentary_settings_are_refused_without_the_preset(tmp_path, body):
    with pytest.raises(SystemExit, match="documentary setting"):
        FilmConfig(film(tmp_path, body))


def test_an_unknown_preset_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="PRESET"):
        FilmConfig(film(tmp_path, "PRESET = 'netflix'\n"))


def test_a_documentary_checks_its_keys(tmp_path):
    with pytest.raises(SystemExit, match="unknown keys"):
        FilmConfig(film(tmp_path, "PRESET = 'documentary'\nDOC = dict(brol=[])\n"))
    with pytest.raises(SystemExit, match="J/L"):
        FilmConfig(film(tmp_path, "PRESET = 'documentary'\nKEEP = [(0, 4, 'a', {'j': 0.5, 'l': 0.2})]\n"))
    assert doc.on(FilmConfig(film(tmp_path, "PRESET = 'documentary'\nKEEP = [(0, 4, 'a'), (5, 9, 'b', {'l': 0.4})]\n")))


def edl():
    return {"total": 10.0, "pieces": [
        dict(clip=1, tag="a", w=[0, 4], out_a=0.0, out_b=4.0, src_a=1.0, src_b=5.0, speed=1.0),
        dict(clip=1, tag="b", w=[5, 9], out_a=4.2, out_b=9.4, src_a=8.0, src_b=13.2, speed=1.0)]}


def test_jl_moves_only_a_documentary_picture(tmp_path):
    normal = FilmConfig(film(tmp_path, "KEEP = [(0, 4, 'a'), (5, 9, 'b')]\n"))
    e = edl()
    assert doc.apply_jl(normal, e) == [] and "jl" not in e and all("pic_a" not in p for p in e["pieces"])
    dfilm = FilmConfig(film(tmp_path, "PRESET = 'documentary'\nKEEP = [(0, 4, 'a'), (5, 9, 'b', {'l': 0.4})]\n"))
    e = edl()
    doc.apply_jl(dfilm, e)
    assert e["pieces"][1]["pic_a"] == pytest.approx(3.8) and e["pieces"][1]["out_a"] == 4.2   # the voice keeps its time
    assert "pic_a" not in e["pieces"][0]


def test_jl_never_starts_a_shot_before_the_one_before_it(tmp_path):
    dfilm = FilmConfig(film(tmp_path, "PRESET = 'documentary'\nKEEP = [(0, 4, 'a'), (5, 9, 'b', {'l': 9.0})]\n"))
    e = edl()
    doc.apply_jl(dfilm, e)
    assert e["pieces"][1]["pic_a"] > e["pieces"][0]["out_a"]


def test_the_page_gets_doc_js_only_when_it_calls_it():
    import sys
    sys.path.insert(0, str(ROOT / "kit/hf"))
    import vendor
    plain = vendor.inline("<head><!--HF:KIT--></head><script>HF.studio(K)</script>")
    assert "HF.doc = function" not in plain
    assert "HF.doc = function" in vendor.inline("<head><!--HF:KIT--></head><script>HF.doc(K, ROOT, {})</script>")


def test_precheck_and_qa_get_the_doc_flags_only_for_a_documentary(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(build, "run", lambda cmd, **kw: seen.append([str(c) for c in cmd]) or SimpleNamespace(returncode=0, stdout="", stderr=""))
    normal = FilmConfig(film(tmp_path, "KEEP = [(0, 4, 'a')]\n"))
    build.precheck(normal)
    assert "--doc" not in seen[-1]
    assert render.doc_black(normal, {"total": 5.0, "pieces": [], "words": []}) == []
    dfilm = FilmConfig(film(tmp_path, "PRESET = 'documentary'\nKEEP = [(0, 4, 'a')]\nDOC = dict(chapters=[dict(at=2.0, title='x', dur=2.0)])\n"))
    build.precheck(dfilm)
    assert "--doc" in seen[-1]
    assert render.doc_black(dfilm, {"total": 5.0, "pieces": [], "words": []}) == ["--allow-black=1.90-4.10"]


def test_the_doc_look_keeps_the_room_as_shot():
    import sys
    sys.path.insert(0, str(ROOT / "kit/look"))
    import looks
    v2 = looks.LOOKS["doc"]["v2"]
    assert v2["vignette"] == 0.0 and v2["bg_stops"] == 0.0 and looks.LOOKS["doc"]["light"]["vignette"] == 0.0
    assert {"vignette", "bg_stops"} <= set(looks.LOOKS["doc"]["v2_pin"])


def test_the_doc_look_tokens_live_in_doc_js_not_core():
    core = (ROOT / "kit/hf/core.js").read_text()
    assert "documentary" not in core
    out = subprocess.run(["node", "-e", f"globalThis.window=globalThis; {(ROOT / 'kit/hf/core.js').read_text()}\n"
                          f"{(ROOT / 'kit/hf/doc.js').read_text()}\nconsole.log(JSON.stringify({{dark: HF.LOOKS.documentary.dark, fn: typeof HF.doc}}))"],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == {"dark": True, "fn": "function"}


# ---- the Netflix cut's score (2026-10-25): swells, scored-music findings
def test_a_positive_quiet_window_is_a_swell_and_a_quiet_window_still_wins():
    import numpy as np
    from kit.audio.mix import SR, quiet_env
    g = quiet_env([{"a": 1.0, "b": 2.0, "depth": 6.0, "ramp": 0.1}, {"a": 1.4, "b": 1.6, "depth": -60.0, "ramp": 0.05}], 3.0)
    db = lambda t: 20 * np.log10(g[int(t * SR)] + 1e-12)        # noqa: E731
    assert abs(db(0.5)) < 1e-6 and abs(db(2.5)) < 1e-6           # outside: unchanged
    assert abs(db(1.2) - 6.0) < 1e-3                               # inside the swell: +6 dB
    assert db(1.5) < -50                                           # a quiet window inside it still takes the music out
    assert abs(quiet_env([{"a": 1.0, "b": 2.0, "depth": -20.0}], 3.0)[int(1.5 * SR)] - 0.1) < 1e-4   # a normal one: as before


def _beds(n, under=-18.0):
    return [SimpleNamespace(_m={"file": "suspense/suspense__mixkit__dark-shadows.mp3"}, a=10.0 * k, under=under) for k in range(n)]


def test_a_documentary_is_judged_as_a_score_and_a_normal_film_as_beds():
    from kit.film import mix as M
    r = {"under_db": -18.2, "lifts_per_min": 9.0}
    scored = M.v11_findings(SimpleNamespace(PRESET="documentary"), {}, _beds(5), r, [], "film")
    assert not scored                                              # 5 cues, lifts in the held beats, no longform tag: fine
    normal = {f["id"].split("@")[0] for f in M.v11_findings(SimpleNamespace(PRESET=None), {}, _beds(5), r, [], "film")}
    assert {"music-beds", "music-lifts", "music-longform"} <= normal
    loud = M.v11_findings(SimpleNamespace(PRESET="documentary"), {}, _beds(7, under=-14.0), dict(r, under_db=-14.0), [], "film")
    assert {f["id"].split("@")[0] for f in loud} >= {"music-beds", "music-loud", "music-level"}   # the level rules still hold
