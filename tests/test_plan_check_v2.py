"""kit/hf/plan_check.py, visual_plan schema 2 (2026-10-22, kit v11): face / cam / groups / bg / transition per passage,
the owner's budgets (long-form face off 15-30 % in takeovers of 4-12 s, >= 3 s of face between, never away > 12 s, the
hook on his face, seated full frame <= 30 %, holds, punches, transition repeats and whips, heavy frames), the calm
long-form music rule, sides merged in the layout share, and kit/film running it before a build (kit/film/render.py)."""
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kit/hf"))
import plan_check as PC  # noqa: E402

V2 = ROOT / "kit/hf/demos/audit/visual_plan_v2.json"          # a clean long-form schema-2 plan (150 s)


def run(tmp_path, plan, edl=None):
    p = tmp_path / "visual_plan.json"
    p.write_text(json.dumps(plan))
    return PC.check(p, edl)


def v2(**changes):
    """The clean fixture with passages changed: changes = {pid: {field: value}} (None removes the field)."""
    plan = json.loads(V2.read_text())
    for p in plan["passages"]:
        for k, v in changes.get(p["id"], {}).items():
            if v is None:
                p.pop(k, None)
            else:
                p[k] = v
    return plan


def passage(pid, a, b, **kw):
    return {"id": pid, "t": [a, b], "goal": "g", "type": kw.pop("type", "emphasis"), "technique": kw.pop("technique", "ui.stamp"),
            "why": "w", "beats": [{"at": a + 0.1, "show": "x"}], **kw}


def test_the_clean_fixture_passes(tmp_path):
    errs, warns, _ = run(tmp_path, v2())
    assert errs == [] and warns == []


def test_fields_are_checked_in_any_schema(tmp_path):
    plan = {"ratio": "16:9", "total": 30, "passages": [passage("p1", 0, 10, face="gone", cam="zoom", transition="wipe", groups=0, bg="")]}
    errs, _, _ = run(tmp_path, plan)
    assert any("face 'gone'" in e for e in errs) and any("cam 'zoom'" in e for e in errs) and any("transition 'wipe'" in e for e in errs)
    assert any("groups must be" in e for e in errs) and any("bg must name" in e for e in errs)


def test_transitions_match_the_engines_kinds(tmp_path):
    # review 2026-10-22 (P-M1): 'fade' is C.takeover's default out and 'glide' a canvas camera travel; both are kinds
    # trans.js logs to window.__trans, so a plan that writes what the engine plays must pass
    assert PC.TRANSITIONS == {"cut", "whip", "glide", "zoom", "match", "card", "chapter", "fade"}
    js = (ROOT / "kit/hf/trans.js").read_text()
    kinds = json.loads(js.split("const KINDS = ", 1)[1].split(";", 1)[0])
    assert set(kinds) == PC.TRANSITIONS
    errs, _, _ = run(tmp_path, v2(p5={"transition": "fade"}, p7={"transition": "glide"}))
    assert not any("transition" in e for e in errs)


def test_a_takeovers_same_kind_in_and_out_is_one_bracket(tmp_path):
    # p11 (face off, 95-103) is entered on 'match' and p12 (his return, 103-115) on 'card': make both 'card', the
    # design's signature move there and back (HF.trans.check folds it): no repeat
    _, warns, _ = run(tmp_path, v2(p11={"transition": "card"}))
    assert not any("twice in a row" in w for w in warns)
    # ... but the same kind out of the bracket into the next passage is a repeat, named from the return
    _, warns, _ = run(tmp_path, v2(p11={"transition": "card"}, p13={"transition": "card"}))
    assert any(w.startswith("p12 -> p13: transition 'card' twice in a row") for w in warns)
    # a fade in and the default fade out: one bracket too
    _, warns, _ = run(tmp_path, v2(p9={"transition": "fade"}, p10={"transition": "fade"}))
    assert not any("twice in a row" in w for w in warns)
    # a passage with its own transition between the two ends (a takeover of two passages) leaves them as they are
    plan = v2(p11={"transition": "card"})
    plan["passages"][10]["t"] = [95, 99]
    plan["passages"].insert(11, passage("p11b", 99, 103, technique="kinetic", face="off", transition="card"))
    _, warns, _ = run(tmp_path, plan)
    assert any(w.startswith("p11 -> p11b: transition 'card' twice in a row") for w in warns)
    assert any(w.startswith("p11b -> p12: transition 'card' twice in a row") for w in warns)
    # the inner passage declaring none (entered on a cut inside the takeover) keeps the bracket
    plan["passages"][11]["transition"] = None
    plan["passages"][11].pop("transition")
    _, warns, _ = run(tmp_path, plan)
    assert not any("twice in a row" in w for w in warns)


