"""kit/hf/explain.js + polish.js (pure parts) and the real-data tools behind them."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HF = ROOT / "kit/hf"
node = pytest.mark.skipif(shutil.which("node") is None, reason="needs node")

RACE = {"source": "test", "board": "code", "metric": "m", "dates": ["d0", "d1", "d2"],
        "series": [{"name": "A", "values": [100, 110, 120]}, {"name": "B", "values": [90, 130, 125]}, {"name": "C", "values": [None, 95, 140]}]}


def run(js: str):
    src = ("const fs=require('fs'),vm=require('vm');const ctx=vm.createContext({console,Math});"
           f"for (const f of ['core.js','explain.js','polish.js']) vm.runInContext(fs.readFileSync({json.dumps(str(HF))}+'/'+f,'utf8'),ctx);"
           "ctx.out=null;vm.runInContext(" + json.dumps(js) + ",ctx);process.stdout.write(JSON.stringify(ctx.out));")
    r = subprocess.run(["node", "-e", src], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@node
def test_race_ranks_swap_and_a_newcomer_is_not_ranked_before_it_appears():
    out = run(f"""const d = {json.dumps(RACE)};
      out = [0, 1, 2].map((u) => HF.raceRanks(HF.raceState(d, u))).concat([HF.raceState(d, 0.5).map((s) => [s.name, s.vis])]);""")
    assert out[0] == {"A": 0, "B": 1}                         # C has no entry on d0 and isn't ranked (it appears on d1)
    assert out[1] == {"B": 0, "A": 1, "C": 2}                 # B overtakes A
    assert out[2] == {"C": 0, "B": 1, "A": 2}
    vis = dict(out[3])
    assert vis["A"] == 1 and 0 < vis["C"] < 1                 # C fades in between d0 and d1


@node
def test_scramble_is_deterministic_and_ends_on_the_text():
    out = run("""const a = HF.scrambleAt('Claude Opus 5.5', 0.5, 12, 3), b = HF.scrambleAt('Claude Opus 5.5', 0.5, 12, 3);
      out = { a, b, end: HF.scrambleAt('Claude Opus 5.5', 1, 40, 3), start: HF.scrambleAt('Claude Opus 5.5', 0, 0, 3, 'x'),
              spaces: HF.scrambleAt('a b c', 0.3, 5, 1).split('').filter((c) => c === ' ').length };""")
    assert out["a"] == out["b"] and out["a"] != "Claude Opus 5.5"
    assert out["end"] == "Claude Opus 5.5" and out["start"] == "x" and out["spaces"] == 2


def test_arena_race_tool_picks_each_labs_best_and_keeps_the_last_date(tmp_path):
    snap = {"d": {"2026-01-01": [("A", "m1", 100), ("A", "m2", 105), ("B", "m3", 90)], "2026-01-08": [("A", "m1", 101), ("B", "m3", 120)],
                  "2026-01-10": [("A", "m1", 103), ("B", "m3", 99), ("C", "m4", 98)]}}
    for day, rows in snap["d"].items():
        (tmp_path / day).mkdir()
        (tmp_path / day / "code.json").write_text(json.dumps({"meta": {}, "models": [{"vendor": v, "model": m, "score": s} for v, m, s in rows]}))
    out = tmp_path / "race.json"
    subprocess.run([sys.executable, str(HF / "tools/arena_race.py"), str(tmp_path), "--board", "code", "--every", "2", "--top", "3", "-o", str(out)],
                   check=True, capture_output=True)
    R = json.loads(out.read_text())
    assert R["dates"] == ["2026-01-01", "2026-01-10"]          # every 2nd day plus the last one
    by = {s["name"]: s["values"] for s in R["series"]}
    assert by == {"A": [105, 103], "B": [90, 99], "C": [None, 98]}


def test_registry_lists_the_new_components_with_existing_fallbacks():
    reg = json.loads((HF / "registry.json").read_text())["components"]
    for cid in ("tokens", "stack", "race", "tiltIn", "sweep", "scramble"):
        c = reg[cid]
        assert (HF / c["file"]).exists()
        if (HF / "previews").is_dir():                   # the shareable copy leaves the previews out (they show the author)
            assert (HF / c["preview"]).exists()
        assert c["fallback"] is None or c["fallback"] in reg or (ROOT / "kit/graphics" / c["fallback"]).exists()
