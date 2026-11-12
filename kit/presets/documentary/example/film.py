"""The documentary preset's smoke test (kit/presets/documentary, 2026-10-24): the kit/film example take (ffmpeg's test
pattern and a synthetic voice) cut as a documentary, with generated cutaways (make_broll.py). A check film, not an edit.

    uv run python kit/film/example/make_take.py
    uv run python kit/presets/documentary/example/make_broll.py
    uv run python -m kit.film kit/presets/documentary/example prep
    uv run python -m kit.film kit/presets/documentary/example cut          # + J/L cuts, cutaways, natural sound
    uv run python -m kit.film kit/presets/documentary/example build        # + D.doc, HF.doc
    uv run python -m kit.film kit/presets/documentary/example draft        # precheck --doc, mix, 1080p draft, qa.py

Word ids are the kit/film example's (kit/film/example/film.py lists the sentences).
"""
from kit.paths import film_temp

PRESET = "documentary"
BROLL = film_temp("kit/presets/documentary/example") / "scratch/broll"
SOURCES = {
    1: dict(job="film-example", file=film_temp("kit/film/example") / "work/take.mp4", kind="interview",
            speaker="Samantha", role="Test voice · kit/film example", clean=dict(dereverb=True), tracks={"aroll": ""}),
}
ROOM_TONE = 0.0
GRADE = dict(look="doc")
FPS = 30
KEEP = [
    (0, 14, "before"),                  # Every film used to copy its own cut, its own page and its own mix.
    (15, 25, "lines"),                  # Over 2,000 lines of edit code, copied from film to film.
    (33, 40, "bugs", 0.4, {"j": 0.6}),  # So every film learned the same bugs again.   (J: the voice leads by 0.6 s)
    (41, 46, "three"),                  # Now a film is three files.
    (47, 55, "files", 0.3),             # A cut list, a scene plan and a template.
    (60, 64, "rest", {"l": 0.4}),       # The kit does the rest.   (L: the picture comes in 0.4 s early)
    (65, 79, "grid"),                   # It snaps every cut to the frame grid, and it listens to every join again.
    (80, 95, "page"),                   # It builds the page, mixes the music under the voice, and renders the film in chunks.
    (96, 110, "reels"),                 # Then it cuts the Reels from the finished film, one whole sentence at a time.
    (111, 119, "one"),                  # One command for each step, and nothing is copied.
]
JUDGED = {}
TIME_FIX = {60: (24.39, 24.51)}
SPELL = {"reels": "Reels"}
DOC = dict(
    broll=[dict(file=BROLL / "insert.mp4", at="w15", dur=3.0, src_in=0.5, audio="natural", gain=-16, label="hands"),
           dict(file=BROLL / "screen.mp4", at="w80", until="w95", grade=False, label="screen"),
           dict(file=BROLL / "location.mp4", at="w111", dur=2.5, audio="natural", gain=-20)],
    chapters=[dict(at="tag:rest", title="The kit", sub="Day 1 · 23:10", dur=2.0)],
    stamps=[dict(at="w65", text="DAY 1 · 23:40", dur=3.0)],
    letterbox=[("tag:before", "tag:bugs")],
    results=dict(at="w96", until="w110", title="What the kit does",
                 rows=[["Every cut on the frame grid", "yes", True], ["Every join re-listened", "yes", True]]),
)
MUSIC = [dict(file="calm/calm__mixkit__piano-reflections.mp3", a=0.0, b="end", under=-18.0, duck="voice", end_fade=1.5)]
LENS = False               # HF.doc moves the camera (one slow push or pull per shot), not the canvas lens
SOUND = "v11"
AMBITION = True
OUT = "doc_example_4k.mp4"
