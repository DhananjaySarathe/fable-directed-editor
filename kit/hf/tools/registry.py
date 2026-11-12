"""Generate kit/hf/registry.json from the kit itself, so the planner and precheck know every component (2026-10-20,
kit/refs/AUDIT_2026-10-20.md: the hand-written registry listed 25 paper_studio-era ids and missed ~90 newer ones, so
plan_check.py rejected the newer components and edits never planned with them).

    python3 kit/hf/tools/registry.py            # the table: every component, its looks, how many films used it
    python3 kit/hf/tools/registry.py --write    # rewrite kit/hf/registry.json
    python3 kit/hf/tools/registry.py --check    # exit 1 if registry.json is stale (a component missing, or no looks/explains)
    python3 kit/hf/tools/registry.py --unused   # the components no film has used yet (pick from these first)

Where entries come from:
  - the API each module documents in its header (`HF.diagram(...)`, `ui.pr(...)`, `A.inbox(...)`, `sc.week(...)`): the
    call and the module. A component the header doesn't document isn't one: document it there first.
  - META below (curated): what each explains (the types in kit/refs/SCENES.md §2) and words_only.
  - looks: the module's home look (HOME below), every look for the components that read the look's tokens
    (THEMED_*: kit/hf/demos/looks checks them in all six), plus every look a film has actually used it in (films/**/template.html,
    the look read from the frame it builds: HF.studio / HF.reel = pastel_box, HF.night, HF.redline, HF.canvas, HF.paper,
    else paper_studio). used_in lists those films.
  - match: how precheck's ambition section finds a call in a film's script (`needs`: the factory that must be called too).
  - the old hand-written fields (inputs, timing, preview, rule, fallback, version) are kept for the ids that had them.
"""
import json
import re
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
HF_DIR = KIT / "hf"
REG = HF_DIR / "registry.json"
FILMS = KIT.parent / "films"

# components that take the active look's tokens (HF.look, 2026-10-20, kit/refs/AUDIT_2026-10-20.md §6): they work in every
# look. kit/hf/demos/looks draws ui.pr / checklist / note / stamp, scoreboard, flow, code, compare, sketch, stickman and a
# marker note in all seven (whitespace twice: through HF.canvas and HF.studio) and checks contrast; the rest of each
# module reads the same tokens. whitespace (2026-10-22): the white page (kit/presets/whitespace)
LOOKS_ALL = ["pastel_box", "canvas_studio", "redline", "night", "paper_studio", "paper_collage", "whitespace"]
THEMED_MODULES = {"shaders.js", "studio_ui.js", "evidence.js", "code.js", "diagram.js", "sketch.js", "annotate.js", "scribble.js", "../stickman/stickman.js"}
THEMED_IDS = {"compare", "chat", "card", "pill", "win", "lowerThird", "stickman", "morph", "shake", "drawIcon", "kinetic"}
# module -> (id prefix, the factory that has to be called first (regex), home looks, ratios)
HOME = {
    "scenes.js": ("", None, ["paper_studio"], ["16:9", "9:16"]),
    "code.js": ("", None, ["paper_studio"], ["16:9", "9:16"]),
    "explain.js": ("", None, ["paper_studio"], ["16:9"]),
    "diagram.js": ("", None, ["paper_studio"], ["16:9", "9:16"]),
    "screen.js": ("", None, ["paper_studio"], ["16:9", "9:16"]),
    "polish.js": ("", None, ["paper_studio"], ["16:9", "9:16"]),
    "kinetic.js": ("", None, ["paper_studio"], ["16:9", "9:16"]),
    "shaders.js": ("", None, ["paper_studio"], ["16:9", "9:16"]),
    "emoji.js": ("", None, LOOKS_ALL, ["16:9", "9:16"]),
    "parallax.js": ("", None, LOOKS_ALL, ["16:9", "9:16"]),
    "sketch.js": ("", None, ["paper_studio"], ["16:9", "9:16"]),
    "annotate.js": ("", None, ["paper_studio"], ["16:9", "9:16"]),
    "scribble.js": ("", None, ["paper_studio"], ["16:9", "9:16"]),
    "collage.js": ("", None, ["paper_studio", "paper_collage"], ["16:9", "9:16"]),
    "box.js": ("", None, ["pastel_box"], ["16:9", "9:16"]),
    "studio.js": ("", r"HF\.(studio|reel)\s*\(", ["pastel_box", "whitespace"], ["16:9", "9:16"]),   # { look: "whitespace" }
    "studio_ui.js": ("ui.", r"HF\.(studio|reel)\s*\(", ["pastel_box"], ["16:9", "9:16"]),
    "evidence.js": ("", r"HF\.(studio|reel)\s*\(", ["pastel_box"], ["16:9", "9:16"]),
    "reel.js": ("sc.", r"HF\.reel\s*\(", ["pastel_box"], ["9:16"]),
    "footage.js": ("footage.", r"HF\.footage\s*\(", ["pastel_box"], ["9:16"]),
    "agent.js": ("agent.", r"HF\.agent\s*\(", ["pastel_box"], ["9:16"]),
    "night.js": ("night.", r"HF\.night\s*\(", ["night"], ["16:9"]),
    "night_reel.js": ("nightReel.", r"HF\.nightReel\s*\(", ["night"], ["9:16"]),
    "redline.js": ("redline.", r"HF\.redline\s*\(", ["redline"], ["16:9", "9:16"]),
    "canvas.js": ("canvas.", r"HF\.canvas\s*\(", ["canvas_studio", "whitespace"], ["16:9"]),   # { look: "whitespace" }
    # transitions (2026-10-22, kit v11): T = HF.trans(K, C) on a canvas, or HF.trans(K, S) / S.trans() on HF.studio / HF.reel
    "trans.js": ("trans.", r"HF\.trans\s*\(|\bS\.trans\s*\(", ["canvas_studio", "whitespace", "pastel_box"], ["16:9", "9:16"]),
    "paper.js": ("paper.", r"HF\.paper\s*\(", ["paper_collage"], ["9:16", "16:9"]),
}
# the object a header's calls are made on, per module (A = HF.agent(...), N = HF.night(...), ...)
OBJ = {"studio_ui.js": "ui", "reel.js": "sc", "footage.js": "F", "agent.js": "A", "night.js": "N", "night_reel.js": "N",
       "redline.js": "R", "canvas.js": "C", "paper.js": "P", "evidence.js": "S", "trans.js": "T"}
