"""Load a film's film.py (or one of its Reels) into one settings object with defaults, plus the folders it uses.

A film is a folder with film.py (the settings below), src/template.html and visual_plan.json (and assets/ for its
screenshots). A Reel cut from the finished film is the folder <film>/reels/<name>/ with its own template.html; its
settings are the film's REELS[<name>] entry over the film's own (kit/film/reels.py). Everything generated goes to
output/ (kit/paths.py), the cut's edl.json and cuts.json included: work/edl.json, never the film folder.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from kit.paths import FILMS, Film, job_dir  # noqa: E402

# the voice chain when a source gives none: kit/reel's (EQ for a close mic, a gentle compressor, -19 LUFS); a film whose
# takes need more (a room's boom, an iPhone a metre away) sets the source's "chain", measured as films/ai-workflows did
VOICE_CLEAN = ("highpass=f=80,"
               "equalizer=f=220:t=q:w=1:g=-2,equalizer=f=3200:t=q:w=1.2:g=2.5,equalizer=f=9000:t=h:w=1:g=1.5,"
               "acompressor=threshold=-26dB:ratio=3:attack=6:release=110:makeup=4,loudnorm=I=-19:TP=-3:LRA=7")

DEFAULTS = dict(
    # ---- the sources: {key: dict} (the key is the "clip" of each piece; word ids are base + the take's word index)
    #   job     the `shorts probe` job of the take (its analysis.json gives the words)
    #   file    the recording, for `prep` (probe + analyze when the job has no analysis yet)
    #   landscape  probe it as 16:9 (default True: films are 16:9)
    #   video   the picture to cut (default: prep's take<c>.mp4 when `picture` is set, else the job's working file)
    #   picture True (or (w, h)): prep makes a CFR SDR copy of the original at FPS (a 4K take; HLG tone-mapped)
    #   clean   True or dict(mic="mono"|"mid"|"right", declip, dereverb, eq=True): prep cleans the voice (WPE when
    #           the two mics differ, DeepFilterNet3) and measures its EQ; the cut then uses both (kit/film/prep.py)
    #   voice   a cleaned voice file to cut (default: prep's, or the video's own audio); chain: its ffmpeg filter
    #           (default: the measured chain for a cleaned source, else VOICE_CLEAN)
    #   base    word-id offset (0, 2000, 4000...); speed: this source's speed (default SPEED; 1.0 for a clip that keeps
    #           its own timing); kind: what the picture is ("cam", "screen", "clip"...)
    #   views   [(a, b, kind)] in source seconds: what the recording shows when (a piece is split at their edges)
    #   tracks  {track name: vf} or {track name: {kind: vf}}: the picture tracks this source feeds and the ffmpeg filter
    #           for each (crop, grade, scale); a kind missing from the dict shows black on that track
    SOURCES={},
    FPS=30, SR=48000,
    TONEMAP="mobius",      # prep's HLG -> SDR for a `picture` source (kit/film/tonemap.py): "mobius" (v11), "hable",
                           # "bt2390" (BT.2390 roll-off as a 3D LUT + 8-bit dither: who-gonna-hire, 2026-10-23), "bt2390c"
    PICTURE_CRF=12,        # x264 CRF of prep's picture copy (lower = fewer generation losses before the cut and grade)
    W=1920, H=1080,        # the page (16:9); the render is 4K (render4k.py), the draft 1080p
    SPEED=1.0,             # talk speed (1.05-1.06 for a chatty take)
    TRACK_SIZE={},         # {track: (w, h) | "native"}: each track's frame size (default: the first source's video size).
                           # "native" (v11): the largest picture its sources' vf give, so a 4K take's 2160 selfie crop
                           # stays 2160 (write the vf without a scale); a 16:9 4K cam shown as a card: (2560, 1440)
    TRACK_SHOW={},         # {track: page px}: the tallest the page shows that track (work/tracks.json's reference for
                           # max_zoom; default the page height H: a full-height card, or full bleed)
    TRACK_CRF=12,
    RENDER_SCALE=None,     # render px per page px for work/tracks.json's zoom budget (None: 4K on a 16:9 film, the page on
                           # a Reel); 1.0 for a film delivered at its page size (1080p), so the lens may crop a 4K take to x2
    ZOOM_CAP=None,         # x over the full frame's cover of the page: the most any shape may magnify the footage (the lens,
                           # punches, pushes, cards). Set, it replaces the source's sharpness in work/tracks.json (sharp_px =
                           # ZOOM_CAP x the page height), accepting that much upscale at the render: who-gonna-hire's 4K60
                           # delivery, 1.3 (2026-10-23). A Reel inherits it (x1.3 over its own page's full-frame cover)
    # ---- the cut (kit/film/cut.py)
    KEEP=[],               # [(src, first id, last id, tag[, gap s after][, "copy"])], or (first, last, tag[, gap]) with
                           # one source. Whole sentences only. "copy" = the same words played twice (a cold open): id + COPY
    COPY=10000,
    JUDGED={},             # {(left id, right id): why} for cutcheck REVIEW/FAIL joins the editor accepted, with the evidence
    TIME_FIX={},           # {(src, i) or i: (start, end)} measured on the voice envelope (the aligner drifts up to 1 s)
    START_FIX={}, END_FIX={},   # {(src, i) or i: s}
    IN_AT={}, OUT_AT={},   # {edit word id: source s}: a piece that starts / ends on that word cuts exactly there (a
                           # screen move it must open on, a run-together edge measured by hand); wins over the search
    LEAD=0.04, SIB_LEAD=0.10,   # in-point pad before a word's sound (more before a hiss)
    SLIVER=0.16, MAX_GAP=0.30,  # a quiet pause longer than MAX_GAP inside a kept range becomes a SLIVER
    SLIVER_AT={},          # {word id: s}: keep a longer pause before that word (a timed beat)
    NOTRIM=set(),          # word ids whose pause before them is never trimmed
    GAP=0.11,              # silence between two kept ranges (source seconds), on top of the edge pads
    HOLD_GAP=set(),        # tags whose picture holds its last frame from the scene's end to the next scene (and through
                           # the film's tail) instead of playing on: a screen recording that runs into another scene
                           # (a caption, the next video, the recorder's UI). True = every scene end. Jump cuts inside a
                           # scene still play on
    VOICE_GAIN={},         # {tag: dB} on that range's voice (a quieter second voice; measure on vo.wav)
    VOICE_MUTE=[],         # [(source, from s, to s)]: that span of the take's voice is silenced (5 ms ramps) before the cut: a
                           # click or a lip smack just before a word, without moving any edge (the picture keeps its frames)
    ROOM_TONE=None,        # dB vs natural: each source's own room tone looped under its stretches of vo.wav (a cleaned
                           # voice leaves digital silence in every pause: mix.py's dropout RUNS); 0.0 = as it was in the take
    GRADE=None,            # dict(look="natural", room=None, tracks=[FACE_TRACK], vignette=0.0, matte=False, reel=None,
                           # kinds={kind: look | None}, regions={kind: [x, y, w, h]}): `grade` runs look v2 on the cut's
                           # tracks (kit/film/grade.py). The room stays as shot by default (OWNER_DEFAULTS §2: no
                           # vignette, no matte dimming or blur); opt in per film. kinds: None = that view kind passes
                           # through as recorded (screen recordings); regions: grade only that rectangle (a cam bubble),
                           # on each track whose frame holds it, or {track: {kind: rect}}. Changing GRADE re-grades on
                           # the next `grade` (the settings in <track>_graded.mp4.ok); until then the page uses the cut
    TAIL=0.6,             # after the last word (a film's fade; a Reel loops with ~0.4)
    FACES=True,            # YuNet (kit/look/faces.py) on FACE_TRACK: each piece's median face for the speaker box
    FACE_TRACK="aroll",
    FACE=[960.0, 430.0, 330.0],   # [cx, cy, size] in page pixels where no face is found (a screen, a test pattern)
    # ---- the camera on him (kit/hf/motion.js HF.motion.lens, 2026-10-22, v11): the page's D.lens (kit/film/build.py)
    LENS=None,             # None (unset): by the film's date, as the v11 sound: on for a film (a Reel: its own template)
                           # made on or after kit/film/mix.py V11_FROM (2026-10-22), off for one made before, so a rebuild
                           # never adds lens moves to a delivered film (build.py lens_why; it prints which and why).
                           # True: the lens moves on him inside every shape (the canvas speaker on FACE_TRACK, HF.box in
                           # HF.studio / HF.reel): pushes, pull-outs, arcs, settles, punches, the jump reframe; False: off
                           # (the page as before v11); or dict(calm=1.0, budget="auto" | "sharp" | "soft" | x, rules={...}):
                           # on, with those (any dict, {} too). budget "auto" (the default): work/tracks.json's sharp
                           # budget of the kind playing (tracks.json kinds) in cards, circles and corners, its soft
                           # allowance for the lens's own moves at full bleed (HF.motion.LENS.full); "sharp" the sharp
                           # budget everywhere, "soft" the soft allowance everywhere, x a fixed cap. Under the sharp
                           # budget a jump-cut reframe it can't pay spends the soft allowance (rules={"jump": {"soft":
                           # False}} keeps it bare), and an HF.box hold the lens leaves still keeps the box's old drift
    STRESS=[],             # word ids the lens may punch on (one lands per 12 s at most); the visual plan's cam "punch"
                           # passages ("punch": <word id>) and say()'s stress ids add to these
    HINGLISH=False,        # the re-listen's whisper prompt
    # ---- the words on screen (kit/film/build.py)
    SPELL={},              # {"heard": "right"} for every word with that text
    TEXT={},               # {word id: "text"} one word ("" hides it from captions and say())
    RESPELL={},            # {(src, first, last[, "copy"]): "what he said, spelled right"}: placed on its own sound
                           # (kit/cut/respell.py: a forced alignment, never an even spread)
    CAPTIONS=dict(chars=42, pause=0.6, span=3.2),   # a caption ends at a sentence end, at `chars`, a pause, or `span` s
    CAPTIONS_FILE="captions.srt",
    DATA={},               # extra JSON for the page (D.x)
    MOUNTS=[],             # HyperFrames catalog pieces on the page: [dict(name, at, dur, box, vars, z, fit)] (kit/hf/mounts.py)
    STICKMAN=True,         # inline the stickman rig
    # ---- the sound (kit/film/mix.py): beds for kit/audio/mix.py
    MUSIC=[],              # [dict(file, a, b, start | drop + at, under, gap, fade_in, fade_out, even, end_fade)]
                           # a / b / at: seconds, "w<id>", "tag:<tag>", "end", "end-<s>". The v11 bed keys (SOUND
                           # "v11", kit/film/mix.py's docstring): duck="voice" (the default there: the bed ducks on his
                           # voice; its gap defaults to under + 6), carve=3 (dB: dips the bed's 1.2-5 kHz band under
                           # speech; opt-in per bed), loop (default True: a bed whose track runs out loops on its own
                           # phrases, kit/audio/loop.py; False: off), xfade (s: the crossfade into this bed at a bed
                           # change, over the phrase-aware 1.5 s; a fallback bed takes 2.0), plan=False (a Reel's planned
                           # "drop" never moves this bed), snap=False (the typed start stays as typed: not snapped to a
                           # downbeat, and the last bed is not moved up to 8 bars to end on its track's ending)
    SOUND=None,            # "v10" | "v11" | None: the mix (kit/film/mix.py sound_why). None: sticky per work/music.json
                           # (the sound the last mix recorded; a music.json without one is v10), else (never mixed) by
                           # the film's date: v11 from V11_FROM (2026-10-22). A REELS entry's sound= wins for that Reel
    AMBITION=None,         # True | False | None: precheck's ambition gate (variety, layouts, stills as HIGH). None: on
                           # for a film made on or after V11_FROM (2026-10-22), off before (kit/film's precheck says
                           # why); --ambition / --no-ambition on the command line win (P-M3)
    # ---- the render (kit/film/render.py)
    OUT="film_4k.mp4",
    DRAFT_WORKERS=4, WORKERS=3, CHUNK=30,
    # ---- Reels cut from the finished film (kit/film/reels.py): {name: dict(sentences=[(first id, last id)], ...)}
    REELS={},
    # ---- the documentary preset (kit/film/doc.py, kit/presets/documentary; 2026-10-24). Opt-in only: a film is a
    # documentary when it says PRESET = "documentary" (he asked for a "Netflix-style" film). Every other film keeps the
    # pipeline exactly as it was: DOC, J/L cuts on KEEP and the doc gates are refused without it (doc.guard)
    PRESET=None,
    DOC={},                # dict(broll=[...], chapters=[...], stamps=[...], letterbox=[...], subtitles=True): kit/film/doc.py
)

# a Reel's own defaults (the film's settings fill the rest)
REEL_DEFAULTS = dict(W=1080, H=1920, TAIL=0.4, OUT=None, MUSIC=[], DATA={}, MOUNTS=[], FACES=False,
                     START_AT={}, END_AT={}, SENTENCES=[], CAPTIONS_FILE=None,
                     SPLIT=[],            # word ids that start a new range though they follow the last one: the pause
                                          # before them is cut to the quiet points (a held beat the film needed, a Reel not)
                     HOLD={},             # {last word id of a range: s}: a beat after it with no voice (the film's
                                          # picture plays on under it; the Reel's page covers it: a reveal, a result)
                     VOICE_FX=[],         # [(first id, last id, ffmpeg -af)]: a filter on one passage of the Reel's voice
                                          # (a soft line in the take: a presence lift), crossfaded in and out over 40 ms
                     OUT_4K=None)         # out_4k: the same page rendered at 2x (2160x3840, kit/hf/render4k.py chunks) after OUT


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FilmConfig:
    """films/<name>/film.py (or kit/film/example/film.py) as one object: every DEFAULTS key as an attribute, plus
    .dir (the recipe folder), .F (kit.paths.Film: work, hf, renders, final), .reel (None, or the Reel's name)."""

    def __init__(self, film):
        p = Path(film)
        if not p.exists():
            p = FILMS / film
        p = p.resolve()
        if p.is_file():
            p = p.parent
        self.dir, self.reel, self.parent = p, None, None
        if (p / "film.py").exists():
            mod = _load(p / "film.py", "film_" + p.name.replace("-", "_"))
            for k, v in DEFAULTS.items():
                setattr(self, k, getattr(mod, k, v))
            self.mod = mod
            self.template = p / "src/template.html"
            self.F = Film(p / "film.py")
        elif p.parent.name == "reels" and (p.parent.parent / "film.py").exists():
            self._as_reel(p)
        else:
            raise SystemExit(f"{p}: no film.py (and not <film>/reels/<name>)")
        if not self.SOURCES:
            raise SystemExit(f"{self.dir}: set SOURCES in film.py")
        self.work = self.F.work
        from kit.film import doc
        doc.guard(self)                                # documentary settings only on a PRESET = "documentary" film

    def _as_reel(self, p: Path):
        parent = FilmConfig(p.parent.parent)
        spec = parent.REELS.get(p.name)
        if spec is None:
            raise SystemExit(f"{p}: the film has no REELS[{p.name!r}]")
        for k in DEFAULTS:
            setattr(self, k, getattr(parent, k))
        for k, v in REEL_DEFAULTS.items():
            setattr(self, k, v)
        # the Reel's words are the film's finished ones (spelled, placed): only its own `text` fixes apply on top
        self.SPELL, self.RESPELL, self.TEXT = {}, {}, {}
        for k, v in spec.items():                       # REELS entries use lower-case keys: sentences, music, out, text...
            setattr(self, k.upper(), v)
        self.mod, self.dir, self.reel, self.parent = parent.mod, p, p.name, parent
        self.template = p / "template.html"
        self.F = Film(p / "template.html")
        self.OUT = self.OUT or f"reel_{p.name}.mp4"
        self.CAPTIONS_FILE = self.CAPTIONS_FILE or f"reel_{p.name}_captions.srt"

    # ---- sources and words
    def src(self, c) -> dict:
        s = dict(self.SOURCES[c])
        s.setdefault("base", 0)
        s.setdefault("kind", "cam")
        s.setdefault("speed", self.SPEED)
        s.setdefault("tracks", {"aroll": ""})
        s.setdefault("views", [])
        s.setdefault("landscape", True)
        return s

    def voice_file(self, c) -> Path:
        """What the cut's voice is cut from: the source's `voice`, prep's cleaned voice (`clean`), or the video's audio."""
        s = self.src(c)
        if s.get("voice"):
            return Path(s["voice"])
        if s.get("clean"):
            p = self.work / f"voice{c}_df.wav"
            if not p.exists():
                raise SystemExit(f"source {c}: `clean` is set but there is no {p.name}: run `python -m kit.film {self.dir} prep`")
            return p
        return self.video(c)

    def voice_chain(self, c) -> str:
        """The source's `chain`; for a cleaned source with eq (the default), the measured chain from prep's voice_eq.json."""
        if "chain" in self.SOURCES[c]:
            return self.SOURCES[c]["chain"]
        from kit.film.prep import clean_opts, measured_chain
        o = clean_opts(self.SOURCES[c])
        if o and o["eq"]:
            mc = measured_chain(self, c)
            if mc is None:
                raise SystemExit(f"source {c}: eq is on but voice_eq.json has no entry for it: run `python -m kit.film {self.dir} prep`")
            return mc
        return VOICE_CLEAN

    def video(self, c) -> Path:
        s = self.src(c)
        if s.get("video"):
            return Path(s["video"])
        if s.get("picture"):                           # prep's CFR SDR intermediate (a 4K take)
            p = self.work / f"take{c}.mp4"
            if not p.exists():
                raise SystemExit(f"source {c}: `picture` is set but there is no {p.name}: run `python -m kit.film {self.dir} prep`")
            return p
        probe = job_dir(s["job"]) / "probe.json"
        if not probe.exists():
            raise SystemExit(f"source {c}: no {probe}: run `python -m kit.film {self.dir} prep` (or `shorts probe`)")
        return Path(json.loads(probe.read_text())["working_path"])

    def size(self, c) -> tuple[int, int]:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                            str(self.video(c))], capture_output=True, text=True, check=True).stdout.strip().split(",")
        return int(r[0]), int(r[1])

    def track_size(self, name) -> tuple[int, int]:
        if self.TRACK_SIZE.get(name) == "native":
            from kit.film.cut import native_size
            return native_size(self, name)
        if name in self.TRACK_SIZE:
            return tuple(self.TRACK_SIZE[name])
        c = next(c for c in self.SOURCES if name in self.src(c)["tracks"])
        return self.size(c)

    def tracks(self) -> list[str]:
        return list(dict.fromkeys(t for c in self.SOURCES for t in self.src(c)["tracks"]))

    def key(self, c, i):
        """A fix map's key for word i of source c: (c, i), or i alone when the film has one source."""
        return (c, i) if len(self.SOURCES) > 1 else i

    def fix(self, table, c, i, default=None):
        return table.get((c, i), table.get(i, default) if len(self.SOURCES) == 1 else default)

    def words(self, c) -> list[dict]:
        """Source c's words (analysis.json) with TIME_FIX / START_FIX / END_FIX applied."""
        s = self.src(c)
        W = json.loads((job_dir(s["job"]) / "analysis.json").read_text())["words"]
        for w in W:
            tf = self.fix(self.TIME_FIX, c, w["i"])
            if tf:
                w["start"], w["end"] = tf
            w["start"] = self.fix(self.START_FIX, c, w["i"], w["start"])
            w["end"] = self.fix(self.END_FIX, c, w["i"], w["end"])
        return W

    def keep(self) -> list[dict]:
        """KEEP as dicts {c, a, b, tag, gap, copy}."""
        one = next(iter(self.SOURCES)) if len(self.SOURCES) == 1 else None
        out = []
        for k in self.KEEP:
            k = list(k)
            if one is not None and isinstance(k[2], str):          # (first, last, tag, ...) with one source
                k = [one] + k
            c, a, b, tag = k[:4]
            gap = next((x for x in k[4:] if isinstance(x, (int, float))), None)
            out.append({"c": c, "a": a, "b": b, "tag": tag, "gap": gap, "copy": "copy" in k[4:]})
        return out

    def eid(self, c, i, copy=False) -> int:
        return self.src(c)["base"] + i + (self.COPY if copy else 0)

    def of_eid(self, e):
        """Edit word id -> (source, word index, copy)."""
        copy = e >= self.COPY
        e0 = e % self.COPY
        c = max((c for c in self.SOURCES if self.src(c)["base"] <= e0), key=lambda c: self.src(c)["base"])
        return c, e0 - self.src(c)["base"], copy

    # ---- generated files (all under output/)
    def track_file(self, name) -> tuple[Path, str | None]:
        """A picture track the page and the Reels use: the graded one (grade step) while it is a complete grade of the
        cut as it is now, else the cut's. -> (path, why it is not graded or None).

        Complete (2026-10-22, v11): <track>_graded.mp4.ok (kit/look/ffio.py) says it holds every frame of the cut it
        was graded from, and that cut is this one. Newer-than-the-cut alone let a grade that stopped short reach the
        page (films/ai-video-editor: 220 frames short, its last ~7 s frozen). A graded file from before the .ok is
        counted once instead. And made with GRADE as it is now (v11 review): a look, room, kinds plan, region or set
        changed since the grade means the graded file is stale too (kit/film/grade.py want(); a record from before
        settings were kept is compared on its looks), so the 4K render refuses it instead of shipping the old look."""
        from kit.look import ffio as FF
        cut, graded = self.work / f"{name}.mp4", self.work / f"{name}_graded.mp4"
        wants = self.GRADE and name in (self.GRADE.get("tracks") or [self.FACE_TRACK])
        want = None
        if wants and not self.reel and graded.exists():
            try:
                from kit.film.grade import want as grade_want
                want = grade_want(self, name)
            except (SystemExit, OSError, ValueError, KeyError, subprocess.CalledProcessError) as e:
                print(f"NOTE: {name}: GRADE's settings could not be worked out ({e}); the graded track is checked for completeness only")
        ok, why = FF.status(cut, graded, want=want) if graded.exists() or FF.part(graded).exists() else (False, None)
        if ok:
            return graded, None
        if not wants or self.reel:                     # a Reel's tracks are cut from the film's graded ones
            return cut, None
        return cut, f"{name}: GRADE is set but " + (why or f"{graded.name} is missing") + ": run `grade`"

    @property
    def edl_path(self) -> Path:
        return self.work / "edl.json"

    def edl(self) -> dict:
        if not self.edl_path.exists():
            raise SystemExit(f"no {self.edl_path}: run `python -m kit.film {self.dir} {'reels' if self.reel else 'cut'}` first")
        return json.loads(self.edl_path.read_text())
