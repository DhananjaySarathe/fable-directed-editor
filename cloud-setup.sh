#!/usr/bin/env bash
# Setup for Claude Code cloud sessions (Linux). The Mac setup is ./setup.sh; this one skips what only a Mac has
# (Homebrew, Xcode, the Apple Vision tools, Chrome in /Applications), so a cloud session can edit code, run the tests and
# build graphics, but not grade, cut out people or do a full render. Safe to re-run. Runs from the SessionStart hook in
# .claude/settings.json only when CLAUDE_CODE_REMOTE=true.
#
#   CLOUD_MODELS=1 ./cloud-setup.sh     also download the speech/face models (~1 GB, needs Full network access)
set -euo pipefail
cd "$(dirname "$0")"
say() { printf '\n==> %s\n' "$*"; }
[ "$(uname)" = Linux ] || { echo "cloud-setup.sh is for Linux. On a Mac run ./setup.sh"; exit 1; }

say "System tools (apt: ffmpeg)"
if ! command -v ffmpeg >/dev/null 2>&1; then
  SUDO=""; [ "$(id -u)" = 0 ] || SUDO="sudo"
  $SUDO apt-get update -qq && $SUDO apt-get install -y -qq ffmpeg
fi
command -v uv >/dev/null 2>&1 || pip install --quiet uv

say "Python packages (uv sync)"
uv sync

say "Node packages (npm install) and the pinned HyperFrames renderer"
npm install --no-audit --no-fund
HF_VERSION="$(uv run python -c 'from shorts import config; print(config.HYPERFRAMES_VERSION)')"
[ "$(hyperframes --version 2>/dev/null)" = "$HF_VERSION" ] || npm install -g "hyperframes@$HF_VERSION" --no-audit --no-fund

say "Fonts"
uv run shorts setup --fonts-only || echo "Fonts skipped (Google Fonts blocked? use Full network access)."

if [ "${CLOUD_MODELS:-}" = "1" ]; then
  say "Models (speech, alignment, face, cut checker)"
  uv run python -c 'from shorts import setup_assets as s; [s._download(u, d) for d, u in s.MODEL_URLS.items() if not d.exists()]; s.prefetch_sat()'
fi

[ -f .env ] || cp .env.example .env
echo "cloud setup done"
