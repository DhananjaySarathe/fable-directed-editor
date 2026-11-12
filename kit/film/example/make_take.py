"""The example film's "recording": ffmpeg's test pattern (1920x1080, 30 fps) with a synthetic voice (macOS `say`), so
kit/film runs end to end with no footage. The voice has what a real take has for the cut to remove: a retake (a line
said twice, the second kept), an aside, a pause inside a sentence (a sliver) and pauses between lines.

    uv run python kit/film/example/make_take.py          # -> output/temp/films/kit-film-example/work/take.mp4
    uv run python -m kit.film kit/film/example prep      # shorts probe --landscape + analyze -> job film-example

Generated files stay under output/ (kit/paths.py). Re-run this after `shorts clean`.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from kit.paths import Film  # noqa: E402

VOICE, RATE = "Samantha", 178
# (line, the pause after it in seconds); [[slnc ms]] is say's own silence (a pause inside a sentence)
LINES = [
    ("Every film used to copy its own cut, its own page and its own mix.", 0.7),
    ("Over two thousand lines of edit code, copied from film to film.", 0.8),
    ("So every film learned the same bugs.", 0.6),                              # the first take (out)
    ("So every film learned the same bugs again.", 0.9),                        # the retake (kept)
    ("Now a film is three files.", 0.5),
    ("A cut list, a scene plan and a template.", 0.8),
    ("Hmm, where was I?", 0.9),                                                 # an aside (out)
    ("The kit does the rest.", 0.6),
    ("It snaps every cut to the frame grid, [[slnc 800]] and it listens to every join again.", 0.7),
    ("It builds the page, mixes the music under the voice, and renders the film in chunks.", 0.8),
    ("Then it cuts the Reels from the finished film, one whole sentence at a time.", 0.7),
    ("One command for each step, and nothing is copied.", 1.0),
]


def main():
    F = Film(HERE / "film.py")
    tmp = F.scratch / "take"
    tmp.mkdir(parents=True, exist_ok=True)
    parts = []
    for k, (line, pause) in enumerate(LINES):
        aiff, wav = tmp / f"l{k:02d}.aiff", tmp / f"l{k:02d}.wav"
        subprocess.run(["say", "-v", VOICE, "-r", str(RATE), "-o", str(aiff), line], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(aiff), "-af", f"apad=pad_dur={pause}", "-ac", "1", "-ar", "48000",
                        "-c:a", "pcm_s16le", str(wav)], check=True)
        parts.append(wav)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    voice = tmp / "voice.wav"
    # 0.6 s of quiet before the first word; a faint room tone so the pauses are a room, not digital silence
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-af", "adelay=600", "-ar", "48000",
                    str(voice)], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(voice)],
                               capture_output=True, text=True, check=True).stdout) + 0.5
    out = F.work / "take.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size=1920x1080:rate=30:duration={dur:.3f}",
                    "-i", str(voice), "-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude=0.0015:duration={dur:.3f}:sample_rate=48000",
                    "-filter_complex", "[1:a]apad[v];[v][2:a]amix=inputs=2:duration=longest:normalize=0,aformat=channel_layouts=stereo[a]",
                    "-map", "0:v", "-map", "[a]", "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-g", "30", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)], check=True)
    print(f"-> {out} ({dur:.2f} s): {len(LINES)} lines, voice {VOICE}")


if __name__ == "__main__":
    main()