def test_a_bracket_counts_once_in_the_whip_share(tmp_path):
    rows = [{"id": "a", "a": 0, "b": 5, "face": "on", "transition": "cut"},
            {"id": "b", "a": 5, "b": 10, "face": "off", "transition": "whip"},
            {"id": "c", "a": 10, "b": 15, "face": "on", "transition": "whip"},
            {"id": "d", "a": 15, "b": 20, "face": "on", "transition": "zoom"}]
    seq = PC.folded(rows, [{"a": 5, "b": 10, "ids": ["b"]}])
    assert [(e["id"], e["kind"], e["back"]) for e in seq] == [("a", "cut", None), ("b", "whip", "c"), ("d", "zoom", None)]
    # whips into and out of the p3 takeover (16-26 s) and the p6 one (45-53 s) are two brackets; with p10, p12 and p14
    # that is 5 whips of 13 folded transitions (38 %), not 7 of 15 (47 %)
    W, G = {"transition": "whip"}, {"transition": "glide"}
    plan = v2(p2=G, p3=W, p4=W, p6=W, p7=W, p8=G, p10=W, p12=W, p14=W)
    _, warns, _ = run(tmp_path, plan)
    assert not any(w.startswith("whips are") for w in warns) and not any("twice in a row" in w for w in warns)
    assert sum(p.get("transition") == "whip" for p in plan["passages"]) / len(plan["passages"]) > PC.WHIP_SHARE   # unfolded: 7 of 15
    # one more single whip (p10's neighbour p9 stays a chapter): 6 of 13 folded is over
    plan["passages"][0]["transition"] = "whip"
    _, warns, _ = run(tmp_path, plan)
    assert any(w.startswith("whips are 46 % of the planned transitions") for w in warns)


