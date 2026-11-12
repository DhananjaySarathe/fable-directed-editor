"""Mount vendored HyperFrames catalog pieces (kit/hf/catalog/) on a film's page, at build time.

HyperFrames resolves a sub-composition when it compiles the page, so a mount has to be in the page's HTML: one created
by the page's script is never rendered (tested 2026-10-20). A film lists its mounts in film.py and kit/film/build.py
writes them into the root composition:

    MOUNTS = [dict(name="cursor-zoom-follow", at="w212", dur=5.8, box=(960, 120, 880, 495),
                   vars=dict(image="assets/shots/dashboard.png", zoom=2.0, click1_x=40, click1_y=22)),
              dict(name="headline-slam", at="tag:verdict", vars=dict(text="Same model. Different limits.", accent_word_index=3))]

  name   a piece in kit/hf/catalog/catalog.json (python3 kit/hf/tools/catalog.py --list)
  at     seconds, "w<id>", "tag:<tag>", "end-<s>" (kit/film/mix.py when); dur defaults to the piece's own length. A
         different dur retimes the piece (a copy with its own length written in: the pieces stretch their hold and keep
         their entrance and exit), so it never leaves early with its box still on screen
  box    (x, y, w, h) in page px (default: the full frame); z (default 8): above the content layers (FRONT 6), under
         captions (11) and chapter cards (12)
  vars   the piece's variables; the rest keep their defaults. `accent` defaults to the film's look accent, so a piece
         never brings the catalog's blue into a canvas or redline film. Image paths are relative to the page.
  fit    "scale": lay the piece out at 1920x1080 and scale it into the box (pieces built for a full frame), instead of
         sizing it to the box (the default)
  css    extra CSS on the mount, mostly the piece's own variables. Some pieces size their own type: marker-highlight fits
         its line to the box's width, so a shorter text is what makes it bigger (check the 32 px floor on a snapshot)

On a canvas page (HF.canvas) a mount sits in screen space, over the camera. To have it ride the camera (whips, pushes),
move it into a station in the page's script: C.adopt(station, "marker-highlight"); its box is then in that station's px.

The look reaches inside a piece through CSS variables (--bg, --fg, --surface, --border, --muted, --accent, --brand,
--font-display, --font-body, --radius), which HF.look writes from the film's tokens (kit/hf/core.js).
"""
from __future__ import annotations

import html as H
import json
import re
import shutil
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
CAT = KIT / "hf/catalog"
CORE = KIT / "hf/core.js"
FRAMES = [("HF.canvas(", "canvas_studio"), ("HF.redline(", "redline"), ("HF.nightReel(", "night"), ("HF.night(", "night"),
          ("HF.paper(", "paper_collage"), ("HF.studio(", "pastel_box"), ("HF.reel(", "pastel_box")]


def manifest() -> dict:
    return json.loads((CAT / "catalog.json").read_text())


def frame_opts(template: str) -> str:
    """The text of the arguments of the template's frame calls that take a look option (HF.canvas / HF.studio /
    HF.reel), each up to its matching parenthesis (strings skipped), joined. '' when it calls none."""
    out = []
    for m in re.finditer(r"HF\.(canvas|studio|reel)\s*\(", template):
        depth, i, q = 1, m.end(), None
        while i < len(template) and depth:
            c = template[i]
            if q:
                q = None if c == q and template[i - 1] != "\\" else q
            elif c in "\"'`":
                q = c
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            i += 1
        out.append(template[m.end():i - 1])
    return "\n".join(out)


def look_of(template: str) -> str:
    """The look a page's frame applies (kit/hf/core.js HF.look), from its template text: an explicit HF.look("x"), else
    a look option on its frame call (HF.canvas / HF.studio / HF.reel { look: "whitespace" }: the v11 default, which a
    canvas page used to be read as canvas_studio from: review 2026-10-22, E-M4; kit/hf/tools/registry.py look_of reads
    it the same way), else the frame's own look; paper_studio with no frame."""
    m = re.search(r"HF\.look\(\s*[\"'](\w+)[\"']", template)
    if m:
        return m.group(1)
    m = re.search(r"\blook\s*:\s*[\"'](\w+)[\"']", frame_opts(template))
    if m:
        return m.group(1)
    return next((look for call, look in FRAMES if call in template), "paper_studio")


def palette_accent(template: str, look: str) -> str | None:
    """The film's own accent when its frame re-accents the look's stage with it: a literal palette { acc: "#..." } on
    HF.canvas / HF.studio / HF.reel of a whitespace page (canvas.js accentOf: a solid-accent stage follows the film's
    palette acc, so the page keeps ONE accent; engine-looks request 0, E-M4). None otherwise (the look's own acc: every
    other look keeps its gradient or its tokens as before, so no older film's mounts change)."""
    if look != "whitespace":
        return None
    m = re.search(r"\bpalette\s*:\s*\{[^{}]*?\bacc\s*:\s*[\"'](#[0-9a-fA-F]{3,8})[\"']", frame_opts(template))
    return m.group(1) if m else None


def look_accent(look: str) -> str | None:
    """The look's acc token, read from HF.LOOKS in core.js (one source of truth for the colours)."""
    src = CORE.read_text()
    m = re.search(rf"\b{look}:\s*{{.*?acc:\s*\"(#[0-9a-fA-F]{{3,8}})\"", src, re.S)
    return m.group(1) if m else None


