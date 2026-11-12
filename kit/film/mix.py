"""The mix: vo.wav + the MUSIC beds + the page's cues (work/cues.json, cues.quiet.json) -> work/mix.wav, mastered to
-14 LUFS / -1.5 dBTP by kit/audio/mix.py (music ~18 dB under the voice on a film, ~12 on a Reel, while he talks, lifted in pauses, out in quiet
moments; small cues thinned; every sound's attack or peak on its cue).

A MUSIC bed is a dict (as kit/reel's): file (under kit/music), a, b, and where the track starts:
  start=12.0          track seconds at a; moved to the nearest downbeat within half a bar (snap=False keeps it as typed)
  drop="auto", at=…   the track's biggest rise (a drop, a build landing) lands on the moment `at`
  drop="section:2"    its 2nd section start lands on `at`
  drop=52.42, at=…    a hand-measured drop (track seconds) lands on `at`; never moved
  end_on="track_end"  the track's own ending lands on b (the last bed of a film or Reel)
under, gap, fade_in, fade_out, even, end_fade as kit/audio/mix.py Bed. a / b / at take seconds, "w<id>" (that word's
start on the cut), "tag:<tag>" (the first piece with that KEEP tag), "end" or "end-<s>"; "w<id>-3.2" / "tag:<tag>+1"
offsets one by seconds (a bed that starts 3.2 s before the word its drop lands on).

The drops, sections and downbeats come from the music map (kit/audio/beats.py -> kit/music/beats.json). music_map()
gives them in film time: build.py hands them to the page as D.music (HF.music.snap lands a card on the beat), and
run() writes work/music.json with the findings qa.py reports (--music): a bed that enters off its downbeat, and a
section change in the music (6 dB or more) with no story sound near it (nothing happens on screen as the music turns;
a fall into the outro in the film's last 8 s is its ending, not a finding).

    uv run python -m kit.film <film> mix

The v11 sound (2026-10-22, kit/audio/mix.py's docstring has the why): films made from V11_FROM on mix with it, older
ones exactly as before (sound_why): SOUND = "v10" | "v11" in film.py (or sound= in a REELS entry) wins; else the
version the film's last mix recorded in work/music.json ("sound"; a music.json without it is a pre-v11, v10 mix) -
the gate is sticky, so an edit or a copy of film.py never flips a film's sound between two mixes; else (never mixed)
the day film.py was added to git, or for an untracked film the oldest of its file times and its work dir's edl.json /
vo.wav. kit/reel's Reels (cut from their own single take) take the same gate and the same planner through
kit/reel/build.py (SOUND in reel.py; made_on their src/template.html). On v11:
  - every bed ducks on the voice (Bed.duck="voice"), its gap defaults to under + 6 (films -18 / -12, Reels -12 / -6),
    carve=3 dips its 1.2-5 kHz band under speech (opt-in per bed);
  - a bed whose track runs out loops on its own phrases (kit/audio/loop.py; loop=False turns it off). kit/film plans
    every play list (looped()) and hands it to the mix, so the page's D.music beats follow the same seams. A typed
    start is kept when a plan fits from it; only the last bed may then start up to 8 bars later to end on its track's
    ending (snap=False, a drop and end_on never move). end_on ends on the track's last audible moment, through a loop
    when the track is shorter than its bed (v10 started it at 0 and padded silence); when no seam matches, a second
    long-form bed (kit/music/library.json longform, same mood first, not used by this film) takes over with a 2 s
    equal-power crossfade, looped the same way if it runs out too;
  - bed changes are phrase-aware on films (the outgoing bed ends on its own next downbeat, a 1.5 s equal-power
    crossfade; xfade= on the incoming bed overrides it); Reels keep v10's quick 0.2 s crossfade (their beds change on
    drops, where a 1.5 s cross would blur the hit);
  - SFX families rotate and the format's budget holds (kit/audio/mix.py Sound: films 8 small cues a minute at most,
    Reels 12; no file over 25 % of the cues or 4 a minute); clips (edl kind "clip") take the music down 19 dB;
  - the visual plan's music moments are executed: "stop" -> a quiet window over the passage's first sentence (unless
    the page's S.quiet already covers it; the mix reports the silent breath it leaves as "in quiet windows (meant)",
    not as dropout RUNS); on Reels "riser" -> a riser that peaks on the passage and "drop" -> the
    covering bed placed by drop="auto" on it (unless the bed already pins its own drop); a moment that cannot be
    played is printed and becomes a music.json finding. Long-form drops and risers are dropped: beds are calm;
  - music.json's findings (qa.py --music reports them, MEDIUM) add: a long-form bed without "longform" in the
    library, a long-form bed louder than -16 under the voice or more than 2 beds, a bed whose track runs out, music
    under speech more than 2 dB off the format's target (-18 / -12), more than 3 lifts a minute;
  - output/music_usage.json records each film's tracks (kit/paths.py) and the mix notes a track another film used;
  - music.json records "sound" (v10 too) and "mix": the measured sound (under_db, lifts_per_min, up_db_s, down_db_s,
    sfx_per_min, small_per_min, top_file, top_share, variants, lra); a looped bed lists its segments and seams.
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import date
from pathlib import Path

import numpy as np

from kit.audio import beats as BT
from kit.audio import loop as LP
from kit.audio.mix import SMALL, V11, V11_REEL, Bed, decode, mix as kmix, sfx_offset
from kit.paths import OUTPUT, ROOT, film_name

MUSIC_DIR = ROOT / "kit/music"
TURN_DB = 6.0           # a section change this loud (either way) is a turn the viewer hears
NEAR = 0.6              # ... and a story sound within this many seconds of it makes it motivated
OFF_BEAT = 0.08         # a bed entering further than this from a downbeat starts mid-bar
V11_FROM = "2026-10-22"                 # films made from this day mix with the v11 sound (old mixes reproduce)
TARGET = {"film": -18.0, "reel": -12.0}  # music under speech (dB vs the voice): OWNER_DEFAULTS §4
FALLBACK_XFADE = 2.0    # s: the crossfade into a second long-form bed when a track can't loop
RISER = "riser/riser__cinematic-trailer-riser__mixkit-790"     # a plan's "riser" on a Reel (2.6 s, builds to its peak)
USAGE = OUTPUT / "music_usage.json"


def made_on(Fm) -> str:
    """The day the film (its film.py) or the Reel (its template.html) was made: git's first commit of it, else (an
    untracked film) the OLDEST of that file's creation and change times and its work dir's edl.json / vo.wav times, as
    YYYY-MM-DD. A birthtime alone moves: `sed -i`, an editor's safe-write or a copy makes a new file today, and a film
    from yesterday would have switched sound on its next mix (review, 2026-10-22). Fm.made_file, when set, names that
    file instead (kit/reel: the Reel's src/template.html)."""
    f = getattr(Fm, "made_file", None) or ((Fm.dir / "template.html") if Fm.reel else (Fm.dir / "film.py"))
    if not f.exists():
        return date.today().isoformat()
    try:
        r = subprocess.run(["git", "log", "--diff-filter=A", "--follow", "--format=%as", "--", f.name], cwd=f.parent,
                           capture_output=True, text=True, timeout=20)
        days = r.stdout.split()
        if r.returncode == 0 and days:
            return days[-1]
    except (OSError, subprocess.SubprocessError):
        pass
    w = getattr(Fm, "work", None)
    times = []
    for p in [f] + ([Path(w) / "edl.json", Path(w) / "vo.wav"] if w else []):
        if p.exists():
            st = p.stat()
            times += [getattr(st, "st_birthtime", st.st_mtime), st.st_mtime]
    return date.fromtimestamp(min(times)).isoformat()


def sound_why(Fm) -> tuple[str, str]:
    """('v11' | 'v10', why), in this order:
      1. SOUND in film.py (or sound= in the REELS entry);
      2. what this film's last mix recorded in work/music.json ("sound"): the gate is sticky, so a later edit, copy or
         re-cut never flips a film's sound between two mixes; a music.json without it was written before v11 (a v10 mix);
      3. never mixed: the day the film was made (made_on) vs V11_FROM."""
    s = getattr(Fm, "SOUND", None) or getattr(getattr(Fm, "mod", None), "SOUND", None)
    if s:
        return str(s), "SOUND in film.py"
    w = getattr(Fm, "work", None)
    p = Path(w) / "music.json" if w else None
    if p is not None and p.exists():
        try:
            M0 = json.loads(p.read_text())
            rec = M0.get("sound", "v10")
        except (OSError, ValueError, AttributeError):
            M0, rec = {}, None
        if rec in ("v10", "v11"):
            return rec, ("recorded by its last mix (work/music.json)" if "sound" in M0 else
                         "its last mix was made before v11 (work/music.json has no 'sound')")
    d = made_on(Fm)
    return ("v11" if d >= V11_FROM else "v10"), f"made on {d}, v11 from {V11_FROM}"


def sound_of(Fm) -> str:
    """'v11' or 'v10' (sound_why without the reason)."""
    return sound_why(Fm)[0]


def fmt_of(Fm) -> str:
    return "reel" if Fm.reel or Fm.H > Fm.W else "film"


def when(edl, v):
    if isinstance(v, (int, float)):
        return float(v)
    m = re.match(r"^(w\d+|tag:[\w-]+)([+-][0-9.]+)$", v)                # "w250-3.2": 3.2 s before word 250
    if m:
        return when(edl, m.group(1)) + float(m.group(2))
    if v == "end":
        return edl["total"]
    if v.startswith("end-"):
        return edl["total"] - float(v[4:])
    if v.startswith("tag:"):
        return next(p["out_a"] for p in edl["pieces"] if p.get("tag") == v[4:])
    if v.startswith("w"):
        i = int(v[1:])
        return next(w["t"] for w in edl["words"] if w["i"] == i)
    return float(v)


def snap_start(e, start, limit=None):
    """The downbeat nearest `start` within half a bar (not past `limit`), or `start` when the map can't say."""
    if not e or not e["steady"] or not e["downbeats"]:
        return start
    d = np.array(e["downbeats"])
    if limit is not None:
        d = d[d <= limit]
    if not len(d):
        return start
    k = float(d[np.argmin(np.abs(d - start))])
    return k if abs(k - start) <= 2 * 60 / e["bpm"] else start


def resolve(m, a, b, edl, tracks, loop=False):
    """(start, how) for one MUSIC bed: the track second that plays at film time a. loop (v11): end_on with a track
    shorter than its bed starts where kit/audio/loop.py's play list ends the track on b (v10: 0, then silence)."""
    e = BT.entry(m["file"], tracks)
    span = b - a
    if "start" in m:
        s = float(m["start"])
        if m.get("snap", True) and e:
            t = snap_start(e, s)
            return t, f"start {s:g} -> downbeat {t:g}" if abs(t - s) > 1e-3 else f"start {s:g} (a downbeat)"
        return s, f"start {s:g}" + ("" if e else " (no music map: not snapped)")
    if m.get("end_on") == "track_end":
        if not e:
            raise SystemExit(f"{m['file']}: end_on needs the music map (python -m kit.audio.beats --check)")
        # v11: the ending is the track's last AUDIBLE moment (a zero-padded tail is not music); v10 used the file's length
        dur = LP.audible_end(LP.pcm(str(MUSIC_DIR / m["file"]))) if loop else e["duration"]
        if loop and m.get("loop", True) and dur - (e["downbeats"][0] if e["downbeats"] else 0.0) < span:
            d0 = e["downbeats"][0] if e["steady"] and e["downbeats"] else 0.0
            p = LP.plan(MUSIC_DIR / m["file"], e, d0, span, end=True)
            if p:
                return p["start"], f"the track's ending on {b:.2f} s through a loop: {p['how']}"
        d = [x for x in (e["downbeats"] if e["steady"] else []) if x <= dur - span]
        s = max(d) if d else max(0.0, dur - span)                      # the last downbeat that still fits the bed
        return s, f"the track's ending on {b:.2f} s (start {s:g}, {dur - s - span:.2f} s of it after the end)"
    if "drop" in m and not isinstance(m["drop"], str):
        return m["drop"] - (when(edl, m["at"]) - a), f"drop {m['drop']} on {m['at']} (hand-measured)"
    if "drop" in m:
        if not e:
            raise SystemExit(f"{m['file']}: drop={m['drop']!r} needs the music map (python -m kit.audio.beats --check)")
        at = when(edl, m["at"])
        lead = at - a
        secs = e["sections"]
        if m["drop"].startswith("section:"):
            cands = [secs[int(m["drop"].split(":")[1]) - 1]]
        else:
            cands = sorted(secs, key=lambda s: -s["rise"])
        fit = [s for s in cands if s["t"] - lead >= 0 and s["t"] - lead + span <= e["duration"] - 0.3]
        if not fit:
            raise SystemExit(f"{m['file']}: no section start fits drop={m['drop']!r} at {at:.2f} s for a {span:.1f} s bed "
                             f"(sections: {', '.join(str(s['t']) for s in secs)}); pick another track or a shorter bed")
        s = fit[0]
        return s["t"] - lead, f"its section at {s['t']} s ({s['rise']:+.1f} dB) on {m['at']} ({at:.2f} s)"
    return 0.0, "start 0"


def plan(Fm, edl, v11=False, drops=(), notes=None):
    """[(MUSIC dict, a, b, start, how, map entry)] in film order. v11: end_on loops a short track; `drops` (a Reel's
    planned drops, film times) place the bed that covers each one by drop="auto" unless the bed pins its own drop or
    ends on its track's end; a drop that can't be placed is appended to `notes`."""
    tracks = BT.load()
    out = []
    for m in Fm.MUSIC:
        a, b = when(edl, m.get("a", 0.0)), min(edl["total"], when(edl, m.get("b", "end")))
        for d in drops:
            if not a <= d["t"] < b:
                continue
            if "drop" in m:
                at = when(edl, m["at"]) if "at" in m else None
                if at is None or abs(at - d["t"]) > 0.3:
                    notes is not None and notes.append(dict(d, why=f"the bed {m['file'].split('/')[-1]} places its own drop at {at}"))
                continue
            if m.get("end_on") or m.get("plan") is False:
                notes is not None and notes.append(dict(d, why=f"the bed {m['file'].split('/')[-1]} ends on its track's end (or plan=False)"))
                continue
            try:
                resolve(dict(m, drop="auto", at=d["t"]), a, b, edl, tracks)
            except SystemExit as err:
                notes is not None and notes.append(dict(d, why=str(err)))
                continue
            m = {k: v for k, v in m.items() if k != "start"} | {"drop": "auto", "at": d["t"]}
            print(f"plan: the drop at {d['t']:.2f} s ({d['id']}) places {m['file'].split('/')[-1]}")
        start, how = resolve(m, a, b, edl, tracks, loop=v11)
        out.append((m, a, b, max(0.0, start), how, BT.entry(m["file"], tracks)))
    return out


def _through(xs, a, segs):
    """[(track time, film time)] of the track times xs through a play list [(t0, t1)] that starts at film time a (a
    looped bed plays some times more than once, each at its own film time)."""
    out, F = [], a
    for t0, t1 in segs:
        out += [(x, F + (x - t0)) for x in xs if t0 - 1e-6 <= x < t1 - 1e-6]
        F += t1 - t0
    return out


def _is_v11(Fm) -> bool:
    try:
        return sound_of(Fm) == "v11"
    except (AttributeError, TypeError):                                # a bare test double: the v10 map
        return False


def music_map(Fm, edl, planned=None, bedlist=None):
    """The beds' musical events in film time: {beds, beats, downbeats, sections: [{t, rise}], drops: [t]} (D.music).
    bedlist (v11): the Beds the mix plays, mapped through their play lists (a looped bed's beats follow its seams; a
    fallback's second bed is in it). A v11 film called without either (build.py) plans its beds here as the mix will."""
    M = {"beds": [], "beats": [], "downbeats": [], "sections": [], "drops": []}
    if planned is None and bedlist is None and _is_v11(Fm):
        bedlist = prepare(Fm, edl)["beds"]
    if bedlist is not None:
        for bd in bedlist:
            m, a, b, start, e = bd._m, bd.a, bd.b, bd.start, BT.entry(bd.file)
            segs = [tuple(s) for s in bd.segments] if bd.segments else [(start, float("inf"))]
            bed = {"file": m["file"], "a": round(a, 3), "b": round(b, 3), "start": round(start, 3), "how": bd._how}
            if bd.segments:
                bed["segments"] = [[round(t0, 3), round(t1, 3)] for t0, t1 in bd.segments]
                bed["seams"] = LP.seam_times(a, bd.segments)
            if e:
                inb = lambda t: a - 1e-6 <= t <= b
                bed["entry_ms"] = None if "drop" in m or not e["downbeats"] else round(min(abs(np.array(e["downbeats"]) - start)) * 1000)
                bed["steady"] = e["steady"]
                M["beats"] += [round(f, 3) for _, f in _through(e["beats"], a, segs) if inb(f)]
                if e["steady"]:
                    M["downbeats"] += [round(f, 3) for _, f in _through(e["downbeats"], a, segs) if inb(f)]
                rise = {s["t"]: s["rise"] for s in e["sections"]}
                M["sections"] += [{"t": round(f, 3), "rise": rise[x]} for x, f in _through(list(rise), a, segs) if a + 0.5 < f < b - 0.5]
                if isinstance(m.get("drop"), (str, int, float)) and "at" in m:
                    M["drops"].append(round(when(edl, m["at"]), 3))
            M["beds"].append(bed)
        for k in ("beats", "downbeats", "drops"):
            M[k] = sorted(set(M[k]))
        M["sections"].sort(key=lambda s: s["t"])
        return M
    for m, a, b, start, how, e in planned or plan(Fm, edl):
        bed = {"file": m["file"], "a": round(a, 3), "b": round(b, 3), "start": round(start, 3), "how": how}
        if e:
            film = lambda x: a + (x - start)
            inb = lambda t: a - 1e-6 <= t <= b
            # a bed placed by its drop starts where the drop puts it (the entry sits under the crossfade): only a bed
            # given a start or end_on is held to its downbeat
            placed = "drop" in m
            bed["entry_ms"] = None if placed or not e["downbeats"] else round(min(abs(np.array(e["downbeats"]) - start)) * 1000)
            bed["steady"] = e["steady"]
            M["beats"] += [round(film(x), 3) for x in e["beats"] if inb(film(x))]
            if e["steady"]:
                M["downbeats"] += [round(film(x), 3) for x in e["downbeats"] if inb(film(x))]
            M["sections"] += [{"t": round(film(s["t"]), 3), "rise": s["rise"]} for s in e["sections"] if a + 0.5 < film(s["t"]) < b - 0.5]
            if isinstance(m.get("drop"), str) or isinstance(m.get("drop"), (int, float)):
                M["drops"].append(round(when(edl, m["at"]), 3))
        M["beds"].append(bed)
    for k in ("beats", "downbeats", "drops"):
        M[k] = sorted(set(M[k]))
    M["sections"].sort(key=lambda s: s["t"])
    return M


def findings(M, cues):
    """What qa.py reports from the music map: [{t, id, detail, fix}] (MEDIUM)."""
    story = sorted(c["at"] for c in cues if c.get("keep") or not any(s in c["name"] for s in SMALL))
    out = []
    for bed in M["beds"]:
        if bed.get("steady") and bed.get("entry_ms") is not None and bed["entry_ms"] > OFF_BEAT * 1000:
            out.append({"t": bed["a"], "id": f"music-entry@{bed['a']:.1f}", "detail": f"{bed['file'].split('/')[-1]} enters "
                        f"{bed['entry_ms']} ms off its downbeat (mid-bar)", "fix": "drop snap=False, or start on a downbeat"})
    end = max((b["b"] for b in M["beds"]), default=0.0)
    for s in M["sections"]:
        if s["rise"] < 0 and s["t"] > end - 8.0:                       # the music falling into its outro as the film ends
            continue
        if abs(s["rise"]) >= TURN_DB and not any(abs(t - s["t"]) <= NEAR for t in story + M["drops"]):
            out.append({"t": s["t"], "id": f"music-turn@{s['t']:.1f}", "detail": f"the music turns at {s['t']:.2f} s "
                        f"({s['rise']:+.1f} dB) with no story sound near it", "fix": "land a reveal or a card there "
                        "(HF.music.near), or move the bed's start so the turn falls on a moment"})
    return out


def beds(Fm, edl, planned=None, v11=False, notes=None):
    """kit/audio/mix.py Beds for the planned MUSIC. v11: voice duck, gap = under + 6, loops (or the fallback's second
    bed) for a track that runs out; each Bed carries its MUSIC dict (_m) and how it was placed (_how)."""
    out = []
    planned = planned or plan(Fm, edl)
    for j, (m, a, b, start, how, e) in enumerate(planned):
        # a placed drop's own break (a riser, half a second of nothing, then the hit) is meant: up to 2.5 s before it
        drop_t = start + (when(edl, m["at"]) - a) if "drop" in m else None
        if not v11:
            out.append(Bed(MUSIC_DIR / m["file"], a, b, start, m.get("gap", -5.0), m.get("under", -12.0 if Fm.reel else -18.0),   # OWNER_DEFAULTS §4
                           m.get("fade_in", 0.3), m.get("fade_out", 0.3), even=m.get("even", 0.0), end_fade=m.get("end_fade"),
                           allow_silence=((drop_t - 2.5, drop_t + 0.05),) if drop_t is not None else ()))
            out[-1]._m, out[-1]._how = m, how
            continue
        under = m.get("under", -12.0 if fmt_of(Fm) == "reel" else -18.0)

        def mk(f, a0, b0, s0, mm, hw, segments=None, xfade=None):
            # loop= only when kit/film planned the play list itself (segments): the mix never re-plans a bed on its own
            # terms, so the page's D.music (music_map), music.json's seams and the mix always play the same list
            return _bed(Bed(MUSIC_DIR / f, a0, b0, s0, mm.get("gap", under + 6.0), under, mm.get("fade_in", 0.3), mm.get("fade_out", 0.3),
                            even=mm.get("even", 0.0), end_fade=mm.get("end_fade"),
                            allow_silence=((drop_t - 2.5, drop_t + 0.05),) if drop_t is not None and f == m["file"] else (),
                            duck=mm.get("duck", "voice"), carve=mm.get("carve", 0.0), loop=segments is not None,
                            segments=segments, xfade=xfade if xfade is not None else mm.get("xfade")), mm, hw)
        last = j == len(planned) - 1
        if not e or not m.get("loop", True):
            out.append(mk(m["file"], a, b, start, m, how))
            continue
        p = looped(m, e, start, b - a, last)
        if p == "fits":
            out.append(mk(m["file"], a, b, start, m, how))
            continue
        if p:
            out.append(mk(m["file"], a, b, p["start"], m, f"{how}; {p['how']}", segments=tuple(p["segments"])))
            print(f"loop {m['file'].split('/')[-1]}: {p['how']}; seams at film "
                  f"{', '.join('%.2f' % x for x in LP.seam_times(a, p['segments']))} s (listen to each)")
            continue
        bar = 240 / e["bpm"]
        D = LP.audible_end(LP.pcm(str(MUSIC_DIR / m["file"])))
        # no seam passes: a second long-form bed takes over on a downbeat before this track's ending, 2 s crossfade
        f2 = second_bed(m["file"], {x[0]["file"] for x in planned})
        downs = [d for d in (e["downbeats"] if e["steady"] else []) if start + 8.0 < d <= D - 4 * bar]
        J = max(downs) if downs else D - 4.0
        T = a + (J - start)
        if f2 is None or T >= b - 4.0:
            out.append(mk(m["file"], a, b, start, m, how))
            notes is not None and notes.append({"t": a, "kind": "runs-out", "id": m["file"],
                                                "why": f"{m['file'].split('/')[-1]} runs out at film {a + D - start:.1f} s and no seam or second bed fits"})
            continue
        # (a few seconds in, so its own lead-in plays under the crossfade; the last bed ends on its track's ending)
        m2 = {"file": f2, "end_on": "track_end"} if last else {"file": f2, "start": FALLBACK_XFADE + 2.0}
        tracks = BT.load()
        s2, how2 = resolve(m2, T, b, edl, tracks, loop=True)
        s2 = max(0.0, s2)
        print(f"music: {m['file'].split('/')[-1]} can't loop (no seam passes): {f2.split('/')[-1]} takes over at {T:.2f} s "
              f"with a {FALLBACK_XFADE:g} s crossfade")
        out.append(mk(m["file"], a, T, start, m, how))
        mm2 = dict(m2, **{k: m[k] for k in ("under", "gap", "carve", "duck", "end_fade") if k in m})
        how2 = f"the fallback for {m['file'].split('/')[-1]}: {how2}"
        # the second track may run out too (end_on through a loop, or a middle bed): its play list is planned here, as
        # the first bed's is, so the page's D.music and the mix follow the same seams
        e2 = BT.entry(f2, tracks)
        p2 = looped(m2, e2, s2, b - T, last) if e2 else "fits"
        if p2 not in ("fits", None):
            out.append(mk(f2, T, b, p2["start"], mm2, f"{how2}; {p2['how']}", segments=tuple(p2["segments"]), xfade=FALLBACK_XFADE))
            print(f"loop {f2.split('/')[-1]}: {p2['how']}; seams at film "
                  f"{', '.join('%.2f' % x for x in LP.seam_times(T, p2['segments']))} s (listen to each)")
            continue
        if p2 is None:
            notes is not None and notes.append({"t": T, "kind": "runs-out", "id": f2,
                                                "why": f"the fallback {f2.split('/')[-1]} runs out too and no seam fits"})
        out.append(mk(f2, T, b, s2, mm2, how2, xfade=FALLBACK_XFADE))
    return out


def looped(m, e, start, span, last):
    """A MUSIC bed's play list when its track runs out (kit/audio/loop.py), "fits" when it doesn't, None when no seam
    passes. The bed needs `span` s (plus a bar and the phrase crossfade after a middle bed). end_on's start came from the
    same planner (resolve) and a drop's start puts the drop on its moment: neither moves. A given start (or the default
    0) is kept when a plan fits from it; only then may the last bed start up to 8 bars later (LP.SHIFT_BARS) to land on
    its track's ending; snap=False never moves (oss-editor's piano moved 0.4 -> 6.4 s before 2026-10-22's review)."""
    path = MUSIC_DIR / m["file"]
    need = span + (0 if last else 240 / e["bpm"] + V11.phrase + 0.5)
    if LP.audible_end(LP.pcm(str(path))) - start >= need - (0.5 if last else 0.0):   # (the film's end fade covers 0.5 s:
        return "fits"                                                                  # the mix warns past that too)
    p = LP.plan(path, e, start, need, end=last, shift=False)
    movable = not m.get("end_on") and "drop" not in m and m.get("snap", True)
    if p is None and last and movable:
        p = LP.plan(path, e, start, need, end=True, shift=True)
    return p


def _bed(bd, m, how):
    bd._m, bd._how = m, how
    return bd


def second_bed(file, used):
    """A second long-form track for a bed that can't loop: kit/music/library.json's longform tracks this film doesn't
    use, the same mood first, then the longest. None when there is none."""
    lib = json.loads((MUSIC_DIR / "library.json").read_text())
    me = next((t for t in lib if t["file"] == "music/" + file), {})
    c = [t for t in lib if t.get("longform") and t["file"] != "music/" + file and t["file"].removeprefix("music/") not in used]
    c.sort(key=lambda t: (t.get("mood") != me.get("mood"), -t.get("duration", 0)))
    return c[0]["file"].removeprefix("music/") if c else None


def moments(Fm, edl, fmt, notes, cues=(), quiet=()):
    """The visual plan's music moments as the mix plays them (v11): {quiet, cues, drops}. A passage's moment is its
    first word on the cut. "stop": the music out over the passage's first sentence (1.2-4 s) unless a quiet window
    (S.quiet) already starts within 1 s of it; on Reels "riser": RISER peaking on the moment unless the page already
    plays a riser in the 4 s before it, and "drop": handed to plan(). On long-form, drops and risers are dropped (calm
    beds) and noted; "turn" is the page's business (HF.music.turns). What can't be played goes to `notes`."""
    out = {"quiet": [], "cues": [], "drops": []}
    p = Fm.dir / "visual_plan.json"
    if not p.exists():
        return out
    ps = json.loads(p.read_text()).get("passages", [])
    W = {w["i"]: w for w in edl["words"]}
    ws = sorted(edl["words"], key=lambda w: w["t"])
    for q in ps:
        k = q.get("music")
        if k not in ("stop", "riser", "drop"):
            continue
        ids = q.get("words") or []
        w0 = W.get(ids[0]) if ids else None
        d = {"id": q.get("id", "?"), "kind": k, "t": round(w0["t"], 3) if w0 else None}
        if w0 is None:
            notes.append(dict(d, why=f"its first word {ids[:1]} is not on the cut"))
            continue
        t = w0["t"]
        last = ids[1] if len(ids) > 1 else ids[0]
        if k == "stop":
            wl = W.get(last)
            if any(x["a"] <= (wl["e"] if wl else t + 4.0) and x["b"] >= t - 1.0 for x in quiet):
                continue                                                 # the page's S.quiet already plays it
            end = next((w["e"] for w in ws if t <= w["t"] and w["e"] <= (wl["e"] if wl else t + 4.0) + 1e-6
                        and re.search(r"[.?!]$", w.get("text", ""))), None)
            end = min(t + 4.0, max(t + 1.2, (end or t + 2.0) + 0.15))
            out["quiet"].append({"a": round(t - 0.1, 3), "b": round(end, 3), "depth": -40.0, "ramp": 0.35})
            print(f"plan: '{d['id']}' stop -> the music out {t - 0.1:.2f}-{end:.2f} s")
        elif fmt != "reel":
            notes.append(dict(d, why=f"a {k} on long-form (calm beds: no drops or risers): use 'turn' or 'stop'"))
        elif k == "riser":
            if any("riser" in c["name"] and t - 4.0 <= c["at"] <= t + 0.5 for c in cues):
                continue
            x = decode(ROOT / f"kit/sfx/{RISER}.wav")
            pk = sfx_offset(x, "peak")
            out["cues"].append({"name": RISER, "at": round(t - pk, 3), "gain_db": -18, "align": "start", "keep": True})
            print(f"plan: '{d['id']}' riser -> {RISER.split('__')[1]} from {t - pk:.2f} s, peaking on {t:.2f} s")
        else:
            out["drops"].append(d)
    return out


def v11_findings(Fm, M, bedlist, r, notes, fmt):
    """The v11 sound rules as music.json findings (qa.py --music: MEDIUM)."""
    out = []
    lib = {t["file"].removeprefix("music/"): t for t in json.loads((MUSIC_DIR / "library.json").read_text())}
    add = lambda t, i, detail, fix: out.append({"t": round(float(t), 2), "id": i, "detail": detail, "fix": fix})
    # a documentary is SCORED (kit/presets/documentary/README.md, "the score"; the owner, 2026-10-25: "The music plays a
    # really important role"): a cue per act with its drop on a moment and swells in the held beats, not one calm bed.
    # Only the level under his voice stays a rule there; a normal film keeps every rule below.
    from kit.film import doc as _doc
    scored = _doc.on(Fm)
    if fmt == "film":
        for bd in bedlist:
            f = bd._m["file"]
            if not scored and not lib.get(f, {}).get("longform"):
                add(bd.a, f"music-longform@{bd.a:.1f}", f"{f.split('/')[-1]} is not a long-form bed (no \"longform\" in kit/music/library.json)",
                    "use a calm long-form bed (kit/music/calm, or one marked longform)")
            if bd.under > -16.0:
                add(bd.a, f"music-loud@{bd.a:.1f}", f"{f.split('/')[-1]} sits {bd.under:g} dB under the voice (long-form: -18, never above -16)",
                    "drop under= (the default is -18)")
        if len(bedlist) > (_doc.SCORE_CUES if scored else 2):
            add(0, "music-beds", f"{len(bedlist)} beds on a long-form film" + (f" (a documentary's score: {_doc.SCORE_CUES} cues at most)" if scored else
                " (one or two calm beds)"), "merge cues" if scored else "use one bed, two at most")
    target = TARGET[fmt]
    if r.get("under_db") == r.get("under_db") and abs(r["under_db"] - target) > 2.0:
        add(0, "music-level", f"the music sits {r['under_db']:.1f} dB under the voice while he talks (target {target:g} +-2)",
            "set under= on the bed (or even= for a track whose own level dips)")
    if r.get("lifts_per_min", 0) > 3.0 and not scored:        # (a score lifts on purpose: DC.swell over the held beats)
        add(0, "music-lifts", f"the bed lifts {r['lifts_per_min']} times a minute (at most 3: it should sit still under the talk)",
            "check the duck (Bed.duck='voice') and the gap (under + 6)")
    for n in notes:
        t = n.get("t") or 0.0
        add(t, f"music-{n.get('kind', 'moment')}@{t:.1f}", f"{n.get('id', '')}: the plan's {n.get('kind')} was not played: {n['why']}",
            "fix the plan or the bed (kit/film/mix.py moments)")
    return out


def record_usage(Fm, bedlist):
    """output/music_usage.json ([{job, file}], kit/paths.py): this film's tracks; prints a track another film used."""
    job = film_name(Fm.dir)
    try:
        U = json.loads(USAGE.read_text()) if USAGE.exists() else []
    except json.JSONDecodeError:
        U = []
    files = list(dict.fromkeys("music/" + bd._m["file"] if not str(bd.file).startswith(str(MUSIC_DIR)) else
                               "music/" + str(bd.file.relative_to(MUSIC_DIR)) for bd in bedlist
                               if not Path(bd._m["file"]).is_absolute()))    # (a film's own clip as a bed is no library track)
    for f in files:
        other = sorted({u["job"] for u in U if u.get("file") == f and u.get("job") != job})
        if other:
            print(f"NOTE {f.split('/')[-1]} was used by {', '.join(other)} (output/music_usage.json): pick another bed if they air close together")
    have = {(u.get("job"), u.get("file")) for u in U}
    U += [{"job": job, "file": f} for f in files if (job, f) not in have]
    USAGE.parent.mkdir(parents=True, exist_ok=True)
    USAGE.write_text(json.dumps(U, indent=1) + "\n")


def prepare(Fm, edl):
    """Everything the mix decides before it mixes: {v11, fmt, planned, beds, moments, notes}."""
    v11, fmt = _is_v11(Fm), fmt_of(Fm)
    notes = []
    if v11:
        cues_p, quiet_p = Fm.work / "cues.json", Fm.work / "cues.quiet.json"
        mom = moments(Fm, edl, fmt, notes, json.load(open(cues_p)) if cues_p.exists() else [],
                      json.load(open(quiet_p)) if quiet_p.exists() else [])
    else:
        mom = {"quiet": [], "cues": [], "drops": []}
    planned = plan(Fm, edl, v11=v11, drops=mom["drops"], notes=notes)
    return {"v11": v11, "fmt": fmt, "planned": planned, "beds": beds(Fm, edl, planned, v11=v11, notes=notes), "moments": mom, "notes": notes}


def run(Fm, record=True):
    edl = Fm.edl()
    if not Fm.MUSIC:
        print("NOTE: no MUSIC beds (the owner's default: a calm bed ~18 dB under the voice on a film, ~12 on a Reel): voice and cues only")
    why = sound_why(Fm)[1]                                              # (read before music.json is rewritten below)
    P = prepare(Fm, edl)
    planned = P["planned"]
    v = "v11" if P["v11"] else "v10"
    print(f"sound: {v} ({P['fmt']}; {why})")
    for m, a, b, start, how, e in planned:
        print(f"music {m['file'].split('/')[-1]} {a:.2f}-{b:.2f} s: {how}")
    M = music_map(Fm, edl, planned, bedlist=P["beds"] if P["v11"] else None)
    M["sound"] = v                                                      # sticky: the next mix of this film keeps it (sound_why)
    cues_p = Fm.work / "cues.json"
    M["findings"] = findings(M, json.load(open(cues_p)) if cues_p.exists() else [])
    for f in M["findings"]:
        print(f"MUSIC {f['id']}: {f['detail']} -> {f['fix']}")
    (Fm.work / "music.json").write_text(json.dumps(M, indent=1))
    if not P["v11"]:
        r = kmix(Fm.work, edl, P["beds"], total=edl["total"])
    else:
        from kit.film import doc as _doc
        snd = V11 if P["fmt"] == "film" else V11_REEL
        if _doc.on(Fm):                                    # a documentary's score swells on purpose: a wider range, kept linear
            from dataclasses import replace
            snd = replace(snd, lra=_doc.SCORE_LRA)
        r = kmix(Fm.work, edl, P["beds"], total=edl["total"], sound=snd,
                 quiet_extra=P["moments"]["quiet"], cues_extra=P["moments"]["cues"])
        extra = v11_findings(Fm, M, P["beds"], r, P["notes"], P["fmt"])
        for f in extra:
            print(f"MUSIC {f['id']}: {f['detail']} -> {f['fix']}")
        M["findings"] += extra
    M["mix"] = {k: x for k, x in r.items() if k != "dropouts"}         # the measured sound (v10 too: to compare)
    (Fm.work / "music.json").write_text(json.dumps(M, indent=1))
    if record and Fm.MUSIC:
        record_usage(Fm, P["beds"])
    return r
