"""Check a visual plan (visual_plan.json) against the scene registries before building a film (kit/refs/SCENES.md).

    python3 kit/hf/plan_check.py <visual_plan.json> [--edl=<edl.json>] [--key]

Checks: required fields and goals, explanation types, that each technique exists (kit/hf/registry.json or a
kit/graphics template) and explains the passage's type, ratio support, fallbacks (present and valid), on-screen time
against each component's limits, stickman budget (2-4 moments, <= 5 s, never back to back), runs of the same technique,
words-only share, and that listed assets exist. Since 2026-10-20 (kit/refs/AUDIT_2026-10-20.md) also: a technique whose
registry 'looks' don't include the plan's preset (it needs restyling), too few distinct techniques for the length (the
same bar as precheck's ambition section: Reels 4; long-form 1.2 a minute, 6-10 since 2026-10-22, when the density gate
started to outrank it) and one box layout over 35 % of the time (the sides merged: 'beside' left and right are one
layout, as OWNER_DEFAULTS §1 counts "a card beside the graphic").
A passage may set "music": "drop" | "stop" | "riser" | "turn" (where the music changes with the story; kit/film/mix.py
places a MUSIC bed's drop on it with drop="auto", at=<the passage's moment>). A Reel of 45 s or more with none is
warned; long-form beds are calm (2026-10-22: 18 dB under the voice, no drops or risers), so a long-form plan is warned
for a drop or a riser instead, and for more than 3 stops.
Schema 2 (2026-10-22, "schema": 2 in the plan; kit/refs/SCENES.md §5 and "When to remove him") adds per passage:
  face  on | off | corner | full | frame   where he is (off = a takeover: he is removed, the scene has the whole frame)
  cam   push | pull | punch | arc | drift | hold   the lens on him while he is on
  groups  how many visual groups the passage puts up at once (default 3); dense: "<why>" when more is the point
  bg    the page behind it (default "white")
  transition  cut | whip | glide | zoom | match | card | chapter | fade   how the passage is entered (kit/hf/trans.js
        KINDS, the kinds the engine logs to window.__trans: glide a slow camera travel, fade the soft return of his
        shape after a takeover, C.takeover's default out)
and budgets over the plan: long-form face-off share 15-30 %, each takeover 4-12 s with >= 3 s of face between two,
never away > 12 s (ERROR), the hook's first 3 s on his face (ERROR on long-form), seated full frame <= 30 %, no held
frame over 8 s while he is on (a corner is not judged: too small for the lens, and precheck skips it too), punches
>= 12 s apart, the same transition in two neighbouring passages (cuts excepted; a passage that declares none is entered
on a cut) and whips over 40 % warned, groups over 3 warned 'heavy'. A takeover is a bracket, as HF.trans.check folds
it: the transition into its first face-off passage and the one into the passage he comes back on, the same kind with
no transition declared between them, are one move there and back ("card" in, "card" out), not a repeat, and count
once in the whip share. The fields are checked whenever present; the budgets only on schema 2, so older plans keep
passing (with a NOTE that they were skipped). `--edl` times 'words' spans when the plan names no EDL (kit/film passes
work/edl.json; kit/film/render.py runs this before every draft and render, and stops on an error).
Diagrams (2026-10-22, kit/refs/DIAGRAMS.md §2-3, HF.diagram.FLAT): a passage whose technique is a diagram
("diagram", "takeover.diagram") or that sets "diagram" names its type, "diagram": "<type>" or {"type": ..., "nodes":
[...] | n, "edges": [...] | n, "focal": n}: process | loop | hub | layers | tree (a name that is not a type is the
developing diagram's name, as before; schema 2 warns that the type is missing). Budgets, warned: at most 5 nodes on
16:9 (4 on 9:16), 6 edges, 2 focal nodes, edge labels of 14 characters or fewer; a type 'compare' or 'quadrant' is
not a diagram (HF.compare, or a card with four cells). A shaderBg technique (or a shader / grain bg) on a whitespace
plan is warned (no shader ground or grain on the white page). On a Reel a passage's music "drop" places the covering
bed's drop on it, which moves where that bed starts unless the bed pins its own drop (start= / drop=<s>): a NOTE.
`--key` prints a cache key over the plan, the versions of the components it uses, the kit files, the preset and the
output settings.
Exit 0 = clean, 2 = warnings only, 3 = errors.
"""
import hashlib
import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
TYPES = {"process", "comparison", "quantity", "relationship", "story", "mechanism", "chronology", "analogy", "instruction", "code",
         "conversation", "definition", "emphasis", "proof", "structure", "ask"}
