"""kit/film/render.py ambition_of (v11 fix P-M3): precheck's ambition gate defaults by the film's date, so a film
delivered before the v11 gates re-renders without --no-ambition; AMBITION in film.py and the command line win."""
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kit.film import mix as MX, render  # noqa: E402


def test_by_date_then_film_py_then_command_line(monkeypatch):
    monkeypatch.setattr(MX, "made_on", lambda Fm: Fm.day)
    old, new = SimpleNamespace(AMBITION=None, day="2026-10-21"), SimpleNamespace(AMBITION=None, day=MX.V11_FROM)
    assert render.ambition_of(old)[0] is False and render.ambition_of(new)[0] is True
    assert render.ambition_of(SimpleNamespace(AMBITION=True, day="2026-10-01")) == (True, "AMBITION = True in film.py")
    assert render.ambition_of(new, False) == (False, "--no-ambition") and render.ambition_of(old, True) == (True, "--ambition")
