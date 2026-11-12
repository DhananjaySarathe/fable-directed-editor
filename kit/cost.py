"""What an edit cost: tokens and list-price dollars per model, from Claude Code's own session logs.

    uv run python kit/cost.py                              # sessions of this project, newest first
    uv run python kit/cost.py --grep=fable-52-experiments  # every session (any project) that mentions this text
    uv run python kit/cost.py --session=be0e65dd           # one session (id prefix), with its subagents
    uv run python kit/cost.py --since=2026-11-01 --all     # every project since a date
    uv run python kit/cost.py --limit=1 --crew             # the latest session, with who worked on it (below)
    uv run python kit/cost.py ... --json=out.json          # also write the numbers

Reads ~/.claude/projects/<project>/<session>.jsonl and <session>/subagents/agent-*.jsonl. A model message is logged as
several lines (one per content block) that repeat the same usage, so usage is counted once per message id.
Under each session it says where the money went: re-reading the conversation on every turn (cache reads, which grow with
the context a session carries), new context (tool output, files and images read once: cache writes and input), and
output with thinking. Prices are the Anthropic list prices per million tokens (platform.claude.com/docs/en/about-claude/pricing, read
2026-11-11). A plan subscription bills differently: these dollars compare models, they are not an invoice.

--crew adds, per session, the agents the main session started (by type), the project's agents it never started, and
the checks the main session ran itself (precheck, plan_check, qa.py, cutcheck, joins). In this project check sweeps
belong to qa-reader and fix lists to edit-builder (skill fable-director, "Handing down is the default"), so a director
that ran 80 checks with no qa-reader in the crew did the cheap work at the expensive price.
"""
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / ".claude" / "projects"
HERE = Path(__file__).resolve().parents[1]

# $ per MTok: input, output, 5 min cache write, 1 h cache write, cache read
PRICES = {
    "claude-fable-5-2": (8, 40, 10, 16, 0.20),
    "claude-fable-5-1": (10, 50, 12.5, 20, 0.25),
    "claude-fable-5": (10, 50, 12.5, 20, 1.0),
    "claude-opus-5-5": (4, 20, 5, 8, 0.20),
    "claude-opus-5": (5, 25, 6.25, 10, 0.50),
    "claude-opus-4-8": (5, 25, 6.25, 10, 0.50),
    "claude-sonnet-5-5": (2, 10, 2.5, 4, 0.10),
    "claude-sonnet-5": (2, 10, 2.5, 4, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, 0.125, 0.20, 0.01),   # prompts over 100K tokens: x5 (handled below)
    "claude-haiku-4-5": (1, 5, 1.25, 2, 0.10),
}


def arg(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith(f"--{name}=")), default)


def flag(name):
    return f"--{name}" in sys.argv[1:]


def project_dir(path):
    return "-" + str(path).strip("/").replace("/", "-").replace(" ", "-")


def price(model, u):
    p = PRICES.get(model)
    if not p:
        return None
    cw = u.get("cache_creation") or {}
    w5, w1 = cw.get("ephemeral_5m_input_tokens"), cw.get("ephemeral_1h_input_tokens")
    if w5 is None and w1 is None:
        w5, w1 = u.get("cache_creation_input_tokens", 0), 0
    inp, out, read = u.get("input_tokens", 0), u.get("output_tokens", 0), u.get("cache_read_input_tokens", 0)
    scale = (5 if model == "claude-haiku-5-5" and inp + read + (w5 or 0) + (w1 or 0) > 100_000 else 1) / 1e6
    return {"in": scale * inp * p[0], "out": scale * out * p[1], "write": scale * ((w5 or 0) * p[2] + (w1 or 0) * p[3]),
            "read": scale * read * p[4]}


def read_log(path):
    """{message id: (model, usage)} plus first/last timestamps and the session title."""
    msgs, t0, t1, title = {}, None, None, None
    with open(path, errors="replace") as fh:
        for line in fh:
            if '"usage"' not in line and '"custom-title"' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") == "custom-title":
                title = d.get("customTitle") or title
                continue
            m = d.get("message")
            if not isinstance(m, dict) or not m.get("usage") or not m.get("model") or m["model"].startswith("<"):
                continue
            msgs[m.get("id") or d.get("uuid")] = (m["model"], m["usage"])
            ts = d.get("timestamp")
            if ts:
                t0, t1 = min(t0 or ts, ts), max(t1 or ts, ts)
    return msgs, t0, t1, title


