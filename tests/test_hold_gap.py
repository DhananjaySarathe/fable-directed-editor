"""kit/film/cut.py hold_gap: a scene in film.py HOLD_GAP holds its last frame to the next scene (and through the tail);
jump cuts inside a scene still play on."""
from types import SimpleNamespace

from kit.film.cut import hold_gap

P = [dict(tag="cold"), dict(tag="cold"), dict(tag="hook"), dict(tag="hook"), dict(tag="chakra")]


def test_only_the_scene_end_of_a_held_tag_holds():
    Fm = SimpleNamespace(HOLD_GAP={"cold", "chakra"})
    assert [hold_gap(Fm, P, k) for k in range(len(P))] == [False, True, False, False, True]


def test_true_holds_every_scene_end_and_empty_holds_none():
    assert [hold_gap(SimpleNamespace(HOLD_GAP=True), P, k) for k in range(len(P))] == [False, True, False, True, True]
    assert not any(hold_gap(SimpleNamespace(HOLD_GAP=set()), P, k) for k in range(len(P)))
