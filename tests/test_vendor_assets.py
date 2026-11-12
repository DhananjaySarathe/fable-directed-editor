"""kit/hf/vendor.py's 2026-10-20 assets: only the emoji a page names are inlined, and the new libraries are vendored."""
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1] / "kit"
sys.path.insert(0, str(KIT / "hf"))
import vendor  # noqa: E402

PAGE = """<html><head><!--HF:KIT--></head><body><script>
HF.emoji(K, L, "fire", 2.0, { x: 10 }); HF.emoji(K, L2, 'mind-blown', 3.0);
</script></body></html>"""


def test_inline_adds_only_the_emoji_a_page_names():
    html = vendor.inline(PAGE, stickman=False)
    assert vendor.emoji_used(PAGE) == ["fire", "mind-blown"]
    block = next(ln for ln in html.splitlines() if ln.startswith("HF.EMOJI = {"))
    data = __import__("json").loads(block[len("HF.EMOJI = "):].rstrip(";"))
    assert sorted(data) == ["fire", "mind-blown"]                       # not the other 49 in kit/emoji/noto


def test_a_missing_emoji_fails_the_build_with_the_names_there_are():
    with pytest.raises(SystemExit, match="no kit/emoji/noto/unicorn.json"):
        vendor.emoji_used('HF.emoji(K, L, "unicorn", 1)')


def test_new_libraries_are_vendored_and_in_the_page():
    names = [n for _, n, _ in vendor.LIBS]
    for n in ("MorphSVGPlugin.min.js", "CustomWiggle.min.js", "paper-shaders.js", "lottie_light.min.js"):
        assert n in names
    html = vendor.inline("<head><!--HF:KIT--></head>", stickman=False)
    assert 'src="vendor/paper-shaders.js"' in html and "HF.shaderBg" in html and "HF.LUCIDE" in html


@pytest.mark.skipif(__import__("shutil").which("node") is None, reason="needs node")
def test_new_modules_parse():
    import subprocess
    for m in ("shaders.js", "emoji.js", "lucide.js", "parallax.js", "kinetic.js", "core.js"):
        r = subprocess.run(["node", "--check", str(KIT / "hf" / m)], capture_output=True, text=True)
        assert r.returncode == 0, (m, r.stderr[-300:])
