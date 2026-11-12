"""Vendor HyperFrames catalog components into the kit (kit/hf/catalog/), so a film can mount them (film.py MOUNTS,
kit/hf/mounts.py). The catalog (hyperframes.heygen.com/catalog, Apache-2.0, heygen-com/hyperframes) has 447 pieces;
the kit takes the ones that explain what this channel explains, and only those with the mount contract:

  - a <template> (the host clones it into the mount) and data-composition-variables (the content comes from the film);
  - no WebGPU (the renderer's headless Chrome has WebGL, not WebGPU);
  - the CDN GSAP <script> inside the template is removed: the page already has the kit's own GSAP, and a render must
    not depend on the network.

    python3 kit/hf/tools/catalog.py add cursor-zoom-follow agent-cursor ...    # hyperframes add -> check -> vendor
    python3 kit/hf/tools/catalog.py --list                                       # what is vendored, with its variables

The manifest kit/hf/catalog/catalog.json keeps each piece's variables, default length and what it explains (EXPLAINS:
curated here, read by kit/hf/tools/registry.py so the planner and precheck know them as `catalog.<name>`).
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
CAT = KIT / "catalog"
MANIFEST = CAT / "catalog.json"
CDN_GSAP = re.compile(r'\s*<script src="https://cdn\.jsdelivr\.net/npm/gsap@[^"]+"></script>')

# name: (explains, what it shows). Types as kit/refs/SCENES.md; looks: every look (the page's tokens reach it, mounts.py).
# Tried and left out (2026-10-20, kit/hf/demos/catalog sheet): pull-back-reveal (ships made-up figures its variables
# can't change: "no invented numbers"), chat-message (a black box around one bubble), ui-focus-zoom (zooms its own
# placeholder UI, no way to give it ours), press-ripple (nothing visible at half frame).
# FULL_FRAME pieces are laid out for 1920x1080: mount them with fit="scale" (mounts.py does it by default).
EXPLAINS = {
    "cursor-zoom-follow": (["instruction", "proof"], "screen-recording auto-zoom: a cursor clicks through your screenshot while the camera follows it in"),
    "agent-cursor": (["process", "mechanism"], "an AI agent's cursor works through named steps, a status chip saying what it is doing"),
    "cursor-text-select": (["proof", "emphasis"], "a cursor drags across a passage and selects the phrase that matters"),
    "headline-slam": (["emphasis"], "a headline slams in, one word in the accent"),
    "marker-highlight": (["emphasis", "definition"], "a line of type with one word swept by a marker"),
    "push-in": (["emphasis"], "a slow push in on one line: the camera leans in on a claim"),
    "decline-chart": (["quantity", "comparison"], "a value falls from start to end with its counter (real numbers only)"),
    "conic-progress-ring": (["quantity"], "a ring fills to a share, the figure in the middle (real numbers only)"),
    "chat-thread": (["conversation", "story"], "a phone chat: messages arrive with typing dots and read receipts"),
    "notes-typing": (["instruction", "process"], "a notes app types a list line by line"),
}


FULL_FRAME = {"headline-slam", "agent-cursor"}


def manifest() -> dict:
    return json.load(open(MANIFEST)) if MANIFEST.exists() else {}


def variables(html: str) -> list:
    m = re.search(r"data-composition-variables='(\[.*?\])'", html, re.S)
    return json.loads(m.group(1)) if m else []


def vendor(name: str, src: Path) -> dict:
    html = src.read_text()
    if "<template" not in html:
        raise SystemExit(f"{name}: no <template> (not a mountable component); not vendored")
    if re.search(r"navigator\.gpu|webgpu", html, re.I):
        raise SystemExit(f"{name}: needs WebGPU (the renderer has WebGL only); not vendored")
    html, n = CDN_GSAP.subn("", html)
    if "https://" in re.sub(r"https://(fonts\.googleapis\.com|fonts\.gstatic\.com|github\.com|hyperframes)[^\s\"')]*", "", html):
        print(f"NOTE {name}: still loads something over https (check it renders offline)")
    dur = re.search(r'data-composition-duration="([0-9.]+)"', html)
    (CAT / f"{name}.html").write_text(f"<!-- vendored from the HyperFrames catalog ({name}), Apache-2.0, kit/hf/catalog/NOTICE.md -->\n" + html)
    ex, what = EXPLAINS.get(name, ([], ""))
    return {"file": f"{name}.html", "duration": float(dur.group(1)) if dur else None, "explains": ex, "what": what,
            "vars": {v["id"]: v.get("default") for v in variables(html)},
            # a colour accent is filled with the film's look accent (mounts.py); an enum one (green/blue/violet) already
            # reads --brand/--accent/--accent-2, which HF.look sets from the look
            "accent_var": "accent" if any(v["id"] == "accent" and v.get("type") == "color" for v in variables(html)) else None,
            "cdn_gsap_removed": n, **({"fit": "scale"} if name in FULL_FRAME else {})}


def add(names: list[str]):
    CAT.mkdir(exist_ok=True)
    M = manifest()
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "hyperframes.json").write_text("{}")
        for name in names:
            r = subprocess.run(["npx", "hyperframes", "add", name, "--dir", tmp, "--no-clipboard", "--json"], capture_output=True, text=True,
                               stdin=subprocess.DEVNULL)
            try:
                info = json.loads(r.stdout)
            except json.JSONDecodeError:
                raise SystemExit(f"{name}: hyperframes add failed: {r.stderr[-300:]}")
            files = [Path(w) for w in info.get("written", []) if w.endswith(".html")]
            if not files:
                raise SystemExit(f"{name}: nothing written")
            M[name] = vendor(name, files[0])
            for w in info.get("written", []):                       # fonts or images a piece ships with
                p = Path(w)
                if "/assets/" in w:
                    dst = CAT / "assets" / p.relative_to(Path(tmp) / "assets")
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, dst)
            print(f"{name}: vendored ({M[name]['duration']} s; vars {', '.join(M[name]['vars'])})")
    MANIFEST.write_text(json.dumps(dict(sorted(M.items())), indent=1) + "\n")


def main():
    if "--list" in sys.argv:
        for k, v in manifest().items():
            print(f"{k:22s} {v['duration'] or '?':>5} s  {', '.join(v['explains']):24s} {v['what']}")
            print(f"{'':22s}        vars: {', '.join(f'{a}={b!r}'[:40] for a, b in v['vars'].items())}")
        return
    if len(sys.argv) > 2 and sys.argv[1] == "add":
        return add(sys.argv[2:])
    print(__doc__)


if __name__ == "__main__":
    main()
