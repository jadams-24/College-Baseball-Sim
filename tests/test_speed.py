"""Speed pass (2026-10-09): the rewritten hot paths compute exactly what they replaced, and the report-only accumulators
(config.diagnostics) change no game.

1. The pitch chain's rewrites against the straightforward forms they replaced, bit for bit, on random tilts: the one-pass
   absorption of K, BB and HBP against absorb(), chain_array's ufunc sum against ndarray.sum, absorb_matrix's direct
   LAPACK call against np.linalg.solve, forward's ufunc accumulate against np.cumsum.
2. 300 games with the diagnostics on and off: identical event logs and identical batting and pitching lines (box-score
   columns included). scripts/check_log_identity.py compares the logs across commits (the same 300 games).
"""
from __future__ import annotations

import hashlib

import numpy as np
import pytest

from config import diagnostics
from config import phase2
from config.phase5 import EVENTS, OUTCOMES, load, load_solved
from engine import pitch as P
from engine.game2 import B_NCOL, P_NCOL, GameSession, PlayerGameEngine
from engine.league import build_league
from engine.manager import Manager
from engine.schedule import make_schedule

N_GAMES = 300


@pytest.fixture(scope="module")
def pm():
    return P.PitchModel(load(), load_solved())


def test_pitch_chain_rewrites_bit_identical(pm):
    rng = np.random.default_rng(20261009)
    for _ in range(2000):
        t = rng.normal(0.0, 0.8, len(EVENTS))
        q0 = pm.q0 * np.exp(t)[None, :]
        q_ref = q0 / q0.sum(axis=1, keepdims=True)
        q = pm.chain_array(t)
        assert np.array_equal(q, q_ref) and pm.chain(t) == q_ref.tolist()
        ql = q.tolist()
        assert pm._absorb3(ql) == (pm.absorb(ql, P.O_K)[0], pm.absorb(ql, P.O_BB)[0], pm.absorb(ql, P.O_HBP)[0])
        qs = pm.slots(q)
        T = np.bincount(P._T_IDX, weights=qs[P._TO], minlength=144).reshape(12, 12)
        R = np.bincount(P._R_IDX, weights=qs[~P._TO], minlength=12 * len(OUTCOMES)).reshape(12, len(OUTCOMES))
        h = pm.absorb_matrix(qs)
        assert np.array_equal(h, np.linalg.solve(np.eye(12) - T, R))
        m = rng.dirichlet(np.ones(len(OUTCOMES)))
        w = np.divide(m, h[0], out=np.zeros_like(m), where=h[0] > 0)
        H = h @ w
        W = qs * np.concatenate([H, w])[P._V_IDX] / H[:, None]
        assert pm.forward(qs, h, m) == np.cumsum(W, axis=1).tolist()


def _gen(ss):
    return np.random.Generator(np.random.PCG64(ss))


def _play(record: bool):
    old = diagnostics.RECORD
    diagnostics.RECORD = record
    try:
        cfg = phase2.load()
        a, b, c = np.random.SeedSequence(20261009).spawn(3)
        lg = build_league(cfg, _gen(a))
        sch = make_schedule(cfg, lg, _gen(b))
        n = len(lg.players)
        eng = PlayerGameEngine(cfg, lg, [[0] * B_NCOL for _ in range(n)], [[0] * P_NCOL for _ in range(n)])
        mgr = Manager(cfg)
        logs = []
        for g, gs in zip(sch[:N_GAMES], c.spawn(N_GAMES)):
            s = GameSession(eng, _gen(gs), lg.teams[g.home], lg.teams[g.away], g.weekend, mgr, week=g.week, day=g.day,
                            date=g.date, log=True)
            s.run()
            logs.append(hashlib.sha256(repr(s.log).encode()).hexdigest())
        return logs, np.array(eng.bstats), np.array(eng.pstats), eng
    finally:
        diagnostics.RECORD = old


def test_diagnostics_off_plays_identical_games():
    on_logs, on_b, on_p, on_eng = _play(True)
    off_logs, off_b, off_p, off_eng = _play(False)
    assert on_logs == off_logs
    assert np.array_equal(on_b, off_b) and np.array_equal(on_p, off_p)
    # the switch does what it says: the report-only tables stay empty when off
    assert on_eng.exp_trials.any() and not off_eng.exp_trials.any()
    assert on_eng.pitch_rec["n_pa"] > 0 and off_eng.pitch_rec["n_pa"] == 0