# calls that build a frame or are plumbing, not something the viewer sees as a component
PLUMBING = {"kit", "stage", "studio", "reel", "studioUI", "reelScenes", "agent", "footage", "night", "nightReel", "redline", "canvas",
            "paper", "HANDLES", "highlight", "land", "leave", "spring", "stagger", "bezier", "esc", "icon", "keyed", "lerpObj",
            "accentTokens", "motion", "hold", "layer", "captions", "theme", "light", "dim", "skip", "page", "bg", "at", "dof", "cmd",
            "line_", "rect", "trans", "whip", "cut", "pick", "list", "check", "log"}
# built into HF.studio / HF.reel (S.say, S.strike, ...): documented in studio.js's body, not as header calls
BUILTIN = {
    "say": ("studio.js", "say(par, fromId, toId, { x, y, w, size, stress, br })", r"\bsay\s*\("),
    "line": ("studio.js", "line(par, \"text with *accent\", t0, { x, y, w, size })", r"\bline\s*\("),
    "strike": ("studio.js", "strike(par, x, y, w, t, target, col, until)", r"\bstrike\s*\("),
    "fromPill": ("studio.js", "fromPill(L, t, x, y, w, h)", r"\bfromPill\s*\("),
    "arrow": ("studio.js", "arrow(par, x0, y0, x1, y1, t)", r"\b(?:S\.)?arrow\s*\("),
    "studio.chapter": ("studio.js", "chapter(t0, t1, num, title, sub, k)", r"\b(?:S\.)?chapter\s*\("),
    "studio.endCard": ("studio.js", "S.endCard({ at, title, slots, handles })", r"\b(?:S\.)?endCard\s*\("),
    "box.morph": ("box.js", "HF.box.morph(K, el, from, to, t, dur)", r"\bHF\.box\.morph\s*\("),
    # takeovers (2026-10-22, kit v11; kit/hf/trans.js): a full-screen scene with him off, by kind, on any frame (C.takeover
    # on a canvas, S.takeover on HF.studio / HF.reel); the planner picks the kind, the frame gives it its paper and camera
    "takeover.type": ("trans.js", "C.takeover(a, b, { kind: \"type\", text: \"Neat beats *busy.*\", kicker, mark: { word, t, kind }, sub, then })", r"kind\s*:\s*[\"']type[\"']"),
    "takeover.diagram": ("trans.js", "C.takeover(a, b, { kind: \"diagram\", type, title, nodes: [{ id, label, sub, focal, at }], edges: [[from, to, t]] or { from, to, t, label, accent }, focus }) (flat on whitespace)", r"kind\s*:\s*[\"']diagram[\"']"),
    "takeover.evidence": ("trans.js", "C.takeover(a, b, { kind: \"evidence\", img | html, url, mark: [x, y, w, h], markAt, note })", r"kind\s*:\s*[\"']evidence[\"']"),
    "takeover.list": ("trans.js", "C.takeover(a, b, { kind: \"list\", kicker, title, items: [[text, t], ...] })", r"kind\s*:\s*[\"']list[\"']"),
    "stickman": ("../stickman/stickman.js", "Stickman.create(svg, { x, ground, scale }); fig.to(t, pose)", r"\bStickman\.\w+\s*\("),
}

