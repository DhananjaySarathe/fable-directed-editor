"""A short digest of a checker's output: every error as printed, repeated warnings grouped, and the verdict line.

    python3 kit/qa/digest.py -- python3 kit/hf/plan_check.py films/<name>/visual_plan.json
    node kit/qa/precheck.mjs <hf>/index.html | python3 kit/qa/digest.py

plan_check on a long film prints 60 warnings, most of them one message about different passages. Read whole, they
fill the conversation; grouped, they are a dozen lines. Lines that start with ERROR, FAIL, CRITICAL or HIGH are kept
word for word. Lines that start with WARN, WARNING, MEDIUM, LOW, NIT or INFO are grouped when they say the same thing
about different items (numbers may differ): the first one is shown with the count and the items. The last line of the
output (the verdict) is always printed. With `--`, the command is run and its exit code is passed on.
"""
import re
import subprocess
import sys

KEEP = ("ERROR", "FAIL", "CRITICAL", "HIGH")
GROUP = ("WARNING", "WARN", "MEDIUM", "LOW", "NIT", "INFO")
LINE = re.compile(rf"^\s*\[?({'|'.join(KEEP + GROUP)})\]?:?\s+(.*\S)\s*$")


def digest(text):
    lines = [l for l in text.splitlines() if l.strip()]
    kept, groups, order = [], {}, []
    for l in lines[:-1] if lines else []:
        m = LINE.match(l)
        if not m:
            continue
        level, rest = m.group(1), m.group(2)
        if level in KEEP:
            kept.append(l.strip())
            continue
        item, sep, msg = rest.partition(": ")
        if not sep or len(item) > 40:
            item, msg = "", rest
        key = (level, re.sub(r"\d+(\.\d+)?", "#", msg))
        if key not in groups:
            groups[key] = {"level": level, "first": rest, "msg": msg, "items": []}
            order.append(key)
        groups[key]["items"].append(item)
    out = list(kept)
    for key in order:
        g = groups[key]
        n = len(g["items"])
        if n == 1:
            out.append(f"{g['level']}    {g['first']}")
        else:
            names = [i for i in g["items"] if i]
            shown = ", ".join(names[:12]) + (f" +{len(names) - 12} more" if len(names) > 12 else "")
            out.append(f"{g['level']} x{n}  {g['msg']}" + (f"  [{shown}]" if names else ""))
    if lines:
        out.append(lines[-1].strip())
    return out


def main():
    if "--" in sys.argv:
        cmd = sys.argv[sys.argv.index("--") + 1:]
        if not cmd:
            sys.exit(__doc__)
        r = subprocess.run(cmd, capture_output=True, text=True)
        print("\n".join(digest(r.stdout + ("\n" + r.stderr if r.stderr.strip() and r.returncode else ""))))
        sys.exit(r.returncode)
    if sys.stdin.isatty():
        sys.exit(__doc__)
    print("\n".join(digest(sys.stdin.read())))


if __name__ == "__main__":
    main()
