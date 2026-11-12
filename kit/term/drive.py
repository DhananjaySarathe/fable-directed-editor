"""Record a session you drive live, one command at a time (for answers you can only write after reading the screen).

    python kit/term/drive.py <out dir> <cwd> "<command>" [--cols 200 --rows 56] [--env K=V ...]

Append JSON lines to <out dir>/cmds.jsonl while it runs:
    {"type": "B"}  {"key": ["C-x", "Tab"]}  {"hold": 2}  {"wait": "regex", "timeout": 60}
    {"idle": 900}  {"mark": "label"}  {"end": true}
After each command the screen is written to <out dir>/screen.txt and a line to <out dir>/done.log.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from kit.term.rec import Session  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("cwd"); ap.add_argument("cmd")
ap.add_argument("--cols", type=int, default=200); ap.add_argument("--rows", type=int, default=56)
ap.add_argument("--env", action="append", default=[])
a = ap.parse_args()
env = dict(kv.split("=", 1) for kv in a.env)
out = Path(a.out).expanduser()
inbox = out.parent / f"{out.name}.cmds.jsonl"   # outside the out dir, which Session wipes on start
inbox.write_text("")

with Session(out, cwd=a.cwd, cmd=a.cmd, cols=a.cols, rows=a.rows, env=env, name=out.name) as s:
    seen = 0
    while True:
        lines = inbox.read_text().splitlines()
        if len(lines) <= seen:
            time.sleep(0.2)
            continue
        c = json.loads(lines[seen]); seen += 1
        if "type" in c: s.type(c["type"], cps=c.get("cps", 14))
        if "key" in c: s.key(*([c["key"]] if isinstance(c["key"], str) else c["key"]))
        if "hold" in c: s.hold(c["hold"])
        if "wait" in c: c["ok"] = s.wait_for(c["wait"], timeout=c.get("timeout", 60))
        if "idle" in c: c["ok"] = s.wait_idle(timeout=c["idle"])
        if "mark" in c: s.mark(c["mark"])
        (out.parent / f"{out.name}.screen.txt").write_text(s.screen())
        with open(out.parent / f"{out.name}.done.log", "a") as f:
            f.write(json.dumps(c) + "\n")
        if c.get("end"):
            break
