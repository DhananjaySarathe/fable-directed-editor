"""Respelled caption text, placed on its own sound.

A film's RESPELL text (names spelled right, his Hindi in romanized Hinglish) rarely has as many words as the transcript's
word slots for the same range, so spreading it evenly over them drifts: on "Framecast" (2026-10-18) captions ran up
to 1.5 s ahead of the voice, a word could sit in the piece before the one it is said in, and a slam missed its word.
`place` force-aligns the whole text on the range's own audio (the wav2vec2 aligner in shorts.analyze.align) and gives each
slot the tokens whose aligned middle is nearest it, with the tokens' measured times; tokens that share a slot spill into
empty neighbour slots, so each caption word keeps its own time.

    from kit.cut.respell import place
    texts, times = place(text, samples16, t0, slots)   # slots: [(start, end)] of the range's words, in source seconds
"""
from __future__ import annotations

import numpy as np

PUNCT = ".,?!\"'“”‘’…;:()"


def place(text: str, samples16: np.ndarray, t0: float, slots: list[tuple[float, float]], aligner=None, vocab=None, group=None):
    """text: what was said over the slots; samples16: 16 kHz mono audio that starts at source time t0 and covers the
    slots. -> (texts, times): one string per slot ("" = none) and one (start, end) in source seconds or None per slot.
    Tokens the aligner cannot place ("...", a stray symbol) ride with the token before them. When the text does not fit
    the audio, the even spread comes back with no times, so a caller can keep its old timing. group: an id per slot (a
    film piece); a crowded slot spills only into slots of its own group, so no word moves into another shot."""
    from shorts.analyze.align import Aligner, align_words, load_vocab
    from shorts.analyze.words import OBVIOUS_FILLERS

    toks = text.split()
    n = len(slots)
    if not toks or not n:
        return [""] * n, [None] * n
    aligner = aligner or Aligner()
    vocab = vocab or load_vocab()
    bare = [t.strip(PUNCT) for t in toks]
    idx = [k for k, b in enumerate(bare) if b]
    logp, fs = aligner.emissions(samples16.astype(np.float32), 16000)
    spans = align_words(logp, fs, [bare[k] for k in idx], vocab, wildcard=OBVIOUS_FILLERS)
    span = [None] * len(toks)
    for k, sp in zip(idx, spans):
        if sp:
            span[k] = (t0 + sp[0], t0 + sp[1])
    if not any(span):
        buckets = [[] for _ in range(n)]
        for k, tok in enumerate(toks):
            buckets[min(n - 1, k * n // len(toks))].append(tok)
        return [" ".join(b) for b in buckets], [None] * n

    def nearest(m):
        best, bd = 0, 1e9
        for j, (a, b) in enumerate(slots):
            d = 0.0 if a <= m <= b else min(abs(m - a), abs(m - b))
            if d < bd - 1e-9:
                best, bd = j, d
        return best

    owner, last = [], 0
    for k in range(len(toks)):
        if span[k]:
            last = max(last, nearest((span[k][0] + span[k][1]) / 2))   # never earlier than the token before
        owner.append(last)
    # tokens that share a slot spill into the empty slots beside it, in order (the slot ids stay; the times are the tokens'
    # own), so a caption word keeps its own time instead of five words landing at once ("Yeah, we all are doing"); the
    # slots between a crowded slot and an empty one (up to 6 away) shift one step toward the empty one to make room
    def spill():
        for j in range(n):
            ks = [k for k in range(len(toks)) if owner[k] == j]
            if len(ks) < 2:
                continue
            used = set(owner)
            g = group[j] if group else None
            for d in range(1, 7):
                e = j - d
                if e < 0 or (group and group[e] != g):
                    break
                if e not in used:
                    for k in range(len(toks)):
                        if e < owner[k] < j:
                            owner[k] -= 1
                    owner[ks[0]] = j - 1
                    return True
            for d in range(1, 7):
                e = j + d
                if e >= n or (group and group[e] != g):
                    break
                if e not in used:
                    for k in range(len(toks)):
                        if j < owner[k] < e:
                            owner[k] += 1
                    owner[ks[-1]] = j + 1
                    return True
        return False
    for _ in range(4 * len(toks)):
        if not spill():
            break
    texts = [[] for _ in range(n)]
    times = [None] * n
    for k, j in enumerate(owner):
        texts[j].append(toks[k])
        if span[k]:
            times[j] = (min(times[j][0], span[k][0]), max(times[j][1], span[k][1])) if times[j] else span[k]
    return [" ".join(t) for t in texts], times