def test_diagram_budgets(tmp_path):
    nodes = [{"id": f"n{i}", "label": "Step", "focal": i < 3} for i in range(6)]
    edges = [{"from": f"n{i}", "to": f"n{i + 1}"} for i in range(5)] + [{"from": "n5", "to": "n0", "label": "fix everything that broke"}, ["n0", "n2"]]
    _, warns, _ = run(tmp_path, v2(p6={"diagram": {"type": "loop", "nodes": nodes, "edges": edges}}))
    assert any(w.startswith("p6: 6 nodes in one diagram (at most 5 on 16:9)") for w in warns)
    assert any(w.startswith("p6: 7 edges in one diagram (at most 6)") for w in warns)
    assert any(w.startswith("p6: 3 focal nodes (at most 2") for w in warns)
    assert any(w.startswith("p6: edge label 'fix everything that broke' is 25 characters (at most 14") for w in warns)
    # 9:16: 4 nodes at most (a column)
    reel = {"ratio": "9:16", "total": 40, "schema": 2, "passages": [passage("p1", 0, 6), passage("p2", 6, 40, technique="takeover.diagram", type="process",
            face="off", diagram={"type": "layers", "nodes": 5, "edges": 4, "focal": 1})]}
    _, warns, _ = run(tmp_path, reel)
    assert any(w.startswith("p2: 5 nodes in one diagram (at most 4 on 9:16)") for w in warns)
    # the type: a string type, a name (the developing diagram's), a typo, compare / quadrant
    errs, warns, _ = run(tmp_path, v2(p6={"diagram": "loop"}))
    assert not errs and not any("p6:" in w for w in warns)
    _, warns, _ = run(tmp_path, v2(p6={"diagram": "workflow"}))
    assert any(w.startswith("p6: a diagram with no type") for w in warns)
    _, warns, _ = run(tmp_path, v2(p6={"diagram": None}))
    assert any(w.startswith("p6: a diagram with no type") for w in warns)
    errs, _, _ = run(tmp_path, v2(p6={"diagram": {"type": "flowchart"}}))
    assert any(e.startswith("p6: diagram type 'flowchart' is not one of") for e in errs)
    _, warns, _ = run(tmp_path, v2(p6={"diagram": {"type": "compare"}}))
    assert any(w.startswith("p6: a 'compare' is not a diagram: use HF.compare") for w in warns)
    _, warns, _ = run(tmp_path, v2(p6={"diagram": "quadrant"}))
    assert any("a card with four cells" in w for w in warns)
    # schema 1: no warning for a diagram named the old way (films/oss-editor's "arch4")
    plan = {"ratio": "16:9", "total": 60, "passages": [passage("p1", 0, 30, technique="diagram", type="process", diagram="arch4", fallback="flow"),
            passage("p2", 30, 60, technique="kinetic")]}
    _, warns, _ = run(tmp_path, plan)
    assert not any("no type" in w for w in warns)


def test_no_shader_ground_on_the_white_page(tmp_path):
    _, warns, _ = run(tmp_path, v2(p7={"technique": "shaderBg", "type": "emphasis"}))
    assert any(w.startswith("p7: a shader ground or grain on the whitespace page (shaderBg)") for w in warns)
    _, warns, _ = run(tmp_path, v2(p8={"bg": "paper grain"}))
    assert any(w.startswith("p8: a shader ground or grain") for w in warns)
    plan = v2(p7={"technique": "shaderBg", "type": "emphasis"})
    plan["preset"] = "preset_canvas_studio"
    _, warns, _ = run(tmp_path, plan)
    assert not any("shader ground" in w for w in warns)


def test_a_reel_drop_is_noted_not_warned(tmp_path):
    reel = {"ratio": "9:16", "total": 50, "passages": [passage("p1", 0, 25), passage("p2", 25, 50, technique="kinetic", music="drop")]}
    notes = []
    p = tmp_path / "reel.json"
    p.write_text(json.dumps(reel))
    errs, warns, _ = PC.check(p, None, notes)
    assert not errs and not any("drop" in w for w in warns)
    assert len(notes) == 1 and notes[0].startswith("music 'drop' on p2: on a Reel the mix lands the covering bed's biggest rise there")
    out = subprocess.run([sys.executable, str(ROOT / "kit/hf/plan_check.py"), str(p)], capture_output=True, text=True)
    assert "NOTE    music 'drop' on p2" in out.stdout and out.returncode == 2       # the variety warning only: a note never counts
    # long-form: the calm-bed warning, no note
    plan = v2(p2={"music": "drop"})
    p.write_text(json.dumps(plan))
    notes = []
    _, warns, _ = PC.check(p, None, notes)
    assert notes == [] and any("long-form beds are calm" in w for w in warns)


def test_budgets_only_run_on_schema_2(tmp_path):
    # a schema-1 plan with a 20 s face-off passage: fields fine, no budget (older plans keep passing)
    plan = {"ratio": "16:9", "total": 150, "passages": [passage("p1", 0, 20, face="off"), passage("p2", 20, 150, technique="kinetic")]}
    errs, warns, _ = run(tmp_path, plan)
    assert not errs and not any("away from him" in w or "hook" in w for w in warns)
    plan["schema"] = 2
    errs, _, _ = run(tmp_path, plan)
    assert any("hook opens on his face" in e for e in errs) and any("away from him 20.0 s" in e for e in errs)