def tally(msgs):
    by = defaultdict(lambda: {"messages": 0, "input": 0, "output": 0, "thinking": 0, "cache_write": 0, "cache_read": 0, "usd": 0.0,
                              "usd_in": 0.0, "usd_out": 0.0, "usd_write": 0.0, "usd_read": 0.0, "priced": True})
    for model, u in msgs.values():
        r = by[model]
        r["messages"] += 1
        r["input"] += u.get("input_tokens", 0)
        r["output"] += u.get("output_tokens", 0)
        r["thinking"] += (u.get("output_tokens_details") or {}).get("thinking_tokens", 0)
        r["cache_write"] += u.get("cache_creation_input_tokens", 0)
        r["cache_read"] += u.get("cache_read_input_tokens", 0)
        c = price(model, u)
        if c is None:
            r["priced"] = False
        else:
            r["usd"] += sum(c.values())
            for k, v in c.items():
                r["usd_" + k] += v
    return dict(by)


# a check the main session ran itself: what it is called -> how its command looks
CHECKS = {"precheck": r"node\s+\S*precheck\.mjs|kit\.(?:film|reel)\s+\S+\s+precheck\b",
          "plan_check": r"python\S*\s+\S*plan_check\.py\s+(?!--help)\S",
          "qa.py": r"python\S*\s+\S*qa\.py\b",
          "cutcheck": r"kit\.cut\.cutcheck\b",
          "joins": r"kit\.(?:film|reel)\s+\S+\s+joins\b|kit\.cut\.relisten\b"}


def crew(path, agents_dir=None):
    """Who worked in a session: the agents its main session started, by type, the project's agents it never started,
    and the checks it ran itself. Read from the main log's tool calls (each call counted once, by its id)."""
    started, checks, seen = defaultdict(int), defaultdict(int), set()
    with open(path, errors="replace") as fh:
        for line in fh:
            if '"tool_use"' not in line:
                continue
            try:
                m = json.loads(line).get("message")
            except ValueError:
                continue
            for c in (m.get("content") if isinstance(m, dict) and isinstance(m.get("content"), list) else []):
                if not isinstance(c, dict) or c.get("type") != "tool_use" or c.get("id") in seen:
                    continue
                seen.add(c.get("id"))
                inp = c.get("input") or {}
                if c.get("name") in ("Agent", "Task"):
                    started[inp.get("subagent_type") or "general-purpose"] += 1
                elif c.get("name") == "Bash":
                    for name, rx in CHECKS.items():
                        if re.search(rx, inp.get("command") or ""):
                            checks[name] += 1
    agents_dir = agents_dir or HERE / ".claude" / "agents"
    known = sorted(p.stem for p in agents_dir.glob("*.md")) if agents_dir.is_dir() else []
    return {"started": dict(started), "never": [a for a in known if a not in started], "checks": dict(checks)}


def session(path, with_crew=False):
    msgs, t0, t1, title = read_log(path)
    subs = []
    sub_dir = path.with_suffix("") / "subagents"
    for sp in sorted(sub_dir.glob("agent-*.jsonl")) if sub_dir.is_dir() else []:
        m, s0, s1, _ = read_log(sp)
        meta = sp.with_suffix(".meta.json")
        info = json.loads(meta.read_text()) if meta.exists() else {}
        subs.append({"agent": info.get("agentType", "?"), "description": info.get("description", sp.stem), "models": tally(m)})
    out = {"session": path.stem, "project": path.parent.name, "title": title, "start": t0, "end": t1,
           "main": tally(msgs), "subagents": subs}
    if with_crew:
        out["crew"] = crew(path)
    return out