NEEDS_FALLBACK = {"screen", "code", "terminal", "diagram", "stickman"}
# HF.box.direct beats (kit/refs/MOTION.md §3; box.js maps every one, and throws on any other, so 'takeover' is not a
# box show: a takeover is "face": "off" in schema 2, which the canvas plays with C.takeover and the box with "graphic")
BOX_SHOWS = {"face", "punch", "beside", "aside", "hero", "graphic", "corner"}
WORDS_ONLY = {"words", "pill", "side"}                                         # + the registry's words_only ids
MUSIC = {"drop", "stop", "riser", "turn"}      # a passage's music moment (OWNER_DEFAULTS §4; kit/film/mix.py, HF.music)
# ---- schema 2 (2026-10-22): face, camera, density, background and the transition in per passage (SCENES.md §5)
FACES = {"on", "off", "corner", "full", "frame"}           # on: a card/circle beside the content; full: seated full frame;
                                                           # frame: the seated 'frame' card; off: a takeover (he is removed)
CAMS = {"push", "pull", "punch", "arc", "drift", "hold"}   # the lens on him (HF.motion.lens): one move per passage
# how the passage is entered (our own code, no shaders): kit/hf/trans.js KINDS, the kinds window.__trans logs
TRANSITIONS = {"cut", "whip", "glide", "zoom", "match", "card", "chapter", "fade"}
BOX_FACE = {"face": "full", "punch": "full", "beside": "on", "aside": "on", "hero": "on", "graphic": "off", "corner": "corner"}
ON = {"on", "full", "frame"}                               # his face big enough for the lens to move on (a corner is not)
# the budgets the owner set on 2026-10-22 (long-form; the hook and 'away' apply to Reels too)
OFF_SHARE = (0.15, 0.30)       # face-off share of a long-form runtime, in takeovers
TAKEOVER = (4.0, 12.0)         # each takeover's length
FACE_BETWEEN = 3.0             # at least this much face between two takeovers
AWAY_MAX = 12.0                # never away longer (was 18 s)
HOOK_FACE = 3.0                # the hook opens on his face
SEATED_MAX = 0.30              # seated full frame share (the 35 % single-layout cap still applies)
HOLD_MAX = 8.0                 # a held frame on him longer than this reads static (precheck: MEDIUM > 8 s, HIGH > 15 s)
PUNCH_GAP = 12.0               # at most one punch per 12 s
WHIP_SHARE = 0.40              # whips among the planned transitions
GROUPS = 3                     # visual groups up at once besides him (one idea: the hero and one or two supporting chips
                               # or lines; his shape, captions and chrome don't count, as in precheck's density gate)
# where removing him helps (SCENES.md "When to remove him"): passages that show a thing rather than claim, feel or ask
OFF_TYPES = {"process", "mechanism", "relationship", "chronology", "quantity", "proof"}
# diagrams (kit/refs/DIAGRAMS.md §2-3; HF.diagram.FLAT's budgets): the types a flat diagram draws, and two that are not
# diagrams at all
DIAGRAM_TYPES = {"process", "loop", "hub", "layers", "tree"}
NOT_DIAGRAMS = {"compare": "HF.compare (before / after, A against B)", "quadrant": "a card with four cells (two axes)"}
DIAGRAM_TECH = {"diagram", "takeover.diagram"}
DG = {"nodes": 5, "nodesP": 4, "edges": 6, "focal": 2, "label": 14}
BLUEPRINTS = {"prompt-type-submit-generate", "agent-progress-theater", "cursor-ui-demo", "transcript-scroll-artifact-reveal",
              "camera-journey", "spatial-pan-stations", "zoom-out-workspace-reveal", "dataviz-countup", "comparison-split",
              "kinetic-type-beats", "ticker-takeover", "fixed-anchor-cycle", "typewriter-reveal", "overwhelm-surround",
              "titlecard-reveal"}                       # a passage's arc (kit/refs/SCENES.md §8)


