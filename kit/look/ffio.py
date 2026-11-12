"""ffmpeg in and out for the grade, the scopes and the face track: one place for the decode flags and the colour tags.

Decode (2026-10-22, v11 grade hygiene): swscale's default YUV -> RGB path rounds fast and interpolates chroma cheaply,
which lost 2-3 code values at the top (a 255 white came back as 253) and blurred chroma edges. Every Python decoder
now converts with `accurate_rnd+full_chroma_int` (measured on a ramp: mean error 1.77 -> 0.29 code values, white 253 ->
255; scratchpad build/picture/enc_test.py). A resize keeps its own algorithm (bicubic, ffmpeg's default) and gains the
same flags, so face detection sees the same picture it always did, only rounded right.

Encode: x264 only writes the colour description (VUI) it is told through -x264-params; `-color_trc` / `-color_primaries`
alone left graded tracks tagged colourspace bt709 but transfer and primaries "unknown" (face_graded.mp4, oss-editor).
The matrix itself was always BT.709 (the round trip is exact), so tagging changes no pixel in the file; it changes what
a player assumes, and Chrome assumed other primaries for the untagged file: orange 200/100/50 showed as 187/95/52, skin
240/200/180 as 234/198/181; tagged, it shows the exact values (scratchpad build/picture/tags, headless Chrome).
"""
from __future__ import annotations

import subprocess

ACC = "accurate_rnd+full_chroma_int"
DECODE_VF = f"scale=flags={ACC}"                     # a format conversion only (no resize), rounded right
BT709 = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
         "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709"]


def scale(w: int, h: int, algo: str = "bicubic") -> str:
    """A resize with the accurate flags (algo: ffmpeg's scaler name; bicubic is what a bare scale=w:h used)."""
    return f"scale={w}:{h}:flags={algo}+{ACC}"


def vf(*filters: str) -> list:
    """['-vf', 'a,b,...,scale=flags=accurate...'] for a decode to rgb24: the given filters, then (when none of them is
    already a scale) the accurate format conversion."""
    fs = [f for f in filters if f]
    if not any(f.startswith("scale=") for f in fs):
        fs.append(DECODE_VF)
    return ["-vf", ",".join(fs)]


def frames(p) -> int:
    """Video frames in a file by counting packets (0.1-0.2 s on a 900 MB 4K track; no decode)."""
    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries", "stream=nb_read_packets",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    try:
        return int(r.stdout.strip().split(",")[0] or 0)
    except ValueError:
        return 0


# ------------------------------------------------------------------------------------------------ completeness (.part / .ok)
# 2026-10-22 (v11 grade hygiene): films/ai-video-editor shipped with its last ~7 s frozen (its graded track is 220
# frames shorter than the cut: 11036 of 11256). The grade had stopped short,
# the file it left was a valid, shorter mp4, and every check downstream took "it exists and is newer than the cut" as
# "it is done": Chrome held the last frame to the end. Now a grade writes <out>.part and renames it only when the frames
# it graded, the frames in the source and the frames in the file all agree, then writes <out>.ok: what it was graded
# from (that cut's frame count, size and mtime) and the graded file's own size. A reader (kit/film config.track_file,
# kit/reel prep) trusts a graded track only through status(): a missing / stale / truncated one never reaches a page.
import json as _json
from pathlib import Path as _Path


def part(out) -> _Path:
    """Where a grade writes before it is complete: <out>.part (muxer named explicitly: '.part' is no known extension)."""
    return _Path(str(out) + ".part")


def ok_path(out) -> _Path:
    return _Path(str(out) + ".ok")


def mark(out, src, n: int, size_of=None, exclusive: bool = False, **info) -> dict:
    """Write <out>.ok: the graded file `out` holds n frames, graded from `src` (its frames, size, mtime at grade time).
    `size_of`: the file whose size is recorded (finish: the .part, before it becomes `out`); default `out`.
    Atomic (a temp file, then os.replace): a build reading it while a grade or another build writes it sees the old
    record or the new one, never half of one. `exclusive`: only if no .ok exists (os.link, which fails on an existing
    name): FileExistsError otherwise, and nothing is replaced."""
    import os
    out, src = _Path(out), _Path(src)
    st, so = src.stat(), _Path(size_of or out).stat()
    rec = {"frames": int(n), "size": so.st_size, "src": src.name, "src_frames": frames(src), "src_size": st.st_size,
           "src_mtime_ns": st.st_mtime_ns, **info}
    tmp = _Path(str(ok_path(out)) + f".{os.getpid()}.tmp")
    tmp.write_text(_json.dumps(rec, indent=1))
    if exclusive:
        try:
            os.link(tmp, ok_path(out))
        finally:
            tmp.unlink(missing_ok=True)
    else:
        os.replace(tmp, ok_path(out))
    return rec