# the hand-written ids whose call isn't HF.<id>(...)
OLD_MATCH = {"words": r"\bK\.words\s*\(", "box": r"\b(?:HF|S)\.box\s*\("}
# trans.js calls whose names other objects share (String.prototype.match; S.chapter, HF.chapter): counted only on the
# variable HF.trans(...) / S.trans() was assigned to (a backreference; JS RegExp reads it the same; review 2026-10-22:
# \w+\.match\( counted every string match on a page that also made a T)
ANCHORED = {f"trans.{n}": rf"\b(\w+)\s*=\s*\w+\.trans\s*\([\s\S]*?\b\1\.{n}\s*\(" for n in ("match", "chapter")}

T = lambda s: s.split()  # noqa: E731
# what each component explains (kit/refs/SCENES.md §2); words_only: it is type, not a picture (plan_check's words-only share)
META = {
    # paper_studio era (scenes.js, code.js, explain.js, diagram.js, screen.js, polish.js)
    "camera": T("structure emphasis"), "card": T("definition proof"), "chapter": T("structure"), "chat": T("conversation"),
    "compare": T("comparison"), "endCard": T("ask"), "insert": T("proof instruction"), "lowerThird": T("structure definition"),
    "pill": T("definition emphasis"), "scroll": T("proof instruction"), "side": T("definition emphasis"), "win": T("proof instruction"),
    "phone": T("proof instruction"), "code": T("code mechanism"), "terminal": T("code proof"), "diagram": T("process relationship mechanism chronology structure"),
    "screen": T("instruction proof"), "tokens": T("mechanism"), "stack": T("structure mechanism"), "race": T("quantity chronology"),
    "tiltIn": T("instruction proof"), "sweep": T("emphasis"), "scramble": T("emphasis"), "words": T("definition emphasis"),
    "box": T("structure"), "stickman": T("story analogy relationship"),
    # v7 hand-made styles, v8 kinetic type
    "sketch": T("process relationship quantity comparison"), "annotate": T("proof code instruction"), "scribble": T("emphasis story"),
    "collage": T("proof comparison story"), "kinetic": T("emphasis definition"),
    "morph": T("comparison emphasis"), "shake": T("emphasis"), "drawIcon": T("structure emphasis process"), "shaderBg": T("structure emphasis story"), "emoji": T("emphasis story"), "parallax": T("story proof"),
    # pastel_box (studio.js built-ins, evidence.js)
    "say": T("emphasis definition"), "line": T("definition emphasis structure"), "strike": T("comparison emphasis"),
    "fromPill": T("structure"), "arrow": T("relationship process"), "studio.chapter": T("structure"), "studio.endCard": T("ask"),
    "box.morph": T("structure"), "focus": T("proof instruction code"), "scoreboard": T("comparison quantity"), "flow": T("process mechanism"),
    "quiet": T("emphasis story"),
    # studio_ui.js cards (S.ui)
    "ui.badge": T("definition proof"), "ui.chat": T("conversation"), "ui.checklist": T("process instruction"), "ui.column": T("comparison structure"),
    "ui.doc": T("proof definition"), "ui.hub": T("relationship mechanism"), "ui.lowerThird": T("structure definition"), "ui.message": T("conversation proof"),
    "ui.note": T("definition emphasis"), "ui.numbered": T("process instruction structure"), "ui.pointer": T("instruction proof"), "ui.pr": T("code proof"),
    "ui.stamp": T("emphasis proof"), "ui.thinking": T("mechanism process"), "ui.thread": T("conversation story"), "ui.tiles": T("comparison structure"),
    "ui.toggle": T("comparison instruction"), "ui.workspace": T("instruction proof mechanism"),
    # reel.js scenes (S.sc)
    "sc.ideaCards": T("comparison structure"), "sc.prompt": T("instruction conversation"), "sc.connect": T("relationship instruction"),
    "sc.scanGrid": T("process mechanism"), "sc.week": T("chronology"), "sc.clock": T("chronology emphasis"), "sc.notif": T("proof story"),
    "sc.shot": T("proof"), "sc.toolPair": T("comparison"), "sc.bars": T("quantity comparison"), "sc.slam": T("emphasis"),
    # footage.js (graphics in the shot), agent.js (an agent's UI)
    "footage.alert": T("emphasis proof"), "footage.behind": T("emphasis quantity"), "footage.corner": T("structure proof"), "footage.flash": T("emphasis"),
    "footage.hud": T("process mechanism"), "footage.pin": T("proof instruction"),
    "agent.chat": T("conversation"), "agent.connect": T("relationship instruction"), "agent.counter": T("quantity"), "agent.flood": T("quantity process"),
    "agent.inbox": T("process proof"), "agent.limits": T("quantity"), "agent.panel": T("proof mechanism"), "agent.title": T("structure"),
    "agent.toast": T("emphasis proof"), "agent.week": T("chronology"),
    # night.js / night_reel.js
    "night.badge": T("definition"), "night.bars": T("quantity comparison"), "night.card": T("definition proof"), "night.chapter": T("structure"),
    "night.chip": T("definition"), "night.pip": T("proof structure"), "night.stamp": T("emphasis"), "night.win": T("proof instruction"),
    "night.word": T("emphasis"), "nightReel.pip": T("proof structure"), "nightReel.stamp": T("emphasis"), "nightReel.win": T("proof instruction"),
    "nightReel.word": T("emphasis"), "nightReel.card": T("definition proof"), "nightReel.chip": T("definition"), "nightReel.lbl": T("definition"),
    "nightReel.icon": T("definition"), "nightReel.badge": T("definition"),
    # redline.js
    "redline.card": T("definition proof"), "redline.face": T("structure"), "redline.fig": T("proof"), "redline.head": T("structure emphasis"),
    "redline.label": T("definition"), "redline.note": T("emphasis definition"), "redline.pen": T("emphasis comparison"),
    "redline.pencil": T("process relationship"), "redline.say": T("emphasis definition"), "redline.sub": T("definition"),
    # canvas.js
    "canvas.beam": T("relationship process"), "canvas.big": T("emphasis quantity"), "canvas.blocks": T("structure mechanism"),
    "canvas.adopt": T("proof process"), "canvas.cam": T("structure"), "canvas.card": T("definition proof"), "canvas.chart": T("quantity comparison"),
    "canvas.highlight": T("proof emphasis"), "canvas.speaker": T("structure"), "canvas.window": T("proof instruction"),
    "canvas.takeover": T("process mechanism relationship chronology quantity proof"),
    # takeovers and transitions (trans.js, 2026-10-22): the kinds, and the transitions a planner picks by meaning (SCENES.md §10)
    "takeover.type": T("emphasis definition"), "takeover.diagram": T("process relationship mechanism structure"),
    "takeover.evidence": T("proof instruction"), "takeover.list": T("process instruction structure"),
    "trans.zoomThrough": T("structure emphasis"), "trans.match": T("relationship structure"), "trans.chapter": T("structure"),
    "trans.cardToGraphic": T("structure"),
    # paper.js (paper collage)
    "paper.chart": T("quantity"), "paper.clipping": T("proof"), "paper.hero": T("emphasis proof"), "paper.ink": T("emphasis"),
    "paper.phone": T("proof"), "paper.polaroid": T("proof story"), "paper.stamp": T("emphasis"), "paper.tag": T("quantity definition"),
    "paper.tape": T("emphasis"), "paper.ticket": T("proof quantity"),
}
WORDS_ONLY = {"words", "side", "pill", "say", "line", "kinetic", "redline.say", "night.word", "nightReel.word", "sc.slam", "takeover.type"}


