"""A podcast's recipe: films/<name>/podcast.py (plain Python settings), read into Pod. Defaults below.

    TAKE = "<job name from `shorts probe ... --job`>"   the one-camera recording (its analysis.json has the words)
    SOURCE = "/path/to/original.mp4"                     the original file at full resolution (crops come from it;
                                                         `shorts probe --landscape` keeps a 1080p copy for the words)
    PEOPLE = {"A": "Host name", "B": "Guest name"}       left-to-right in the frame (A = the leftmost face)
    CUT = [(first_word, last_word, "why"), ...]          word ranges to remove (repetition, phone reading, tangents)
    SPEAKER_FIX = {(first_word, last_word): "B"}         corrections to the automatic speaker of those words
    CHAPTERS = [(word_id, "Title"), ...]                 topic changes: a wide shot, a YouTube chapter
    GAP_MAX = 0.6                                        a pause longer than this is shortened to GAP_KEEP
    GAP_KEEP = 0.35
    MUSIC = None                                         or {"file": "chill/...", "intro": 6.0, "outro": 8.0, "under": -24}
    DENOISE_DB = 14                                      DeepFilterNet's attenuation limit: gentle noise reduction
    DEREVERB = False                                     WPE first (an echoing room)
    LUFS = -14.0                                         YouTube; -16 for an audio-only export
    OUT = "podcast.mp4"; RES = 1080                      output height (2160 needs a 4K source for clean crops)
    FPS = None                                           the take's own rate (60 stays 60); set 30 only on purpose
    LOOK = {"warmth": 0.02, "contrast": 1.06, "sat": 1.06}   the light grade (kit/podcast/look.py); "denoise", "sharpen",
                                                         "vignette": True only on purpose (they cost detail: 2026-10-12)
    SEQUENCE = [(first, last), ...]                      word ranges in output order (a part recorded later, moved)
    CROP = {"single": 0.20, "tight": 0.25}               face share of the crop height (default camera.SIZES)
    WIDE_ZOOM = 1.0                                      >1 tightens the wide on the pair
    SPLITS = [824.597]                                   source times where a joined take starts (crops per take)
    LOWER_THIRDS = True                                  False when a designed intro already names everyone
An HDR (HLG/PQ) source is tone-mapped to SDR in the render (render.tonemap), the same chain as shorts probe.
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from kit.paths import Film, job_dir, job_source  # noqa: E402

DEFAULTS = dict(TAKE=None, SOURCE=None, PEOPLE={"A": "Host", "B": "Guest"}, CUT=[], SPEAKER_FIX={}, CHAPTERS=[], GAP_MAX=0.6, GAP_KEEP=0.35,
                MUSIC=None, DENOISE_DB=14, DEREVERB=False, LUFS=-14.0, OUT="podcast.mp4", RES=1080,
                LOOK={"warmth": 0.02, "contrast": 1.06, "sat": 1.06}, MIN_HOLD=2.5, MAX_HOLD=15.0, FPS=None,
                SEQUENCE=None, CROP=None, WIDE_ZOOM=1.0, SPLITS=[], LOWER_THIRDS=True)


def source_fps(src):
    """The take's frame rate rounded to 30 or 60 (iPhone takes are ~60 variable); 30 when it can't be read."""
    import subprocess
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(src)],
                         capture_output=True, text=True).stdout.strip()
    try:
        a, b = out.split("/")[:2]
        return 60 if float(a) / float(b) >= 45 else 30
    except (ValueError, ZeroDivisionError):
        return 30


class Pod:
    def __init__(self, film):
        self.dir = Path(film).resolve()
        spec = importlib.util.spec_from_file_location("podcast_recipe", self.dir / "podcast.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for k, v in DEFAULTS.items():
            setattr(self, k, getattr(mod, k, v))
        if not self.TAKE:
            raise SystemExit("podcast.py: set TAKE (the job name from `uv run shorts probe <file> --job <name>`)")
        self.F = Film(self.dir / "podcast.py")
        self.work = self.F.work
        self.work.mkdir(parents=True, exist_ok=True)
        self.job = job_dir(self.TAKE)
        src = Path(self.SOURCE).expanduser() if self.SOURCE else None
        self.source = (src if src.is_absolute() else ROOT / src) if src else job_source(self.TAKE)
        if getattr(mod, "FPS", None) is None:              # keep the take's frame rate (a 60 fps iPhone take stays 60)
            self.FPS = source_fps(self.source)

    def words(self):
        return json.load(open(self.job / "analysis.json"))["words"]

    def probe(self):
        return json.load(open(self.job / "probe.json"))