def registry() -> dict:
    """{id: {source, explains, ratios, fallback, timing, version}} for long-form components and short-form templates."""
    reg = {}
    hf = json.loads((KIT / "hf/registry.json").read_text())
    for cid, c in hf["components"].items():
        reg[cid] = {"source": "kit/hf", "explains": c.get("explains", []), "ratios": [r.split(" ")[0] for r in c.get("ratios", [])],
                    "fallback": c.get("fallback"), "timing": c.get("timing", {}), "version": c.get("version", "1"),
                    "looks": c.get("looks", []), "words_only": c.get("words_only", False)}
    for meta in sorted((KIT / "graphics").glob("*/meta.json")):
        m = json.loads(meta.read_text())
        if m.get("internal"):
            continue
        d = m.get("duration", {})
        reg[m["id"]] = {"source": "kit/graphics", "explains": m.get("explains", []), "ratios": m.get("ratios", ["9:16"]), "fallback": m.get("fallback"),
                        "timing": {"min": d.get("min", 1.0), "max": d.get("max", 6.0)}, "version": str(m.get("version", "1"))}
    return reg


def span(p: dict, words: dict) -> tuple[float, float] | None:
    if "t" in p:
        return float(p["t"][0]), float(p["t"][1])
    if "words" in p and words:
        a, b = p["words"]
        if a in words and b in words:
            return words[a][0], words[b][1]
    return None


def fields(p: dict) -> list[str]:
    """Errors in a passage's schema-2 fields (checked whenever they are present: a typo is a typo in any schema)."""
    pid, out = p.get("id", "?"), []
    for f, ok in (("face", FACES), ("cam", CAMS), ("transition", TRANSITIONS)):
        if p.get(f) is not None and p[f] not in ok:
            out.append(f"{pid}: {f} '{p[f]}' is not one of {sorted(ok)}")
    g = p.get("groups")
    if g is not None and (isinstance(g, bool) or not isinstance(g, int) or g < 1):
        out.append(f"{pid}: groups must be a whole number >= 1 (visual groups up at once), got {g!r}")
    if p.get("bg") is not None and (not isinstance(p["bg"], str) or not p["bg"].strip()):
        out.append(f"{pid}: bg must name the page behind the passage (default 'white'), got {p['bg']!r}")
    return out


def face_of(p: dict) -> str:
    """The passage's face: its own field, else what its box beat implies (HF.box.direct), else on."""
    bx = p.get("box") if isinstance(p.get("box"), dict) else {}
    return p.get("face") or BOX_FACE.get(bx.get("show"), "on")


def diagram_rules(p: dict, ratio: str, schema2: bool) -> tuple[list[str], list[str]]:
    """A diagram passage against kit/refs/DIAGRAMS.md §2-3 (HF.diagram.FLAT's budgets) -> (errors, warnings).
    p["diagram"]: a type name ("loop"), a developing diagram's own name ("workflow": not a type, so the type is unknown),
    or {"type", "nodes": [...] | n, "edges": [...] | n, "focal": [...] | n}; nodes as dicts may carry focal: true, edges
    as dicts a label. A diagram technique with no "diagram" field has no type either (warned on schema 2 only)."""
    pid, dg = p.get("id", "?"), p.get("diagram")
    if p.get("technique") not in DIAGRAM_TECH and not dg:
        return [], []
    errs, warns = [], []
    spec = dg if isinstance(dg, dict) else {}
    ty = spec.get("type") if isinstance(dg, dict) else dg if isinstance(dg, str) and (dg in DIAGRAM_TYPES or dg in NOT_DIAGRAMS) else None
    if ty in NOT_DIAGRAMS:
        warns.append(f"{pid}: a '{ty}' is not a diagram: use {NOT_DIAGRAMS[ty]} (kit/refs/DIAGRAMS.md §2)")
        return errs, warns
    if ty is not None and ty not in DIAGRAM_TYPES:
        errs.append(f"{pid}: diagram type '{ty}' is not one of {sorted(DIAGRAM_TYPES)} (or compare / quadrant, which are not diagrams)")
    elif ty is None and schema2:
        warns.append(f"{pid}: a diagram with no type: set \"diagram\": {{\"type\": one of {sorted(DIAGRAM_TYPES)}, ...}} "
                     "(kit/refs/DIAGRAMS.md §2: pick it from what the passage does; the budgets go by it)")

    def count(v):
        return len(v) if isinstance(v, list) else v if isinstance(v, int) and not isinstance(v, bool) else None
    nodes, edges = spec.get("nodes"), spec.get("edges")
    n_nodes, n_edges = count(nodes), count(edges)
    focal = count(spec.get("focal")) if spec.get("focal") is not None else (
        sum(1 for n in nodes if isinstance(n, dict) and n.get("focal")) if isinstance(nodes, list) else None)
    portrait = ratio == "9:16"
    most = DG["nodesP"] if portrait else DG["nodes"]
    if n_nodes is not None and n_nodes > most:
        warns.append(f"{pid}: {n_nodes} nodes in one diagram (at most {most} on {ratio}): delete or merge one, or split it into an "
                     "overview and a detail station (kit/refs/DIAGRAMS.md §3)")
    if n_edges is not None and n_edges > DG["edges"]:
        warns.append(f"{pid}: {n_edges} edges in one diagram (at most {DG['edges']}): can an arrow go? (kit/refs/DIAGRAMS.md §3)")
    if focal is not None and focal > DG["focal"]:
        warns.append(f"{pid}: {focal} focal nodes (at most {DG['focal']}, normally 1: the part he names)")
    for e in edges if isinstance(edges, list) else []:
        lab = e.get("label") if isinstance(e, dict) else None
        if isinstance(lab, str) and len(lab) > DG["label"]:
            warns.append(f"{pid}: edge label '{lab}' is {len(lab)} characters (at most {DG['label']}: a mono caps kicker on the line)")
    return errs, warns


