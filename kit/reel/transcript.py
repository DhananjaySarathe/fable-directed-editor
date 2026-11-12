"""Hand-corrected transcript for a take (generic; from films/*/transcript.py, 2026-10-10).

Whisper sometimes returns a take without punctuation (the sentence map then sees no sentence ends) or mishears names
("cloud" for Claude). The film's reel.py gives the corrected text as LINES; this writes it into the take's
analysis.json (the whisper version is kept next to it as analysis.whisper.json, and every run starts from that copy).

    TRANSCRIPT = [((0.00, 4.95), "This is how I audit my YouTube channel, ..."), ...]   # (window s, the words)

A token "caption|spoken" shows `caption` and is aligned as `spoken` ("Claude|cloud", "7AM|seven-ay-em").
When the corrected tokens line up one-to-one with whisper's words (same count, same spoken word), whisper's times are
kept as they are (only text and punctuation change). Otherwise the wav2vec2 aligner places every word again.
TIME_FIX = {word id: (start, end)} overrides what the aligner gets wrong (measure it on the voice envelope).
"""
import json
import re
import shutil

import numpy as np

from kit.paths import job_dir, job_temp


def tokens(lines):
    """(caption, spoken, rough start, rough end) per word: the rough times spread each line over its window."""
    out = []
    for (a, b), line in lines:
        toks = line.split()
        lens = [max(1, len(t.split("|")[-1])) for t in toks]
        t, tot = a, sum(lens)
        for tok, n in zip(toks, lens):
            cap, _, spoken = tok.partition("|")
            d = (b - a) * n / tot
            out.append((cap, (spoken or cap).replace("-", " "), t, t + d))
            t += d
    return out


def bare(s):
    return re.sub(r"[^a-z0-9']", "", s.lower())


def fix(take, lines, time_fix=None):
    from shorts.analyze.words import find_pauses, group_sentences
    from shorts.schemas import Word
    jd, tj = job_dir(take), job_temp(take)
    keep = jd / "analysis.whisper.json"
    if not keep.exists():
        shutil.copy(jd / "analysis.json", keep)
    an = json.loads(keep.read_text())
    T = tokens(lines)
    old = an["words"]
    same = len(old) == len(T) and all(bare(o["text"]) == bare(s.split()[0]) or len(s.split()) > 1 for o, (c, s, *_r) in zip(old, T))
    if same:
        ws = [Word(**{**o, "text": c}) for o, (c, *_r) in zip(old, T)]
        how = "whisper times kept (one-to-one)"
    else:
        from shorts.analyze.align import Aligner, align_words, load_vocab
        from shorts.analyze.audio import read_wav
        from shorts.analyze.transcribe import RawWord
        from shorts.analyze.words import OBVIOUS_FILLERS, place_fillers, refine_words
        samples, sr = read_wav(tj / "audio16k.wav")
        db = np.load(tj / "energy.npy")
        logp, frame_s = Aligner().emissions(samples, sr)
        flat, owner = [], []
        for k, (_, spoken, *_r) in enumerate(T):
            for s in spoken.split():
                flat.append(s.strip(".,?!")); owner.append(k)
        spans = place_fillers(flat, align_words(logp, frame_s, flat, load_vocab(), wildcard=OBVIOUS_FILLERS), db, an["dip_db"])
        merged = [None] * len(T)
        for k, sp in zip(owner, spans):
            if sp:
                merged[k] = (min(merged[k][0], sp[0]), max(merged[k][1], sp[1])) if merged[k] else sp
        raw = [RawWord(text=c, start=a, end=b, p=1.0) for c, _, a, b in T]
        ws = refine_words(raw, merged, db, an["quiet_db"], gap_db=an["dip_db"])
        miss = [w.text for w, m in zip(ws, merged) if m is None]
        how = f"re-aligned ({len(miss)} not aligned: {miss})"
    for i, (a, b) in (time_fix or {}).items():
        ws[i].start, ws[i].end = a, b
    an["words"] = [w.model_dump() for w in ws]
    an["sentences"] = [s.model_dump() for s in group_sentences(ws)]
    an["pauses"] = [p.model_dump() if hasattr(p, "model_dump") else p for p in find_pauses(ws)]
    an["warnings"] = [w for w in an.get("warnings", []) if not w.startswith("transcript:")] + ["transcript: corrected by hand (reel.py TRANSCRIPT)"]
    (jd / "analysis.json").write_text(json.dumps(an, indent=1, ensure_ascii=False))
    # the sentence map reads analysis.json: rebuild it
    import subprocess
    import sys
    from kit.paths import ROOT
    subprocess.run([sys.executable, "-m", "kit.cut.sentmap", take, "--force"], cwd=ROOT, check=False, capture_output=True)
    print(f"{len(ws)} words, {how}")
    for s in an["sentences"]:
        print(f"  {s['id']:>4} {s['start']:6.2f}-{s['end']:6.2f}  {s['text']}")
    return an
