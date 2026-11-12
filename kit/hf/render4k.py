"""Render a long HyperFrames film at 4K in time chunks (2026-10-20: was three film copies, films/*/render4k.py; kit/refs/
AUDIT_2026-10-20.md §3). Each chunk is its own small composition, its videos clipped to the chunk and kept from streaming;
the chunks are joined by stream copy into one raw.mp4 (mux the audio after, as the film's build.py --mux does). A
finished chunk is skipped on a re-run. Why chunks: a 4-5 min film rendered in one go at 4K stalled or ran out of memory
(memory: hf-4k-chunk-render); 30 s chunks render in ~3-4 min each with 3 workers.
A chunk is reused only while its cNN.key matches (chunk_key: its page, assets/ sizes + mtimes, vendor/ bytes, render args).

    uv run python kit/hf/render4k.py films/<video>            # F = Film(films/<video>): F.hf/index.html -> F.renders/raw.mp4
    uv run python kit/hf/render4k.py output/temp/films/<name>/hf --out=<renders>/raw.mp4    # any HyperFrames project
      [--chunk=30] [--fps=30] [--workers=3] [--resolution=4k|portrait-4k] [--only=0,1] [--plan]
  (60 fps: --chunk=15 keeps a chunk at ~900 frames, the size the node heap held at 4K)

  --plan   print the chunks and exit (no render)
  --only   render just these chunks (no join)
One heavy render at a time on this Mac (memory: render-concurrency).
"""
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def opt(name, default):
    return next((a.split("=", 1)[1] for a in sys.argv if a.startswith(f"--{name}=")), default)


CHUNK = float(opt("chunk", 30))
FPS = int(opt("fps", 30))
WORKERS = opt("workers", "3")
RESOLUTION = opt("resolution", "4k")        # hyperframes --resolution: "4k" (3840x2160), "portrait-4k" (a Reel at 2x: 2160x3840)
ONLY = {int(x) for x in opt("only", "").split(",") if x}

OFFSET_JS = """
<script>
/* chunk %(k)d: [%(t0).4f, %(t1).4f) of the film (render4k.py) */
(function () {
  const T0 = %(t0).6f, T1 = %(t1).6f;
  const root = document.querySelector("[data-composition-id]");
  const id = root.dataset.compositionId, inner = window.__timelines[id];
  const outer = gsap.timeline({ paused: true });
  outer.add(inner.tweenFromTo(T0, T1, { ease: "none", duration: T1 - T0 }), 0);
  window.__timelines[id] = outer;
  document.querySelectorAll("video[data-start]:not([data-chunked])").forEach((v) => {   // static tags are clipped in the HTML
    const s = +v.dataset.start || 0, d = +(v.dataset.duration || 0), m = +(v.dataset.mediaStart || 0);
    const a = Math.max(s, T0), b = Math.min(s + d, T1);
    if (b <= a + 1e-3) {              // outside this chunk: gone (a window past the end failed the coverage gate, and a
      v.remove(); return; }            // src-less <video> never became "ready": a 5-10 min wait per worker)
    v.dataset.start = (a - T0).toFixed(4); v.dataset.duration = (b - a).toFixed(4); v.dataset.mediaStart = (m + (a - s)).toFixed(4);
  });
  // No video here may stream: the renderer draws each one from its pre-extracted frames. The runtime load()s every video
  // active at time 0, which in a chunk is the 4K A-roll and the cut-out in every capture page: with 4 pages they held all
  // 6 of Chrome's connections to the page server, and the 4th page and the others' fonts and images never loaded (chunk 0
  // hung 15 min at 0 frames, 2026-10-18 08:30). So every video is reset to preload="none", and load()/play() do nothing.
  const quiet = (v) => {
    if (v.__hfQuiet) return;
    v.__hfQuiet = true;
    try { Object.defineProperty(v, "preload", { configurable: true, get: () => "none", set: () => {} }); } catch (e) {}
    v.load = () => {};
    v.play = () => Promise.resolve();
    v.removeAttribute("autoplay");
    v.setAttribute("preload", "none");
    const src = v.getAttribute("src");
    if (src) { v.removeAttribute("src"); HTMLMediaElement.prototype.load.call(v); v.setAttribute("src", src); }   // aborts a fetch already started
  };
  document.querySelectorAll("video").forEach(quiet);
  new MutationObserver((ms) => ms.forEach((mu) => mu.addedNodes.forEach((n) => {
    if (n.nodeType !== 1) return;
    if (n.matches("video")) quiet(n);
    n.querySelectorAll("video").forEach(quiet);
  }))).observe(document.documentElement, { childList: true, subtree: true });
})();
</script>
"""