def covered(spans: list[tuple[float, float]]) -> float:
    """Seconds covered by the union of [a, b] spans: passages may overlap (a beat that starts before the last one ends),
    and a share counts each second once (0-40 s and 10-50 s full frame is 50 s, not 80 s)."""
    total, end = 0.0, None
    for a, b in sorted(spans):
        if end is None or a > end:
            total, end = total + (b - a), b
        elif b > end:
            total, end = total + (b - end), b
    return total


def budgets(rows: list[dict], runtime: float, long_form: bool) -> tuple[list[str], list[str]]:
    """The 2026-10-22 face, camera, density and transition budgets over a timed plan (schema 2).
    rows: [{id, a, b, face, cam, transition, groups, dense, type, blueprint}] in time order. Time no passage covers is
    face on (he is talking; the engine's default). Returns (errors, warnings)."""
    errs, warns = [], []
    rows = sorted(rows, key=lambda r: r["a"])
    # takeovers: face-off passages that touch (within 0.25 s) are one stretch away from him
    offs = []
    for r in rows:
        if r["face"] != "off":
            continue
        if offs and r["a"] - offs[-1]["b"] <= 0.25:
            offs[-1]["b"], offs[-1]["ids"] = max(offs[-1]["b"], r["b"]), offs[-1]["ids"] + [r["id"]]
        else:
            offs.append({"a": r["a"], "b": r["b"], "ids": [r["id"]]})
    for o in offs:
        d, ids = o["b"] - o["a"], "+".join(o["ids"])
        if o["a"] < HOOK_FACE - 0.05:
            (errs if long_form else warns).append(f"{ids}: face off at {o['a']:.1f} s: the hook opens on his face (the first {HOOK_FACE:.0f} s)")
        if d > AWAY_MAX + 0.05:
            errs.append(f"{ids}: away from him {d:.1f} s (never more than {AWAY_MAX:.0f} s): split the takeover with a face beat")
        elif d < TAKEOVER[0] - 0.05:
            warns.append(f"{ids}: a takeover of {d:.1f} s (4-12 s): too short to read as its own scene; merge it or keep him on")
    for o1, o2 in zip(offs, offs[1:]):
        if o2["a"] - o1["b"] < FACE_BETWEEN - 0.05:
            warns.append(f"{'+'.join(o1['ids'])} -> {'+'.join(o2['ids'])}: only {o2['a'] - o1['b']:.1f} s of face between two takeovers "
                         f"(>= {FACE_BETWEEN:.0f} s: the takeaway line after a takeover is his)")
    if runtime > 0:
        off = covered([(r["a"], r["b"]) for r in rows if r["face"] == "off"]) / runtime
        if long_form and not OFF_SHARE[0] <= off <= OFF_SHARE[1]:
            cands = [f"{r['id']} ({r['type']}, {r['b'] - r['a']:.0f} s)" for r in rows
                     if r["face"] != "off" and r["type"] in OFF_TYPES and r["b"] - r["a"] >= 5.0][:6]
            warns.append(f"face off for {round(100 * off)} % of the runtime (long-form: {round(100 * OFF_SHARE[0])}-{round(100 * OFF_SHARE[1])} % in "
                         f"takeovers of 4-12 s)" + (f"; candidates (SCENES.md 'When to remove him'): {', '.join(cands)}" if off < OFF_SHARE[0] and cands else ""))
        seated = covered([(r["a"], r["b"]) for r in rows if r["face"] == "full"]) / runtime
        if seated > SEATED_MAX + 0.005:
            warns.append(f"seated full frame for {round(100 * seated)} % of the runtime (max {round(100 * SEATED_MAX)} %)")
    # the camera on him: a held frame reads static past 8 s; punches are rationed
    last_punch = None
    for r in rows:
        d = r["b"] - r["a"]
        if r["face"] in ON and r["cam"] == "hold" and d > HOLD_MAX + 0.05:
            warns.append(f"{r['id']}: cam 'hold' on him for {d:.1f} s (a framing change every 4-8 s: push, pull or arc across the thought)")
        if r["cam"] == "punch":
            if last_punch is not None and r["a"] - last_punch < PUNCH_GAP - 0.05:
                warns.append(f"{r['id']}: a punch {r['a'] - last_punch:.1f} s after the last one (at most one per {PUNCH_GAP:.0f} s)")
            last_punch = r["a"]
        # a groups value fields() rejected (a string, a bool, 0) is already an ERROR: judge the passage at the default
        g = r["groups"] if isinstance(r["groups"], int) and not isinstance(r["groups"], bool) and r["groups"] >= 1 else GROUPS
        if g > GROUPS and not r["dense"] and r["blueprint"] != "overwhelm-surround":
            warns.append(f"{r['id']}: heavy: {g} visual groups up at once (max {GROUPS}: one idea per frame; set dense: \"<why>\" when the pile-up is the point)")
    # transitions: never the same kind twice in a row (a hard cut is the absence of one, so cuts may repeat), whips rationed.
    # 'In a row' is between neighbouring passages: one that declares none is entered on a cut (the engine's default), so
    # whip, (none), whip is not a repeat (review 2026-10-22). A takeover is a bracket (folded() below), as HF.trans folds it
    seq = folded(rows, offs)
    for e1, e2 in zip(seq, seq[1:]):
        if e1["kind"] == e2["kind"] and e1["kind"] != "cut":
            # after a bracket the repeat is named from its return (the end next to the second one), as HF.trans.check does
            warns.append(f"{e1['back'] or e1['id']} -> {e2['id']}: transition '{e1['kind']}' twice in a row (vary it; each kind should mean something)")
    tr = [e for e in seq if e["declared"]]
    if len(tr) >= 3:
        wh = sum(1 for e in tr if e["kind"] == "whip") / len(tr)
        if wh > WHIP_SHARE + 1e-9:
            warns.append(f"whips are {round(100 * wh)} % of the planned transitions (max {round(100 * WHIP_SHARE)} %)")
    return errs, warns