def header(src):
    m = re.match(r"\s*/\*(.*?)\*/", src, re.S)
    return m.group(1) if m else ""


def discover():
    """{id: {file, call, match, needs}} from the module headers (and reel.js's scene list) plus the built-ins. An HF.x call
    counts only in the module that defines HF.x (a header also mentions other modules' calls)."""
    out = {}
    for f in sorted(HF_DIR.glob("*.js")):
        if f.name not in HOME:
            continue
        src = f.read_text()
        doc = header(src) + "\n" + "\n".join(ln for ln in src.splitlines() if re.match(r"\s*//\s+sc\.\w+\(", ln))
        prefix, needs, _, _ = HOME[f.name]
        obj, defs = OBJ.get(f.name), set(re.findall(r"^\s*HF\.([a-zA-Z]\w*)\s*=", src, re.M))
        for ln in doc.splitlines():
            for m in re.finditer(r"(?<![\w.])(HF|ui|sc|[A-Z])\.([a-zA-Z_]\w*)\s*\(", ln):
                o, name = m.groups()
                if name in PLUMBING:
                    continue
                if o == "HF" and name in defs:
                    cid, match, nd = name, rf"\bHF\.{name}\s*\(", None
                elif o == obj and obj in ("ui", "sc"):
                    cid, match, nd = prefix + name, rf"\b{obj}\.{name}\s*\(", needs
                elif o == obj and f.name == "evidence.js":
                    cid, match, nd = name, rf"\b(?:S|HF)\.{name}\s*\(", None
                elif o == obj:
                    cid, match, nd = prefix + name, rf"\b\w+\.{name}\s*\(", needs
                else:
                    continue
                call = ln.strip().lstrip("*/ ").strip()
                out.setdefault(cid, {"file": f.name, "call": call[:160], "match": match, "needs": nd})
    for cid, (fn, call, match) in BUILTIN.items():
        out.setdefault(cid, {"file": fn, "call": call, "match": match, "needs": HOME["studio.js"][1] if fn == "studio.js" else None})
    return out


