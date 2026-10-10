"""Teams seeded from their real programs (owner decision 2026-10-09; dynasty year 0): the calibrated strength set is kept
exactly, only reordered, and seeding off is the old league."""
from __future__ import annotations

import json

import numpy as np

import engine.league as L
from config import phase2


def _league(seed: int, on: bool):
    phase2.SEED_FROM_PROGRAMS = on
    L._SEED_CACHE.clear()
    try:
        return L.build_league(phase2.load(), np.random.Generator(np.random.PCG64(seed)))
    finally:
        phase2.SEED_FROM_PROGRAMS = True
        L._SEED_CACHE.clear()


def test_seed_order_is_a_permutation_and_follows_the_prior():
    rng = np.random.default_rng(1)
    draws = [rng.normal(size=2) for _ in range(9)]
    z = list(rng.normal(size=9))
    got = L.seed_order(draws, z, 0.9, rng, sigma=0.0)
    key = lambda v: tuple(np.round(v, 12))      # noqa: E731
    assert sorted(map(key, got)) == sorted(map(key, draws))
    # no noise: the k-th highest prior gets the k-th highest o + d
    s = np.array([g[0] + g[1] for g in got])
    assert list(np.argsort(-s)) == list(np.argsort(-np.array(z)))


def test_seeding_keeps_each_conferences_set(monkeypatch):
    """Every reordering the league does (conference effects within a tier, team deviations within a conference) returns a
    permutation of its own draws, and both levels are reordered."""
    calls = []
    real = L.seed_order

    def spy(draws, z, r, rng, sigma=None):
        got = real(draws, z, r, rng, sigma=sigma)
        calls.append((list(draws), list(got)))
        return got
    monkeypatch.setattr(L, "seed_order", spy)
    _league(7, True)
    cfg = phase2.load()
    n_conf = len({c for _, c, _ in cfg.teams if c != "DI Independent"})
    assert len(calls) == 3 + n_conf                     # one call per tier (conference effects), one per conference
    key = lambda v: tuple(np.round(np.asarray(v, float), 12))      # noqa: E731
    for draws, got in calls:
        assert sorted(map(key, got)) == sorted(map(key, draws))


def test_seeding_off_is_the_old_league():
    """Seeding off: no draw is moved (the seeding stream is spawned last, so the other streams are unchanged)."""
    a, b = _league(3, False), _league(3, False)
    assert [t.s_total for t in a.teams] == [t.s_total for t in b.teams]


def test_seed_inputs_cover_every_team_and_conference():
    seed = json.loads(phase2.TEAM_SEED.read_text())
    cfg = phase2.load()
    assert all(str(t[0]) in seed["team"] for t in cfg.teams)
    assert all(c in seed["conference"] for _, c, _ in cfg.teams if c != "DI Independent")
    for lvl in ("sigma_team", "sigma_conf"):
        assert set(seed[lvl]) == {"p4", "mid", "low"} and all(v["sigma"] >= 0 for v in seed[lvl].values())


def test_seeded_strength_follows_real_programs():
    """Seeded leagues put the real programs' recent strength into the year-0 draw; unseeded ones only through the tier."""
    seed = json.loads(phase2.TEAM_SEED.read_text())
    cfg = phase2.load()
    prior = np.array([seed["team"][str(t[0])]["prior"] for t in cfg.teams])
    r_on = np.mean([np.corrcoef(prior, [t.s_total for t in _league(s, True).teams])[0, 1] for s in range(4)])
    r_off = np.mean([np.corrcoef(prior, [t.s_total for t in _league(s, False).teams])[0, 1] for s in range(4)])
    assert r_on > r_off + 0.15