def folded(rows: list[dict], offs: list[dict]) -> list[dict]:
    """The plan's transitions in time order, one per passage ({id, kind, declared, back}: kind "cut" when the passage
    declares none), with each takeover folded the way HF.trans.check folds window.__trans: the transition into a
    takeover's first face-off passage and the one into the passage he comes back on (the first that starts within
    0.25 s of the takeover's end), the same kind with no transition declared on a passage between them, are ONE entry
    (back: the return passage's id). The same move there and back is one idea, not a repeat (in "card" / out "card",
    the design's signature; a fade in and the default fade out)."""
    seq = [{"id": r["id"], "kind": r["transition"] or "cut", "declared": bool(r["transition"]), "back": None, "a": r["a"]} for r in rows]
    drop = set()
    for o in offs:
        first = next((i for i, r in enumerate(rows) if r["id"] == o["ids"][0]), None)
        ret = next((i for i, r in enumerate(rows) if i > (first if first is not None else 1e9) and r["face"] != "off" and abs(r["a"] - o["b"]) <= 0.25), None)
        if first is None or ret is None or not seq[first]["declared"] or not seq[ret]["declared"]:
            continue
        inner = range(first + 1, ret)
        if seq[first]["kind"] == seq[ret]["kind"] and not any(seq[i]["declared"] for i in inner):
            seq[first]["back"] = rows[ret]["id"]
            drop.add(ret)
    return [e for i, e in enumerate(seq) if i not in drop]


