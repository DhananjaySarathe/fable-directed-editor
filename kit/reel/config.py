"""Load a film's reel.py into one settings object with defaults, plus the folders it uses (kit.paths.Film)."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from kit.paths import FILMS, Film, job_dir  # noqa: E402

DEFAULTS = dict(
    TAKE=None,             # the `shorts probe` job name of the take
    ROOM=None,             # kit/look/looks.py room profile ("shelf"...). None: prep grades with 'asshot', his room's colour
                           # as shot (v11, OWNER_DEFAULTS §2); "woodoffice" was the old set-back look's default
    ROOM_SET_BACK=False,   # True: the pre-v11 set-back grade for a Reel he asked it of (the person matte, the room's
                           # vignette, ROOM or else "woodoffice"); a change re-grades (kit/reel/prep.py grade_args)
    LOOK="natural",        # look v2 preset
    FLIP=False,            # a mirrored selfie take is flipped back
    DEREVERB=True,         # WPE on both mics before DeepFilterNet (office rooms ring)
    FPS=30, SR=48000, SPEED=1.0,
    W=1080, H=1920,
    KEEP=[],               # [(first word id, last word id, tag)], whole sentences only
    JUDGED={},             # {(left id, right id): why} for cutcheck REVIEW joins the editor accepted
    START_FIX={}, END_FIX={},   # {word id: seconds} measured on the voice envelope (joins audit)
    LEAD=0.04, SIB_LEAD=0.10,   # in-point pad before a word (more before a hiss)
    SLIVER=0.14, MAX_GAP=0.30,  # a pause longer than MAX_GAP inside a kept range becomes a SLIVER
    SLIVER_AT={},          # {word id: sliver s} to keep a longer pause before that word (a timed beat)
    NOTRIM=set(),          # word ids whose pause before them is never trimmed (a trim there would be a visible jump on a full face)
    TRIM=set(),            # word ids whose gap before them is cut even with sound in it (a hum, a drawl, a mumbled fragment):
                           # set the exact edges with END_FIX on the word before and START_FIX on this one (measured)
    GAP=0.10,              # extra silence between two kept ranges
    GAP_AFTER={},          # {last word id of a kept range: gap s} a longer breath where two sentences must read apart
    VOICE_GAIN={},         # {KEEP tag: dB} on that range's voice in vo.wav (a quieter second voice): measure it on vo.wav, after the clean chain
    ROOM_TONE=None,        # dB vs natural: the take's own room tone looped under vo.wav, so a pause is a beat, not a hole
    TAIL=0.30,             # after the last word (no end screen: it loops)
    OPEN_HOLD=0,           # frames: output frames 0..n-1 show frame n (frame 1 fell on a blink; the voice is untouched)
    CUTOUTS=[],            # tags whose span gets a transparent cut-out WebM (him over graphics)
    CUTOUT_REFINE=False,   # re-cut the cut-out's edge on the picture (build.refine_edge): a bright room shown on a dark background
    BG_DULL=None,          # dict(ev, sat, blur, choke, feather, top, side): the CUTOUTS WebM keeps his room, dulled (build.dull_room)
    HIDE=None,             # dict(emoji, scale, blur): blur + emoji over a bystander's face in every frame (kit/reel/hide.py)
    SAMPLE=15.0,           # the sample's length (hook + one middle beat)
    SAMPLE_CUT=None,       # optional [(a, b), ...] output ranges for the sample when it skips ahead
    MUSIC=[],              # [dict(file, a, b, start, under, gap)] beds for kit.audio.mix
    OUT="reel.mp4",
    DATA={},               # extra JSON handed to the template as D.x (screenshot sizes, prompt lines, etc.)
)


class Reel:
    def __init__(self, film):
        p = Path(film)
        if not p.exists():
            p = FILMS / film
        self.dir = p.resolve()
        spec = importlib.util.spec_from_file_location(f"reel_{self.dir.name.replace('-', '_')}", self.dir / "reel.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for k, v in DEFAULTS.items():
            setattr(self, k, getattr(mod, k, v))
        self.mod = mod
        if not self.TAKE:
            raise SystemExit(f"{self.dir}/reel.py: set TAKE")
        self.F = Film(self.dir / "reel.py")
        self.job = job_dir(self.TAKE)
        self.source = self.job / "source.mp4"

    @property
    def work(self):
        return self.F.work

    def words(self):
        import json
        return json.load(open(self.job / "analysis.json"))["words"]
