"""kit/hf/render4k.py reuses a finished chunk only while its key matches (renders/chunks/cNN.key: the chunk page, the size
and mtime of every file under assets/, vendor/'s bytes, the render args). 2026-11-06: films/snappaste's re-edited 4K
final carried the old picture for 0-45 s, because a right frame count was enough to say "done already". No real render:
the hyperframes render, ffprobe and the ffmpeg join are stubbed, and a stub chunk file holds its frame count as text."""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from kit.hf import render4k as R

PAGE = """<!doctype html><html><body>
<div id="root" data-composition-id="main" data-width="1920" data-height="1080" data-duration="2.5"><p>take one</p></div>
</body></html>
"""
CHUNKS = [0, 1, 2]          # 2.5 s at 10 fps in 1 s chunks: 10 + 10 + 5 frames


@pytest.fixture
def film(tmp_path, monkeypatch):
    hf = tmp_path / "hf"
    (hf / "assets/clips").mkdir(parents=True)
    (hf / "vendor").mkdir()
    (tmp_path / "broll").mkdir()
    (hf / "index.html").write_text(PAGE)
    (hf / "assets/face.mp4").write_bytes(b"the graded take")
    (hf / "assets/clips/c01.mp4").write_bytes(b"clip one")
    (tmp_path / "broll/cafe.mp4").write_bytes(b"cafe")
    (hf / "assets/broll").symlink_to(tmp_path / "broll")          # a linked folder is followed
    (hf / "assets/loop").symlink_to(hf / "assets")                # ... once
    (hf / "vendor/gsap.min.js").write_text("/* gsap */")
    rendered, joined, failing = [], [], set()

    def run(cmd, **kw):
        cmd = [str(c) for c in cmd]
        if cmd[:3] == ["npx", "hyperframes", "render"]:
            proj, out = Path(cmd[3]), Path(cmd[cmd.index("-o") + 1])
            k = int(proj.name[1:])
            rendered.append(k)
            if k in failing:                                       # stopped: whatever was in out stays there
                return subprocess.CompletedProcess(cmd, 1)
            dur = float(re.search(r'data-duration="([0-9.]+)"', (proj / "index.html").read_text()).group(1))
            out.write_text(str(round(dur * int(cmd[cmd.index("--fps") + 1]))))
            return subprocess.CompletedProcess(cmd, 0)
        if cmd[0] == "ffprobe":                                    # frames(): the count a stub chunk holds
            return subprocess.CompletedProcess(cmd, 0, stdout=Path(cmd[-1]).read_text() + "\n", stderr="")
        if cmd[0] == "ffmpeg":                                     # the join: the chunks' counts added up
            parts = re.findall(r"file '(.+)'", Path(cmd[cmd.index("-i") + 1]).read_text())
            Path(cmd[-1]).write_text(str(sum(int(Path(p).read_text()) for p in parts)))
            joined.append(cmd[-1])
            return subprocess.CompletedProcess(cmd, 0)
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(subprocess, "run", run)
    for name, value in {"CHUNK": 1.0, "FPS": 10, "RESOLUTION": "4k", "WORKERS": "1"}.items():
        monkeypatch.setattr(R, name, value)

    def go(only=()):
        """One render4k run on the page; the chunks it rendered."""
        rendered.clear()
        joined.clear()
        monkeypatch.setattr(R, "ONLY", set(only))
        monkeypatch.setattr(sys, "argv", ["render4k.py", str(hf)])
        R.main()
        return list(rendered)

    return SimpleNamespace(hf=hf, chunks=hf.resolve().parent / "renders/chunks", go=go, rendered=rendered,
                           joined=joined, failing=failing)


def edit_page(film):
    page = film.hf / "index.html"
    page.write_text(page.read_text().replace("take one", "take two"))


def later(p, seconds=1):
    st = p.stat()
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + seconds * 10**9))


def test_an_unchanged_page_skips_every_finished_chunk(film, capsys):
    assert film.go() == CHUNKS
    assert sorted(p.name for p in film.chunks.glob("*.key")) == ["c00.key", "c01.key", "c02.key"]
    capsys.readouterr()
    assert film.go() == []
    assert capsys.readouterr().out.count("done already (its key matches)") == 3
    assert film.joined and (film.chunks.parent / "raw.mp4").read_text() == "25"     # still joined: 10 + 10 + 5


