"""Record a real terminal session (tmux) as timed ANSI frames, for rendering with render.mjs.

Drive it from a script:

    from kit.term.rec import Session
    with Session("out/r1", cwd="~/excalidraw", cmd="claude", cols=200, rows=56) as s:
        s.hold(2)
        s.type("/learn-repo"); s.key("Enter")
        s.wait_idle(timeout=900)

Frames: <out>/frames/NNNNN.ansi (deduplicated) and <out>/timeline.jsonl ({t, frame}),
plus <out>/marks.jsonl for labels you add with s.mark("band shown").
The tmux server starts with a clean environment, so the session is not a child of whatever runs the script.
"""
from __future__ import annotations

import json
import os
import random
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

TMUX = shutil.which("tmux") or "/opt/homebrew/bin/tmux"
FPS = 15
CLEAN_ENV = {
    "HOME": os.environ["HOME"], "USER": os.environ.get("USER", ""), "LOGNAME": os.environ.get("USER", ""),
    "SHELL": "/bin/zsh", "PATH": "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
    "LANG": "en_US.UTF-8", "TERM": "xterm-256color",
}


class Session:
    def __init__(self, out: str | Path, cwd: str, cmd: str, cols: int = 200, rows: int = 56,
                 env: dict[str, str] | None = None, name: str = "rec"):
        self.out = Path(out).expanduser()
        self.cwd = str(Path(cwd).expanduser())
        self.cmd, self.cols, self.rows, self.name = cmd, cols, rows, name
        self.env = {**CLEAN_ENV, **(env or {})}
        self._stop = threading.Event()
        self._t0 = 0.0
        self._n = 0

    # ── lifecycle ──────────────────────────────────────────────────────────
    def __enter__(self) -> "Session":
        if self.out.exists():
            shutil.rmtree(self.out)
        (self.out / "frames").mkdir(parents=True)
        subprocess.run([TMUX, "-L", self.name, "kill-server"], capture_output=True)
        subprocess.run([TMUX, "-L", self.name, "new-session", "-d", "-s", self.name, "-x", str(self.cols),
                        "-y", str(self.rows), "-c", self.cwd, self.cmd], env=self.env, check=True)
        subprocess.run([TMUX, "-L", self.name, "set", "-g", "status", "off"], capture_output=True)
        self._t0 = time.monotonic()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.hold(0.5)
        self._stop.set()
        self._thread.join()
        subprocess.run([TMUX, "-L", self.name, "kill-server"], capture_output=True)
        (self.out / "meta.json").write_text(json.dumps(
            {"cols": self.cols, "rows": self.rows, "duration": round(time.monotonic() - self._t0, 3)}))

    # ── capture ────────────────────────────────────────────────────────────
    def screen(self, ansi: bool = False) -> str:
        args = [TMUX, "-L", self.name, "capture-pane", "-p", "-t", self.name] + (["-e"] if ansi else [])
        return subprocess.run(args, capture_output=True, text=True).stdout

    def _capture_loop(self) -> None:
        last = None
        with open(self.out / "timeline.jsonl", "w") as tl:
            while not self._stop.is_set():
                t = time.monotonic() - self._t0
                shot = self.screen(ansi=True)
                if shot != last:
                    self._n += 1
                    (self.out / "frames" / f"{self._n:05d}.ansi").write_text(shot)
                    tl.write(json.dumps({"t": round(t, 3), "frame": self._n}) + "\n")
                    tl.flush()
                    last = shot
                time.sleep(max(0.0, 1 / FPS - (time.monotonic() - self._t0 - t)))

    def mark(self, label: str) -> None:
        with open(self.out / "marks.jsonl", "a") as f:
            f.write(json.dumps({"t": round(time.monotonic() - self._t0, 3), "label": label}) + "\n")

    # ── input ──────────────────────────────────────────────────────────────
    def type(self, text: str, cps: float = 14.0) -> None:
        """Type like a person: one key at a time, a little jitter, longer after spaces."""
        for ch in text:
            subprocess.run([TMUX, "-L", self.name, "send-keys", "-t", self.name, "-l", ch])
            base = 1 / cps
            time.sleep(base * random.uniform(0.6, 1.5) * (1.8 if ch == " " else 1))

    def key(self, *keys: str, gap: float = 0.25) -> None:
        for k in keys:
            subprocess.run([TMUX, "-L", self.name, "send-keys", "-t", self.name, k])
            time.sleep(gap)

    def hold(self, seconds: float) -> None:
        time.sleep(seconds)

    # ── waiting ────────────────────────────────────────────────────────────
    def wait_for(self, pattern: str, timeout: float = 60, absent: bool = False) -> bool:
        rx = re.compile(pattern)
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            found = bool(rx.search(self.screen()))
            if found != absent:
                return True
            time.sleep(0.2)
        return False

    def wait_idle(self, timeout: float = 600, busy: str = r"esc to interrupt", settle: float = 2.0) -> bool:
        """Wait for Claude to start working, then for it to stop (the busy hint gone for `settle` s)."""
        self.wait_for(busy, timeout=20)
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if self.wait_for(busy, timeout=end - time.monotonic(), absent=True):
                time.sleep(settle)
                if not re.search(busy, self.screen()):
                    return True
        return False
