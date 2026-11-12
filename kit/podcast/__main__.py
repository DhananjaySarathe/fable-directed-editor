"""The podcast pipeline (kit/podcast/README.md):

    uv run shorts probe "<file>" --job <take> --landscape && uv run shorts analyze <take>     # words (whisper + align)
    uv run python -m kit.podcast films/<name> marks       # faces + mouths + eyes at 10 fps (Apple Vision, ~1/10 real time)
    uv run python -m kit.podcast films/<name> speakers    # who says each word -> work/speakers.txt (review the '?' lines)
    uv run python -m kit.podcast films/<name> trims       # candidates -> work/trims.md (judge them; write CUT in podcast.py)
    uv run python -m kit.podcast films/<name> plan        # edit list + shot list + work/plan.md: SHOW THE OWNER, wait for ok
    uv run python -m kit.podcast films/<name> preview [--at=120]   # 90 s at 720p from --at (s on the edited timeline)
    uv run python -m kit.podcast films/<name> render      # the episode: sound, picture, captions.srt, chapters, qa
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from kit.podcast import audio, camera, look, render, speakers, trims  # noqa: E402
from kit.podcast import edl as pedl  # noqa: E402
from kit.podcast.config import Pod  # noqa: E402

BIN = ROOT / "kit/bin/facemarks"
SRC = ROOT / "kit/podcast/facemarks.swift"


def opt(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv if a.startswith(f"--{name}=")), default)


def mm(s):
    return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{int(s % 60):02d}" if s >= 3600 else f"{int(s // 60):02d}:{int(s % 60):02d}"


def duration(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout)


def size(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:stream_side_data=rotation", "-of", "json", str(p)],
                         capture_output=True, text=True).stdout
    s = json.loads(out)["streams"][0]
    w, h = s["width"], s["height"]
    rot = abs(int(next((d.get("rotation", 0) for d in s.get("side_data_list", []) if "rotation" in d), 0)))
    return (h, w) if rot in (90, 270) else (w, h)


def marks(P):
    if not BIN.exists() or BIN.stat().st_mtime < SRC.stat().st_mtime:
        subprocess.run(["swiftc", "-O", "-o", str(BIN), str(SRC)], check=True)
    out = P.work / "marks.jsonl"
    subprocess.run([str(BIN), str(P.source), str(out), "10"], check=True, stderr=subprocess.DEVNULL)
    print("marks ->", out)


def load_speakers(P):
    M = speakers.load(P.work / "marks.jsonl")
    people = speakers.people(M, k=len(P.PEOPLE))
    t, act = speakers.activity(M, people)
    an = json.load(open(P.job / "analysis.json"))
    attr = speakers.attribute(an["words"], t, act, an.get("sentences"), P.SPEAKER_FIX)
    return M, people, attr, an


def do_speakers(P):
    M, people, attr, an = load_speakers(P)
    T = speakers.turns(attr)
    json.dump({"people": people, "words": attr, "turns": T}, open(P.work / "speakers.json", "w"))
    lines = speakers.sheet(attr, T, P.work / "speakers.txt")
    for p in people:
        print(f"{p['id']} ({P.PEOPLE.get(p['id'])}): face x {p['cx']:.2f}, seen in {p['seen'] * 100:.0f} % of samples")
    weak = sum(1 for l in lines if l.split()[1].endswith("?"))
    print(f"{len(T)} turns, {weak} weak ('?') -> {P.work / 'speakers.txt'} (fix with SPEAKER_FIX)")


def do_trims(P):
    M, people, attr, an = load_speakers(P)
    t, eyes = speakers.per_person(M, people, "eyes")
    items = trims.pauses(an["words"], P.GAP_MAX) + trims.phone(t, eyes, people, an["words"]) + trims.repeats(an["sentences"]) + \
        trims.restarts(an["sentences"]) + trims.fillers(an["words"])
    lines = trims.report(items, P.work / "trims.md")
    print("\n".join(lines[:60]))


def build(P):
    M, people, attr, an = load_speakers(P)
    env, thr = pedl.voice_env(P.source)
    E = pedl.build(P, attr, env, thr)
    pedl.save(P.work / "edl.json", E)
    SW, SH = size(P.source)
    rects, warn = camera.crops(people, SW, SH, P.RES, P.CROP, P.WIDE_ZOOM)
    if P.SPLITS:                                  # joined takes: people sit a little differently in each, so crops per take
        edges = [0.0, *P.SPLITS, 1e9]
        rects = []
        for a, b in zip(edges, edges[1:]):
            pk = speakers.people([m for m in M if a <= m["t"] < b], k=len(P.PEOPLE))
            rk, wk = camera.crops(pk, SW, SH, P.RES, P.CROP, P.WIDE_ZOOM)
            rects.append({"a": a, "b": b, "rects": rk})
            warn += [w for w in wk if w not in warn]
    ot = {w["i"]: w["ot"] for w in E["words"]}
    chap_t = [ot[i] for i, _ in P.CHAPTERS if i in ot]
    shots, log, stats = camera.direct(E, [p["id"] for p in people], E["total"], chap_t, P.MIN_HOLD, P.MAX_HOLD, P.FPS)
    flat = lambda r: {f"{k[0]}:{k[1]}": v for k, v in r.items()}
    rj = flat(rects) if isinstance(rects, dict) else [dict(r, rects=flat(r["rects"])) for r in rects]
    json.dump({"shots": shots, "rects": rj, "log": log, "stats": stats}, open(P.work / "shots.json", "w"), indent=0)
    return E, people, rects, shots, stats, warn, an


def plan(P):
    E, people, rects, shots, stats, warn, an = build(P)
    src_d = an.get("duration") or duration(P.source)
    cut_s = sum(an["words"][b]["end"] - an["words"][a]["start"] for a, b, *_ in P.CUT if b < len(an["words"]))
    why = {}
    for a, b, *r in P.CUT:
        why[r[0] if r else "cut"] = why.get(r[0] if r else "cut", 0) + 1
    L = [f"# Plan: {P.dir.name} (check this before anything renders)", "",
         f"- Length: {mm(src_d)} recorded -> {mm(E['total'])} edited ({src_d - E['total']:.0f} s out: {len(P.CUT)} cuts"
         f" [{', '.join(f'{k} x{v}' for k, v in why.items()) or 'none yet'}] ~{cut_s:.0f} s, pauses over {P.GAP_MAX} s shortened).",
         f"- Camera: one wide shot cropped into wide / single / tight; {stats['shots']} shots, {stats['per_min']} a minute; time on "
         + ", ".join(f"{k} {int(v * 100)} %" for k, v in sorted(stats["share"].items())) + ".",
         f"- People: " + ", ".join(f"{p['id']} = {(lambda v: v.get('name') if isinstance(v, dict) else v)(P.PEOPLE.get(p['id']))}" for p in people) + ("; a name card the first time each gets a single." if P.LOWER_THIRDS else "; named by the designed intro."),
         f"- Sound: gentle noise reduction (-{P.DENOISE_DB} dB max){', dereverb' if P.DEREVERB else ''}, both voices levelled, "
         f"light compression, {P.LUFS} LUFS; music: {'intro/outro bed only' if P.MUSIC else 'none'}.",
         f"- Look: light grade measured from both faces (white balance and exposure halfway to natural skin), soft contrast.",
         f"- Chapters: " + ("; ".join(t for _, t in P.CHAPTERS) if P.CHAPTERS else "none yet") + "."]
    if warn:
        L += ["", "Warnings:"] + [f"- {w}" for w in warn]
    L += ["", "Cuts (word ranges, why):"] + [f"- {a}-{b}: {r[0] if r else ''}" for a, b, *r in P.CUT]
    (P.work / "plan.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def do_render(P, preview=None):
    E, people, rects, shots, stats, warn, an = build(P)
    mix, gains = audio.run(P, E)
    meas = look.measure(P.source, P.SPLITS[0] if P.SPLITS else duration(P.source), people)   # one take's face boxes
    vf = look.filters(meas, P.LOOK)
    print(f"look: WB r x{meas['r']:.3f} b x{meas['b']:.3f}, exposure x{meas['exp']:.2f} (skin {meas.get('skin')})")
    out = (P.F.renders / "preview.mp4") if preview else (P.F.final / P.OUT)
    out.parent.mkdir(parents=True, exist_ok=True)
    o, n = render.render(P, E, shots, rects, vf, mix, out, preview=preview)
    print(f"-> {o} ({n} segments)")
    if not preview:
        srt(P, E)
        chapters(P, E)
        cuts = P.work / "cuts.json"
        cuts.write_text(json.dumps(E["cuts"]))
        subprocess.run([sys.executable, str(ROOT / "kit/qa/qa.py"), str(o), f"--cuts={cuts}", f"--expect-duration={E['total']:.2f}",
                        f"--expect-size={round(P.RES * 16 / 9 / 2) * 2}x{P.RES}"])
    return o


def srt(P, E, per=7):
    ts = lambda s: f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d},{int(s * 1000 % 1000):03d}"
    W, out, k = E["words"], [], 1
    for i in range(0, len(W), per):
        g = W[i:i + per]
        out.append(f"{k}\n{ts(g[0]['ot'])} --> {ts(g[-1]['oe'])}\n{' '.join(w['text'] for w in g)}\n")
        k += 1
    (P.F.final / "captions.srt").write_text("\n".join(out))


def chapters(P, E):
    ot = {w["i"]: w["ot"] for w in E["words"]}
    rows = ["00:00 Intro"] + [f"{mm(ot[i])} {t}" for i, t in P.CHAPTERS if i in ot]
    (P.F.final / "chapters.txt").write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        raise SystemExit(__doc__)
    P, step = Pod(args[0]), args[1]
    if step == "marks":
        marks(P)
    elif step == "speakers":
        do_speakers(P)
    elif step == "trims":
        do_trims(P)
    elif step == "plan":
        plan(P)
    elif step == "preview":
        a = float(opt("at", 0))
        do_render(P, preview=(a, a + float(opt("len", 90))))
    elif step == "render":
        do_render(P)
    else:
        raise SystemExit(__doc__)
