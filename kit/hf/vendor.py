"""Put the paper-studio component kit into a HyperFrames film.

HyperFrames serves only the project folder, so a film can't load files from kit/. This copies what the kit needs
(fonts, gsap) into the film and inlines the kit's CSS and JS into the page at the `<!--HF:KIT-->` marker.

    python3 kit/hf/vendor.py <film_dir>                                  # copy fonts + gsap into the film
    python3 kit/hf/vendor.py <film_dir> src/template.html index.html     # ... and write index.html with the kit inlined

From a film's build.py:
    sys.path.insert(0, str(ROOT / "kit/hf")); import vendor
    vendor.copy_assets(HERE); html = vendor.inline(html)
"""
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
ROOT = KIT.parent
FONTS = ["InstrumentSerif-Regular.ttf", "InstrumentSerif-Italic.ttf", "Inter-500.ttf", "Inter-600.ttf", "Inter-700.ttf", "Inter-800.ttf",
         "JetBrainsMono-500.ttf", "JetBrainsMono-700.ttf"]
MODULES = ["core.js", "lucide.js", "motion.js", "box.js", "scenes.js", "diagram.js", "screen.js", "code.js", "explain.js", "polish.js"]
GSAP_CANDIDATES = [ROOT / "node_modules/gsap/dist/gsap.min.js"]     # the repo root's npm install (./setup.sh)
# v7 styles (README: sketch / annotate / scribble / collage): their modules, hand fonts and libraries (repo-root `npm i`)
MODULES += ["sketch.js", "annotate.js", "scribble.js", "collage.js"]
FONTS += ["Excalifont-Regular.woff2", "Caveat-700.ttf"]
# v8 motion (README "v8 motion"): kinetic type, springs and motion tokens, plus its display faces
MODULES += ["kinetic.js"]
FONTS += ["Anton-400.ttf", "Montserrat-800.ttf", "Montserrat-900.ttf"]
# pastel-box preset (kit/presets/pastel_box): the film frame (world, chrome, chapters, type, layers, box wiring) + UI cards
MODULES += ["studio.js", "studio_ui.js"]
# evidence (kit/refs/RESEARCH.md, 2026-10-10): focus zoom, running scoreboard, declared reading holds, quiet moments
MODULES += ["evidence.js"]
# paper collage (kit/presets/paper_collage, 2026-10-11): aged paper, cut-out objects, stamps, tape, tickets, a drawn chart
MODULES += ["paper.js"]
# the night-build frame (films/ai-portfolio, 2026-10-17): dark developer desktop, HUD clock, contender colours, windows
MODULES += ["night.js"]
# redline (kit/presets/redline, 2026-10-19): graph paper, black grotesk, one red pen, pencil sketches, real screens as figures
MODULES += ["redline.js"]
FONTS += ["SchibstedGrotesk-800.ttf", "SchibstedGrotesk-900.ttf", "AtkinsonHyperlegibleNext-500.ttf", "AtkinsonHyperlegibleNext-700.ttf",
          "MartianMono-500.ttf", "NanumPenScript-400.ttf"]
# the studio canvas (kit/hf/canvas.js, 2026-10-20): one lit stage, a camera, 3D windows/cards, beams, a speaker card
MODULES += ["canvas.js"]
FONTS += ["ArchivoCondensed-900.ttf"]
# transitions and takeovers (kit/hf/trans.js, 2026-10-22, kit v11): C.takeover / S.takeover scenes with him off, T.zoomThrough,
# T.match, T.chapter, T.cardToGraphic, the per-film budget in window.__trans. It only defines HF.trans / HF.takeover (and
# window.__speaker for HF.camera pages), so a page that calls none of it draws what it drew before.
MODULES += ["trans.js"]
# the 9:16 Reel kit and its Reel-only add-ons (2026-10-20, kit/refs/AUDIT_2026-10-20.md §3): every Reel pipeline had to
# remember to append these. They only define HF.reel / HF.footage / HF.agent / HF.nightReel, so 16:9 films are unaffected.
MODULES += ["reel.js", "footage.js", "agent.js", "night_reel.js"]
# living backgrounds (2026-10-20): HF.shaderBg over Paper Shaders (kit/hf/lib/paper-shaders.js, a bundle of
# @paper-design/shaders 0.0.81, Apache-2.0)
MODULES += ["shaders.js"]
# animated emoji (2026-10-20): HF.emoji over Noto's Lottie files (kit/emoji/noto, CC BY 4.0) and lottie-web's light
# player (MIT). inline() adds the data of the emoji a page names (HF.EMOJI), never the whole set.
MODULES += ["emoji.js"]
# the 2.5D camera move through a still (2026-10-20): HF.parallax over a depth map from kit/look/depth.py
MODULES += ["parallax.js"]
EMOJI_DIR = KIT / "emoji/noto"
LIBS = [("gsap/dist/DrawSVGPlugin.min.js", "DrawSVGPlugin.min.js", None),            # (node_modules path, vendor/ name, CJS global)
        ("roughjs/bundled/rough.js", "rough.js", None),
        ("perfect-freehand/dist/cjs/index.js", "perfect-freehand.js", "PerfectFreehand"),
        # GSAP's plugins, free under the standard GSAP license since 3.13 (2026-10-20): icon morphs (HF.morph), the
        # "wrong" shake (HF.shake). Every one is a tween on the paused timeline, so frames seek exactly.
        ("gsap/dist/MorphSVGPlugin.min.js", "MorphSVGPlugin.min.js", None),
        ("gsap/dist/CustomEase.min.js", "CustomEase.min.js", None),
        ("gsap/dist/CustomWiggle.min.js", "CustomWiggle.min.js", None),
        ("kit:hf/lib/paper-shaders.js", "paper-shaders.js", None),
        ("kit:hf/lib/lottie_light.min.js", "lottie_light.min.js", None)]                       # "kit:" = a file vendored in kit/


