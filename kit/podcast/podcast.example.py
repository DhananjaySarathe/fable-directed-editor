# films/<name>/podcast.py: a podcast's recipe (copy this file; kit/podcast/config.py has the defaults)
TAKE = "pod1"                                   # uv run shorts probe "<file>" --job pod1 --landscape && uv run shorts analyze pod1
SOURCE = "~/Downloads/podcast.mp4"              # the original file at full resolution (the crops come from it)
PEOPLE = {"A": {"name": "Your Name", "sub": "Your channel"},    # left to right in the frame
          "B": {"name": "Guest Name", "sub": "what they build"}}
CUT = [
    # (first word, last word, "why"): repetition, phone reading, tangents. Whole thoughts only.
]
SPEAKER_FIX = {}                                # {(first word, last word): "B"} where work/speakers.txt is wrong
CHAPTERS = []                                   # [(word id, "Title")]: a wide shot + a YouTube chapter
GAP_MAX, GAP_KEEP = 0.6, 0.35                   # pauses over 0.6 s keep 0.35 s of room quiet
MUSIC = None                                    # or {"file": "chill/<track>.mp3", "intro": 6, "outro": 8, "under": -24}
DENOISE_DB = 14                                 # gentle; raise to 20 for a noisy room
DEREVERB = False                                # True in an echoing room (WPE, slower)
LUFS = -14.0
OUT = "podcast.mp4"
RES = 1080                                      # 2160 only with a 4K source
FPS = None                                      # keep the take's frame rate (an iPhone 4K60 take stays 60)
LOOK = {"warmth": 0.02, "contrast": 1.06, "sat": 1.06}   # no denoise / sharpen / vignette: they cost detail (2026-10-12)
