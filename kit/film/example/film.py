"""The kit/film example: a check film, not an edit. ffmpeg's test pattern and a synthetic voice (make_take.py), cut,
built, mixed and rendered by the shared pipeline, so the pipeline can be run end to end with no footage:

    uv run python kit/film/example/make_take.py                  # the "recording" (test pattern + say voice)
    uv run python -m kit.film kit/film/example prep              # probe + analyze (job film-example), clean voice, EQ
    uv run python -m kit.film kit/film/example cut               # cutcheck gate, edl.json, vo.wav (+ room tone), aroll.mp4
    uv run python -m kit.film kit/film/example joins             # the voice-cut audit + whisper on every join
    uv run python -m kit.film kit/film/example grade             # look v2 on the cut -> aroll_graded.mp4
    uv run python -m kit.film kit/film/example draft             # build, lint, cues, precheck, mix, 1080p draft, qa.py
    uv run python -m kit.film kit/film/example reels             # Reel a from the finished film
    uv run python -m kit.film kit/film/example/reels/a draft     # its page, mix, 1080x1920 draft, qa.py
    uv run python -m kit.film kit/film/example render            # the one 4K render (chunks), mux, qa.py

The take (job film-example, word ids from its analysis.json; `prep` prints the sentences):
  s1  0-14    Every film used to copy its own cut, its own page and its own mix.
  s2  15-25   Over 2,000 lines of edit code, copied from film to film.
  s3  26-32   So every film learned the same bugs.                (the first take: out)
  s4  33-40   So every film learned the same bugs again.          (the retake: kept)
  s5  41-46   Now a film is three files.                          (also the cold open, a copy: ids + 10000)
  s6  47-55   A cut list, a scene plan and a template.
  s7  56-59   Hmm, where was I?                                   (an aside: out)
  s8  60-64   The kit does the rest.                              ("The" re-timed: TIME_FIX)
  s9  65-79   It snaps every cut to the frame grid, [0.8 s] and it listens to every join again.   (a sliver)
  s11 80-95   It builds the page, mixes the music under the voice, and renders the film in chunks.
  s12 96-110  Then it cuts the reels from the finished film, one whole sentence at a time.
  s13 111-119 One command for each step, and nothing is copied.
"""
from kit.paths import film_temp

SOURCES = {
    # clean: DeepFilterNet3 + the measured EQ (prep); dereverb is asked for, and prep skips it because this take's two
    # channels are one signal (two-channel WPE on identical channels cancels the voice)
    1: dict(job="film-example", file=film_temp("kit/film/example") / "work/take.mp4", kind="cam",
            clean=dict(dereverb=True), tracks={"aroll": ""}),
}
ROOM_TONE = 0.0            # the take's own room (its pink-noise floor) back under the cleaned voice: no digital silence
GRADE = dict(look="natural")   # look v2 on the cut; the room as shot (vignette 0, no matte), each take/kind its own shot
FPS = 30
SPEED = 1.0
KEEP = [
    (41, 46, "hook", 0.5, "copy"),     # the cold open: "Now a film is three files." (said again in context at 0:15)
    (0, 14, "copy"),                   # Every film used to copy its own cut, its own page and its own mix.
    (15, 25, "lines"),                 # Over 2,000 lines of edit code, copied from film to film.
    (33, 40, "bugs", 0.4),             # So every film learned the same bugs again.   (the retake; the first take is out)
    (41, 46, "three"),                 # Now a film is three files.
    (47, 55, "files", 0.3),            # A cut list, a scene plan and a template.
    (60, 64, "rest"),                  # The kit does the rest.   (the aside before it is out)
    (65, 79, "grid"),                  # It snaps every cut to the frame grid, and it listens to every join again.
    (80, 95, "page"),                  # It builds the page, mixes the music under the voice, and renders the film in chunks.
    (96, 110, "reels"),                # Then it cuts the Reels from the finished film, one whole sentence at a time.
    (111, 119, "one"),                 # One command for each step, and nothing is copied.
]
JUDGED = {}
# measured on the voice's 10 ms envelope: the aligner stretched "The" over the 1.2 s pause after the aside (23.23-24.51);
# its sound starts at 24.39 (without the fix the piece opened on 1.2 s of air)
TIME_FIX = {60: (24.39, 24.51)}
SPELL = {"reels": "Reels"}
RESPELL = {(96, 110): "Then it cuts the Reels from the finished film, one whole sentence at a time."}
# the music map (kit/music/beats.json): the track's biggest rise (its drop at 52.87 s, +16 dB) lands on the reveal "Now a
# film is three files."; nobody measured it. Its next turn (+6 dB, 17.6 s later) would fall mid-sentence, so a second bed
# takes over at the Reels line and ends with the track's own ending (end_on)
#
# v11 (2026-10-23, P-M4: SOUND = "v11" below): one calm long-form bed instead (OWNER_DEFAULTS §4, kit/music/library.json
# longform), ~18 dB under the voice with the voice-keyed duck, no drop; the two beds above were v10's
MUSIC = [dict(file="chill/chill__mixkit__dim-the-lights.mp3", a=0.0, b="end", start=0.21, under=-18.0, duck="voice", end_fade=1.5)]
# (start 0.21: the track's first downbeat, kit/music/beats.json)
# the smoke test runs the v11 kit whatever day the example was made (2026-10-20): the lens on him, the v11 sound and
# precheck's ambition, speaker and density gates as HIGH (v11 fix P-M4)
LENS = dict(calm=0.6)      # calmer: a 36 s film with eight box layouts already moves often (precheck's pace, 7.5-15 a min)
SOUND = "v11"
AMBITION = True
OUT = "kit_film_example_4k.mp4"
DATA = {"title": "kit/film"}
REELS = {
    # a standalone story: what a film is now, and what the kit does with it
    "a": dict(sentences=[(41, 46), (47, 55), (60, 64), (65, 79)], out="reel_a_three_files.mp4",
              music=[dict(file="tech/tech__mixkit__brainiac.mp3", a=0.0, b="end", start=20.0, under=-12.5, gap=-6.0, even=2.0, end_fade=0.6)]),
}
