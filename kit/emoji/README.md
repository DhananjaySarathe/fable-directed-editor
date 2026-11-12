# Animated emoji (Google Noto, Lottie)

51 animated emoji from Google's Noto Emoji (https://googlefonts.github.io/noto-emoji-animation/), fetched on 2026-10-20
from `https://fonts.gstatic.com/s/e/notoemoji/latest/<codepoint>/lottie.json` and saved as `noto/<name>.json`.

**Licence: CC BY 4.0.** Commercial use, including monetised videos, is allowed with credit. When a film uses one,
kit/film's build writes the credit into `output/final/<film>/credits.txt`:

    Animated emoji: Google Noto Emoji (CC BY 4.0)

Paste it into the video description (with the music credits the same file lists).

In a page: `HF.emoji(K, parent, "fire", t, { x, y, size, until, loops, speed })` (kit/hf/emoji.js). vendor.py inlines
only the emoji a page names. Names: the file names here (fire, rocket, mind-blown, thinking, party, hundred, check,
cross, eyes, skull, joy, ...). To add one: find its codepoint at the URL above and save `noto/<name>.json`.