def static_video(m, t0, t1):
    """Clip a static <video ...> tag's window to [t0, t1] (the compile step reads these from the HTML text)."""
    tag = m.group(0)
    g = lambda k, d=0.0: float(re.search(rf'data-{k}="([0-9.]+)"', tag).group(1)) if re.search(rf'data-{k}="([0-9.]+)"', tag) else d
    s, d, ms = g("start"), g("duration"), g("media-start")
    a, b = max(s, t0), min(s + d, t1)
    if b <= a + 1e-3:                       # outside the chunk: a plain element (scripts look it up by id), not a clip
        vid = re.search(r'id="([^"]+)"', tag)
        return f'<div data-chunked="1" id="{vid.group(1) if vid else "v"}"></div>'     # scripts restyle it by id; not a video
    for k, v in (("start", a - t0), ("duration", b - a), ("media-start", ms + (a - s))):
        tag = re.sub(rf'data-{k}="[0-9.]+"', f'data-{k}="{v:.4f}"', tag) if f"data-{k}=" in tag else tag.replace("<video ", f'<video data-{k}="{v:.4f}" ', 1)
    return tag.replace("<video ", '<video data-chunked="1" preload="none" ', 1)


def chunk_html(html, k, t0, t1):
    # the duration rounded DOWN at 4 decimals: the renderer makes ceil(duration * fps) frames, so 106/60 written as 1.7667
    # came out as 107 frames (the film's last chunk, 2026-10-18 10:07)
    dur = math.floor((t1 - t0) * 1e4) / 1e4
    out = re.sub(r'(data-composition-id="[^"]+"[^>]*?data-duration=")([0-9.]+)(")', lambda m: f"{m.group(1)}{dur:.4f}{m.group(3)}", html, count=1)
    # only the page's static tags (a literal number in data-start): the video tags inside the script's template strings
    # carry "${...}" and are patched at run time by OFFSET_JS
    out = re.sub(r'<video [^>]*data-start="[0-9.]+"[^>]*></video>', lambda m: static_video(m, t0, t1), out)
    # the script's template-string tags: no fetch at parse (only real tags: the kit's error strings say "no <video id=" + ...)
    out = out.replace('<video id="${', '<video preload="none" id="${')
    return out.replace("</body>", OFFSET_JS % {"k": k, "t0": t0, "t1": t1} + "</body>", 1)