def test_the_hook_is_an_error_on_long_form_and_a_warning_on_a_reel(tmp_path):
    errs, _, _ = run(tmp_path, v2(p1={"face": "off"}))
    assert any(e.startswith("p1: face off at 0.0 s: the hook") for e in errs)
    reel = {"ratio": "9:16", "total": 40, "schema": 2, "passages": [passage("p1", 0, 6, face="off"), passage("p2", 6, 40, technique="kinetic")]}
    errs, warns, _ = run(tmp_path, reel)
    assert not any("hook" in e for e in errs) and any("the hook opens on his face" in w for w in warns)


def test_touching_takeovers_are_one_stretch_away(tmp_path):
    errs, _, _ = run(tmp_path, v2(p4={"face": "off", "cam": None}))       # p3 16-26 + p4 26-33
    assert any(e.startswith("p3+p4: away from him 17.0 s") for e in errs)


def test_takeover_length_and_face_between(tmp_path):
    # p4 shortened to 1.5 s of face, p5 a takeover up to 40 s, p5b his face again before p6's takeover
    plan = v2(p4={"t": [26, 27.5]}, p5={"t": [27.5, 38], "face": "off", "cam": None})
    plan["passages"].insert(5, passage("p5b", 38, 45, technique="kinetic", face="on", cam="pull", transition="card"))
    _, warns, _ = run(tmp_path, plan)
    assert any(w.startswith("p3 -> p5: only 1.5 s of face between two takeovers") for w in warns)
    _, warns, _ = run(tmp_path, v2(p9={"t": [72, 74.5]}, p10={"t": [74.5, 95]}))
    assert any(w.startswith("p9: a takeover of 2.5 s (4-12 s)") for w in warns)


def test_face_off_share_names_candidates(tmp_path):
    # every takeover back on: 0 % off, and the process/mechanism/proof passages of >= 5 s are proposed
    plan = v2(**{p: {"face": "on"} for p in ("p3", "p6", "p9", "p11", "p13")})
    _, warns, _ = run(tmp_path, plan)
    w = next(w for w in warns if w.startswith("face off for 0 %"))
    assert "candidates" in w and "p3 (process, 10 s)" in w and "p6 (mechanism, 8 s)" in w
    # too much: 4 more takeovers -> over 30 %
    _, warns, _ = run(tmp_path, v2(p5={"face": "off", "cam": None}))
    assert any(w.startswith("face off for 36 %") for w in warns)


def test_seated_full_frame_cap(tmp_path):
    plan = v2(p2={"face": "full"}, p5={"face": "full"}, p8={"face": "full"}, p10={"face": "full"})
    _, warns, _ = run(tmp_path, plan)
    assert any(w.startswith("seated full frame for 41 %") for w in warns)


def test_shares_count_overlapping_passages_once(tmp_path):
    # review 2026-10-22: full frame at 0-40 s and 10-50 s is 50 s of 150 (33 %), not 80 s (53 %)
    plan = {"ratio": "16:9", "total": 150, "schema": 2, "passages": [
        passage("p1", 0, 40, face="full", cam="push"), passage("p2", 10, 50, technique="kinetic", face="full", cam="pull"),
        passage("p3", 50, 150, technique="scoreboard", type="comparison", cam="arc")]}
    _, warns, _ = run(tmp_path, plan)
    assert any(w.startswith("seated full frame for 33 %") for w in warns) and not any("for 53 %" in w for w in warns)
    # the face-off share too: two takeovers over the same 6 s are 6 s off
    plan["passages"] = [passage("p1", 0, 40, cam="push"), passage("p2", 40, 46, technique="kinetic", face="off"),
                        passage("p3", 40, 46, technique="scoreboard", type="comparison", face="off"), passage("p4", 46, 150, cam="arc")]
    _, warns, _ = run(tmp_path, plan)
    assert any(w.startswith("face off for 4 %") for w in warns)
    assert PC.covered([(0, 40), (10, 50), (60, 70), (65, 66)]) == 60 and PC.covered([]) == 0


