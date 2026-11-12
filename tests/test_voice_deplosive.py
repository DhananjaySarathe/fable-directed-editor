"""kit/film/prep.py measured_chain (2026-10-23, v11-sample draft 1: a plosive on "stop." 23 dB over its surroundings
under 100 Hz): v11 films get a 4-pole 90 Hz high-pass after the measured EQ; older films' chain is unchanged."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kit.film import prep  # noqa: E402


def fm(tmp_path, v11):
    (tmp_path / "voice_eq.json").write_text(json.dumps({"1": {"63": -1.8, "100": 0.0}, "gain1": 2.0}))
    return SimpleNamespace(work=tmp_path, _v11_voice=v11)


def test_v11_chain_high_passes_after_the_eq(tmp_path):
    ch = prep.measured_chain(fm(tmp_path, True), 1)
    eq_at, hp_at = ch.index("firequalizer"), ch.index(f"highpass=f={prep.DEPLOSIVE_HZ},highpass=f={prep.DEPLOSIVE_HZ}")
    assert eq_at < hp_at < ch.index("deesser") and "highpass=f=70" in ch


def test_older_films_keep_their_chain(tmp_path):
    ch = prep.measured_chain(fm(tmp_path, False), 1)
    assert f"highpass=f={prep.DEPLOSIVE_HZ}" not in ch and "highpass=f=70,firequalizer" in ch