def frames(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries", "stream=nb_read_packets",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return int(r.stdout.strip().split("\n")[0].strip().rstrip(",") or 0)   # some ffprobe builds print "5826," (2026-10-23)


def tree(d, by_bytes=False):
    """One sha1 over every file under d, each by its path and its size + mtime (or by_bytes, its contents); dot files are
    left out (a Finder .DS_Store changes no picture) and a linked folder is followed once. '' when there is no d."""
    h, seen = hashlib.sha1(), set()
    for top, dirs, files in os.walk(d, followlinks=True):
        real = os.path.realpath(top)
        if real in seen:
            dirs[:] = []
            continue
        seen.add(real)
        dirs[:] = sorted(x for x in dirs if not x.startswith("."))
        for f in sorted(x for x in files if not x.startswith(".")):
            p = Path(top) / f
            try:
                sig = hashlib.sha1(p.read_bytes()).hexdigest() if by_bytes else "{0.st_size} {0.st_mtime_ns}".format(p.stat())
            except OSError:                                     # a broken link
                sig = "gone"
            h.update(f"{p.relative_to(d).as_posix()}\0{sig}\n".encode())
    return h.hexdigest() if seen else ""


def chunk_key(page, files, look):
    """What a finished chunk was rendered from, written beside it as cNN.key: the sha1 of its page (chunk_html), the page's
    linked folders (`files`: assets/ by size + mtime, so a re-graded face.mp4 or a remade clip counts; vendor/ by its bytes,
    since every build rewrites it) and the render args that shape the picture. A frame count alone let a re-edited
    films/snappaste deliver the previous version's picture for 0-45 s (2026-11-06)."""
    return {"page": hashlib.sha1(page.encode()).hexdigest(), **files, "render": " ".join(look)}


CHANGED = {"page": "the page changed", "assets": "assets/ changed", "vendor": "vendor/ changed",
           "render": "the render args changed"}


def redo(out, key, want):
    """Why the chunk file `out` must be rendered again for `key`, or None when it stands (its key matches, all frames there)."""
    kf = out.with_suffix(".key")
    try:
        old = json.loads(kf.read_text())
    except FileNotFoundError:
        return f"no {kf.name}"
    except ValueError:
        old = None
    if not isinstance(old, dict):
        return f"{kf.name} unreadable"
    diff = [CHANGED.get(n, f"{n} changed") for n in dict.fromkeys([*key, *old]) if old.get(n) != key.get(n)]
    if diff:
        return ", ".join(diff)
    got = frames(out)
    return None if got == want else f"{out.name} has {got} of {want} frames"


def where(arg):
    """(hf project dir, temp dir for the chunk projects and caches, raw.mp4 path) from a film dir or a project dir."""
    p = Path(arg).resolve()
    if (p / "index.html").exists():
        out = Path(opt("out", str(p.parent / "renders" / "raw.mp4"))).resolve()
        return p, p.parent, out
    sys.path.insert(0, str(ROOT))
    from kit.paths import Film
    F = Film(p / "build.py" if p.is_dir() else p)
    return F.hf, F.temp, Path(opt("out", str(F.renders / "raw.mp4"))).resolve()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--help" in sys.argv or "-h" in sys.argv or len(args) != 1:
        print(__doc__.split("\n\n")[1].replace("    uv run", "usage: uv run", 1))
        return
    hf, temp, raw = where(args[0])
    html = (hf / "index.html").read_text()
    if 'class="hf-mount"' in html:      # 2026-10-21: a chunk would need each piece's data-start shifted and its source linked
        raise SystemExit("render4k: the page has HyperFrames catalog pieces (film.py MOUNTS); chunks can't place them yet. "
                         "Build the piece natively in the template (films/oss-editor's prompt notes) or render without chunks.")
    total = float(re.search(r'data-composition-id="[^"]+"[^>]*?data-duration="([0-9.]+)"', html).group(1))
    nfr = int(round(total * FPS))
    per = int(round(CHUNK * FPS))
    bounds = [(i, min(i + per, nfr)) for i in range(0, nfr, per)]
    outdir = raw.parent / "chunks"
    if "--plan" in sys.argv:
        for k, (f0, f1) in enumerate(bounds):
            print(f"chunk {k}: {f0 / FPS:.3f}-{f1 / FPS:.3f} ({f1 - f0} frames) -> {outdir / f'c{k:02d}.mp4'}")
        print(f"{len(bounds)} chunks, {nfr} frames at {FPS} fps -> {raw}")
        return
    outdir.mkdir(parents=True, exist_ok=True)
    # the ready timeout is short on purpose: the probe page (before extraction, no skip list) waits it out on the quiet
    # videos (preload="none" never reaches readyState 2); the capture pages skip extracted videos and are ready in <1 s
    env = dict(os.environ, HYPERFRAMES_NO_UPDATE_CHECK="1", FFMPEG_PROCESS_TIMEOUT_MS="3600000",
               PRODUCER_PAGE_NAVIGATION_TIMEOUT_MS="300000", PRODUCER_PLAYER_READY_TIMEOUT_MS="20000",
               PRODUCER_PUPPETEER_PROTOCOL_TIMEOUT_MS="1200000",
               NODE_OPTIONS=(os.environ.get("NODE_OPTIONS", "") + " --max-old-space-size=5120").strip())
    look = ["--resolution", RESOLUTION, "--fps", str(FPS), "--quality", "delivery"]      # the render args that shape the picture
    files = {"assets": tree(hf / "assets"), "vendor": tree(hf / "vendor", by_bytes=True)}   # the same for every chunk
    parts = []
    for k, (f0, f1) in enumerate(bounds):
        t0, t1 = f0 / FPS, f1 / FPS
        out = outdir / f"c{k:02d}.mp4"
        parts.append(out)
        head = f"chunk {k}: {t0:.3f}-{t1:.3f} ({f1 - f0} frames)"
        if ONLY and k not in ONLY:
            print(f"{head} skipped", flush=True)
            continue
        page = chunk_html(html, k, t0, t1)
        key = chunk_key(page, files, look)
        why = redo(out, key, f1 - f0) if out.exists() else ""       # "": no chunk there yet
        if why is None:
            print(f"{head} done already (its key matches)", flush=True)
            continue
        # each chunk is its own small project (one root index.html, the real assets linked in): a second root file in hf/
        # fails the lint ("multiple_root_compositions")
        proj = temp / "hf_chunks" / f"c{k:02d}"
        proj.mkdir(parents=True, exist_ok=True)
        for d in ("assets", "vendor"):
            if (hf / d).exists() and not (proj / d).exists():
                (proj / d).symlink_to(hf / d)
        if (hf / "hyperframes.json").exists():
            shutil.copy2(hf / "hyperframes.json", proj / "hyperframes.json")
        (proj / "index.html").write_text(page)
        cache = temp / "cache4k" / f"{k:02d}"
        cache.mkdir(parents=True, exist_ok=True)
        print(f"{head} -> {out.name}" + (f" (re-render: {why})" if why else ""), flush=True)
        out.with_suffix(".key").unlink(missing_ok=True)          # a key stands only beside a chunk that finished with it
        r = subprocess.run(["npx", "hyperframes", "render", str(proj), "-o", str(out), *look, "--workers", WORKERS,
                            "--frames-cache-dir", str(cache)], cwd=ROOT, env=env)
        shutil.rmtree(cache, ignore_errors=True)                 # a chunk's extracted frames: tens of GB
        got = frames(out) if out.exists() else 0
        if r.returncode or got != f1 - f0:
            raise SystemExit(f"chunk {k} failed (exit {r.returncode}, {got} of {f1 - f0} frames)")
        out.with_suffix(".key").write_text(json.dumps(key, sort_keys=True) + "\n")
        print(f"chunk {k}: ok ({got} frames)", flush=True)
    if ONLY:
        return
    lst = outdir / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(raw)], check=True)
    print(f"-> {raw} ({frames(raw)} frames, want {nfr})", flush=True)


if __name__ == "__main__":
    main()
