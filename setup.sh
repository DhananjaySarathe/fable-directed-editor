#!/usr/bin/env bash
# One-time setup on a new Mac: system tools, Python + Node packages, models, fonts and the Apple Vision tools.
# Safe to re-run (everything already present is skipped).
#
#   git clone <this repo> "fable-directed-editor"
#   cd "fable-directed-editor" && ./setup.sh
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
say() { printf '\n==> %s\n' "$*"; }
[ "$(uname)" = Darwin ] || { echo "setup.sh is for macOS. On Linux (Claude Code cloud) run ./cloud-setup.sh"; exit 1; }

say "System tools (Homebrew: ffmpeg, whisper.cpp, uv, node)"
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is missing. Install it from https://brew.sh, then run ./setup.sh again."; exit 1
fi
for f in ffmpeg whisper.cpp uv node; do brew list --formula "$f" >/dev/null 2>&1 || brew install "$f"; done
if ! xcode-select -p >/dev/null 2>&1; then
  echo "The Xcode command line tools are missing (needed to build the Vision tools)."
  echo "Run:  xcode-select --install   then run ./setup.sh again."; exit 1
fi
[ -d "/Applications/Google Chrome.app" ] || echo "WARNING: install Google Chrome (graphics and HyperFrames render with it): https://www.google.com/chrome/"

say "Python packages (uv sync)"
uv sync

say "Node packages (npm install) and the pinned HyperFrames renderer"
npm install --no-audit --no-fund
HF_VERSION="$(uv run python -c 'from shorts import config; print(config.HYPERFRAMES_VERSION)')"
[ "$(hyperframes --version 2>/dev/null)" = "$HF_VERSION" ] || npm install -g "hyperframes@$HF_VERSION" --no-audit --no-fund
echo "hyperframes $(hyperframes --version)"

say "Models, fonts, Vision tools and the cut checker's text model (~1.2 GB the first time)"
uv run shorts setup

say "Music and sound effects (downloaded from their sources; tracks already present are skipped)"
uv run python kit/assets_src/fetch.py || echo "Some audio could not be downloaded; run: uv run python kit/assets_src/fetch.py"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example (no keys are needed yet)."
fi

say "Check (uv run shorts doctor)"
uv run shorts doctor || true