def crew_lines(c, turns):
    """The two lines --crew prints under a session."""
    ran = ", ".join(f"{a} {n}" for a, n in sorted(c["started"].items(), key=lambda kv: (-kv[1], kv[0]))) or "no agents"
    lines = [f"  crew: {ran}." + (f" Never started: {', '.join(c['never'])}." if c["never"] else "")]
    n = sum(c["checks"].values())
    if n:
        kinds = ", ".join(f"{k} {v}" for k, v in sorted(c["checks"].items(), key=lambda kv: -kv[1]))
        owed = [a for a in ("qa-reader", "edit-builder") if a in c["never"]]
        lines.append(f"  the main session ran {n} checks itself ({kinds}) in {turns} turns."
                     + (f" Sweeps belong to qa-reader and fix lists to edit-builder: {' and '.join(owed)} never ran." if owed else ""))
    return lines


def usd(models):
    return sum(r["usd"] for r in models.values())


def mtok(n):
    return f"{n / 1e6:.2f}M" if n >= 1e5 else f"{n / 1e3:.0f}k"


def show(s):
    hours = ""
    if s["start"] and s["end"]:
        a, b = (datetime.fromisoformat(x.replace("Z", "+00:00")) for x in (s["start"], s["end"]))
        hours = f", {(b - a).total_seconds() / 3600:.1f} h"
    total = usd(s["main"]) + sum(usd(x["models"]) for x in s["subagents"])
    print(f"\n{s['session'][:8]}  {s['title'] or '(untitled)'}  [{s['project']}]  {(s['start'] or '')[:16]}{hours}  ${total:.2f}")
    rows = [("main", "", s["main"])] + [(x["agent"], x["description"], x["models"]) for x in s["subagents"]]
    for who, desc, models in rows:
        for model, r in sorted(models.items(), key=lambda kv: -kv[1]["usd"]):
            cost = f"${r['usd']:.2f}" + ("" if r["priced"] else " (no price)")
            label = f"{who}: {desc}"[:44]
            print(f"  {label:44s} {model:20s} {r['messages']:4d} msgs  out {mtok(r['output']):>6s} (think {mtok(r['thinking'])})"
                  f"  read {mtok(r['cache_read']):>6s}  write {mtok(r['cache_write']):>6s}  {cost:>9s}")
    every = [r for _, _, models in rows for r in models.values()]
    if total > 0:
        part = lambda k: sum(r["usd_" + k] for r in every)
        main_msgs = sum(r["messages"] for r in s["main"].values())
        context = sum(r["input"] + r["cache_read"] + r["cache_write"] for r in s["main"].values()) / max(1, main_msgs)
        print(f"  where it went: re-reading the conversation ${part('read'):.2f} ({part('read') / total:.0%}), new context ${part('write') + part('in'):.2f} "
              f"({(part('write') + part('in')) / total:.0%}), output and thinking ${part('out'):.2f} ({part('out') / total:.0%}). "
              f"The main session carried {mtok(context)} tokens of context a turn on average.")
    if s.get("crew"):
        print("\n".join(crew_lines(s["crew"], sum(r["messages"] for r in s["main"].values()))))


def main():
    if flag("help") or flag("h"):
        sys.exit(__doc__)
    dirs = [d for d in ROOT.iterdir() if d.is_dir()] if (flag("all") or arg("grep")) else [ROOT / project_dir(HERE)]
    logs = [p for d in dirs for p in d.glob("*.jsonl")]
    if arg("session"):
        logs = [p for p in logs if p.stem.startswith(arg("session"))]
    if arg("grep"):
        needle = arg("grep")
        def mentions(p):
            files = [p] + list((p.with_suffix("") / "subagents").glob("agent-*.jsonl"))
            return any(needle in f.read_text(errors="replace") for f in files if f.exists())
        logs = [p for p in logs if mentions(p)]
    out = [session(p, with_crew=flag("crew")) for p in logs]
    if arg("since"):
        out = [s for s in out if (s["end"] or "") >= arg("since")]
    out.sort(key=lambda s: s["start"] or "", reverse=True)
    out = [s for s in out if s["main"] or s["subagents"]]
    for s in out[: int(arg("limit", 30))]:
        show(s)
    grand = defaultdict(float)
    for s in out:
        for models in [s["main"]] + [x["models"] for x in s["subagents"]]:
            for model, r in models.items():
                grand[model] += r["usd"]
    print(f"\n{len(out)} sessions. By model: " + ", ".join(f"{m} ${v:.2f}" for m, v in sorted(grand.items(), key=lambda kv: -kv[1])))
    if arg("json"):
        Path(arg("json")).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