def look_of(s: str) -> str:
    """The look a film page's script builds, from the frame it calls (HF.night, HF.redline, HF.canvas, HF.paper,
    HF.studio / HF.reel, else paper_studio). A canvas / studio / reel frame built with a look option ({ look:
    "whitespace" }, 2026-10-22) is a film in that look: read inside the frame call's own arguments, the same way
    kit/hf/mounts.py look_of reads it (the two disagreed before: E-M4)."""
    sys.path.insert(0, str(HF_DIR))
    from mounts import frame_opts
    m = re.search(r"\blook\s*:\s*[\"'](\w+)[\"']", frame_opts(s))
    if m and m.group(1) in LOOKS_ALL:
        return m.group(1)
    return ("night" if re.search(r"HF\.night(Reel)?\s*\(", s) else "redline" if re.search(r"HF\.redline\s*\(", s)
            else "canvas_studio" if re.search(r"HF\.canvas\s*\(", s) else "paper_collage" if re.search(r"HF\.paper\s*\(", s)
            else "pastel_box" if re.search(r"HF\.(studio|reel)\s*\(", s) else "paper_studio")


def film_looks():
    """{page path: (film, look, script)} for every film page (templates, and the older films' own index/reel pages)."""
    res = {}
    for p in sorted(FILMS.glob("**/*.html")):
        if {"assets", "compositions"} & set(p.parts) or "sample" in p.name:      # media, transitions, a sample of a template
            continue
        s = p.read_text(errors="replace")
        res[str(p.relative_to(FILMS.parent))] = (p.relative_to(FILMS).parts[0], look_of(s), s)
    return res


def catalog_entries():
    """The vendored HyperFrames catalog pieces (kit/hf/catalog, kit/hf/tools/catalog.py) as `catalog.<name>`: mounted by
    film.py MOUNTS, so precheck finds them in the page's HTML (scope "html": data-mount="<name>"), not in its script."""
    man = HF_DIR / "catalog/catalog.json"
    if not man.exists():
        return {}
    films = {str(p.relative_to(FILMS)): p.read_text(errors="replace") for p in FILMS.glob("**/film.py")}
    out = {}
    for name, c in json.loads(man.read_text()).items():
        dur = c.get("duration") or 4.0
        out[f"catalog.{name}"] = {
            "file": f"catalog/{c['file']}", "call": f"film.py MOUNTS: dict(name=\"{name}\", at, box=(x, y, w, h), vars=dict({', '.join(c['vars'])}))   {c.get('what', '')}",
            "explains": c.get("explains", []), "looks": LOOKS_ALL, "ratios": ["16:9", "9:16"],
            "used_in": sorted({f.split("/")[0] for f, s in films.items() if f'"{name}"' in s}),
            "match": f'data-mount="{name}"', "scope": "html", "version": "1.0.0", "timing": {"min": 1.5, "max": round(dur * 1.6, 1)}}
    return out


