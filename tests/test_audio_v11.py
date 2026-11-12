"""The v11 sound (2026-10-22): the voice-keyed duck, SFX families and budgets, section-aware bed looping, phrase-aware
bed changes, and the film mix's v11 gate. Synthetic audio only (numpy -> wav), no music library audio."""
import json
import wave
from pathlib import Path

import numpy as np
import pytest

from kit.audio import loop as LP
from kit.audio import mix as M
from kit.film import mix as MX

SR = M.SR


def wav(path: Path, x: np.ndarray, sr=SR):
    """Write mono or stereo float audio as 16-bit PCM."""
    x = np.asarray(x, np.float64)
    x = x[:, None] if x.ndim == 1 else x
    with wave.open(str(path), "wb") as w:
        w.setnchannels(x.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return path


def speech(spans, total, sr=SR, level=0.25, room=0.002, seed=0):
    """A stand-in voice: noise bursts at `level` inside each (a, b) span, room tone elsewhere."""
    rng = np.random.default_rng(seed)
    x = rng.normal(0, room, int(total * sr))
    for a, b in spans:
        i, j = int(a * sr), int(b * sr)
        x[i:j] = rng.normal(0, level, j - i) * (0.6 + 0.4 * np.sin(np.arange(j - i) / sr * 2 * np.pi * 4) ** 2)
    return x


def words(spans, step=0.3):
    out, i = [], 0
    for a, b in spans:
        t = a
        while t < b - 0.05:
            out.append({"i": i, "t": round(t, 3), "e": round(min(b, t + step - 0.04), 3)})
            i, t = i + 1, t + step
    return out


# ---- the voice-keyed duck --------------------------------------------------------------------------------------
def test_duck_holds_through_short_gaps_and_lifts_only_in_a_real_pause():
    spans = [(0.2, 2.0), (4.0, 6.0), (6.5, 8.0)]                  # a 2 s pause, then a 0.5 s gap between two words
    vo = speech(spans, 9.0)
    env, sp = M.duck_env(vo, words(spans), 9.0, M.db(vo[np.abs(vo) > 1e-3]), "film")
    at = lambda t: env[int(round(t * 100))]
    assert at(0.1) > 0.99                                          # the hook's first word: the bed enters under him
    assert min(env[200:240]) > 0.99                                # hold 0.4 s after the last word
    assert at(3.4) < 0.01                                          # released (0.8 s) well inside the 2 s pause
    assert at(4.0) > 0.95                                          # ducked again as the next word starts (60 ms look-ahead)
    assert min(env[600:650]) > 0.99                                # a 0.5 s gap is not a pause on a film: no lift
    reel, _ = M.duck_env(vo, words(spans), 9.0, M.db(vo[np.abs(vo) > 1e-3]), "reel")
    assert min(reel[600:650]) < 0.7                                # ... on a Reel (0.4 s) it is
    st = M.gain_stats([(-12 + (-18 + 12) * env, -18.0)])
    assert st["lifts"] == 2                                        # the pause and the tail after the last word
    assert st["up_db_s"] < 10.0                                    # 6 dB over 0.8 s, corners rounded: no pumping
    assert st["down_db_s"] > 60.0                                  # the duck itself is fast (40 ms)


def test_duck_keys_on_the_words_where_the_voice_track_is_silent():
    spans = [(1.0, 3.0)]
    vo = np.zeros(int(5.0 * SR))                                   # a voice too quiet to key on: the word mask carries it
    env, sp = M.duck_env(vo + 1e-6, words(spans), 5.0, -60.0, "film")
    assert env[int(1.5 * 100)] > 0.99 and env[int(4.8 * 100)] < 0.01


def test_voice_threshold_sits_between_the_room_and_the_voice():
    lv = np.concatenate([np.full(200, -40.0), np.full(800, -18.0)])
    assert M.voice_threshold(lv, -18.0) == pytest.approx(-30.0)    # 12 dB under the voice (the room is lower)
    assert M.voice_threshold(np.full(1000, -24.0), -18.0) == pytest.approx(-18.0)   # never inside a loud room


def test_carve_dips_the_presence_band_only_under_speech():
    rng = np.random.default_rng(1)
    x = rng.normal(0, 0.1, (SR * 2, 2)).astype(np.float32)
    env = np.r_[np.ones(SR), np.zeros(SR)]
    y = M.carve(x, env, 3.0)
    band = lambda z: np.abs(np.fft.rfft(z[:, 0]))[(np.fft.rfftfreq(len(z), 1 / SR) > 2000) & (np.fft.rfftfreq(len(z), 1 / SR) < 4000)].mean()
    low = lambda z: np.abs(np.fft.rfft(z[:, 0]))[(np.fft.rfftfreq(len(z), 1 / SR) > 100) & (np.fft.rfftfreq(len(z), 1 / SR) < 400)].mean()
    on, off = slice(SR // 4, SR * 3 // 4), slice(SR * 5 // 4, SR * 7 // 4)
    assert 20 * np.log10(band(y[on]) / band(x[on])) == pytest.approx(-3.0, abs=0.6)
    assert abs(20 * np.log10(low(y[on]) / low(x[on]))) < 0.3       # the rest of the bed is untouched
    assert abs(20 * np.log10(band(y[off]) / band(x[off]))) < 0.1   # nothing when he is quiet


# ---- SFX: budgets, families, caps --------------------------------------------------------------------------------
POP, DRY, SLIDE = ("ui/ui__bubble-pop-up-alert-notification__mixkit-2357", "ui/ui__dry-pop-up-notification-alert__mixkit-2356",
                   "whoosh/whoosh__technology-transition-slide__mixkit-3120")
HIT = "impact/impact__short-bass-hit__mixkit-2299"


def test_thin_per_minute_budget_and_v10_rules_unchanged():
    small = [{"name": POP, "at": 1.0 + 3.1 * i, "gain_db": -24} for i in range(40)]      # 40 pops, 3.1 s apart
    story = [{"name": HIT, "at": 2.0 + 20 * i, "gain_db": -12} for i in range(6)]
    v10 = M.thin(small + story)
    assert len(v10) == len(M.thin(small + story, per_min=None))
    kept = M.thin(small + story, per_min=8)
    ts = [c["at"] for c in kept if M.is_small(c)]
    assert max(sum(1 for u in ts if t - 60 < u <= t) for t in ts) <= 8
    assert sum(1 for c in kept if c["name"] == HIT) == 6           # story sounds always play


def test_rotate_cycles_the_family_from_the_asked_file_with_fixed_jitter(tmp_path):
    lib = [{"file": f"sfx/{POP}.wav", "family": "pop"}, {"file": f"sfx/{DRY}.wav", "family": "pop"}, {"file": f"sfx/{SLIDE}.wav"}]
    (tmp_path / "library.json").write_text(json.dumps(lib))
    fam = M.families(tmp_path)
    assert fam[POP] == [POP, DRY] and fam[DRY] == [POP, DRY] and SLIDE not in fam
    cues = [{"name": POP, "at": float(i), "gain_db": -24} for i in range(5)] + [{"name": DRY, "at": 10.0, "gain_db": -24}]
    r = M.rotate(cues, fam, 1.5)
    assert [c["name"] for c in r[:5]] == [POP, DRY, POP, DRY, POP]
    assert r[5]["name"] == POP                                     # the family's 6th cue (k=5), asked as DRY: [DRY, POP][1]
    assert all(c["asked"] in (POP, DRY) and abs(c["jitter_db"]) <= 1.5 for c in r)
    assert [c["jitter_db"] for c in M.rotate(cues, fam, 1.5)] == [c["jitter_db"] for c in r]   # the same on every run
    assert M.rotate([{"name": SLIDE, "at": 1.0, "gain_db": -22}], fam)[0].get("jitter_db") is None


def test_cap_holds_any_file_to_a_quarter_and_four_a_minute_but_never_drops_story_sounds():
    pops = [{"name": POP, "at": 2.0 * i, "gain_db": -24} for i in range(30)]
    other = [{"name": SLIDE, "at": 1.0 + 7.0 * i, "gain_db": -22} for i in range(8)]
    hits = [{"name": HIT, "at": 0.5 + 6.0 * i, "gain_db": -12} for i in range(10)]
    out = M.cap(pops + other + hits, 0.25, 4)
    n = lambda f: sum(1 for c in out if c["name"] == f)
    assert n(HIT) == 10                                            # story: 10 of the played cues, more than 25 %, kept
    ts = [c["at"] for c in out if c["name"] == POP]
    assert max(sum(1 for u in ts if t - 60 < u <= t) for t in ts) <= 4
    assert n(POP) <= 0.25 * len(out) + 1e-9
    assert M.cap(pops[:3] + hits[:3], 0.25, None) == sorted(pops[:3] + hits[:3], key=lambda c: c["at"])   # under 8 cues: no share rule


# ---- decode and render -----------------------------------------------------------------------------------------
def test_decode_pads_a_negative_start_instead_of_clamping_it(tmp_path):
    x = np.zeros(SR)
    x[0] = 0.5                                                     # a click at the file's head
    f = wav(tmp_path / "click.wav", x)
    y = M.decode(f, -0.25, 0.5, ch=1, pad=True)[:, 0]
    assert len(y) == SR // 2 and np.argmax(np.abs(y)) == SR // 4   # the click lands 0.25 s in, not at 0
    assert np.argmax(np.abs(M.decode(f, -0.25, 0.5, ch=1)[:, 0])) == 0   # v10 (pad=False): clamped, as before


def test_render_crosses_each_seam_at_constant_power(tmp_path):
    rng = np.random.default_rng(2)
    f = wav(tmp_path / "noise.wav", rng.normal(0, 0.1, (SR * 20, 2)))
    x = M.render(f, 1.0, 0.5, 13.0, [(2.0, 8.0), (3.0, 12.0)])
    assert len(x) == int(round(12.5 * SR))
    w = int(0.02 * SR)
    lv = [M.db(x[i:i + w]) for i in range(int(6.8 * SR) - int(0.5 * SR), int(7.2 * SR) - int(0.5 * SR), w)]   # the seam at film 7.0
    body = M.db(x[SR:3 * SR])
    assert max(abs(v - body) for v in lv) < 1.5                    # equal power: no dip, no bump through the 80 ms seam


def test_phrase_aware_change_waits_for_the_outgoing_downbeat(tmp_path, monkeypatch):
    e = {"duration": 100.0, "bpm": 120.0, "steady": True, "downbeats": [0.3 + 2 * i for i in range(50)], "sections": [], "beats": []}
    monkeypatch.setattr(M, "_track_entry", lambda f: e if "a.wav" in str(f) else None)
    A, B, C = tmp_path / "a.wav", tmp_path / "b.wav", tmp_path / "c.wav"
    beds = [M.Bed(A, 0.0, 20.0, 0.0, duck="voice"), M.Bed(B, 20.0, 40.0, 8.0, duck="voice"), M.Bed(C, 40.0, 60.0, 0.0, duck="voice")]
    lay = M._layout(beds, 60.0, 0.2, M.V11)
    (ra0, rb0, _, _, fo0, _), (ra1, rb1, _, fi1, fo1, _), (ra2, _, _, fi2, _, _) = lay
    # A's next downbeat after the change at 20 s is film 20.3 (track 20.3): it crosses B over [18.8, 20.3], equal power
    assert rb0 == pytest.approx(20.3) and ra1 == pytest.approx(18.8)
    t = np.array([19.55])
    assert float(fo0(t)[0] ** 2 + fi1(t)[0] ** 2) == pytest.approx(1.0)
    # B has no map: a crossfade centred on 40 s; C starts at its head (no lead-in), so the window starts at 40
    assert ra2 == pytest.approx(40.0) and rb1 == pytest.approx(40.75) and float(fi2(np.array([40.0]))[0]) == 0.0
    layer = M._layout([M.Bed(A, 0.0, 60.0, 0.0, duck="voice"), M.Bed(B, 0.0, 30.0, 5.0, duck="voice")], 60.0, 0.2, M.V11)
    assert layer[0][1] == pytest.approx(60.0) and layer[1][0] == 0.0   # a layer under the music is not a change: both play


# ---- section-aware looping -------------------------------------------------------------------------------------
def track(tmp_path, bpm=120.0, bars=40, chords=((0, 4, 7), (5, 9, 0), (7, 11, 2), (0, 4, 7))):
    """A synthetic steady track: 4/4, one chord per 8-bar section, cycling; a 2-bar fade at the end. -> (path, map)."""
    bar = 240 / bpm
    n = int(bars * bar * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k in range(bars // 8):
        a, b = int(k * 8 * bar * SR), int((k + 1) * 8 * bar * SR)
        for pc in chords[k % len(chords)]:
            x[a:b] += 0.08 * np.sin(2 * np.pi * 220 * 2 ** (pc / 12) * t[a:b])
    beat = 60 / bpm
    x *= 0.8 + 0.2 * (np.cos(2 * np.pi * t / beat) > 0.9)          # a soft pulse on each beat
    x[-int(2 * bar * SR):] *= np.linspace(1, 0, int(2 * bar * SR))
    f = wav(tmp_path / "steady.wav", x)
    beats = [round(i * beat, 3) for i in range(int(bars * 4))]
    e = {"size": f.stat().st_size, "duration": round(n / SR, 2), "bpm": bpm, "agree": 1.0, "steady": True, "beats": beats,
         "downbeats": beats[::4], "sections": [{"t": round(k * 8 * bar, 2), "rise": 0.0} for k in range(1, bars // 8)], "drops": []}
    return f, e


def test_loop_plan_fills_the_bed_and_ends_on_the_tracks_own_ending(tmp_path):
    f, e = track(tmp_path)                                         # 80 s of music, bars of 2 s
    LP.pcm.cache_clear()
    need = 190.0
    p = LP.plan(f, e, 0.0, need, end=True)
    assert p is not None
    segs = p["segments"]
    total = sum(b - a for a, b in segs)
    bar = 2.0
    assert need - bar / 2 - 1e-6 <= total <= need + bar + 1e-6
    assert segs[-1][1] == pytest.approx(LP.audible_end(LP.pcm(str(f))), abs=0.06)   # ends on the track's ending
    downs = set(e["downbeats"])
    for (a0, j), (k, _) in zip(segs, segs[1:]):
        assert j in downs and k in downs and round((j - k) / bar) % 4 == 0 and j - k >= LP.MIN_SPAN
    assert LP.seam_times(10.0, segs)[0] == pytest.approx(10.0 + segs[0][1] - segs[0][0])
    assert LP.plan(f, e, 0.0, 60.0) is None                        # it fits: no loop
    mid = LP.plan(f, e, 0.0, 150.0, end=False)
    assert sum(b - a for a, b in mid["segments"]) >= 150.0


def test_loop_finds_no_seam_in_a_track_that_never_repeats(tmp_path):
    f, e = track(tmp_path, bars=32, chords=((0, 4, 7), (1, 5, 8), (3, 6, 10), (6, 9, 1)))   # four unrelated chords
    LP.pcm.cache_clear()
    assert LP.seams(f, e) == []                                    # no two phrase starts sound alike 16 s or more apart
    assert LP.plan(f, e, 0.0, 120.0) is None                       # so kit/film/mix.py falls back to a second bed


# ---- the film mix's v11 gate -----------------------------------------------------------------------------------
class FakeFm:
    def __init__(self, d, sound=None, reel=None, W=1920, H=1080, music=(), work=None, edl=None):
        self.dir, self.reel, self.W, self.H, self.MUSIC = d, reel, W, H, list(music)
        if work is not None:
            self.work = work
        self._edl = edl
        if sound:
            self.SOUND = sound

    def edl(self):
        return self._edl


def test_sound_of_follows_film_py_then_the_day_it_was_made(tmp_path):
    assert MX.sound_of(FakeFm(tmp_path, "v10")) == "v10"
    (tmp_path / "film.py").write_text("SOURCES = {}\n")              # an untracked film made today
    assert MX.sound_of(FakeFm(tmp_path)) == "v11"
    assert MX.fmt_of(FakeFm(tmp_path, reel="a")) == "reel" and MX.fmt_of(FakeFm(tmp_path, W=1080, H=1920)) == "reel"
    root = Path(__file__).resolve().parents[1]
    if (root / "films/oss-editor/film.py").exists():
        assert MX.sound_of(FakeFm(root / "films/oss-editor")) == "v10"   # made 2026-10-21: its mix reproduces


def test_the_sound_gate_is_sticky_once_a_film_was_mixed(tmp_path):
    import os
    film, work = tmp_path / "film", tmp_path / "work"
    film.mkdir(), work.mkdir()
    (film / "film.py").write_text("SOURCES = {}\n")                # today's file: an edit (sed -i, a safe-write) or a copy
    assert MX.sound_why(FakeFm(film, work=work))[0] == "v11"       # never mixed, nothing older: today -> v11
    (work / "music.json").write_text(json.dumps({"beds": []}))     # a mix made before v11 (no "sound"): it stays v10
    v, why = MX.sound_why(FakeFm(film, work=work))
    assert v == "v10" and "before v11" in why
    (work / "music.json").write_text(json.dumps({"beds": [], "sound": "v10"}))
    assert MX.sound_of(FakeFm(film, work=work)) == "v10"           # recorded by its last mix
    (work / "music.json").write_text(json.dumps({"beds": [], "sound": "v11"}))
    assert MX.sound_of(FakeFm(film, work=work)) == "v11"
    assert MX.sound_of(FakeFm(film, "v10", work=work)) == "v10"   # SOUND in film.py still wins
    (work / "music.json").unlink()                                 # never mixed, but cut on 2026-10-20: the oldest time wins
    (work / "edl.json").write_text("{}")
    old = 1792454400                                               # 2026-10-20 00:00 UTC
    os.utime(work / "edl.json", (old, old))
    assert MX.made_on(FakeFm(film, work=work)) < MX.V11_FROM and MX.sound_of(FakeFm(film, work=work)) == "v10"


def test_v11_beds_duck_on_the_voice_with_gap_under_plus_6(tmp_path, monkeypatch):
    monkeypatch.setattr(MX.BT, "entry", lambda f, tracks=None: None)
    edl = {"total": 60.0, "pieces": [], "words": []}
    planned = [({"file": "calm/x.mp3", "a": 0.0}, 0.0, 60.0, 0.0, "start 0", None)]
    b = MX.beds(FakeFm(tmp_path), edl, planned, v11=True)[0]
    assert (b.under, b.gap, b.duck, b.carve) == (-18.0, -12.0, "voice", 0.0)
    r = MX.beds(FakeFm(tmp_path, reel="a"), edl, [({"file": "calm/x.mp3", "under": -13.0, "carve": 3}, 0.0, 60.0, 0.0, "", None)], v11=True)[0]
    assert (r.under, r.gap, r.carve) == (-13.0, -7.0, 3)
    old = MX.beds(FakeFm(tmp_path), edl, planned, v11=False)[0]
    assert (old.under, old.gap, old.duck) == (-18.0, -5.0, "mask") and M._v10(old, M.Sound())


def test_a_track_that_cannot_loop_hands_over_to_a_second_long_form_bed(tmp_path, monkeypatch):
    e = {"duration": 60.0, "bpm": 120.0, "steady": True, "downbeats": [0.5 + 2 * i for i in range(29)], "sections": [], "beats": []}
    monkeypatch.setattr(MX.BT, "entry", lambda f, tracks=None: e)
    monkeypatch.setattr(MX.BT, "load", lambda: {})
    monkeypatch.setattr(MX.LP, "pcm", lambda p: np.zeros(10))
    monkeypatch.setattr(MX.LP, "audible_end", lambda x: 59.0)
    monkeypatch.setattr(MX.LP, "plan", lambda *a, **k: None)              # no seam passes
    monkeypatch.setattr(MX, "second_bed", lambda f, used: "calm/y.mp3")
    edl = {"total": 120.0, "pieces": [], "words": []}
    bs = MX.beds(FakeFm(tmp_path), edl, [({"file": "calm/x.mp3", "start": 0.5}, 0.0, 120.0, 0.5, "start 0.5", e)], v11=True)
    assert [b.file.name for b in bs] == ["x.mp3", "y.mp3"]
    assert bs[0].b == bs[1].a == pytest.approx(50.0)                # the last downbeat 4 bars before its end (50.5 - 0.5)
    assert bs[1].xfade == MX.FALLBACK_XFADE and bs[1].duck == "voice" and bs[1].b == 120.0


def test_second_bed_picks_an_unused_long_form_track_of_the_same_mood():
    f = MX.second_bed("calm/calm__mixkit__piano-reflections.mp3", {"calm/calm__mixkit__piano-reflections.mp3"})
    lib = {t["file"]: t for t in json.loads((MX.MUSIC_DIR / "library.json").read_text())}
    assert f and lib["music/" + f].get("longform") and lib["music/" + f]["mood"] == "calm"


def test_end_on_with_a_short_track_loops_onto_its_ending(monkeypatch):
    e = {"duration": 60.0, "bpm": 120.0, "steady": True, "downbeats": [0.5 + 2 * i for i in range(29)], "sections": [], "beats": []}
    monkeypatch.setattr(MX.BT, "entry", lambda f, tracks=None: e)
    monkeypatch.setattr(MX.LP, "pcm", lambda p: np.zeros(10))
    monkeypatch.setattr(MX.LP, "audible_end", lambda x: 60.0)
    monkeypatch.setattr(MX.LP, "plan", lambda f, e, s, need, end=True: {"start": 4.5, "how": "loops 1x (40->16)", "segments": [(4.5, 40), (16, 60)]})
    s, how = MX.resolve({"file": "x", "end_on": "track_end"}, 10.0, 100.0, {"total": 100.0}, {}, loop=True)
    assert s == 4.5 and "through a loop" in how
    s0, _ = MX.resolve({"file": "x", "end_on": "track_end"}, 10.0, 100.0, {"total": 100.0}, {})
    assert s0 == 0.0                                                # v10 as it was (it starts at 0 and runs out)


def test_v11_end_on_lands_the_audible_ending_not_the_padded_file_end(monkeypatch):
    # a 60 s file whose music stops at 52 s (8 s of zero padding): v10 lands the FILE's end on b (8 s of silence under
    # the film's end); v11 lands the last audible moment, from the last downbeat that still fits
    e = {"duration": 60.0, "bpm": 120.0, "steady": True, "downbeats": [0.5 + 2 * i for i in range(29)], "sections": [], "beats": []}
    monkeypatch.setattr(MX.BT, "entry", lambda f, tracks=None: e)
    monkeypatch.setattr(MX.LP, "pcm", lambda p: np.zeros(10))
    monkeypatch.setattr(MX.LP, "audible_end", lambda x: 52.0)
    s10, _ = MX.resolve({"file": "x", "end_on": "track_end"}, 0.0, 30.0, {"total": 30.0}, {})
    s11, _ = MX.resolve({"file": "x", "end_on": "track_end"}, 0.0, 30.0, {"total": 30.0}, {}, loop=True)
    assert s10 == pytest.approx(28.5) and s11 == pytest.approx(20.5)   # downbeats <= 60 - 30 and <= 52 - 30


def test_plan_moments_stop_riser_drop(tmp_path):
    plan = {"passages": [{"id": "p1", "words": [1, 4], "music": "stop"}, {"id": "p2", "words": [5, 6], "music": "riser"},
                         {"id": "p3", "words": [7, 8], "music": "drop"}, {"id": "p4", "words": [99, 100], "music": "stop"}]}
    (tmp_path / "visual_plan.json").write_text(json.dumps(plan))
    W = [{"i": 1, "text": "That", "t": 10.0, "e": 10.2}, {"i": 2, "text": "was", "t": 10.25, "e": 10.4},
         {"i": 3, "text": "free.", "t": 10.45, "e": 10.9}, {"i": 4, "text": "Now", "t": 11.2, "e": 11.4},
         {"i": 5, "text": "and", "t": 20.0, "e": 20.2}, {"i": 6, "text": "then", "t": 20.3, "e": 20.6},
         {"i": 7, "text": "boom", "t": 30.0, "e": 30.4}, {"i": 8, "text": "here.", "t": 30.5, "e": 30.9}]
    edl = {"total": 40.0, "words": W, "pieces": []}
    notes = []
    mo = MX.moments(FakeFm(tmp_path, reel="a"), edl, "reel", notes)
    assert mo["quiet"] == [{"a": 9.9, "b": 11.2, "depth": -40.0, "ramp": 0.35}]   # to the first sentence's end, at least 1.2 s
    assert mo["cues"][0]["name"] == MX.RISER and mo["cues"][0]["at"] < 20.0 and mo["cues"][0]["align"] == "start"
    assert [d["t"] for d in mo["drops"]] == [30.0]
    assert [n["id"] for n in notes] == ["p4"]                      # its words are not on the cut
    notes = []
    lf = MX.moments(FakeFm(tmp_path), edl, "film", notes, quiet=[{"a": 10.4, "b": 11.0}])
    assert lf["quiet"] == [] and lf["cues"] == [] and lf["drops"] == []   # the page's S.quiet covers the stop; long-form is calm
    assert sorted(n["kind"] for n in notes) == ["drop", "riser", "stop"]


def test_clip_pieces_take_the_music_down_by_themselves():
    edl = {"pieces": [{"kind": "cam", "out_a": 0.0, "out_b": 5.0}, {"kind": "clip", "out_a": 5.0, "out_b": 7.0},
                      {"kind": "clip", "out_a": 7.2, "out_b": 9.0}, {"kind": "clip", "out_a": 20.0, "out_b": 22.0}]}
    assert M.clip_windows(edl, -19.0) == [{"a": 5.0, "b": 9.0, "depth": -19.0, "ramp": 0.35},
                                          {"a": 20.0, "b": 22.0, "depth": -19.0, "ramp": 0.35}]


def test_v11_mix_end_to_end_on_synthetic_audio(tmp_path):
    spans = [(0.3, 3.0), (3.2, 6.0), (7.5, 11.0)]                  # one real pause (6.0-7.5)
    total = 12.0
    wav(tmp_path / "vo.wav", speech(spans, total))
    rng = np.random.default_rng(3)
    bed = wav(tmp_path / "bed.wav", rng.normal(0, 0.05, (int(30 * SR), 2)))
    (tmp_path / "cues.json").write_text("[]")
    edl = {"words": words(spans), "talk_end": 11.0, "total": total, "pieces": []}
    r = M.mix(tmp_path, edl, [M.Bed(bed, 0.0, total, 2.0, -12.0, -18.0, duck="voice")], total, sound=M.V11)
    assert (tmp_path / "mix.wav").exists()
    assert r["under_db"] == pytest.approx(-18.0, abs=2.0)
    assert r["lifts"] >= 1 and r["up_db_s"] < 10.0
    r0 = M.mix(tmp_path, edl, [M.Bed(bed, 0.0, total, 2.0, -5.0, -18.0)], total, out_name="m10.wav")
    assert r0["lifts"] >= 2 and r0["up_db_s"] > r["up_db_s"]       # the v10 mask pumps 13 dB in every word gap


# ---- Reels on v11 (review 2026-10-22: every V11_REEL mix raised UnboundLocalError in _layout) ----------------------
def test_reel_layout_one_and_two_beds(tmp_path):
    A, B = tmp_path / "a.wav", tmp_path / "b.wav"
    one = M._layout([M.Bed(A, 0.0, 30.0, 0.0, duck="voice")], 30.0, 0.2, M.V11_REEL)
    assert [(ra, rb) for ra, rb, *_ in one] == [(0.0, 30.0)] and one[0][2] == [(0.0, 30.0)]
    two = M._layout([M.Bed(A, 0.0, 20.0, 0.0, duck="voice"), M.Bed(B, 20.0, 30.0, 4.0, duck="voice")], 30.0, 0.2, M.V11_REEL)
    (ra0, rb0, s0, fi0, fo0, _), (ra1, rb1, s1, fi1, fo1, _) = two
    # Reels keep v10's quick crossfade: 0.1 s each side of the change, linear
    assert (ra0, rb0, ra1, rb1) == pytest.approx((0.0, 20.1, 19.9, 30.0))
    assert s1 == [(4.0, 4.0 + 10.0)] and float(fo0(np.array([20.1]))[0]) == 0.0 and float(fi1(np.array([19.9]))[0]) == 0.0


def test_v11_reel_mix_end_to_end_on_synthetic_audio(tmp_path):
    spans = [(0.2, 2.5), (2.7, 5.0), (5.6, 8.0)]                   # a 0.6 s pause: a Reel lifts in it (0.4 s), a film doesn't
    total = 9.0
    wav(tmp_path / "vo.wav", speech(spans, total))
    rng = np.random.default_rng(4)
    a = wav(tmp_path / "a.wav", rng.normal(0, 0.05, (int(20 * SR), 2)))
    b = wav(tmp_path / "b.wav", rng.normal(0, 0.05, (int(20 * SR), 2)))
    (tmp_path / "cues.json").write_text("[]")
    edl = {"words": words(spans), "talk_end": 8.0, "total": total, "pieces": []}
    beds = [M.Bed(a, 0.0, 4.0, 1.0, -6.0, -12.0, duck="voice"), M.Bed(b, 4.0, total, 2.0, -6.0, -12.0, duck="voice")]
    r = M.mix(tmp_path, edl, beds, total, sound=M.V11_REEL)
    assert (tmp_path / "mix.wav").exists()
    assert r["under_db"] == pytest.approx(-12.0, abs=2.0) and r["lifts"] >= 1


def test_kit_film_run_mixes_a_v11_reel_and_records_its_sound(tmp_path, monkeypatch):
    music, film, work = tmp_path / "music", tmp_path / "reel", tmp_path / "work"
    for d in (music, film, work, music / "calm"):
        d.mkdir(exist_ok=True)
    rng = np.random.default_rng(5)
    wav(music / "calm/bed.wav", rng.normal(0, 0.05, (int(20 * SR), 2)))
    (music / "library.json").write_text(json.dumps([{"file": "music/calm/bed.wav", "mood": "calm", "longform": True}]))
    (film / "template.html").write_text("<html></html>")             # a Reel made today: v11
    spans = [(0.2, 3.0), (3.6, 7.5)]
    wav(work / "vo.wav", speech(spans, 8.0))
    (work / "cues.json").write_text("[]")
    edl = {"words": words(spans), "talk_end": 7.5, "total": 8.0, "pieces": []}
    monkeypatch.setattr(MX, "MUSIC_DIR", music)
    monkeypatch.setattr(MX.BT, "entry", lambda f, tracks=None: None)     # no music map: start as typed
    monkeypatch.setattr(MX.BT, "load", lambda: {})
    Fm = FakeFm(film, reel="a", W=1080, H=1920, work=work, edl=edl, music=[{"file": "calm/bed.wav", "a": 0.0, "b": "end", "start": 1.0}])
    r = MX.run(Fm, record=False)
    assert (work / "mix.wav").exists() and r["under_db"] == pytest.approx(-12.0, abs=2.0)
    M1 = json.loads((work / "music.json").read_text())
    assert M1["sound"] == "v11" and "mix" in M1 and M1["mix"]["lifts_per_min"] >= 0
    assert MX.sound_why(Fm)[1].startswith("recorded")              # the next mix of this Reel reads it back


def test_v10_run_records_its_sound_too(tmp_path, monkeypatch):
    music, film, work = tmp_path / "music", tmp_path / "film", tmp_path / "work"
    for d in (music, film, work):
        d.mkdir()
    wav(music / "bed.wav", np.random.default_rng(6).normal(0, 0.05, (int(12 * SR), 2)))
    (film / "film.py").write_text("SOURCES = {}\n")
    spans = [(0.2, 4.0)]
    wav(work / "vo.wav", speech(spans, 5.0))
    edl = {"words": words(spans), "talk_end": 4.0, "total": 5.0, "pieces": []}
    monkeypatch.setattr(MX, "MUSIC_DIR", music)
    monkeypatch.setattr(MX.BT, "entry", lambda f, tracks=None: None)
    monkeypatch.setattr(MX.BT, "load", lambda: {})
    MX.run(FakeFm(film, "v10", work=work, edl=edl, music=[{"file": "bed.wav", "start": 0.0}]), record=False)
    assert json.loads((work / "music.json").read_text())["sound"] == "v10"
    assert MX.sound_of(FakeFm(film, work=work)) == "v10"           # film.py is today's, the recorded mix wins


# ---- kit/film plans every loop (review: a fallback's loop and a moved start) ----------------------------------------
def test_looped_keeps_a_typed_start_and_moves_it_only_when_allowed(monkeypatch):
    e = {"duration": 60.0, "bpm": 120.0, "steady": True, "downbeats": [0.5 + 2 * i for i in range(29)], "sections": [], "beats": []}
    calls = []
    monkeypatch.setattr(MX.LP, "pcm", lambda p: np.zeros(10))
    monkeypatch.setattr(MX.LP, "audible_end", lambda x: 59.0)

    def plan(f, e, s, need, end=True, shift=True):
        calls.append(shift)
        return {"start": s + (6.0 if shift else 0.0), "segments": [(s, 40.0), (16.0, 59.0)], "how": "x"} if shift else None
    monkeypatch.setattr(MX.LP, "plan", plan)
    assert MX.looped({"file": "x", "start": 0.5}, e, 0.5, 100.0, True)["start"] == 6.5 and calls == [False, True]
    calls.clear()
    assert MX.looped({"file": "x", "start": 0.5, "snap": False}, e, 0.5, 100.0, True) is None and calls == [False]
    calls.clear()
    assert MX.looped({"file": "x", "drop": "auto", "at": 30.0}, e, 3.0, 100.0, True) is None and calls == [False]
    calls.clear()
    assert MX.looped({"file": "x", "start": 0.5}, e, 0.5, 100.0, False) is None and calls == [False]   # a middle bed: no shift
    assert MX.looped({"file": "x", "start": 0.5}, e, 0.5, 58.7, True) == "fits"   # within the film's 0.5 s end fade


def test_direct_api_layout_tries_the_typed_start_first(tmp_path, monkeypatch):
    e = {"duration": 60.0, "bpm": 120.0, "steady": True, "downbeats": [0.5 + 2 * i for i in range(29)], "sections": [], "beats": []}
    monkeypatch.setattr(M, "_track_entry", lambda f: e)
    calls = []

    def plan(f, e, s, need, end=True, shift=True):
        calls.append(shift)
        return {"segments": [(s, 40.0), (16.0, 59.0)], "how": "x"} if (shift or s == 0.5) else None
    monkeypatch.setattr(LP, "plan", plan)
    M._layout([M.Bed(tmp_path / "a.wav", 0.0, 80.0, 0.5, duck="voice", loop=True)], 80.0, 0.2, M.V11)
    assert calls == [False]                                        # a plan fits from the typed start: kept
    calls.clear()
    M._layout([M.Bed(tmp_path / "a.wav", 0.0, 80.0, 2.5, duck="voice", loop=True)], 80.0, 0.2, M.V11)
    assert calls == [False, True]                                  # only then may the last bed's start move


def test_a_fallback_bed_that_runs_out_gets_its_own_planned_loop(tmp_path, monkeypatch):
    e = {"duration": 60.0, "bpm": 120.0, "steady": True, "downbeats": [0.5 + 2 * i for i in range(29)], "sections": [], "beats": []}
    monkeypatch.setattr(MX.BT, "entry", lambda f, tracks=None: e)
    monkeypatch.setattr(MX.BT, "load", lambda: {})
    monkeypatch.setattr(MX.LP, "pcm", lambda p: p)
    monkeypatch.setattr(MX.LP, "audible_end", lambda x: 59.0)

    def plan(f, e, s, need, end=True, shift=True):                 # x can't loop; y loops 40 -> 16
        return None if "x.mp3" in str(f) else {"start": s, "segments": [(s, 40.0), (16.0, 59.0)], "how": "loops 1x (40->16)"}
    monkeypatch.setattr(MX.LP, "plan", plan)
    monkeypatch.setattr(MX, "second_bed", lambda f, used: "calm/y.mp3")
    edl = {"total": 120.0, "pieces": [], "words": []}
    bs = MX.beds(FakeFm(tmp_path), edl, [({"file": "calm/x.mp3", "start": 0.5}, 0.0, 120.0, 0.5, "start 0.5", e)], v11=True)
    assert [b.file.name for b in bs] == ["x.mp3", "y.mp3"]
    y = bs[1]
    assert y.segments is not None and y.loop and y.start == y.segments[0][0] and y.xfade == MX.FALLBACK_XFADE
    assert not bs[0].loop and bs[0].segments is None              # the mix never re-plans a bed kit/film didn't loop
    Mm = MX.music_map(FakeFm(tmp_path), edl, bedlist=bs)           # the page's map follows y's seam
    assert Mm["beds"][1]["seams"] == LP.seam_times(y.a, y.segments)


def test_dropouts_inside_a_quiet_window_are_reported_as_meant(tmp_path, capsys):
    total = 6.0
    vo = speech([(0.2, 2.0), (3.5, 5.5)], total, room=0.0)       # a cleaned voice: digital silence between the lines
    wav(tmp_path / "vo.wav", vo)
    bed = wav(tmp_path / "bed.wav", np.random.default_rng(7).normal(0, 0.05, (int(10 * SR), 2)))
    (tmp_path / "cues.json").write_text("[]")
    edl = {"words": words([(0.2, 2.0), (3.5, 5.5)]), "talk_end": 5.5, "total": total, "pieces": []}
    stop = [{"a": 2.3, "b": 3.4, "depth": -60.0, "ramp": 0.2}]       # a planned stop over the pause
    M.mix(tmp_path, edl, [M.Bed(bed, 0.0, total, 0.0, -12.0, -18.0, duck="voice")], total, sound=M.V11, quiet_extra=stop)
    out = capsys.readouterr().out
    line = next(x for x in out.splitlines() if x.startswith("dropouts"))
    assert "in quiet windows (meant" in line and "RUNS" not in line
