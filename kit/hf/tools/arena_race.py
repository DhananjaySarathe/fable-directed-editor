"""Leaderboard-race data for HF.race (kit/hf/explain.js) from real Arena (LMArena) snapshots: each lab's best model score
on one board, sampled over time. Never type race numbers by hand.

    git clone --depth 1 https://github.com/oolong-tea-2026/arena-ai-leaderboards arena     # daily snapshots, MIT
    python3 kit/hf/tools/arena_race.py arena/data --board code --every 14 --top 6 -o race.json [--by model]

--board  text | code | vision | document | search | text-to-image | ... (one JSON per board per day)
--by     vendor (default: each lab's best model that day) or model (individual models; noisier, renames break lines)
--every  keep one snapshot every N days (plus the last one)
Output: { source, board, metric, dates: [...], series: [{ name, values: [...] }] } (null where a lab has no entry)
"""
import argparse
import json
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("data", help="the snapshots folder (data/ in the arena-ai-leaderboards repo)")
    ap.add_argument("--board", default="text")
    ap.add_argument("--by", default="vendor", choices=["vendor", "model"])
    ap.add_argument("--every", type=int, default=14)
    ap.add_argument("--top", type=int, default=6, help="how many names to keep: the best on the last date")
    ap.add_argument("--from", dest="since", default="")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    days = sorted(d for d in Path(a.data).iterdir() if d.is_dir() and (d / f"{a.board}.json").exists() and d.name >= a.since)
    if not days:
        sys.exit(f"no {a.board}.json snapshots under {a.data}")
    keep = days[:: a.every]
    if keep[-1] != days[-1]:
        keep.append(days[-1])
    table = {}
    for d in keep:
        best = {}
        for m in json.loads((d / f"{a.board}.json").read_text())["models"]:
            k = m["vendor"] if a.by == "vendor" else m["model"]
            if m.get("score") is not None and m["score"] > best.get(k, -1e9):
                best[k] = m["score"]
        table[d.name] = best
    last = table[keep[-1].name]
    names = sorted(last, key=lambda k: -last[k])[: a.top]
    R = {"source": "Arena (LMArena) daily snapshots via github.com/oolong-tea-2026/arena-ai-leaderboards", "board": a.board,
         "metric": f"best Arena score per {a.by}", "dates": [d.name for d in keep],
         "series": [{"name": n, "values": [table[d.name].get(n) for d in keep]} for n in names]}
    if a.out:
        Path(a.out).write_text(json.dumps(R, indent=1) + "\n")
    print(f"{a.board}: {len(keep)} dates {keep[0].name} .. {keep[-1].name}")
    for s in R["series"]:
        print(f"  {s['name']:<18} " + " ".join("  -  " if v is None else f"{v:5.0f}" for v in s["values"]))


if __name__ == "__main__":
    main()