def test_camera_hold_punch_and_lens_on_a_takeover(tmp_path):
    _, warns, _ = run(tmp_path, v2(p10={"cam": "hold"}, p5={"cam": "punch"}, p3={"cam": "push"}))
    assert any(w.startswith("p10: cam 'hold' on him for 15.0 s") for w in warns)
    assert any(w.startswith("p5: a punch 7.0 s after the last one") for w in warns)       # p4 punches at 26 s, p5 at 33 s
    assert any(w.startswith("p3: cam 'push' on a takeover") for w in warns)


def test_transitions_repeat_and_whip_share(tmp_path):
    _, warns, _ = run(tmp_path, v2(p11={"transition": "zoom"}, p12={"transition": "cut"}, p13={"transition": "cut"}, p14={"transition": "zoom"},
                                   p15={"transition": "zoom"}))
    assert any(w.startswith("p14 -> p15: transition 'zoom' twice in a row") for w in warns)
    # into a takeover and out of it on the same kind is one bracket (P-M1, HF.trans.check's fold): p6 (face off) zoom,
    # p7 (his return) zoom is not a repeat
    _, warns, _ = run(tmp_path, v2(p5={"transition": "cut"}, p6={"transition": "zoom"}, p7={"transition": "zoom"}))
    assert not any("twice in a row" in w for w in warns)
    # cuts may repeat: p4 cut, p5 cut is fine
    assert not any("'cut' twice" in w for w in warns)
    whips = {p: {"transition": "whip"} for p in ("p1", "p3", "p5", "p7", "p9", "p11", "p13")}
    _, warns, _ = run(tmp_path, v2(**whips))
    # + p2, p8, p14: 10 of 15, and p13 (face off) -> p14 (his return) is one bracket: 9 of 14
    assert any(w.startswith("whips are 64 % of the planned transitions") for w in warns)


def test_transition_repeats_are_between_neighbouring_passages(tmp_path):
    # review 2026-10-22: whip, (none), whip is not "twice in a row": a passage with no transition is entered on a cut
    _, warns, _ = run(tmp_path, v2(p3={"transition": None}, p4={"transition": "whip"}))   # p2 whip, p3 none, p4 whip
    assert not any("twice in a row" in w for w in warns)
    _, warns, _ = run(tmp_path, v2(p3={"transition": "whip"}))                          # p2 whip, p3 whip: neighbours
    assert any(w.startswith("p2 -> p3: transition 'whip' twice in a row") for w in warns)


def test_a_bad_groups_value_is_an_error_not_a_crash(tmp_path):
    # review 2026-10-22: groups "4" crashed budgets() (str > int) before fields()' ERROR could be printed
    errs, warns, _ = run(tmp_path, v2(p8={"groups": "4"}, p9={"groups": True}))
    assert any(e.startswith("p8: groups must be a whole number") for e in errs) and any(e.startswith("p9: groups must be") for e in errs)
    assert not any("heavy" in w for w in warns)                             # judged at the default (3)
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(v2(p8={"groups": "4"})))
    out = subprocess.run([sys.executable, str(ROOT / "kit/hf/plan_check.py"), str(p)], capture_output=True, text=True)
    assert out.returncode == 3 and "Traceback" not in out.stderr and "ERROR   p8: groups must be" in out.stdout


def test_cache_key_with_passages_that_have_no_fallback(tmp_path):
    # review 2026-10-22 (from before v11): --key crashed when a passage had no fallback (None sorted among names)
    out = subprocess.run([sys.executable, str(ROOT / "kit/hf/plan_check.py"), str(V2), "--key"], capture_output=True, text=True)
    assert out.returncode == 0 and "Traceback" not in out.stderr
    key = out.stdout.strip().splitlines()[-1]
    assert key.startswith("cache key: ") and len(key.split(": ")[1]) == 16
    assert PC.cache_key(json.loads(V2.read_text())) == key.split(": ")[1]


