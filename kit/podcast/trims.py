"""What to take out of a conversation, as a review list for the editor (Claude) and the owner. Nothing is cut here:
the editor reads the list with the transcript and writes CUT ranges into podcast.py.

    pauses      a gap between words longer than GAP_MAX: edl.py shortens it automatically to GAP_KEEP (listed for info)
    phone       someone looks down (eye openness well under their own median) for 1.5 s+ while nobody talks much:
                reading a phone; propose cutting the gap, and the words around it if they're him reading out loud
    repeat      a sentence that says nearly the same as one in the last 90 s (word overlap): keep the later, complete one
    restart     a sentence abandoned after 1-4 words and started again
    filler      runs of fillers ("um uh", "matlab matlab", "you know you know")

Rules (EDITING.md §12): cut whole thoughts, never half a sentence; keep a question with its answer; keep laughter
and real reactions; when in doubt keep it and list it for the owner.
"""
import re
from difflib import SequenceMatcher

import numpy as np

FILLERS = {"um", "uh", "uhm", "erm", "hmm", "ah", "matlab", "basically", "like", "actually", "so", "haan"}


def bare(s):
    return re.sub(r"[^\w']", "", s.lower())


def pauses(words, gap_max):
    out = []
    for a, b in zip(words, words[1:]):
        g = b["start"] - a["end"]
        if g > gap_max:
            out.append({"kind": "pause", "after": a["i"], "a": a["end"], "b": b["start"], "len": round(g, 2)})
    return out


def phone(marks_t, eyes, people, words, min_len=1.5):
    """Spans where a person's eyes are well under their median (looking down) and little is said."""
    out = []
    talk = np.zeros(len(marks_t), bool)
    for w in words:
        talk |= (marks_t >= w["start"]) & (marks_t <= w["end"])
    for p in people:
        e = eyes[p["id"]]
        low = (e < 0.7 * p["eyes_p50"]) & ~np.isnan(e)
        i = 0
        while i < len(low):
            if low[i]:
                j = i
                while j + 1 < len(low) and low[j + 1]:
                    j += 1
                a, b = marks_t[i], marks_t[j]
                if b - a >= min_len and talk[i:j + 1].mean() < 0.5:
                    out.append({"kind": "phone", "who": p["id"], "a": round(float(a), 2), "b": round(float(b), 2), "len": round(float(b - a), 2)})
                i = j + 1
            else:
                i += 1
    return out


def repeats(sentences, window=90.0, ratio=0.72):
    out = []
    toks = [[bare(w) for w in s["text"].split() if bare(w)] for s in sentences]
    for j, s in enumerate(sentences):
        if len(toks[j]) < 4:
            continue
        for i in range(j - 1, -1, -1):
            if s["start"] - sentences[i]["end"] > window:
                break
            if len(toks[i]) < 4:
                continue
            r = SequenceMatcher(None, toks[i], toks[j]).ratio()
            if r >= ratio:
                out.append({"kind": "repeat", "first": sentences[i]["id"], "again": s["id"], "ratio": round(r, 2),
                            "a": sentences[i]["start"], "text": sentences[i]["text"][:80], "text2": s["text"][:80]})
                break
    return out


def restarts(sentences):
    out = []
    for a, b in zip(sentences, sentences[1:]):
        ta, tb = a["text"].split(), b["text"].split()
        if 1 <= len(ta) <= 4 and len(tb) > len(ta) and [bare(x) for x in tb[:len(ta)]] == [bare(x) for x in ta]:
            out.append({"kind": "restart", "sentence": a["id"], "a": a["start"], "text": a["text"]})
    return out


def fillers(words):
    out, run = [], []
    for w in words + [{"text": "", "i": -1, "start": 1e9, "end": 1e9}]:
        if bare(w["text"]) in FILLERS:
            run.append(w)
        else:
            if len(run) >= 2:
                out.append({"kind": "filler", "first": run[0]["i"], "last": run[-1]["i"], "a": run[0]["start"], "text": " ".join(x["text"] for x in run)})
            run = []
    return out


def report(items, path):
    mm = lambda s: f"{int(s // 60):02d}:{s % 60:04.1f}"
    lines = ["# Trim candidates (judge each one with the transcript; nothing is cut until it is in podcast.py CUT)", ""]
    for it in sorted(items, key=lambda x: x["a"]):
        k = it["kind"]
        if k == "pause":
            continue
        if k == "phone":
            lines.append(f"- {mm(it['a'])} PHONE   {it['who']} looks down {it['len']} s (little talk)")
        elif k == "repeat":
            lines.append(f"- {mm(it['a'])} REPEAT  s{it['first']} ~ s{it['again']} ({it['ratio']}): \"{it['text']}\" / \"{it['text2']}\"")
        elif k == "restart":
            lines.append(f"- {mm(it['a'])} RESTART s{it['sentence']}: \"{it['text']}\"")
        elif k == "filler":
            lines.append(f"- {mm(it['a'])} FILLER  words {it['first']}-{it['last']}: \"{it['text']}\"")
    ps = [it for it in items if it["kind"] == "pause"]
    lines += ["", f"{len(ps)} pauses over GAP_MAX ({sum(p['len'] for p in ps):.0f} s) are shortened automatically."]
    open(path, "w").write("\n".join(lines) + "\n")
    return lines