def retimed(text: str, own: float, dur: float) -> str:
    """A piece's HTML with its own length (the composition, its root and its clip: every data-duration and
    data-composition-duration that equals `own`) set to `dur`. The pieces read it back to lay out their timeline."""
    def sub(m):
        return f'{m.group(1)}{dur:g}"' if abs(float(m.group(2)) - own) < 1e-6 else m.group(0)
    return re.sub(r'(data-(?:composition-)?duration=")([0-9.]+)"', sub, text)


def own_length(piece: dict) -> float | None:
    """The piece's built-in length: the manifest's, else its root's data-duration."""
    if piece.get("duration"):
        return float(piece["duration"])
    m = re.search(r'id="root"[^>]*data-duration="([0-9.]+)"', (CAT / piece["file"]).read_text())
    return float(m.group(1)) if m else None


def piece_file(hf: Path, i: int, spec: dict) -> str:
    """Copy mount i's piece into hf/compositions/catalog/ and return its file name there: the piece itself, or a copy
    retimed to the mount's dur when that differs from the piece's own length."""
    piece = manifest()[spec["name"]]
    dst = hf / "compositions/catalog"
    dst.mkdir(parents=True, exist_ok=True)
    own = own_length(piece)
    dur = float(spec.get("dur") or own or 4.0)
    if own is None or abs(dur - own) < 1e-3:
        shutil.copy2(CAT / piece["file"], dst / piece["file"])
        return piece["file"]
    name = f'{Path(piece["file"]).stem}--m{i}.html'
    (dst / name).write_text(retimed((CAT / piece["file"]).read_text(), own, dur))
    return name


def mount_html(i: int, spec: dict, t: float, look: str, file: str | None = None, acc: str | None = None) -> str:
    """One mount's div. acc: the accent its piece takes (the film's palette accent on a re-accented stage,
    palette_accent), else the look's acc token."""
    M = manifest()
    name = spec["name"]
    if name not in M:
        raise SystemExit(f"MOUNTS: '{name}' is not vendored (python3 kit/hf/tools/catalog.py --list / add {name})")
    piece = M[name]
    dur = float(spec.get("dur") or own_length(piece) or 4.0)
    vars_ = dict(spec.get("vars", {}))
    if piece.get("accent_var") and piece["accent_var"] not in vars_:
        acc = acc or look_accent(look)
        if acc:
            vars_[piece["accent_var"]] = acc
    unknown = [k for k in vars_ if k not in piece["vars"]]
    if unknown:
        raise SystemExit(f"MOUNTS {name}: unknown variable(s) {unknown} (it takes {', '.join(piece['vars'])})")
    x, y, w, h = spec.get("box", (0, 0, 1920, 1080))
    z = spec.get("z", 8)
    if spec.get("fit", piece.get("fit")) == "scale":                   # a piece laid out for the full frame
        style = f"position:absolute;left:{x}px;top:{y}px;width:1920px;height:1080px;transform:scale({w / 1920:.5f});transform-origin:0 0;z-index:{z}"
    else:
        style = f"position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;z-index:{z};overflow:hidden" + \
                (f";border-radius:{spec['radius']}px" if spec.get("radius") else "")
    if spec.get("css"):                                                 # the piece's own CSS variables (--mh-font-size: 54px)
        style += ";" + spec["css"].strip().rstrip(";")
    vv = H.escape(json.dumps(vars_), quote=True)
    return (f'<div id="mount-{i}" class="hf-mount" data-mount="{name}" data-composition-id="mount{i}-{name}" '
            f'data-composition-src="compositions/catalog/{file or piece["file"]}" data-start="{t:.4f}" data-duration="{dur:.4f}" '
            f'data-track-index="{20 + i}" data-variable-values="{vv}" style="{style}"></div>')


def install(hf: Path, specs: list, times: list, template: str, look: str | None = None) -> str:
    """Copy the pieces into hf/compositions/catalog/ and return the template with the mounts written into its root
    composition (right after the opening tag of the first element with data-composition-id). look: the page's look
    (default: read from the template's frame call). A piece's accent is the film's palette accent on a whitespace
    page whose frame passes one (palette_accent), else the look's."""
    if not specs:
        return template
    look = look or look_of(template)
    acc = palette_accent(template, look)
    M = manifest()
    for s in specs:
        if s["name"] not in M:
            raise SystemExit(f"MOUNTS: '{s['name']}' is not vendored (python3 kit/hf/tools/catalog.py --list / add {s['name']})")
    files = [piece_file(hf, i, s) for i, s in enumerate(specs)]
    if (CAT / "assets").exists():
        shutil.copytree(CAT / "assets", hf / "compositions/catalog/assets", dirs_exist_ok=True)
    divs = "\n".join("      " + mount_html(i, s, t, look, f, acc) for i, (s, t, f) in enumerate(zip(specs, times, files)))
    m = re.search(r"<[a-z]+[^>]*\bdata-composition-id=\"[^\"]+\"[^>]*>", template)
    if not m:
        raise SystemExit("MOUNTS: the template has no root composition (an element with data-composition-id)")
    return template[: m.end()] + "\n      <!-- kit/hf/mounts.py: HyperFrames catalog pieces (film.py MOUNTS) -->\n" + divs + template[m.end():]
