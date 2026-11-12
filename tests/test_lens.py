"""kit/hf/motion.js HF.motion.lens (2026-10-22, kit v11): the camera on him inside every shape. Runs the pure plan and
the cover math in node (no browser), plus kit/film/build.py's D wiring (D.lens, D.tracks, the visual plan's cam)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HF = ROOT / "kit/hf"
node = pytest.mark.skipif(shutil.which("node") is None, reason="needs node")

# a talk of short sentences (0.42 s a word), two holds: full frame (budget 1.2) and a 620 px circle after a shape move
SETUP = """
const MO = HF.motion, words = []; let t = 0.3, i = 0;
'So this is the thing. I built it in a week and it works. Then the critic checks every single frame. That is the whole workflow, honestly. And going forward it gets better every week. Try it. We ship it every week to everyone who asked for it. That is the plan.'
  .split(' ').forEach((w) => { words.push({ i: i++, t, e: t + 0.28, text: w }); t += 0.42; if (/[.]$/.test(w)) t += 0.35; });
const END = t + 2;
const O = (x = {}) => Object.assign({ holds: [{ t0: 0, t1: 14, w: 1920, h: 1080, kmax: 1.2, enter: 'start', open: 1 },
  { t0: 14.6, t1: END, w: 620, h: 620, kmax: 1.4, enter: 'move' }], words, stress: [16, 30], cuts: [5.1, 9.3, 20.2], whips: [[24, 24.5]], fps: 30 }, x);