def test_heavy_frames_unless_declared_dense(tmp_path):
    _, warns, _ = run(tmp_path, v2(p8={"groups": 5}))
    assert any(w.startswith("p8: heavy: 5 visual groups") for w in warns)
    _, warns, _ = run(tmp_path, v2(p8={"groups": 5, "dense": "the pile-up is the point"}))
    assert not any("heavy" in w for w in warns)


def test_long_form_music_is_calm_and_reels_keep_the_moment_rule(tmp_path):
    _, warns, _ = run(tmp_path, v2(p2={"music": "drop"}, p8={"music": "riser"}))
    assert any("long-form beds are calm" in w and "p2 (drop)" in w and "p8 (riser)" in w for w in warns)
    assert not any("no passage plans a music moment" in w for w in warns)
    reel = {"ratio": "9:16", "total": 50, "passages": [passage("p1", 0, 25), passage("p2", 25, 50, technique="kinetic")]}
    _, warns, _ = run(tmp_path, reel)
    assert any("no passage plans a music moment" in w for w in warns)


def test_layout_sides_merge(tmp_path):
    plan = {"ratio": "16:9", "total": 100, "passages": [
        passage("p1", 0, 20, box={"show": "beside", "side": "left"}), passage("p2", 20, 40, technique="kinetic", box={"show": "beside", "side": "right"}),
        passage("p3", 40, 100, technique="scoreboard", type="comparison", box={"show": "graphic"})]}
    _, warns, _ = run(tmp_path, plan)
    assert any("the box is 'beside' for 40 %" in w for w in warns)          # 20 + 20 s: one layout


def test_variety_minimum_for_calm_long_form(tmp_path):
    _, warns, _ = run(tmp_path, v2())
    assert not any("distinct techniques" in w for w in warns)              # 13 techniques, the bar is 6 for 2.5 min
    plan = {"ratio": "16:9", "total": 600, "passages": [passage("p1", 0, 600)]}
    _, warns, _ = run(tmp_path, plan)
    assert any("1 distinct techniques for 10.0 min (want 10)" in w for w in warns)   # 1.2 a minute, capped at 10


def test_words_are_timed_from_a_passed_edl(tmp_path):
    edl = tmp_path / "edl.json"
    edl.write_text(json.dumps({"total": 150, "words": [{"i": i, "t": float(i), "e": i + 0.8} for i in range(150)]}))
    plan = {"ratio": "16:9", "schema": 2, "passages": [
        {**passage("p1", 0, 0), "words": [0, 10]}, {**passage("p2", 0, 0, face="off"), "words": [11, 30]},
        {**passage("p3", 0, 0, technique="kinetic"), "words": [31, 149]}]}
    for p in plan["passages"]:
        p.pop("t")
    errs, warns, _ = run(tmp_path, plan)
    assert any("can't be timed" in w for w in warns) and not any("away" in e for e in errs)
    errs, warns, _ = run(tmp_path, plan, edl)
    assert any(e.startswith("p2: away from him 19.8 s") for e in errs)


@pytest.fixture
def fm(tmp_path):
    d = tmp_path / "film"
    d.mkdir()
    return SimpleNamespace(dir=d, edl_path=tmp_path / "work/edl.json")


def test_kit_film_runs_plan_check_first(fm, capsys):
    from kit.film import render

    assert render.plan(fm) == 0 and "no visual_plan.json" in capsys.readouterr().out
    bad = v2(p1={"face": "off"})
    (fm.dir / "visual_plan.json").write_text(json.dumps(bad))
    with pytest.raises(SystemExit, match="errors in visual_plan.json"):
        render.plan(fm)
    assert "ERROR" in capsys.readouterr().out
    assert render.plan(fm, force=True) == 3                                 # --force goes on
    (fm.dir / "visual_plan.json").write_text(json.dumps(v2(p8={"groups": 5})))
    assert render.plan(fm) == 2 and "heavy" in capsys.readouterr().out     # warnings print, the build goes on