def check(plan_path: Path, edl: Path | None = None, notes: list | None = None) -> tuple[list[str], list[str], dict]:
    """(errors, warnings, the plan). notes: a list to append NOTE lines to (main prints them; they never change the
    exit code)."""
    notes = notes if notes is not None else []
    plan = json.loads(plan_path.read_text())
    reg = registry()
    errs, warns = [], []
    ratio = plan.get("ratio", "16:9")
    words, edl_total = {}, None
    e = plan_path.parent / plan["edl"] if plan.get("edl") else None
    if e is not None and not e.exists():
        if edl is None or not Path(edl).exists():
            warns.append(f"edl {plan['edl']} not found: word spans can't be timed")
        e = None
    e = e or (Path(edl) if edl is not None and Path(edl).exists() else None)
    if e is not None:
        E = json.loads(e.read_text())
        words, edl_total = {w["i"]: (w["t"], w["e"]) for w in E["words"]}, E.get("total")
    ps = plan.get("passages", [])
    if not ps:
        errs.append("no passages")
    stick, last, run, words_only = [], None, 0, 0
    look = (plan.get("preset") or "").replace("preset_", "")              # the plan's look (registry 'looks' use these names)
    used, layout, t_end = set(), {}, 0.0
    for p in ps:
        pid = p.get("id", "?")
        for f in ("id", "goal", "type", "technique", "beats"):
            if not p.get(f):
                errs.append(f"{pid}: missing '{f}'")
        if "words" not in p and "t" not in p:
            errs.append(f"{pid}: needs 'words' [first, last] or 't' [a, b]")
        if p.get("blueprint") is not None and p["blueprint"] not in BLUEPRINTS:
            warns.append(f"{pid}: blueprint '{p['blueprint']}' is not in kit/refs/SCENES.md §8")
        if p.get("music") is not None and p["music"] not in MUSIC:
            errs.append(f"{pid}: music '{p['music']}' is not one of {sorted(MUSIC)}")
        bx = p.get("box")                                    # the speaker box's beat (kit/refs/MOTION.md §3)
        if bx is not None:
            if not isinstance(bx, dict) or bx.get("show") not in BOX_SHOWS:
                errs.append(f"{pid}: box needs {{show: one of {sorted(BOX_SHOWS)}}}, got {bx!r}")
            elif bx["show"] in ("beside", "aside") and bx.get("side") not in ("left", "right", "top", "bottom"):
                errs.append(f"{pid}: box '{bx['show']}' needs side: where the content sits (left/right, or top/bottom in 9:16)")
        errs += fields(p)
        if p.get("face") == "off" and p.get("cam") not in (None, "hold"):
            warns.append(f"{pid}: cam '{p['cam']}' on a takeover (face off): the lens moves on him, and he is not on screen")
        e_dg, w_dg = diagram_rules(p, ratio, str(plan.get("schema", 1)) == "2")
        errs, warns = errs + e_dg, warns + w_dg
        bgs = str(p.get("bg") or "").lower()
        if look == "whitespace" and (p.get("technique") == "shaderBg" or "shader" in bgs or "grain" in bgs):
            warns.append(f"{pid}: a shader ground or grain on the whitespace page ({p.get('technique') if p.get('technique') == 'shaderBg' else p.get('bg')}): "
                         "no shader ground and no grain on the white page (kit/refs/DIAGRAMS.md §11; a lit field or a soft reveal is CSS and GSAP)")
        ty, te = p.get("type"), p.get("technique")
        if ty and ty not in TYPES:
            errs.append(f"{pid}: unknown type '{ty}' (one of {sorted(TYPES)})")
        c = reg.get(te)
        if te and not c:
            errs.append(f"{pid}: technique '{te}' is not in kit/hf/registry.json or kit/graphics")
            continue
        if not c:
            continue
        used.add(te)
        if look and c.get("looks") and look not in c["looks"]:
            warns.append(f"{pid}: '{te}' has only been used in {'/'.join(c['looks'])}, not {look}: check it renders in this look, or restyle it")
        if ty in TYPES and c["explains"] and ty not in c["explains"]:
            warns.append(f"{pid}: '{te}' isn't listed for '{ty}' (it explains {c['explains']}); check kit/refs/SCENES.md §2")
        if c["ratios"] and ratio not in c["ratios"]:
            fb = p.get("fallback") or c["fallback"]
            (warns if fb else errs).append(f"{pid}: '{te}' doesn't support {ratio}" + (f"; the fallback '{fb}' will be used" if fb else " and has no fallback"))
        fb = p.get("fallback")
        if te in NEEDS_FALLBACK and not fb:
            errs.append(f"{pid}: '{te}' needs a 'fallback' (the asset or ratio can fail)")
        if fb and fb not in reg and fb != "none":
            errs.append(f"{pid}: fallback '{fb}' is not a known component or template")
        sp = span(p, words)
        if sp:
            dur = sp[1] - sp[0]
            t_end = max(t_end, sp[1])
            if isinstance(bx, dict) and bx.get("show"):
                k = bx["show"]                     # the sides merged: a card beside the graphic is one layout (OWNER_DEFAULTS §1)
                layout[k] = layout.get(k, 0.0) + dur
            mn, mx = c["timing"].get("min"), c["timing"].get("max")
            if mn and dur < mn - 0.05:
                warns.append(f"{pid}: {te} on screen {dur:.1f} s, under its {mn} s minimum")
            if mx and dur > mx + 0.05:
                warns.append(f"{pid}: {te} on screen {dur:.1f} s, over its {mx} s maximum (split it or develop it across passages)")
            for b in p.get("beats", []):
                at = b.get("at")
                t = words.get(at, (None,))[0] if isinstance(at, int) and words else at if isinstance(at, float) else None
                if t is not None and not (sp[0] - 0.05 <= t <= sp[1] + 0.05):
                    warns.append(f"{pid}: beat at {at} falls outside the passage")
            if te == "stickman":
                stick.append((pid, dur, sp))
        elif te == "stickman":
            stick.append((pid, None, None))
        for a in p.get("assets", []):
            if not (plan_path.parent / a).exists():
                warns.append(f"{pid}: asset {a} not found (relative to the plan)")
        same = te == last and not (te == "diagram" and p.get("diagram"))
        run = run + 1 if same else 1
        if run >= 3:
            warns.append(f"{pid}: '{te}' {run} passages in a row; vary it unless it's one developing diagram")
        last = te
        words_only += te in WORDS_ONLY or bool(c.get("words_only"))
        if not p.get("why"):
            warns.append(f"{pid}: no 'why' (how this visual helps the viewer)")
    try:                                                                    # looks per passage (kit/refs/SCENES.md §6)
        sys.path.insert(0, str(KIT / "look"))
        import looks as LK
        names = set(LK.LOOKS)
    except Exception:
        names = None
    seq = [p.get("look", "natural") for p in ps]
    for p, lk in zip(ps, seq):
        if names is not None and lk not in names:
            errs.append(f"{p.get('id')}: unknown look '{lk}' (one of {sorted(names)})")
    others = {lk for lk in seq if lk != "natural"}
    if len(others) > 3:
        warns.append(f"{len(others)} different looks besides natural ({sorted(others)}); keep it to 2-3")
    flips = sum(1 for k in range(2, len(seq)) if seq[k] == seq[k - 2] != seq[k - 1])
    if flips >= 2:
        warns.append("looks flip back and forth passage by passage; hold a mood (>= 3 s) or stay natural")
    if len(stick) > 4:
        errs.append(f"{len(stick)} stickman moments (max 4 per video)")
    for pid, dur, _ in stick:
        if dur and dur > 5.05:
            warns.append(f"{pid}: stickman moment {dur:.1f} s (keep it 2-5 s)")
    ids = [p.get("id") for p in ps]
    for k in range(1, len(ps)):
        if ps[k].get("technique") == "stickman" and ps[k - 1].get("technique") == "stickman":
            errs.append(f"{ids[k - 1]} and {ids[k]}: stickman moments back to back")
    runtime = float(plan.get("total") or edl_total or t_end)
    # long-form or a Reel: the plan says ("form": "long" | "reel"), else 9:16 or under 2 minutes is a Reel (the same split
    # as the variety bar); the calm-bed, hook and face-off budgets are long-form's
    long_form = plan.get("form") == "long" or (plan.get("form") is None and ratio != "9:16" and runtime >= 120)
    if runtime:
        # the variety minimum (precheck's bar): Reels 4; long-form 1.2 a minute, 6-10 (2026-10-22: calm long-form, and the
        # density gate outranks it)
        need = 4 if runtime < 120 else min(10, max(6, round(1.2 * runtime / 60)))
        if len(used) < need:
            warns.append(f"{len(used)} distinct techniques for {runtime / 60:.1f} min (want {need}): kit/hf/registry.json has "
                         f"{sum(1 for c in reg.values() if c['source'] == 'kit/hf')}; `python3 kit/hf/tools/registry.py --unused` lists the ones no film has tried")
        for k, v in layout.items():
            if v / runtime > 0.35:
                warns.append(f"the box is '{k}' for {round(100 * v / runtime)} % of the time (max 35 %): vary it (kit/refs/SCENES.md §7)")
    mus = [p.get("music") for p in ps if p.get("music")]
    if long_form:
        # long-form beds sit 18 dB under the voice and stay calm (OWNER_DEFAULTS §4, 2026-10-22): the music may turn or stop
        # with the story, never drop or rise
        loud = [f"{p.get('id')} ({p['music']})" for p in ps if p.get("music") in ("drop", "riser")]
        if loud:
            warns.append(f"long-form beds are calm (no drops or risers): {', '.join(loud)}: use 'turn' (a new section) or 'stop' (the punchline)")
    elif runtime and runtime >= 45 and not mus:
        warns.append("no passage plans a music moment: the music should change with the story (a drop on the reveal, a stop "
                     "on the punchline, a riser before the payoff): set 'music' on 2-4 passages (OWNER_DEFAULTS §4)")
    if not long_form:
        drops = [p.get("id", "?") for p in ps if p.get("music") == "drop"]
        if drops:
            # kit/film/mix.py (v11, Reels): a planned drop places the covering bed with drop="auto" on the passage
            notes.append(f"music 'drop' on {', '.join(drops)}: on a Reel the mix lands the covering bed's biggest rise there, which moves "
                         "where that bed starts in its track, unless the bed pins its own drop (start= or drop=<track s> in MUSIC)")
    if mus.count("stop") > 3:
        warns.append(f"{mus.count('stop')} music stops planned (S.quiet: 2-3 a video)")
    if str(plan.get("schema", 1)) not in ("1", "2"):
        errs.append(f"schema {plan.get('schema')!r}: this check knows 1 and 2")
    if str(plan.get("schema", 1)) == "2":                                   # face, camera, density, transitions (2026-10-22)
        rows, untimed = [], []
        for p in ps:
            sp = span(p, words)
            if not sp:
                untimed.append(p.get("id", "?"))
                continue
            rows.append({"id": p.get("id", "?"), "a": sp[0], "b": sp[1], "face": face_of(p), "cam": p.get("cam"), "transition": p.get("transition"),
                         "groups": p.get("groups"), "dense": p.get("dense"), "type": p.get("type"), "blueprint": p.get("blueprint")})
        if untimed:
            warns.append(f"schema 2: {', '.join(untimed[:6])} can't be timed (no EDL for their words), so the face and camera budgets skip them")
        e2, w2 = budgets(rows, runtime, long_form)
        errs += e2
        warns += w2
    if ps and words_only / len(ps) > 0.4:
        warns.append(f"{words_only}/{len(ps)} passages are words-only; show the thing instead (SCENES.md §3)")
    return errs, warns, plan