def copy_libs(film: Path) -> None:
    """Copy the style libraries into vendor/ (a CJS file is wrapped so it sets a global). Missing ones are skipped."""
    for src, name, glob in LIBS:
        if src.startswith("kit:"):
            p = KIT / src[4:]
            p = p if p.exists() else None
        else:
            p = next((r / "node_modules" / src for r in (ROOT,) if (r / "node_modules" / src).exists()), None)
        if p is None:
            print(f"vendor.py: {src} not installed (run `npm i` at the repo root); {name} skipped", file=sys.stderr)
            continue
        js = p.read_text()
        if glob:
            js = f"(function(){{var exports={{}},module={{exports:exports}};\n{js}\nwindow.{glob}=module.exports;}})();\n"
        (film / "vendor" / name).write_text(js)


def gsap_path() -> Path:
    for p in GSAP_CANDIDATES:
        if p.exists():
            return p
    raise SystemExit("gsap not found: run `npm install` in the repo root (./setup.sh does it)")


def copy_assets(film: Path) -> None:
    film = Path(film)
    (film / "assets/fonts").mkdir(parents=True, exist_ok=True)
    (film / "vendor").mkdir(exist_ok=True)
    for f in FONTS:
        shutil.copy2(KIT / "fonts" / f, film / "assets/fonts" / f)
    shutil.copy2(gsap_path(), film / "vendor/gsap.min.js")
    copy_libs(film)


def inline(html: str, stickman: bool = True) -> str:
    """Replace <!--HF:KIT--> with gsap + the kit's CSS and JS (and the stickman rig)."""
    if "<!--HF:KIT-->" not in html:
        raise SystemExit("template has no <!--HF:KIT--> marker (put it in <head>)")
    css = (HERE / "paper.css").read_text().replace("FONTS/", "assets/fonts/")
    js = [(HERE / m).read_text() for m in dict.fromkeys(MODULES)]      # once each, though a build may append a module again
    if "HF.doc(" in html:                                       # the documentary preset's pieces: only on a page that calls them
        js.append((HERE / "doc.js").read_text())                # (kit/presets/documentary), so every other page is unchanged
    if stickman:
        js.append((KIT / "stickman/stickman.js").read_text())
    block = ['<script src="vendor/gsap.min.js"></script>'] + [f'<script src="vendor/{n}"></script>' for _, n, _ in LIBS] + [f"<style>\n{css}\n</style>"]
    block += [f"<script>\n{s}\n</script>" for s in js]
    # the channel's handles (kit/brand.json, the one place they live): HF.BRAND, and HF.HANDLES for end cards
    brand = json.loads((KIT / "brand.json").read_text())
    block.append(f"<script>\nHF.BRAND = {json.dumps(brand)}; HF.HANDLES = HF.BRAND.end_card;\n</script>")
    used = emoji_used(html)
    if used:                                                    # only the emoji this page names (HF.emoji(..., "fire", ...))
        data = {n: json.loads((EMOJI_DIR / f"{n}.json").read_text()) for n in used}
        block.append(f"<script>\nHF.EMOJI = {json.dumps(data, separators=(',', ':'))};\n</script>")
    return html.replace("<!--HF:KIT-->", "\n".join(block))


def emoji_used(html: str) -> list[str]:
    """The Noto emoji a page's script names in HF.emoji(K, parent, "name", ...) calls (kit/emoji/noto/<name>.json)."""
    names = sorted(set(re.findall(r"HF\.emoji\(\s*[^,]+,\s*[^,]+,\s*[\"']([a-z0-9-]+)[\"']", html)))
    missing = [n for n in names if not (EMOJI_DIR / f"{n}.json").exists()]
    if missing:
        raise SystemExit(f"HF.emoji: no kit/emoji/noto/{missing[0]}.json (have: {', '.join(sorted(p.stem for p in EMOJI_DIR.glob('*.json')))})")
    return names


if __name__ == "__main__":
    film = Path(sys.argv[1])
    copy_assets(film)
    if len(sys.argv) >= 4:
        src, out = film / sys.argv[2], film / sys.argv[3]
        out.write_text(inline(src.read_text()))
        print(f"{out}: kit inlined ({', '.join(dict.fromkeys(MODULES))} + stickman)")
    else:
        print(f"{film}: fonts + gsap copied")
