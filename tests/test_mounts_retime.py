"""kit/hf/mounts.py: a mount's dur retimes its catalog piece, so the piece never exits early with its box on screen."""
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1] / "kit"
sys.path.insert(0, str(KIT / "hf"))
import mounts  # noqa: E402


def test_retimed_changes_only_the_pieces_own_length():
    text = ('<html data-composition-duration="3.5"><div id="root" data-duration="3.5">'
            '<div class="clip" data-start="0" data-duration="3.5"></div><i data-duration="0.6"></i></div></html>')
    out = mounts.retimed(text, 3.5, 4.8)
    assert out.count('"4.8"') == 3
    assert 'data-duration="0.6"' in out and '"3.5"' not in out


def test_piece_file_copies_as_is_or_retimed(tmp_path):
    own = mounts.own_length(mounts.manifest()["marker-highlight"])
    assert own == 3.5
    same = mounts.piece_file(tmp_path, 0, dict(name="marker-highlight", dur=3.5))
    longer = mounts.piece_file(tmp_path, 1, dict(name="marker-highlight", dur=4.8))
    assert same == "marker-highlight.html" and longer == "marker-highlight--m1.html"
    html = (tmp_path / "compositions/catalog" / longer).read_text()
    assert 'id="root" data-composition-id="marker-highlight" data-duration="4.8"' in html


def test_install_points_each_mount_at_its_file(tmp_path):
    tpl = '<div id="root" data-composition-id="film" data-start="0"></div>'
    out = mounts.install(tmp_path, [dict(name="push-in", vars=dict(text="Read the diff")),
                                    dict(name="push-in", dur=6, vars=dict(text="Then ship"))], [1.0, 5.0], tpl, look="canvas_studio")
    assert 'data-composition-src="compositions/catalog/push-in.html"' in out
    assert 'data-composition-src="compositions/catalog/push-in--m1.html" data-start="5.0000" data-duration="6.0000"' in out


def test_look_of_reads_the_frames_look_option_and_its_accent(tmp_path):
    """E-M4: a whitespace canvas (the v11 default) is read as whitespace, not as canvas_studio from HF.canvas, the same
    way kit/hf/tools/registry.py does; its palette acc re-accents a mounted catalog piece (one accent on the page)."""
    tpl = ('<div id="root" data-composition-id="film" data-start="0"></div><script>'
           'const C = HF.canvas(K, ROOT, { w: 5760, look: "whitespace", palette: { acc: "#0A7CFF" } });</script>')
    assert mounts.look_of(tpl) == "whitespace"
    assert mounts.look_of("const S = HF.studio(K, ROOT, st, { end: 9, look: 'whitespace' });") == "whitespace"
    assert mounts.look_of("const C = HF.canvas(K, ROOT, { w: 5760 });") == "canvas_studio"   # no look: the frame's own
    assert mounts.look_of('HF.look("paper_collage"); const C = HF.canvas(K, ROOT, { look: "whitespace" });') == "paper_collage"
    assert mounts.palette_accent(tpl, "whitespace") == "#0A7CFF" and mounts.palette_accent(tpl, "canvas_studio") is None
    out = mounts.install(tmp_path, [dict(name="agent-cursor")], [1.0], tpl)
    assert "#0A7CFF" in out and mounts.look_accent("whitespace") not in out
    plain = mounts.install(tmp_path, [dict(name="agent-cursor")], [1.0], tpl.replace(', palette: { acc: "#0A7CFF" }', ""))
    assert mounts.look_accent("whitespace") in plain                 # no palette: the look's own accent token