def cache_key(plan: dict) -> str:
    reg = registry()
    h = hashlib.sha256()
    h.update(json.dumps(plan, sort_keys=True).encode())
    # a passage with no fallback (or no technique) gives None: leave it out, sorted() can't order None among names
    for te in sorted(({p.get("technique") for p in plan.get("passages", [])} | {p.get("fallback") for p in plan.get("passages", [])}) - {None}):
        if te in reg:
            h.update(f"{te}@{reg[te]['version']}".encode())
    for f in sorted((KIT / "hf").glob("*.js")) + [KIT / "hf/paper.css", KIT / "stickman/stickman.js", KIT / "presets/paper_studio/preset.json"]:
        if f.exists():
            h.update(f.read_bytes())
    h.update(json.dumps({k: plan.get(k) for k in ("ratio", "fps", "width", "height", "preset")}, sort_keys=True).encode())
    return h.hexdigest()[:16]


def main():
    path = Path(next(a for a in sys.argv[1:] if not a.startswith("--")))
    edl = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--edl=")), None)
    notes = []
    errs, warns, plan = check(path, Path(edl) if edl else None, notes)
    for e in errs:
        print("ERROR  ", e)
    for w in warns:
        print("WARN   ", w)
    for n in notes:                                         # never change the exit code
        print("NOTE   ", n)
    if str(plan.get("schema", 1)) == "1":                  # a note, not a warning: older plans keep their exit code
        print("NOTE    schema 1: the face, camera, density and transition budgets were not checked (a new plan sets "
              "\"schema\": 2 and face/cam/groups/transition per passage: kit/refs/SCENES.md §5, §9, §10)")
    n = len(plan.get("passages", []))
    print(f"{'FAIL' if errs else 'WARN' if warns else 'PASS'}: {path.name}  {n} passages, {len(errs)} errors, {len(warns)} warnings")
    if "--key" in sys.argv:
        print("cache key:", cache_key(plan))
    sys.exit(3 if errs else 2 if warns else 0)


if __name__ == "__main__":
    main()