def build():
    old = json.loads(REG.read_text()) if REG.exists() else {"components": {}}
    films = film_looks()
    comps = {}
    found = discover()
    for cid, c in old.get("components", {}).items():         # keep the hand-written ids that the kit still has
        if cid not in found:
            found[cid] = {"file": c.get("file", "scenes.js"), "call": c.get("call", ""), "match": OLD_MATCH.get(cid, rf"\bHF\.{cid}\s*\("), "needs": None}
    for cid, m in {**OLD_MATCH, **ANCHORED}.items():
        if cid in found:
            found[cid]["match"] = m
    for cid in sorted(found, key=lambda k: (HOME.get(found[k]["file"], ("", None, ["zz"], []))[2][0], k)):
        d = found[cid]
        home = HOME.get(d["file"], ("", None, ["paper_studio"], ["16:9", "9:16"]))
        used = []
        for path, (film, look, s) in films.items():
            if re.search(d["match"], s) and (not d["needs"] or re.search(d["needs"], s)):
                used.append((film, look, path))
        prev = old.get("components", {}).get(cid, {})
        themed = d["file"] in THEMED_MODULES or cid in THEMED_IDS
        looks = list(dict.fromkeys(home[2] + (LOOKS_ALL if themed else []) + [lk for _, lk, _ in used]))
        e = {"file": d["file"], "call": prev.get("call") or d["call"], "explains": prev.get("explains") or META.get(cid, []),
             "looks": looks, "ratios": prev.get("ratios") or home[3], "used_in": sorted({f for f, _, _ in used}),
             "match": d["match"]}
        if d["needs"]:
            e["needs"] = d["needs"]
        if cid in WORDS_ONLY:
            e["words_only"] = True
        for k in ("version", "inputs", "timing", "assets", "fallback", "preview", "rule"):
            if k in prev:
                e[k] = prev[k]
        e.setdefault("version", "1.0.0")
        e.setdefault("timing", {"min": 0.8, "max": None})
        comps[cid] = e
    comps.update(catalog_entries())
    return {"registry": "kit/hf", "version": "2.0.0",
            "notes": ("Every visual component in kit/hf, generated by kit/hf/tools/registry.py from the module headers (do not "
                      "hand-edit: document the call in the module's header and add its META line, then --write). 'explains' uses "
                      "the types in kit/refs/SCENES.md §2; 'looks' = the module's home look + every look a film has used it in "
                      "('used_in'); 'match'/'needs' are how kit/qa/precheck.mjs counts it in a film's script; 'timing' is seconds "
                      "on screen. Short-form templates live in kit/graphics/<id>/meta.json with the same fields."),
            "components": comps}


def main():
    reg = build()
    comps = reg["components"]
    if "--write" in sys.argv:
        REG.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n")
        print(f"{REG}: {len(comps)} components")
        return 0
    if "--check" in sys.argv:
        cur = json.loads(REG.read_text()).get("components", {})
        missing = sorted(set(comps) - set(cur))
        stale = sorted(set(cur) - set(comps))
        thin = sorted(k for k, c in cur.items() if not c.get("looks") or not c.get("explains"))
        nometa = sorted(k for k, c in comps.items() if not c["explains"])
        bad = missing or stale or thin or nometa
        if bad:
            for what, ids in (("not in registry.json", missing), ("in registry.json but not in the kit", stale),
                              ("no looks/explains", thin), ("no META explains (add a line in tools/registry.py)", nometa)):
                if ids:
                    print(f"{what}: {', '.join(ids)}")
            print("run: python3 kit/hf/tools/registry.py --write")
            return 1
        print(f"ok: {len(cur)} components, each with looks and explains")
        return 0
    rows = sorted(comps.items(), key=lambda kv: (len(kv[1]["used_in"]), kv[0]))
    if "--unused" in sys.argv:
        rows = [r for r in rows if not r[1]["used_in"]]
    for cid, c in rows:
        print(f"{cid:22} {len(c['used_in']):2} films  {'/'.join(c['looks']):34} {', '.join(c['explains'])}")
    print(f"{len(rows)} components" + (" never used in a film" if "--unused" in sys.argv else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