"""


def run(js: str):
    """Evaluate js with motion.js loaded (and box.js); js sets `out`, returned as JSON."""
    src = (
        "const fs=require('fs'),vm=require('vm');const ctx=vm.createContext({console,Math});"
        f"for (const f of ['motion.js','box.js']) vm.runInContext(fs.readFileSync({json.dumps(str(HF))}+'/'+f,'utf8'),ctx);"
        "ctx.out=null;vm.runInContext(" + json.dumps(SETUP + js) + ",ctx);process.stdout.write(JSON.stringify(ctx.out));"
    )
    r = subprocess.run(["node", "-e", src], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@node
def test_deterministic_and_visible():
    out = run("""
      const A = MO.lens(O()), B = MO.lens(O()), ts = []; for (let x = 0; x < END; x += 0.1) ts.push(+x.toFixed(2));
      const a = ts.map((x) => A.at(x)), b = ts.map((x) => B.at(x));
      // framing changes while he is on: the k range inside each 8 s window of the first hold
      const ks = ts.filter((x) => x < 14).map((x) => A.at(x).k);
      out = { same: JSON.stringify(a) === JSON.stringify(b), log: A.log, kmin: Math.min(...ks), kmax: Math.max(...ks), kinds: A.kinds() };
    """)
    assert out["same"]                                              # pure: the same input plans the same camera
    assert out["kmax"] / out["kmin"] - 1 >= 0.06                   # visible: +6 % or more across the first hold
    assert {"push", "arc"} <= set(out["kinds"])


@node
def test_no_move_twice_in_a_row():
    out = run("""
      const kinds = [];
      for (const len of [9, 17, 26, 40]) for (const plan of [[], [{ a: 0, b: 8, cam: 'push' }, { a: 8, b: 16, cam: 'push' }, { a: 16, b: 30, cam: 'arc' }, { a: 30, b: 40, cam: 'arc' }]]) {
        const L = MO.lens({ holds: [{ t0: 0, t1: len, w: 1200, h: 1200, kmax: 1.5, enter: 'start' }, { t0: len + 0.5, t1: len + 12, w: 800, h: 800, kmax: 1.5, enter: 'move' }], words, plan, fps: 30 });
        kinds.push(L.kinds());
      }
      out = kinds;
    """)
    for ks in out:
        assert ks, "a long hold gets moves"
        th = [k for k in ks if k != "settle"]                   # a settle at a landing is not a break (review 2026-10-22)
        assert all(a != b for a, b in zip(th, th[1:])), ks      # never the same move twice in a row (a plan included)


@node
def test_moves_rotate_across_shape_changes():
    """His shape changes every 5-8 s (the decided pacing): each hold opens with a settle, and the thought moves still
    rotate push > arc > pull across holds (review 2026-10-22: every hold went settle > push, pull-outs never came)."""
    out = run("""
      const res = [];
      for (const [len, kmax, w] of [[7, 1.5, 900], [10, 1.5, 900], [7, 1.2, 1920], [6, 1.14, 1680]]) {
        const holds = []; let a = 0;
        for (let k = 0; k < 8; k++) { holds.push({ t0: a, t1: a + len, w, h: Math.min(w, 1080), kmax, enter: k ? 'move' : 'start' }); a += len + 0.6; }
        const L = MO.lens({ holds, words, fps: 30 });
        const pulls = L.holds.flatMap((h) => h.segs.filter((s) => s.kind === 'pull').map((s) => s.from.k / s.to.k));
        res.push({ kinds: L.kinds(), firsts: L.holds.slice(1).map((h) => h.segs.find((s) => s.kind && s.kind !== 'settle').kind), pulls });
      }
      out = res;
    """)
    for r in out:
        th = [k for k in r["kinds"] if k != "settle"]
        assert all(a != b for a, b in zip(th, th[1:])), r["kinds"]
        assert {"push", "arc", "pull"} <= set(r["firsts"]), r["firsts"]   # each kind opens some hold
        assert r["pulls"] and min(r["pulls"]) >= 1.06 - 1e-6              # a pull-out reads (6 % or more)


@node
def test_respects_the_zoom_budget():
    out = run("""
      const L = MO.lens(O()), ks = { a: 0, b: 0 };
      for (let x = 0; x < END; x += 1 / 30) { const s = L.at(x), h = x < 14.3 ? 'a' : 'b'; ks[h] = Math.max(ks[h], s.k); }
      const none = MO.lens(O({ holds: [{ t0: 0, t1: 14, w: 1920, h: 1080, kmax: 1.0, enter: 'start' }] }));
      let still = 0; for (let x = 0; x < 14; x += 0.25) still = Math.max(still, Math.abs(none.at(x).k - 1));
      const B = (tr, mode) => MO.lensBudget(tr, 1080, 0.5, 0.5, mode);
      out = { ks, still, noTrack: B(null), sharp: B({ sharp_px: 1080, max_zoom: 1.0 }), soft: B({ sharp_px: 1080, soft: 0.24 }, 'soft'),
        circle: MO.lensBudget({ sharp_px: 540 }, 420, 420 / 1080, 420 / 1080), fixed: B(null, 1.1), punches: L.punches.map((p) => p.s) };
    """)
    assert out["ks"]["a"] <= 1.2 + 1e-9 and out["ks"]["b"] <= 1.4 + 1e-9    # never past kmax, punches and jumps included
    assert out["still"] == 0                                                   # no budget: the lens holds still
    assert out["noTrack"]["zoom"] == 1.2 and out["noTrack"]["kmax"] == pytest.approx(1.2)   # the contract's default
    assert out["sharp"]["zoom"] == 1.0                                         # a 4K room at full height on a 4K render
    assert out["soft"]["zoom"] == pytest.approx(1.24)                          # the softer allowance, when the film takes it
    assert out["circle"]["zoom"] == pytest.approx(540 / 420)                   # a small shape has its own headroom
    assert out["fixed"]["kmax"] == pytest.approx(1.1)
    assert out["punches"] and all(1.12 - 1e-9 <= s <= 1.15 + 1e-9 for s in out["punches"])   # decided x1.12-1.18


@node
def test_punches_keep_their_room_or_are_skipped():
    """A hold with a candidate keeps x1.12 free for it (budget 1.2: base moves up to 1.2 / 1.12); a tighter budget keeps
    the base lens moving and lands a punch only where it reaches x1.12, else logs the skip (never a x1.06 punch); a join
    is 'hidden under' only a punch that plays."""
    out = run("""
      const roomy = MO.lens(O({ cuts: [] }));                              // the base lens and its punches (no jump reframes)
      const base = []; for (let x = 0.5; x < 13.5; x += 0.05) if (!roomy.punches.some((p) => x >= p.t0 && x < p.t1)) base.push(roomy.at(x).k);
      const tight = MO.lens(O({ holds: [{ t0: 0, t1: 14, w: 1920, h: 1080, kmax: 1.14, enter: 'start' }], stress: [16, 30] }));
      const tk = []; for (let x = 0; x < 14; x += 0.05) tk.push(tight.at(x).k);
      // a 1.0-budget hold: the punch is dropped, so the join under its window is reframed, not 'hidden'
      const none = MO.lens(O({ holds: [{ t0: 0, t1: 14, w: 1920, h: 1080, kmax: 1.0, ksoft: 1.2, enter: 'start' }], cuts: [7.6] }));
      out = { roomyMax: Math.max(...base), roomyP: roomy.punches.map((p) => p.s), tightP: tight.punches.map((p) => p.s),
        tightRange: Math.max(...tk) / Math.min(...tk), tightLog: tight.log.filter((l) => /punch/.test(l)),
        noneLog: none.log.filter((l) => /punch|join/.test(l)), noneJ: none.jumps.map((j) => j.t) };
    """)
    assert out["roomyMax"] <= 1.2 / 1.12 + 1e-6                 # the base leaves the punch its x1.12
    assert out["roomyP"] and min(out["roomyP"]) >= 1.12 - 1e-9
    assert out["tightRange"] >= 1.06 - 1e-9                       # a tight budget: the base lens still moves
    assert all(s >= 1.12 - 1e-9 for s in out["tightP"])           # ... and a punch is x1.12 or skipped
    assert any("skipped" in l for l in out["tightLog"]) or out["tightP"]
    assert any("skipped" in l for l in out["noneLog"])            # the 1.0-budget punch is dropped ...
    assert not any("hidden under the punch" in l for l in out["noneLog"]) and 7.6 in out["noneJ"]   # ... and hides nothing


@node
def test_a_punch_after_a_join_steps_x112_on_screen():
    """Review 2026-10-22: a punch is a factor on the framing in force. With a join 2 s before the stressed word (it went
    in x1.1), the punch used to replace that framing: a logged x1.15 showed as x1.02-1.05. Now the step from the frame
    before its ease-in to the word is x1.12 or more, whatever the joins before it did, and nothing passes kmax."""
    out = run("""
      const w16 = words.find((w) => w.i === 16).t, res = [];
      for (const [kmax, ksoft] of [[1.4, 1.4], [1.2, 1.4], [1.2, 1.2], [1.3, 1.5]])
        for (const cuts of [[w16 - 2.0], [w16 - 3.6, w16 - 2.0], [w16 - 1.0], [w16 - 0.3], [w16 - 5.0, w16 - 2.6, w16 + 1.5], []]) {
          const L = MO.lens({ holds: [{ t0: 0, t1: 14, w: 1920, h: 1080, kmax, ksoft, enter: 'start' }], words, stress: [16], cuts, fps: 30 });
          let over = 0; for (let x = 0; x < 14; x += 1 / 60) { const s = L.at(x); if (s.k > (s.soft ? ksoft : kmax) + 1e-9) over++; }
          res.push({ kmax, cuts, over, p: L.punches.map((p) => ({ s: p.s, step: L.at(p.land).k / L.at(p.t0 - 1 / 30).k, land: p.land, t: w16 })),
            log: L.log.filter((l) => /punch|join/.test(l)) });
        }
      // dense joins (every 1.7 s) through the default talk: every punch that plays still steps x1.12
      const dense = []; for (let c = 1.2; c < 30; c += 1.7) dense.push(+c.toFixed(2));
      const D2 = MO.lens(O({ cuts: dense }));
      out = { res, dense: D2.punches.map((p) => D2.at(p.land).k / D2.at(p.t0 - 1 / 30).k), dj: D2.jumps.length };
    """)
    for r in out["res"]:
        assert r["over"] == 0, r
        assert len(r["p"]) == 1, r                          # the budget pays a punch in every case: it plays
        for p in r["p"]:
            assert 1.12 - 1e-6 <= p["s"] <= 1.15 + 1e-9
            assert p["step"] >= 1.12 - 1e-6, r            # x1.12 on screen, not x1.02 (the round-2 bug)
            assert abs(p["land"] - p["t"]) <= 2 / 30 + 1e-9
    assert out["dense"] and min(out["dense"]) >= 1.12 - 1e-6 and out["dj"] >= 5


@node
def test_punch_slots_go_to_punches_that_play():
    """Review 2026-10-22: the 12 s gap ran before the budget sizing, so a candidate the budget dropped still held its
    slot and silently hid a later one that could play. Sizing comes first now, and a gap skip is logged."""
    out = run("""
      const W = []; let tt = 0.3;
      for (let k = 0; k < 60; k++) { W.push({ i: k, t: tt, e: tt + 0.28, text: (k % 8 == 7) ? 'end.' : 'w' + k }); tt += 0.42; if (k % 8 == 7) tt += 0.35; }
      const holds = [{ t0: 0, t1: 10, w: 1920, h: 1080, kmax: 1.05, enter: 'start' }, { t0: 10.6, t1: 26, w: 600, h: 600, kmax: 1.6, enter: 'move' }];
      const a = W.find((w) => w.t > 4).i, b = W.find((w) => w.t > 14).i, c = W.find((w) => w.t > 18).i;
      const L = MO.lens({ holds, words: W, stress: [a, b], fps: 30 }), G = MO.lens({ holds, words: W, stress: [b, c], fps: 30 });
      out = { n: L.punches.map((p) => p.land), want: W[b].t, log: L.log.filter((l) => /punch/.test(l)), gap: G.log.filter((l) => /punch/.test(l)), gn: G.punches.length };
    """)
    assert out["n"] == [out["want"]]                                   # the circle's punch plays
    assert any("skipped: the zoom budget" in l for l in out["log"])    # the full-frame one is dropped, logged
    assert out["gn"] == 1 and any("skipped: within 12 s of the punch" in l for l in out["gap"])


@node
def test_joins_spend_the_soft_allowance_when_the_sharp_budget_cant():
    """Review 2026-10-22: on a 4K render full frame has no sharp room; a join must still reframe (eased), on the soft
    allowance, flagged soft; rules.jump.soft = false keeps the cap (a bare cut, logged)."""
    out = run("""
      const H = [{ t0: 0, t1: 12, w: 1920, h: 1080, kmax: 1.0, ksoft: 1.12 }];
      const J = MO.jumps([2, 4, 6], H, {}), log = [], off = MO.jumps([2, 4, 6], H, { rules: { jump: { soft: false } }, log });
      const thin = MO.jumps([2], [{ t0: 0, t1: 12, w: 1920, h: 1080, kmax: 1.0, ksoft: 1.03 }], {});
      const L = MO.lens(O({ holds: [{ t0: 0, t1: 14, w: 1920, h: 1080, kmax: 1.0, ksoft: 1.12, enter: 'start' }], stress: [], cuts: [3.1, 6.2, 9.3] }));
      let over = 0, hard = 0, soft = 0;
      for (let x = 0; x < 14; x += 1 / 30) { const s = L.at(x); if (s.k > 1.12 + 1e-9) over++; if (!s.soft && s.k > 1.0 + 1e-9) hard++; if (s.soft) soft++; }
      // the shape leaves a hold while a soft framing holds: the move out of it stays soft until it has blended away
      const M = MO.lens({ holds: [{ t0: 0, t1: 10, w: 1920, h: 1080, kmax: 1.0, ksoft: 1.12, enter: 'start' },
        { t0: 10.6, t1: 20, w: 600, h: 600, kmax: 1.5, enter: 'move' }], words, cuts: [3.1], fps: 30 });
      out = { J, off, log, thin, still: L.holds[0].still, jumps: L.jumps.map((j) => [j.t, j.to, j.soft]), over, hard, soft,
        mid: [L.at(3.1).k, L.at(3.1 + 0.125).k, L.at(3.5).k], leave: [M.at(9.9).soft, M.at(10.3, 0.5).soft, M.at(10.3, 1).soft, M.at(11).soft] };
    """)
    assert [(j["to"], j["soft"]) for j in out["J"]] == [(1.1, True), (1, True), (1.1, True)]   # in, back, in: all eased
    assert all(j["dur"] == 0.25 for j in out["J"])
    assert out["off"] == [] and any("bare cut" in l for l in out["log"])                       # opt-out: logged, bare
    assert out["thin"] == []                                                                  # the soft room under x1.06
    assert out["still"] and [j[0] for j in out["jumps"]] == [3.1, 6.2, 9.3]                    # base still, joins reframed
    assert out["over"] == 0 and out["hard"] == 0 and out["soft"] > 0       # never past ksoft; over kmax only while soft
    assert out["mid"][0] < out["mid"][1] < out["mid"][2] == pytest.approx(1.1)               # eased, not a hard step
    assert out["leave"] == [True, True, False, False]      # soft while it blends out of the soft framing, then sharp


@node
def test_punch_lands_on_the_word():
    out = run("""
      const L = MO.lens(O());
      out = L.punches.map((p) => { const w = words.find((x) => x.i === p.word), pre = L.at(w.t - 2 / 30).k, at = L.at(w.t).k, peak = L.at(w.t + 0.2).k;
        return { land: p.land, t: w.t, t0: p.t0, s: p.s, pre, at, peak, move: L.at(w.t).move, gap: null }; });
      const P = MO.lens(O({ stress: words.map((w) => w.i) }));                 // every word stressed: the budget wins
      out = { first: out, n: P.punches.length, gaps: P.punches.slice(1).map((p, k) => p.t0 - P.punches[k].t0) };
    """)
    assert out["first"], "a stressed word in a big enough hold gets a punch"
    for p in out["first"]:
        assert abs(p["land"] - p["t"]) <= 2 / 30 + 1e-9                     # lands within 2 frames of the word
        assert p["t"] - p["t0"] == pytest.approx(13 / 30)                     # 13 frames in (power3.out)
        assert p["move"] == "punch" and p["at"] >= p["pre"]
    assert all(g >= 12 - 1e-6 for g in out["gaps"])                          # one per 12 s at most


@node
def test_whip_windows_hold_still():
    out = run("""
      const L = MO.lens(O({ whips: [[21.0, 21.6], [25, 25.4]] }));
      const span = (a, b) => { const v = []; for (let x = a; x <= b; x += 0.02) v.push(L.at(x)); return v; };
      const w = span(21.0, 21.59), w2 = span(25.0, 25.39);
      const flat = (v) => v.every((s) => Math.abs(s.k - v[0].k) < 1e-9 && Math.abs(s.dx - v[0].dx) < 1e-9 && Math.abs(s.rot - v[0].rot) < 1e-9);
      out = { flat: flat(w) && flat(w2), moving: Math.abs(L.at(20.0).k - L.at(20.9).k) > 1e-4, after: L.at(22.2).move,
        punchNear: L.punches.some((p) => p.t1 > 20.3 && p.t0 < 22.3), end: END };
    """)
    assert out["end"] > 26
    assert out["moving"] and out["flat"]                   # ride 0: the lens moves before, holds still while the canvas whips
    assert out["after"] == "settle"                        # ... and settles after it
    assert not out["punchNear"]                            # no punch within 0.7 s of a whip


@node
def test_jumps_alternate_and_hide_under_punches():
    out = run("""
      const L = MO.lens(O());
      const J = MO.jumps([1, 3, 5, 7, 9], [{ t0: 0, t1: 12, w: 1000, h: 1000, kmax: 1.3 }], {});
      const small = MO.jumps([3], [{ t0: 0, t1: 12, w: 200, h: 200, kmax: 1.3 }], {});
      const nearEdge = MO.jumps([0.2, 11.8], [{ t0: 0, t1: 12, w: 1000, h: 1000, kmax: 1.3 }], {});
      out = { J, small, nearEdge, lensJ: L.jumps, hidden: L.log.filter((x) => /hidden under the punch/.test(x)).length,
        ease: [L.at(L.jumps[0].t + 0.125).k, L.at(L.jumps[0].t).k, L.at(L.jumps[0].t + 0.3).k] };
    """)
    tos = [j["to"] for j in out["J"]]
    assert tos == [1.1, 1, 1.1, 1, 1.1]                    # wide / close alternate, never a step twice the same way
    assert all(j["dur"] == 0.25 for j in out["J"])         # eased 0.25 s, not a hard step
    assert out["small"] == [] and out["nearEdge"] == []    # too small to read; a move within 0.45 s hides the join
    assert out["hidden"] >= 1                              # the join at 9.3 s sits under the punch
    a, mid, b = out["ease"][1], out["ease"][0], out["ease"][2]
    assert min(a, b) < mid < max(a, b)                     # mid-reframe: between the two framings


@node
def test_hard_jump_steps_on_the_join_frame():
    """rules.jump.dur 0 (who-gonna-hire 2026-10-23): the reframe is a hard step on the join's own frame (the cut time is
    stored to 4 decimals, so that frame may sit just before it), never an ease and never a frame late."""
    out = run("""
      const L = MO.lens(O({ rules: { jump: { s: 1.2, dur: 0 } } })), j = L.jumps[0], f = Math.round(j.t * 30) / 30;
      out = { dur: j.dur, to: j.to, before: L.at(f - 1 / 30).k, on: L.at(f - 0.0001).k, after: L.at(f + 1 / 30).k };
    """)
    step = max(out["to"], 1 / out["to"])                   # in or out, whichever the budget gives
    assert out["dur"] == 0 and step > 1.05
    assert max(out["on"] / out["before"], out["before"] / out["on"]) > step - 0.02   # the step lands on the join's frame
    assert abs(out["after"] / out["on"] - 1) < 0.02        # and holds: no ease after it


@node
def test_lens_frame_clamps_to_cover():
    out = run("""
      const SRC = [1920, 1080], eye = [960, 400];
      const inside = (g, f, R) => {                          // every corner of the box maps inside R in source px
        const [a, b, c, d, e, ff] = f.m, det = a * d - b * c, pts = g.circle ? [] : [[0, 0], [g.bw, 0], [0, g.bh], [g.bw, g.bh]];
        if (g.circle) for (let k = 0; k < 16; k++) pts.push([g.bw / 2 + g.bw / 2 * Math.cos(k * Math.PI / 8), g.bh / 2 + g.bh / 2 * Math.sin(k * Math.PI / 8)]);
        return pts.every(([x, y]) => { const u = (d * (x - e) - c * (y - ff)) / det, v = (-b * (x - e) + a * (y - ff)) / det;
          return u >= R[0] - 0.01 && u <= R[2] + 0.01 && v >= R[1] - 0.01 && v <= R[3] + 0.01; }); };
      const res = [];
      const shapes = [{ bw: 1920, bh: 1080, vs: 1, vx: 0, vy: 0 }, { bw: 900, bh: 506, vs: 0.47, vx: 0, vy: 0 },
        { bw: 500, bh: 500, vs: 0.47, vx: -200, vy: -10, circle: true }, { bw: 520, bh: 620, vs: 0.6, vx: -300, vy: -100 }];
      for (const g of shapes) for (const st of [{ k: 1 }, { k: 1.3, dx: 0.4, dy: -0.4, rot: 3 }, { k: 1.01, dx: -0.5, rot: -0.6 }, { k: 1.5, dx: 0.03, rot: 0.6 }])
        for (const R of [[0, 0, 1920, 1080], [300, 120, 1700, 1080]]) {
          const f = MO.lensFrame(g, st, { src: SRC, eye, rect: R, smax: g.vs * 1.4 });
          res.push({ ok: inside(g, f, R), rot: f.rot, zoom: f.zoom });
        }
      const rest = MO.lensFrame({ bw: 520, bh: 620, vs: 0.6, vx: -300, vy: -20 }, { k: 1 }, { src: SRC, eye });
      const circ = MO.lensFrame({ bw: 500, bh: 500, vs: 0.6, vx: -300, vy: -100, circle: true }, { k: 1, rot: 0.6 }, { src: SRC, eye, smax: 0.6 });
      const rect = MO.lensFrame({ bw: 1920, bh: 1080, vs: 1, vx: 0, vy: 0 }, { k: 1, rot: 0.6 }, { src: SRC, eye, smax: 1.0 });
      const rect2 = MO.lensFrame({ bw: 1920, bh: 1080, vs: 1, vx: 0, vy: 0 }, { k: 1, rot: 0.6 }, { src: SRC, eye, smax: 1.2 });
      out = { res, rest: rest.m, circRot: circ.rot, rectRot: rect.rot, rect2: [rect2.rot, rect2.s] };
    """)
    assert all(r["ok"] for r in out["res"])                # no edge of the footage (or of the clean rect) ever shows
    assert out["rest"] == [0.6, 0, 0, 0.6, -300, -20]     # at rest it is exactly the base framing
    assert out["circRot"] == pytest.approx(0.6)            # a circle rolls free
    assert out["rectRot"] == 0                             # a full frame with no budget can't pay a roll's cover zoom
    assert out["rect2"][0] == pytest.approx(0.6) and 1.0 < out["rect2"][1] < 1.04   # with budget: ~3 % per degree


# v11-sample's speaker track as kit/film/cut.py wrote output/temp/films/v11-sample/work/tracks.json (2026-10-22): ONE
# native 4K track, his selfie ("cam", sharp 1080 px at the 1080 ref) and Framecast's bubble ("chrome", sharp 162 px);
# the top level is the poorest kind. Pieces: the hook on cam, the bubble from 12.07 s, take 3's cam from 37.90 s
V11_FACE = {"w": 3840, "h": 2160, "src_w": 576, "src_h": 324, "render_scale": 2.0, "ref_px": 1080.0, "sharp_px": 162.0,
            "max_zoom": 1.0, "soft_zoom": 1.036, "soft": 0.24,
            "kinds": {"cam": {"src_w": 3840, "src_h": 2160, "sharp_px": 1080.0, "max_zoom": 1.0, "soft_zoom": 1.24, "share": 0.584},
                      "chrome": {"src_w": 576, "src_h": 324, "sharp_px": 162.0, "max_zoom": 1.0, "soft_zoom": 1.036, "share": 0.416}}}
V11_PIECES = [{"kind": "cam", "out_a": 0.0}, {"kind": "chrome", "out_a": 12.07}, {"kind": "cam", "out_a": 37.9}]


@node
def test_budget_per_kind_and_full_bleed_tier():
    """E-M1: a hold's budget reads the tracks.json kind playing in it (the poorest one inside its span), not the track's
    poorest overall: a cam hold in v11-sample's 1680 x 945 frame card is sharp to x1.143 (1080 / 945), where the track's
    top level (the bubble's 162 px) held it at x1.0. E-M2: the default budget ('auto') spends soft_zoom at full bleed
    only (x1.24 on the native 4K cam), cards stay sharp; 'sharp' restores strict; a number is fixed."""
    out = run(f"""
      const T = {json.dumps(V11_FACE)}, PS = {json.dumps(V11_PIECES)};
      const hb = (t0, t1, w, h, budget, full) => {{ const cover = Math.max(w / 3840, h / 2160);
        const b = MO.holdBudget(T, {{ pieces: PS, t0, t1, Hc: 2160 * cover, cover, vs: cover, budget, full }}); return [+b.zoom.toFixed(3), b.mode, b.kind]; }};
      out = {{ camCard: hb(40, 46, 1680, 945), bubbleSpan: hb(10, 14, 1680, 945), noPieces: MO.holdBudget(T, {{ t0: 40, t1: 46, Hc: 945, cover: 945 / 2160, vs: 945 / 2160 }}).zoom,
        camFull: hb(40, 46, 1920, 1080, undefined, true), camFullSharp: hb(40, 46, 1920, 1080, 'sharp', true), camFullFixed: hb(40, 46, 1920, 1080, 1.2, true),
        modes: [MO.lensMode(undefined, true), MO.lensMode('auto', false), MO.lensMode('sharp', true), MO.lensMode('soft', false), MO.lensMode(1.1, true)],
        kinds: MO.kindsOver(PS, 11, 13), noKinds: MO.trackKind({{ sharp_px: 540 }}, ['cam']).sharp_px }};
    """)
    assert out["camCard"] == [1.143, "sharp", "cam"]                 # per kind, not the track's poorest (x1.0)
    assert out["bubbleSpan"] == [1.0, "sharp", "chrome"]             # a hold over the bubble: the poorest inside it
    assert out["noPieces"] == 1.0                                    # no D.pieces: the track's top level, as before
    assert out["camFull"] == [1.24, "soft", "cam"] and out["camFullSharp"] == [1.0, "sharp", "cam"] and out["camFullFixed"][0] == 1.2
    assert out["modes"] == ["soft", "sharp", "sharp", "soft", 1.1]
    assert out["kinds"] == ["cam", "chrome"] and out["noKinds"] == 540


@node
def test_planned_pull_and_land_in_after_a_zoom_through():
    """Fix round 2026-10-23: a hold entered by a move (or a cut) whose plan says 'pull' lands on a closer framing and
    pulls out of it (it used to turn into an arc: a settled x1.0 has nothing to pull from); after a zoom-through's landing
    (a whip tagged 'land') the lens cuts in on the zoom's cut frame and pulls out after it, never twice in a row."""
    out = run("""
      const res = {};
      for (const enter of ['move', 'cut', 'start']) {
        const L = MO.lens({ holds: [{ t0: 0, t1: 9, w: 1680, h: 945, kmax: 1.25, enter }], words, plan: [{ a: 0, b: 9, cam: 'pull' }], fps: 30 });
        const s = L.holds[0].segs.find((x) => x.kind === 'pull');
        res[enter] = { kinds: L.kinds(), pull: s ? s.from.k / s.to.k : 0 };
      }
      const Z = MO.lens({ holds: [{ t0: 0, t1: 16, w: 1680, h: 945, kmax: 1.25, enter: 'start' }], words, whips: [[6.7, 7.0], [7.0, 7.45, 'land']], fps: 30 });
      const after = Z.holds[0].segs.find((x) => x.a >= 7.45 - 1e-6 && x.kind);
      res.land = { first: after && after.kind, from: after && after.from.k, at: [Z.at(6.9).k, Z.at(7.0).k, Z.at(7.4).k],
        log: Z.log.filter((l) => /lands in/.test(l)).length, kinds: Z.kinds() };
      out = res;
    """)
    for enter in ("move", "cut", "start"):
        r = out[enter]
        assert "pull" in r["kinds"] and r["pull"] >= 1.06 - 1e-6, (enter, r)
    L = out["land"]
    assert L["first"] == "pull" and L["from"] >= 1.06 and L["log"] == 1
    assert L["at"][1] == pytest.approx(L["at"][2]) and L["at"][1] >= L["at"][0] - 1e-9   # in on the zoom's cut, held through it
    th = [k for k in L["kinds"] if k != "settle"]
    assert all(a != b for a, b in zip(th, th[1:])), L["kinds"]


@node
def test_amplitude_scales_with_the_shape():
    out = run("""
      out = [200, 240, 360, 540, 900].map((m) => MO.lensAmp(m));
      const L = MO.lens({ holds: [{ t0: 0, t1: 12, w: 200, h: 200, kmax: 2, enter: 'start' }], words, stress: [16], fps: 30 });
      out = { amp: out, still: [0, 3, 6, 9, 11].every((x) => L.at(x).k === 1), punches: L.punches.length };
    """)
    assert out["amp"][0] == 0 and out["amp"][1] == pytest.approx(0.4) and out["amp"][3] == 1 and out["amp"][4] == 1
    assert 0.4 < out["amp"][2] < 1
    assert out["still"] and out["punches"] == 0            # a 200 px circle: no lens, no punch (jitter)


@node
def test_box_drift_goes_only_where_the_lens_moves():
    """Without the lens the box drifts as before; with it, the drift goes from the holds the lens moves and stays in the
    holds it leaves still (no zoom budget), so turning the lens on never takes motion away (review 2026-10-22)."""
    out = run("""
      const B = HF.box, shots = [{ t: 0, at: 'full' }, { t: 12, at: 'right' }];
      const P = B.plan({ shots }), PL = B.plan({ shots, lens: true }), PS = B.plan({ shots, lens: true });
      B.lensPlan(PL, { lens: {}, end: 24 }, { words_: words, fps: 30 });                       // no tracks.json: 1.2, moves
      B.lensPlan(PS, { lens: { budget: 1.0 }, end: 24 }, { words_: words, fps: 30 });          // a fixed 1.0 cap: still
      out = { off: B.at(P, 5).zoom, on: B.at(PL, 5).zoom, still: B.at(PS, 5).zoom, flag: [P.lens, PL.lens],
        moves: PL.keys.map((k) => !!k.lensMoves), stillMoves: PS.keys.map((k) => !!k.lensMoves) };
    """)
    assert out["off"] == pytest.approx(1.03)               # the old linear drift, unchanged without the lens
    assert out["on"] == 1 and out["flag"] == [False, True] # the lens replaces it where it moves
    assert out["moves"] == [True, True] and out["stillMoves"] == [False, False]
    assert out["still"] == pytest.approx(1.03)             # a hold the lens leaves still keeps the drift


@node
def test_box_lens_on_a_4k_render_reframes_every_join():
    """HF.box under work/tracks.json budgets as kit/film/cut.py writes them (sim of the review): a 1080 track on a 4K
    render has no sharp room in full frame or cards; every join away from a move still gets an eased reframe on the
    soft allowance (the pre-v11 kit's 1.12 steps), and the face circle (HF.reel CIRCLE, pill: 1, tint 0) is a lens
    shape and a 'circle' in window.__speaker, the accent pill is off."""
    out = run("""
      globalThis.D = { total: 36, lens: { on: true, track: 'aroll' }, tracks: { aroll: { file: 'a', sharp_px: 540, max_zoom: 1.0, soft: 0.24 } } };
      const B = HF.box, P = B.plan({ shots: [{ t: 0, at: 'full' }, { t: 12, at: 'right' }, { t: 24, at: 'full' }], width: 1920, height: 1080, lens: true });
      const cuts = [3.1, 6.2, 9.0, 15.5, 19.0, 27.0, 30.5];
      // budget 'sharp' (LENS = dict(budget="sharp")): the strict regime this test is about; the default ('auto', E-M2)
      // spends the soft tier at full bleed only (LA below)
      const LP = B.lensPlan(P, { lens: { cuts, budget: 'sharp' }, src: [1920, 1080], end: 36 }, { words_: words, fps: 30 });
      const LA = B.lensPlan(P, { lens: { cuts }, src: [1920, 1080], end: 36 }, { words_: words, fps: 30 });
      let maxk = 0; for (let x = 0; x < 36; x += 1 / 30) maxk = Math.max(maxk, LP.L.at(x).k);
      const CIRCLE = { cx: 0.24, cy: 0.762, w: 0.3889, h: 0.2188, rot: 0, pill: 1 };
      const R = B.plan({ shots: [{ t: 0, at: 'full' }, { t: 4, at: CIRCLE, in: 'shrink' }, { t: 14, at: 'pill' }], width: 1080, height: 1920, lens: true });
      const RL = B.lensPlan(R, { lens: {}, src: [1080, 1080], end: 20 }, { words_: words, fps: 30 });
      out = { jumps: LP.L.jumps.map((j) => [j.t, j.soft]), maxk, ksoft: LP.info.map((i) => i.ksoft), kmax: LP.info.map((i) => i.kmax),
        circle: B.speakerKind(B.at(R, 8), 1080, 1920), pill: B.speakerKind(B.at(R, 16), 1080, 1920), full: B.speakerKind(B.at(R, 1), 1080, 1920),
        holds: RL.L.holds.map((h) => h.key), auto: LA.info.map((i) => [+i.kmax.toFixed(4), i.mode]) };
    """)
    assert out["kmax"] == [1, 1, 1]                                    # the sharp budget: no room anywhere
    # E-M2 'auto': full frame spends soft_zoom (1 + 0.24 x 540 / 1080 = x1.12), the card keeps the sharp cap
    assert out["auto"] == [[1.12, "soft"], [1, "sharp"], [1.12, "soft"]]
    assert [j[0] for j in out["jumps"]] == [3.1, 6.2, 9.0, 15.5, 19.0, 27.0, 30.5] and all(j[1] for j in out["jumps"])
    assert out["maxk"] <= max(out["ksoft"]) + 1e-9
    assert out["circle"] == {"on": True, "kind": "circle"}            # his face circle is him
    assert out["pill"] == {"on": False, "kind": "off"} and out["full"]["kind"] == "full"
    assert 1 in out["holds"] and 2 not in out["holds"]                 # the lens runs in the circle, not in the accent pill


@node
def test_canvas_frame_card_fits_the_page_and_clean_rects_follow_the_take():
    js = (
        "globalThis.window=globalThis;globalThis.gsap={parseEase:()=>(p)=>p};"
        + "".join(f"require({json.dumps(str(HF / m))});" for m in ("core.js", "motion.js", "box.js", "studio.js", "canvas.js"))
        + "const F=HF.canvas.frameBox,C=HF.canvas.cleanRect,FULL=[0,0,1080,1080];"
        "console.log(JSON.stringify({land:F({},1920,1080),port:F({},1080,1920),full:F({full:true},1080,1920),own:F({w:800,h:600,x:500,y:400},1920,1080),"
        "rects:[C(null,0,FULL),C([10,0,900,1080],1,FULL),C({0:[100,0,1080,1080],1:[0,0,800,1080]},1,FULL),C({0:[100,0,1080,1080]},2,FULL)]}))"
    )
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert out["land"] == {"bx": 120, "by": 67.5, "bw": 1680, "bh": 945}      # 1920 x 1080: the v11 default, unchanged
    p = out["port"]
    assert p["bw"] == 945 and p["bh"] == 1181 and p["bx"] >= 0 and p["bx"] + p["bw"] <= 1080   # a Reel: inside the page
    assert out["full"] == {"bx": 0, "by": 0, "bw": 1080, "bh": 1920}
    assert out["own"] == {"bx": 100, "by": 100, "bw": 800, "bh": 600}
    assert out["rects"] == [[0, 0, 1080, 1080], [10, 0, 900, 1080], [0, 0, 800, 1080], [0, 0, 1080, 1080]]


CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
chrome = pytest.mark.skipif(shutil.which("node") is None or not CHROME.exists() or not (ROOT / "node_modules/puppeteer-core").exists(),
                            reason="needs node, puppeteer-core and Google Chrome")
# a canvas page with one speaker (a grey test card, never his face): D.shots, D.pieces, D.lens / D.tracks as given
PAGE = """<!doctype html><html lang="en"><head><meta charset="UTF-8" /><!--HF:KIT--></head><body>
<div id="root" data-composition-id="fx" data-start="0" data-duration="20" data-width="1920" data-height="1080" style="position:relative;width:1920px;height:1080px;overflow:hidden">
<img id="face" alt="" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='3840' height='2160'%3E%3Crect width='3840' height='2160' fill='%23889'/%3E%3C/svg%3E" /></div>
<script>
const D = /*D*/;
(function () {
  const tl = gsap.timeline({ paused: true });
  window.__timelines = { fx: tl };
  const K = HF.kit({ tl, id: "fx", width: 1920, height: 1080, words: D.words, pieces: D.pieces });
  const C = HF.canvas(K, document.getElementById("root"), { w: 5760, h: 3240, look: "whitespace" });
  C.station(0, D.total, "mid", [2880, 1620]);
  C.speaker("face", D.shots, { src: [3840, 2160], at: [1964, 1196], head: 510 });
  K.finish(D.total);
})();
</script></body></html>"""
# per time: where source point (sx, sy) sits on the page, the footage's scale, and the lens log / holds
PROBE = """
import { createRequire } from "node:module";
const puppeteer = createRequire(%(pkg)s)("puppeteer-core");
const [file, a, b, st] = process.argv.slice(2), [sx, sy] = [1964, 1094];
const br = await puppeteer.launch({ executablePath: %(chrome)s, headless: true, args: ["--allow-file-access-from-files"] });
const p = await br.newPage(), errs = [];
p.on("pageerror", (e) => errs.push(String(e.message || e)));
await p.setViewport({ width: 1920, height: 1080 });
await p.goto("file://" + file, { waitUntil: "domcontentloaded" });
await p.waitForFunction(() => !!(window.__timelines && window.__timelines.fx), { timeout: 60000 });
const r = await p.evaluate((a, b, st, sx, sy) => {
  const tl = window.__timelines.fx, v = document.getElementById("face"), box = v.parentElement, rows = [];
  for (let t = a; t <= b + 1e-9; t += st) {
    tl.seek(t, false);
    const m = v.style.transform.match(/matrix\\(([^)]*)\\)/)[1].split(",").map(Number), bx = parseFloat(box.style.left), by = parseFloat(box.style.top);
    rows.push([+t.toFixed(4), bx + m[0] * sx + m[2] * sy + m[4], by + m[1] * sx + m[3] * sy + m[5], Math.hypot(m[0], m[1])]);
  }
  const L = window.__lens && window.__lens.face;
  return { rows, log: L ? L.log : null, holds: L ? L.holds.length : null };
}, +a, +b, +st, sx, sy);
console.log(JSON.stringify(Object.assign(r, { errs })));
await br.close();
"""


def canvas_page(tmp_path, name, D):
    import sys
    sys.path.insert(0, str(HF))
    import vendor
    if not (tmp_path / "vendor/gsap.min.js").exists():
        vendor.copy_assets(tmp_path)
    f = tmp_path / f"{name}.html"
    f.write_text(vendor.inline(PAGE).replace("/*D*/", json.dumps(D)))
    return f


def probe(tmp_path, f, a, b, st):
    js = tmp_path / "probe.mjs"
    js.write_text(PROBE % {"pkg": json.dumps(str(ROOT / "package.json")), "chrome": json.dumps(str(CHROME))})
    r = subprocess.run(["node", str(js), str(f), str(a), str(b), str(st)], capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["errs"] == [], out["errs"]
    return out


WORDS = [{"i": i, "t": 0.3 + 0.42 * i, "e": 0.58 + 0.42 * i, "text": "w." if i % 9 == 8 else "w"} for i in range(44)]
TRACK = {"w": 3840, "h": 2160, "src_w": 3840, "src_h": 2160, "sharp_px": 2160.0, "max_zoom": 1.125, "soft_zoom": 1.4, "soft": 0.24}


@chrome
def test_canvas_moves_into_a_clean_frame_without_a_pop(tmp_path):
    """Review 2026-10-22: on the first frame of a move into a frame shot, the new clean rect clamped the old shape's
    framing at once (a 113 px jump of his face in one frame, lens on). The rect now blends with the move. Measured as
    the largest change of a source point's per-frame motion (a pop is a spike; an eased move changes smoothly), at
    60 steps a second, against the same page with the lens off. Round 2's engine: 115 px (circle -> frame) and 845 px
    (two frame shots with different clean rects); lens off: 12 and 11."""
    circle = {"mode": "card", "x": 1480, "y": 560, "w": 560, "h": 560, "r": 280}
    shots = [dict(circle, t=0), {"t": 6.6, "mode": "frame", "clean": [1500, 0, 3840, 2160]}, dict(circle, t=14.0)]
    pcs = [{"out_a": 0, "out_b": 20, "src_a": 0, "src_b": 20, "clip": 1}]
    base = {"total": 20, "words": WORDS, "pieces": pcs, "shots": shots, "tracks": {"face": TRACK}}
    ff = [{"t": 0, "mode": "frame", "clean": [1500, 0, 3840, 2160]}, {"t": 6.6, "mode": "frame", "full": True, "clean": [0, 200, 2600, 2160]}]
    on, off = ({"on": True, "track": "face", "fps": 30, "budget": "soft"}, {"on": False, "track": "face"})

    def jerk(name, D, a, b):
        rows = probe(tmp_path, canvas_page(tmp_path, name, D), a, b, 1 / 60)["rows"]
        v = [(r[1] - q[1], r[2] - q[2]) for q, r in zip(rows, rows[1:])]
        return max(((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5 for q, p in zip(v, v[1:]))
    for shots_, a, b in ((shots, 6.4, 7.4), (shots, 13.8, 14.8), (ff, 6.4, 7.4)):
        jon = jerk("on", dict(base, shots=shots_, lens=on), a, b)
        joff = jerk("off", dict(base, shots=shots_, lens=off), a, b)
        assert jon <= 1.25 * joff + 2, (a, jon, joff)


@chrome
def test_canvas_names_a_clean_rect_too_small_for_its_frame(tmp_path):
    """Review 2026-10-22: a clean rect too narrow for the frame's aspect pushes its base framing past the zoom budget
    (x2.67 against 1.24) with nothing said; the lens log (and the console) now names the shot."""
    shots = [{"t": 0, "mode": "frame", "full": True, "clean": [2400, 600, 3840, 2160]}, {"t": 8, "mode": "frame", "clean": [700, 0, 3840, 2160]}]
    D = {"total": 20, "words": WORDS, "pieces": [{"out_a": 0, "out_b": 20, "src_a": 0, "src_b": 20}], "shots": shots, "tracks": {"face": TRACK},
         "lens": {"on": True, "track": "face", "fps": 30, "budget": "soft"}}
    log = probe(tmp_path, canvas_page(tmp_path, "narrow", D), 1, 1, 1)["log"]
    warn = [x for x in log if "past the zoom budget" in x]
    assert len(warn) == 1 and warn[0].startswith("0.00 frame shot 0: its clean rect frames x2.67"), log


@chrome
def test_canvas_template_jump_shots_are_one_lens_hold(tmp_path):
    """Review 2026-10-22: a rebuilt film that keeps its inline 'every other join x1.12' loop split the lens's holds at
    each cut shot and the lens restarted at x1 there, eating the template's step (x1.052 on screen). Same-shape cut
    shots are now one hold: the lens carries across, the template's x1.12 step shows whole, and the lens adds no
    reframe of its own on those joins."""
    c = {"mode": "card", "x": 1480, "y": 560, "w": 600, "h": 600, "r": 300, "s": 600 / 2160}
    shots = [dict(c, t=0), dict(c, t=4.3, s=c["s"] * 1.12, cut=True), dict(c, t=8.1, cut=True), dict(c, t=11.9, s=c["s"] * 1.12, cut=True)]
    cuts = [0, 4.3, 8.1, 11.9, 20]
    pcs = [{"out_a": a, "out_b": b, "src_a": a + 3 * k, "src_b": b + 3 * k, "clip": 1} for k, (a, b) in enumerate(zip(cuts, cuts[1:]))]
    f = canvas_page(tmp_path, "loop", {"total": 20, "words": WORDS, "pieces": pcs, "shots": shots, "lens": {"on": True, "track": "face", "fps": 30}})
    out = probe(tmp_path, f, 0.2, 19.8, 1 / 30)
    sc = {round(r[0], 4): r[3] for r in out["rows"]}
    at = lambda t: sc[min(sc, key=lambda x: abs(x - t))]   # noqa: E731
    steps = [at(t + 1 / 60) / at(t - 1 / 30) for t in (4.3, 8.1, 11.9)]
    assert out["holds"] == 1
    assert sum("template's own cut shot" in l for l in out["log"]) == 3 and not any("join: in" in l or "join: out" in l for l in out["log"])
    assert steps[0] == pytest.approx(1.12, abs=0.006) and steps[1] == pytest.approx(1 / 1.12, abs=0.006) and steps[2] == pytest.approx(1.12, abs=0.006)
    ks = [r[3] / (c["s"] * (1.12 if 4.3 <= r[0] < 8.1 or r[0] >= 11.9 else 1)) for r in out["rows"]]
    assert max(ks) / min(ks) >= 1.03                     # the lens still moves inside what the closer framing leaves


def test_build_wires_the_lens(tmp_path, monkeypatch):
    """kit/film/build.py: D.lens from LENS / STRESS / the visual plan; D.tracks carries tracks.json."""
    from kit.film import build as B

    class F:
        pass
    Fm = F()
    Fm.dir, Fm.work, Fm.FACE_TRACK, Fm.FPS = tmp_path, tmp_path, "face", 30
    Fm.LENS, Fm.STRESS = True, [3, 99]
    words = [{"i": i, "t": i * 0.5, "e": i * 0.5 + 0.3, "text": "w."} for i in range(20)]
    (tmp_path / "visual_plan.json").write_text(json.dumps({"schema": 2, "passages": [
        {"id": "p1", "words": [0, 5], "cam": "push"}, {"id": "p2", "t": [3.0, 6.0], "cam": "punch", "punch": 8},
        {"id": "p3", "words": [12, 15], "cam": "wobble"}, {"id": "p4", "words": [16, 19], "beats": [{"at": 17, "punch": True}]}]}))
    (tmp_path / "tracks.json").write_text(json.dumps({"face": {"w": 2160, "h": 2160, "src_w": 2160, "src_h": 2160, "max_zoom": 1.0}}))
    L = B.lens_data(Fm, words)
    assert L["on"] and L["track"] == "face" and L["fps"] == 30
    assert L["stress"] == [3, 17]                          # film.py's ids in the cut, plus the plan's punch beats
    assert L["plan"] == [{"a": 0.0, "b": 2.8, "cam": "push"}, {"a": 3.0, "b": 6.0, "cam": "punch", "punch": 8}]
    Fm.LENS = dict(calm=0.6, budget="soft")
    assert {"calm": 0.6, "budget": "soft"}.items() <= B.lens_data(Fm, words).items()
    Fm.LENS = {}                                           # an empty dict is "on with defaults" (bool({}) was off)
    assert B.lens_data(Fm, words)["on"] is True
    Fm.LENS = False
    assert B.lens_data(Fm, words) == {"on": False, "track": "face", "fps": 30}
    # E-M3: LENS unset follows the film's date (the v11 sound's gate): off for a film made before V11_FROM, on from it
    from kit.film import mix as MX
    Fm.LENS = None
    monkeypatch.setattr(MX, "made_on", lambda fm: "2026-10-12")
    assert B.lens_why(Fm) == (False, f"made on 2026-10-12, v11 from {MX.V11_FROM}") and B.lens_data(Fm, words)["on"] is False
    monkeypatch.setattr(MX, "made_on", lambda fm: MX.V11_FROM)
    assert B.lens_why(Fm)[0] is True and B.lens_data(Fm, words)["on"] is True
    Fm.LENS = False                                        # an explicit LENS wins over the date
    assert B.lens_why(Fm) == (False, "LENS in film.py")
    T = B.track_data(Fm, {"face": "assets/face.mp4", "room": "assets/room.mp4"})
    assert T["face"]["max_zoom"] == 1.0 and T["face"]["file"] == "assets/face.mp4" and T["room"] == {"file": "assets/room.mp4"}


def test_lens_faces_are_in_the_face_tracks_px(tmp_path):
    """D.lens.faces: the face track per output frame in the TRACK's px. A film reads work/<track>.face.json as is; a
    Reel's edl faces are in the film's page px (kit/film/reels.py: x film.W / track_w), so they are divided back
    (review 2026-10-22: a 1080 face track on a 1920 film read x1.78 off, the lens anchored beside his face)."""
    from kit.film import build as B

    class F:
        pass
    film = F()
    film.W = 1920
    Fm = F()
    Fm.work, Fm.FACE_TRACK, Fm.reel, Fm.parent = tmp_path, "face", "a", film
    track = [[556.0, 638.0, 273.0], None, [540.0, 600.0, 270.0]]          # YuNet in the 1080 track's px
    s = 1920 / 1080
    edl = {"tracks": {"room": [3840, 2160], "face": [1080, 1080]}, "faces": [[round(v * s, 1) for v in f] if f else None for f in track]}
    faces, px = B.lens_faces(Fm, edl)
    assert px == [1080, 1080] and faces[1] is None
    for got, want in zip(faces[::2], track[::2]):
        assert got == pytest.approx(want, abs=0.1)                      # back in source px
    Fm.reel, Fm.parent = None, None                                     # a film: the face track's own file
    (tmp_path / "face.face.json").write_text(json.dumps(track))
    faces, px = B.lens_faces(Fm, {"tracks": {"face": [1080, 1080]}})
    assert faces == track and px == [1080, 1080]
    assert B.lens_faces(Fm, {"tracks": {}})[0] == track                 # no size: faces_px unknown (canvas: fo.src)
    (tmp_path / "face.face.json").unlink()
    assert B.lens_faces(Fm, {"tracks": {"face": [1080, 1080]}}) == (None, None)