def test_a_rebuild_of_the_same_page_still_skips(film):
    # kit/film/build.py runs before every render: the same page text, vendor/ written again (a new mtime, the same bytes),
    # the film's assets copied with copy2 (size and mtime kept); and a Finder visit leaves a .DS_Store
    film.go()
    for f in (film.hf / "index.html", film.hf / "vendor/gsap.min.js"):
        f.write_bytes(f.read_bytes())
        later(f, 5)
    face, tmp = film.hf / "assets/face.mp4", film.hf / "face.tmp"
    shutil.copy2(face, tmp)
    os.replace(tmp, face)
    (film.hf / "assets/.DS_Store").write_bytes(b"finder")
    assert film.go() == []


def test_an_edited_page_renders_every_chunk_again(film, capsys):
    film.go()
    edit_page(film)
    capsys.readouterr()
    assert film.go() == CHUNKS
    assert capsys.readouterr().out.count("(re-render: the page changed)") == 3


@pytest.mark.parametrize("change, why", [
    (lambda hf: later(hf / "assets/face.mp4"), "assets/ changed"),                     # re-graded: same size, later mtime
    (lambda hf: (hf / "assets/clips/c01.mp4").write_bytes(b"clip one, remade"), "assets/ changed"),
    (lambda hf: (hf / "assets/clips/c02.mp4").write_bytes(b"clip two"), "assets/ changed"),
    (lambda hf: later(hf / "assets/broll/cafe.mp4"), "assets/ changed"),               # inside a linked folder
    (lambda hf: (hf / "vendor/gsap.min.js").write_text("/* gsap 4 */"), "vendor/ changed"),
], ids=["regraded-face", "remade-clip", "new-clip", "linked-broll", "vendor-bytes"])
def test_a_changed_asset_renders_every_chunk_again(film, capsys, change, why):
    film.go()
    change(film.hf)
    capsys.readouterr()
    assert film.go() == CHUNKS
    assert capsys.readouterr().out.count(f"(re-render: {why})") == 3


def test_other_render_args_render_every_chunk_again(film, monkeypatch, capsys):
    film.go()
    monkeypatch.setattr(R, "RESOLUTION", "portrait-4k")
    capsys.readouterr()
    assert film.go() == CHUNKS
    assert capsys.readouterr().out.count("(re-render: the render args changed)") == 3


@pytest.mark.parametrize("spoil, why", [
    (lambda key: key.unlink(), "no c01.key"),                      # a chunk from before keys, or from a stopped render
    (lambda key: key.write_text("{"), "c01.key unreadable"),
])
def test_a_chunk_without_its_key_renders_again(film, capsys, spoil, why):
    film.go()
    spoil(film.chunks / "c01.key")
    capsys.readouterr()
    assert film.go() == [1]                                        # though c01.mp4 has all 10 frames
    out = capsys.readouterr().out
    assert f"chunk 1: 1.000-2.000 (10 frames) -> c01.mp4 (re-render: {why})" in out
    assert out.count("done already") == 2


def test_a_stopped_render_resumes_without_the_old_picture(film):
    film.go()
    edit_page(film)
    film.failing.add(1)
    with pytest.raises(SystemExit, match="chunk 1 failed"):
        film.go()
    assert film.rendered == [0, 1]
    # c01.mp4 still holds the first page's picture with all its frames: its key went before the render, so it can't stand
    assert (film.chunks / "c01.mp4").exists() and not (film.chunks / "c01.key").exists()
    film.failing.clear()
    assert film.go() == [1, 2]                                     # chunk 0, finished on the new page, is kept


def test_only_renders_the_named_chunks_and_keys_them(film, capsys):
    film.go()
    edit_page(film)
    capsys.readouterr()
    assert film.go(only=[1]) == [1] and not film.joined            # --only: no join
    assert capsys.readouterr().out.count("skipped") == 2
    assert film.go(only=[1]) == []                                 # its key is the new page's now
    assert film.go() == [0, 2]
