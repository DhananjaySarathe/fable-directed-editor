# kit/term: real terminal demos as 4K video

- `rec.py`: `Session` runs a command in a clean tmux (no inherited env) and saves deduplicated ANSI frames 15×/s. Script it with type/key/wait_for/wait_idle/mark.
- `drive.py`: the same, driven live by appending JSON lines to `<out>.cmds.jsonl` (for answers you write after reading the screen).
- `render.mjs`: frames → MP4 at 3840×2160, 60 fps (Chrome draws each unique frame; `--from/--to/--speed` for time-lapses).
- `docscroll.mjs`: a Markdown file as a dark editor preview (mermaid drawn), stopping at each `##`, as MP4.

Run interactive `claude` outside the sandbox (the sandbox can't read the keychain login). First used for films/repo-sensei (2026-11-07).
