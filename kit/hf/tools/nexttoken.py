"""Real next-token probabilities for HF.tokens (kit/hf/explain.js): the top-k candidates at every step, from a real model.
Never type these numbers by hand (kit/refs/SCENES.md: real data only).

    # offline, any machine: GPT-2 small (ONNX model zoo, 665 MB) + the GPT-2 tokenizer from npm (gpt-tokenizer)
    python3 kit/hf/tools/nexttoken.py --onnx gpt2-lm-head-10.onnx --tok <dir with node_modules/gpt-tokenizer> \
        --prompt "The best way to learn to code is" --steps 6 [--force " to build things"] [--k 5] [--temps 0.7,1.5] -o tokens.json
    # any local server with logprobs (llama.cpp server, LM Studio, vLLM: an OpenAI-compatible /v1/completions)
    python3 kit/hf/tools/nexttoken.py --endpoint http://localhost:8080/v1 --model qwen3 --prompt "..." --steps 6 -o tokens.json

--force  make the model continue with this text (scripted), still recording what it *wanted* at each step
--temps  also store each step's top-k re-weighted at these temperatures (for the temperature beat)
Output: { model, source, prompt, steps: [{ chosen, forced, top: [{ t, p }], temps: { "1.5": [{ t, p }] } }] }
The model's name goes on screen with the bars (HF.tokens shows `model`).
"""
import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

import numpy as np

TOK_JS = """
const t = require(process.argv[1] + '/node_modules/gpt-tokenizer/cjs/encoding/r50k_base');
const q = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const out = { enc: q.enc.map((s) => t.encode(s)), dec: q.dec.map((ids) => t.decode(ids)) };
process.stdout.write(JSON.stringify(out));
"""


def tok(dir_, enc=(), dec=()):
    r = subprocess.run(["node", "-e", TOK_JS, str(Path(dir_).resolve())], input=json.dumps({"enc": list(enc), "dec": [list(map(int, d)) for d in dec]}),
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def softmax(x, temp=1.0):
    z = (x - x.max()) / temp
    e = np.exp(z)
    return e / e.sum()


def onnx_steps(a):
    import onnxruntime as ort
    sess = ort.InferenceSession(a.onnx)
    name = sess.get_inputs()[0].name
    ids = tok(a.tok, enc=[a.prompt])["enc"][0]
    forced = tok(a.tok, enc=[a.force])["enc"][0] if a.force else []
    n = len(forced) if forced else a.steps
    raw = []
    for i in range(n):
        logits = sess.run(None, {name: np.array([[ids]], dtype=np.int64)})[0][0, 0, -1].astype(np.float64)
        p = softmax(logits)
        top = np.argsort(-p)[: a.k]
        temps = {str(T): (lambda q: [(int(j), float(q[j])) for j in np.argsort(-q)[: a.k]])(softmax(logits, T)) for T in a.temps}
        nxt = forced[i] if forced else int(top[0])
        raw.append({"top": [(int(j), float(p[j])) for j in top], "temps": temps, "chosen": nxt, "chosen_p": float(p[nxt]), "forced": bool(forced)})
        ids.append(nxt)
    every = sorted({j for r in raw for j, _ in r["top"]} | {j for r in raw for v in r["temps"].values() for j, _ in v} | {r["chosen"] for r in raw})
    words = dict(zip(every, tok(a.tok, dec=[[j] for j in every])["dec"]))
    steps = [{"chosen": words[r["chosen"]], "chosen_p": round(r["chosen_p"], 4), "forced": r["forced"],
              "top": [{"t": words[j], "p": round(q, 4)} for j, q in r["top"]],
              "temps": {T: [{"t": words[j], "p": round(q, 4)} for j, q in v] for T, v in r["temps"].items()}} for r in raw]
    return {"model": "GPT-2 small (2019)", "source": "onnx/models gpt2-lm-head-10, run locally", "prompt": a.prompt, "steps": steps}


def endpoint_steps(a):
    text, steps = a.prompt, []
    for _ in range(a.steps):
        body = json.dumps({"model": a.model, "prompt": text, "max_tokens": 1, "logprobs": a.k, "temperature": 0}).encode()
        req = urllib.request.Request(a.endpoint.rstrip("/") + "/completions", body, {"Content-Type": "application/json"})
        ch = json.load(urllib.request.urlopen(req, timeout=60))["choices"][0]
        tl = ch["logprobs"]["top_logprobs"][0]
        top = sorted(((t, float(np.exp(lp))) for t, lp in tl.items()), key=lambda x: -x[1])[: a.k]
        steps.append({"chosen": ch["text"], "chosen_p": round(top[0][1], 4), "forced": False, "top": [{"t": t, "p": round(p, 4)} for t, p in top], "temps": {}})
        text += ch["text"]
    return {"model": a.model, "source": a.endpoint, "prompt": a.prompt, "steps": steps}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--steps", type=int, default=6)
    ap.add_argument("--force", default="")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--temps", default="", help="comma list, e.g. 0.7,1.5")
    ap.add_argument("--onnx")
    ap.add_argument("--tok", help="a folder whose node_modules has gpt-tokenizer (npm i gpt-tokenizer)")
    ap.add_argument("--endpoint")
    ap.add_argument("--model", default="local")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    a.temps = [float(x) for x in a.temps.split(",") if x]
    if not (a.onnx or a.endpoint):
        sys.exit("give --onnx (+ --tok) or --endpoint")
    if a.onnx and not a.tok:
        sys.exit("--onnx needs --tok (a folder with node_modules/gpt-tokenizer)")
    R = onnx_steps(a) if a.onnx else endpoint_steps(a)
    s = json.dumps(R, ensure_ascii=False, indent=1)
    if a.out:
        Path(a.out).write_text(s + "\n")
    for st in R["steps"]:
        print(f"{st['chosen']!r:>14} {'(forced) ' if st['forced'] else ''}<- " + "  ".join(f"{c['t']!r} {c['p']:.0%}" for c in st["top"]))


if __name__ == "__main__":
    main()