# ------------------------------------------------------------------------------------------------ settings (what a grade was asked for)
# 2026-10-22 (v11 review): completeness alone let a changed GRADE keep the old grade: set look="clean", run `grade`, and
# it printed "graded already" and the page kept natural. A grade now records what it was asked for in its .ok
# ("settings"), and the readers that know what they want (kit/film grade and config.track_file, kit/reel prep) pass it
# to status(): a different look, room, kinds plan, region, matte, reel finish or GRADE_V2_SET is a stale grade.
DATA_OPTS = ("track", "map")             # the face data, not a choice: derived from the cut (its own record covers a re-cut)
ON_OPTS = ("matte", "balance")           # where a choice's files are: recorded as on, never as a path


def _val(v):
    """A setting's value as compared: numbers as floats ('0' == '0.0'), words as they are."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def settings(args, v2set: str = "", plan=None) -> dict:
    """What a grade is asked to do, with no paths: {"opts": {option: value}, "set": {GRADE_V2_SET key: value}}.

    args: kit/look/grade.py's arguments after <src> <out> (as passed: '--look=clean', '--v2', '--looks=<file>' ...);
    --track / --map are dropped, --matte / --balance count as on, --looks is the plan's content (`plan`, else the file's),
    a bare flag is True. v2set: GRADE_V2_SET ('vignette=0,wb_ref=white'; last wins, as v2.params reads it)."""
    opts = {}
    for a in map(str, args):
        if not a.startswith("--"):
            continue
        k, eq, v = a[2:].partition("=")
        if k in DATA_OPTS:
            continue
        if k in ON_OPTS:
            v = "on"
        elif k == "looks":
            if plan is None:
                try:
                    plan = _json.loads(_Path(v).read_text())
                except (OSError, ValueError):
                    plan = f"unreadable {_Path(v).name}"
            v = plan
        opts[k] = _val(v) if eq else True
    sets = {}
    for kv in filter(None, (x.strip() for x in (v2set or "").split(","))):
        k, _, v = kv.partition("=")
        sets[k.strip()] = _val(v.strip())
    return _json.loads(_json.dumps({"opts": opts, "set": sets}, sort_keys=True))


def looks_of(st: dict) -> set:
    """The look names a settings dict grades with: the --looks plan's (passthroughs left out), else --look (default
    natural, as grade.py)."""
    o = st.get("opts", {})
    if isinstance(o.get("looks"), list):
        return {str(p.get("look")) for p in o["looks"] if p.get("look")}
    return {str(o.get("look", "natural"))}


def _graded_looks(out, rec) -> set | None:
    """A record with no settings (a grade from before they were recorded): the looks it was graded in, from the record
    (2026-10-22 first .ok files) or from <out>.balance.json (every v2 grade writes one: {look: balance} per shot);
    None when neither says."""
    if isinstance(rec.get("look"), list):
        return {x for x in rec["look"] if x and x != "None"}
    b = _Path(str(out) + ".balance.json")
    try:
        shots = _json.loads(b.read_text())
        return {k for s in shots if s.get("bal") for k in s["bal"]} or None
    except (OSError, ValueError, AttributeError):
        return None


def _diff(have: dict, want: dict) -> str:
    """'look natural -> clean, set.vignette 0.0 -> (none)': the first few settings that differ."""
    out = []
    for sec in ("opts", "set"):
        a, b = have.get(sec, {}), want.get(sec, {})
        for k in sorted(set(a) | set(b)):
            if a.get(k) != b.get(k):
                show = lambda v: "(none)" if v is None else ("plan" if isinstance(v, list) else str(v))   # noqa: E731
                out.append(f"{'' if sec == 'opts' else 'set.'}{k} {show(a.get(k))} -> {show(b.get(k))}")
    return ", ".join(out[:3]) + (f" (+{len(out) - 3} more)" if len(out) > 3 else "")


def _settings_ok(out, rec, want) -> tuple:
    if want is None:
        return True, None
    have = rec.get("settings")
    if have is not None:
        return (True, None) if have == want else (False, f"{_Path(out).name} was graded with other settings ({_diff(have, want)}): re-grade")
    looks = _graded_looks(out, rec)                     # older record: only its looks can be compared
    if looks is not None and looks != looks_of(want):
        return False, (f"{_Path(out).name} was graded in {', '.join(sorted(looks))}; the grade now asks for "
                       f"{', '.join(sorted(looks_of(want)))}: re-grade")
    return True, None


def finish(tmp, out, src, n: int, **info) -> dict:
    """The end of a grade: tmp (the .part) becomes `out` only if n (frames graded) == the source's frames == the file's
    frames; then <out>.ok is written. Otherwise tmp is left for a look and SystemExit says what is short (an older
    complete `out`, if any, is untouched and keeps its own .ok)."""
    a, b = frames(src), frames(tmp)
    if not (n == a == b):
        raise SystemExit(f"{_Path(out).name}: incomplete grade: {n} frames graded, the source has {a}, the file holds {b} "
                         f"(left as {_Path(tmp).name}; nothing replaced)")
    # the record first (for the .part's size), then the rename (2026-10-22, v11 review): the old order (drop the .ok,
    # rename, then count and write the record, ~0.2 s) left a moment with a new file and no .ok, and a build that looked
    # then took status()'s pre-v11 path and wrote a record with no settings over the real one. Now an .ok always exists
    # from here on: until the rename it names the new size, so the old file (or none) reads as stale, never as graded
    rec = mark(out, src, n, size_of=tmp, **info)
    _Path(tmp).replace(out)
    return rec


def status(src, out, write=True, want=None) -> tuple:
    """Is `out` (a graded track) a complete grade of `src` (the cut) as it is now, and (with `want`, a settings()
    dict) made with those settings? -> (ok, why or None).

    With <out>.ok: its frames == the cut's frames at grade time, the graded file is still the size it was written at
    (not truncated or replaced), the cut is still the one it was graded from (size + mtime), and its recorded settings
    are `want`. A record from before settings were recorded is compared on its looks only (_graded_looks); one that
    says nothing is trusted (as it was). A graded file from before 2026-10-22 has no .ok (or an unreadable one: an
    interrupted write): it is trusted only when it is newer than the cut and holds as many frames as the cut (both
    counted, ~0.2 s each), and then the .ok is written (`write`) so the next look is a stat."""
    src, out = _Path(src), _Path(out)
    if not out.exists():
        return False, f"{out.name} is missing" + (f" ({part(out).name} is an unfinished grade)" if part(out).exists() else "")
    if not src.exists():
        return False, f"no {src.name}"
    okp = ok_path(out)
    rec, unreadable = None, False
    if okp.exists():
        try:
            rec = _json.loads(okp.read_text())
        except (OSError, ValueError):
            rec = None
        unreadable = not isinstance(rec, dict)          # unreadable (or not a record): counted again below, and rewritten
    if isinstance(rec, dict):
        st = src.stat()
        if rec.get("frames") != rec.get("src_frames"):
            return False, f"{out.name}: {rec.get('frames')} frames, the cut had {rec.get('src_frames')}"
        if rec.get("size") != out.stat().st_size:
            return False, f"{out.name} changed after its grade ({out.stat().st_size} bytes, graded {rec.get('size')}): re-grade"
        if rec.get("src_size") != st.st_size or rec.get("src_mtime_ns") != st.st_mtime_ns:
            return False, f"{out.name} was graded from an older {src.name}"
        return _settings_ok(out, rec, want)
    if out.stat().st_mtime <= src.stat().st_mtime:
        return False, f"{out.name} is older than the cut"
    a, b = frames(src), frames(out)
    if a != b or a == 0:
        return False, f"{out.name}: {b} frames, the cut has {a}"
    rec = {"legacy": True}
    if write:
        # only where no record exists (exclusive): a grade that finished while this counted has written its own, with
        # its settings, and a record without settings must never replace it. An unreadable one is replaced (it says
        # nothing; atomic writes since v11 make it a leftover of an older interrupted write)
        try:
            rec = mark(out, src, b, exclusive=not unreadable, legacy=True)
        except FileExistsError:
            return status(src, out, write=False, want=want)   # someone wrote one meanwhile: judge by it
        except OSError:
            pass
    return _settings_ok(out, rec, want)
