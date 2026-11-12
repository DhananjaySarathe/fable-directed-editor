"""kit/hf/box.js (the speaker box): plan, states, the director's rules, pace. Runs the page script in Node."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

HF = Path(__file__).resolve().parents[1] / "kit/hf"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="needs node")


def run(js: str):
    """Evaluate js with HF.motion + HF.box loaded; js sets `out`, returned as JSON."""
    src = (
        "const fs=require('fs'),vm=require('vm');const ctx=vm.createContext({console,Math});"
        f"for (const f of ['motion.js','box.js']) vm.runInContext(fs.readFileSync({json.dumps(str(HF))}+'/'+f,'utf8'),ctx);"
        "ctx.out=null;vm.runInContext(" + json.dumps(js) + ",ctx);process.stdout.write(JSON.stringify(ctx.out));"
    )
    r = subprocess.run(["node", "-e", src], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_full_frame_is_identity_and_card_sways_within_limits():
    out = run("""
      const B = HF.box, P = B.plan({ shots: [{ t: 0, at: 'full' }, { t: 2, at: 'right', in: 'shrink' }] });
      const f = B.at(P, 1.0), I = B.inner(1920, 1080, [945, 300], 1);
      const rots = []; for (let t = 2.2; t < 8; t += 0.1) rots.push(B.at(P, t).rot);
      out = { f, I, lo: Math.min(...rots), hi: Math.max(...rots), mid: B.at(P, 2.06) };
    """)
    assert out["f"]["w"] == 1 and out["f"]["rot"] == 0
    assert out["I"] == {"s": 1, "tx": 0, "ty": 0}
    assert 1.8 - 0.41 <= out["lo"] < out["hi"] <= 1.8 + 0.41          # sway +-0.4 deg around the slot's tilt
    assert out["mid"]["kind"] == "shrink" and out["mid"]["w"] < 0.75   # expo out: most of the travel in the first half


def test_shots_that_overlap_a_move_are_refused():
    r = subprocess.run(["node", "-e", "const fs=require('fs'),vm=require('vm');const c=vm.createContext({console,Math});"
                        f"for (const f of ['motion.js','box.js']) vm.runInContext(fs.readFileSync({json.dumps(str(HF))}+'/'+f,'utf8'),c);"
                        "vm.runInContext(\"HF.box.plan({shots:[{t:0,at:'full'},{t:1,at:'pill',in:'collapse'},{t:1.2,at:'off',in:'cut'}]})\",c)"],
                       capture_output=True, text=True)
    assert r.returncode != 0 and "before the move" in r.stderr


def test_director_rules():
    out = run("""
      const D = HF.box.direct({ beats: [
        { t: 0, show: 'face' }, { t: 3, show: 'graphic', card: true }, { t: 6, show: 'punch', section: true },
        { t: 9, show: 'beside', side: 'left' }, { t: 12, show: 'graphic' }, { t: 15, show: 'punch', section: true },
        { t: 18, show: 'graphic', card: true }, { t: 21, show: 'beside', side: 'right', card: true },
        { t: 24, show: 'graphic' }, { t: 27, show: 'aside', side: 'left', card: true } ] });
      out = D.shots.map((s) => [s.t, s.at, s.in]);
    """)
    moves = {round(t): (at, mv) for t, at, mv in out}
    assert moves[3] == ("off", "collapse")             # full -> a graphic that starts as a card
    assert moves[6] == ("full", "tiles")               # back to the face at a section
    assert moves[9] == ("right", "shrink")             # content on the left -> the card on the right
    assert moves[12] == ("off", "slide")               # a side card leaves off its own side
    assert moves[15] == ("full", "grow")               # tiles budget: <= 1 per 20 s
    assert moves[21] == ("left", "flip")               # a card turns over into the face
    assert moves[27] == ("rightSmall", "swing")        # flip budget: <= 1 per 25 s


def test_pace_reports_face_share_and_absence():
    out = run("""
      const P = HF.box.plan({ shots: [{ t: 0, at: 'full' }, { t: 2, at: 'off', in: 'dissolve' }, { t: 8, at: 'left', in: 'swing' }] });
      out = HF.box.pace(P, 10);
    """)
    assert 0.38 < out["faceShare"] < 0.45 and 5.7 < out["maxAway"] < 6.1 and out["moves"] == 2


def test_collapse_off_lands_on_the_pill_then_hands_over():
    out = run("""
      const B = HF.box, P = B.plan({ shots: [{ t: 0, at: 'full' }, { t: 2, at: 'off', in: 'collapse' }] });
      out = { end: B.at(P, 2.29), after: B.at(P, 2.5), pill: B.SLOTS['16:9'].pill };
    """)
    assert abs(out["end"]["w"] - out["pill"]["w"]) < 0.01 and out["end"]["op"] == 1 and out["end"]["tint"] == 1
    assert out["after"]["op"] == 0
