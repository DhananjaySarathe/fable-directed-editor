"""Caption sync: an edit's caption words (edl.json words: text, t, e) against what whisper hears in its own voice stem.

On the Framecast reels (2026-10-18) the burned-in captions ran up to 1.5 s ahead of the voice in places (the film's
respelled text sat on the wrong transcript slots) and only a fresh critic caught it, by ear. This catches it before the
critic: whisper (kit.cut.relisten, word times) on the voice, a fuzzy in-order match of caption words to heard words, and
the offset of every matched word.

    uv run python kit/qa/capsync.py <edl.json> <vo.wav> [--en] [--tol=0.45] [--json=<out>]

Prints each caption word more than --tol off (caption start minus heard start: + = late, - = early) and the median.
Exit 3 when a word is more than 0.8 s off or over a fifth of the matched words are past --tol; 0 otherwise. Advisory:
whisper's own word times wander by ~0.3 s, drift for seconds after a long silence (a held run with no voice) and pile a
window's last words on its end, so check a flagged word against the voice envelope's pauses before moving it (on the
Framecast reels the aligner was right more often than whisper).
Romanized Hindi is matched loosely (gayi/gahi, hai/he), so a word whisper spells differently still counts.
`heard(vo, total)` and `align(cap, heard)` are importable (films/reverse-engineer/shorts/cut.py re-times the gross ones).
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def align(cap: list[dict], heard: list[dict], thr: float = 0.55):
    """Needleman-Wunsch over the two word lists; a pair counts when its spelling similarity >= thr and the times are
    within 2.5 s. -> [(caption index, heard index)]."""
    n, m = len(cap), len(heard)
    NEG = -1e9
    S = [[0.0] * (m + 1) for _ in range(n + 1)]
    P = [[0] * (m + 1) for _ in range(n + 1)]
    gap = -0.25
    for i in range(1, n + 1):
        S[i][0], P[i][0] = S[i - 1][0] + gap, 1
    for j in range(1, m + 1):
        S[0][j], P[0][j] = S[0][j - 1] + gap, 2
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            s = sim(cap[i - 1]["n"], heard[j - 1]["n"])
            ok = s >= thr and abs(cap[i - 1]["t"] - heard[j - 1]["t"]) < 2.5
            d = S[i - 1][j - 1] + (s if ok else NEG / 1e6)
            u, l = S[i - 1][j] + gap, S[i][j - 1] + gap
            S[i][j], P[i][j] = max((d, 0), (u, 1), (l, 2))
    i, j, out = n, m, []
    while i > 0 and j > 0:
        if P[i][j] == 0:
            if sim(cap[i - 1]["n"], heard[j - 1]["n"]) >= thr:
                out.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif P[i][j] == 1:
            i -= 1
        else:
            j -= 1
    return out[::-1]


def heard(vo: Path, total: float, hinglish: bool = True) -> list[dict]:
    """Whisper's words in the voice stem: [{text, n (normalised), t (start s)}]."""
    from kit.cut.relisten import _extract, transcribe_many
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "vo.wav"
        _extract(Path(vo), 0.0, total, wav)
        hs = transcribe_many([wav], hinglish=hinglish)[0]
    return [{"text": h["text"], "n": norm(h["text"]), "t": float(h["start"])} for h in hs if norm(h["text"])]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        raise SystemExit(2)
    edl, vo = Path(args[0]), Path(args[1])
    tol = float(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--tol=")), 0.45))
    words = json.loads(edl.read_text())["words"]
    cap = []
    for w in words:
        for k, tok in enumerate(str(w.get("text", "")).split()):
            if norm(tok):
                cap.append({"i": w["i"], "text": tok, "n": norm(tok), "t": w["t"] if k == 0 else None, "e": w["e"]})
    # a word whose text holds several tokens: only its first token has its own time
    cap = [c for c in cap if c["t"] is not None]
    heard_ = heard(vo, float(json.loads(edl.read_text()).get("total", 0)) or 600.0, hinglish="--en" not in sys.argv)
    pairs = align(cap, heard_)
    offs = [(cap[i], heard_[j], cap[i]["t"] - heard_[j]["t"]) for i, j in pairs]
    bad = [(c, h, o) for c, h, o in offs if abs(o) > tol]
    med = sorted(o for _, _, o in offs)[len(offs) // 2] if offs else 0.0
    for c, h, o in bad:
        print(f"  [{c['i']}] '{c['text']}' at {c['t']:.2f}  heard '{h['text']}' at {h['t']:.2f}  {o:+.2f} s")
    worst = max((abs(o) for _, _, o in offs), default=0.0)
    verdict = "FAIL" if worst > 0.8 or (offs and len(bad) > len(offs) / 5) else "PASS"
    print(f"{verdict}: {edl.parent.name}  {len(offs)} of {len(cap)} caption words matched; {len(bad)} past {tol:.2f} s; median {med:+.2f} s; worst {worst:.2f} s")
    out = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--json=")), None)
    if out:
        Path(out).write_text(json.dumps([{"i": c["i"], "text": c["text"], "t": c["t"], "heard": h["t"], "off": round(o, 3)} for c, h, o in offs], indent=1))
    raise SystemExit(3 if verdict == "FAIL" else 0)


if __name__ == "__main__":
    main()
