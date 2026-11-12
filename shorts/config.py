"""Paths, tool lookup and tunable constants for Fable-Directed Editor."""
from __future__ import annotations

import shutil
from pathlib import Path

from dotenv import load_dotenv

from shorts.errors import ShortsError

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "kit"
MODELS = KIT / "models"
FONTS = KIT / "fonts"
# Everything the pipeline generates lives under output/ (gitignored). Same layout as kit/paths.py (films use that one).
#   output/final/<name>/  deliverables: the finished video, its contact sheet (keep)
#   output/jobs/<name>/   one take: the footage copy (source.mp4) + transcript + edit decisions (keep while re-editing)
#   output/temp/          everything else: audio, frames, previews, logs, caches (delete any time)
OUTPUT = ROOT / "output"
JOBS = OUTPUT / "jobs"
TEMP = OUTPUT / "temp"
FINAL = OUTPUT / "final"
CACHE = TEMP / "cache"

load_dotenv(ROOT / ".env")

# Output frame of a vertical short (probe normalizes to it, the face pass scales to it).
OUT_W, OUT_H = 1080, 1920

# Model files (downloaded by `shorts setup`).
WHISPER_MODEL = MODELS / "ggml-large-v3-turbo-q5_0.bin"
ALIGN_MODEL = MODELS / "wav2vec2-base-960h-int8.onnx"
ALIGN_VOCAB = MODELS / "wav2vec2-base-960h-vocab.json"
FACE_MODEL = MODELS / "face_detection_yunet_2023mar.onnx"
TURN_MODEL = MODELS / "smart-turn-v3.2-cpu.onnx"        # kit/cut: end-of-utterance (Pipecat Smart Turn v3.2, BSD-2)
VAD_MODEL = MODELS / "silero_vad.onnx"                 # kit/cut: pauses (Silero VAD, MIT)
HYPERFRAMES_VERSION = "0.8.134"                         # the renderer every film so far was made with; setup.sh installs exactly this
BIN = KIT / "bin"                                      # Apple Vision tools, compiled by `shorts setup` (gitignored)

# Whisper drops fillers ("uh", "um") unless the prompt itself contains them. This prompt keeps
# fillers AND gives proper casing and punctuation (measured on the first sample, 2026-09-26).
WHISPER_PROMPT = ("Umm, so, uh, today I'm testing, like, a new app. Uh, honestly? "
                  "It's, um, amazing. So yeah, let's see.")
# Hindi speech: whisper's "hi" output is Devanagari or an invented English translation, but English decoding
# primed with romanized Hinglish writes what was said in Latin script (measured on video2, 2026-09-27).
HINDI_LANGS = ("hi", "ur")
HINGLISH_PROMPT = ("Toh, umm, basically main aaj ek naya hack try kar raha hoon. Matlab, maine apna room thoda "
                   "set kiya hai, aur uh, focus bahut badh gaya hai. Dekho, yeh jagah hai jahan main kaam karunga.")
# second try for a chunk the first prompt under-transcribed (whisper's skips depend on the prompt)
HINGLISH_PROMPT_ALT = ("Haan toh dekho, aaj maine ek funny cheez observe ki. Hum hamesha poochte hain ki kitna "
                       "time lagega. Matlab, yaar, bas itna batao, theek hai?")

_FORMULA = {"ffmpeg": "ffmpeg", "ffprobe": "ffmpeg", "whisper-cli": "whisper-cpp", "node": "node"}


def tool(name: str) -> str:
    """Absolute path of a command-line tool, or a clear error saying how to install it."""
    path = shutil.which(name)
    if not path:
        raise ShortsError("E_TOOL_MISSING", f"{name} is not installed or not on PATH.",
                          f"brew install {_FORMULA.get(name, name)}")
    return path
