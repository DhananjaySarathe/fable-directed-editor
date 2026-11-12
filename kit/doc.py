"""Read one section of a long kit document instead of the whole file.

    python3 kit/doc.py kit/hf/README.md                 # the headings, with each section's size
    python3 kit/doc.py kit/hf/README.md "The lens"      # that section (its sub-sections included)
    python3 kit/doc.py kit/refs/EDITING.md 4 7          # sections by number: "## 4." and "## 7."
    python3 kit/doc.py kit/hf/README.md --find=takeover # headings whose section mentions a word, with a count

kit/hf/README.md is 93 KB (about 23,000 tokens) and an edit needs two or three of its sections. A section read costs
a few hundred tokens once; the whole file stays in the conversation and is paid for again on every later turn.
A name matches a heading that contains it, ignoring case. A number matches a heading that starts with it ("4." or "§4").
"""
import re
import sys
from pathlib import Path

HEAD = re.compile(r"^(#{1,4})\s+(.*\S)\s*$")


def sections(text):
    """[(level, title, first line, end line)]: a section runs to the next heading of the same or a higher level."""
    lines = text.splitlines()
    heads, fence = [], False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fence = not fence
        m = None if fence else HEAD.match(line)
        if m:
            heads.append((len(m.group(1)), m.group(2), i))
    out = []
    for k, (level, title, i) in enumerate(heads):
        end = next((j for lv, _, j in heads[k + 1:] if lv <= level), len(lines))
        out.append((level, title, i, end))
    return lines, out


def matches(title, want):
    t = title.lower().lstrip("§ ")
    if want.isdigit():
        return re.match(rf"{want}\b", t) is not None
    return want.lower() in title.lower()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    find = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--find=")), None)
    if not args:
        sys.exit(__doc__)
    path = Path(args[0])
    lines, secs = sections(path.read_text())
    if find:
        for level, title, a, b in secs:
            n = sum(find.lower() in l.lower() for l in lines[a:b])
            if n:
                print(f"{'  ' * (level - 1)}{title}  ({n}x)")
        return
    if len(args) == 1:
        print(f"{path}: {len(lines)} lines, {len(path.read_bytes()) // 1024} KB")
        for level, title, a, b in secs:
            print(f"{'  ' * (level - 1)}{title}  ({sum(len(l) + 1 for l in lines[a:b]) / 1024:.1f} KB)")
        return
    missing = []
    for want in args[1:]:
        hit = [s for s in secs if matches(s[1], want)]
        exact = [s for s in hit if s[1].lower() == want.lower()]
        hit = exact or hit[:1]                     # the first heading that contains the name
        if not hit:
            missing.append(want)
            continue
        _, _, a, b = hit[0]
        print("\n".join(lines[a:b]).rstrip() + "\n")
    if missing:
        sys.exit(f"no section matches: {', '.join(missing)} (run without a name to list the headings)")


if __name__ == "__main__":
    main()
