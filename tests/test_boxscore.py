"""Box-score bookkeeping (engine/boxscore.py): it changes no outcome, and its counts are consistent.

1. 300 games played with the bookkeeping on and off give identical event logs (sha256 of every game's log) and identical
   scores: the bookkeeping draws nothing and feeds no decision.
2. Consistency over the same 300 games: runs credited to batters equal the runs scored; every decided game has exactly one
   win and one loss (on opposite teams; the winner's on the winning team) and at most one save, never to the winner;
   runs batted in never exceed runs; stolen bases plus caught stealing never exceed the attempts the box score counts.
"""
from __future__ import annotations

import copy
import hashlib

import numpy as np
import pytest

from config import box as box_cfg
from config import phase2
from engine.game2 import B_CS, B_NCOL, B_R, B_RBI, B_SB, P_HLD, P_L, P_NCOL, P_SV, P_W, GameSession, PlayerGameEngine
from engine.league import build_league
from engine.manager import Manager
from engine.schedule import make_schedule

N_GAMES = 300


def _gen(ss):
    return np.random.Generator(np.random.PCG64(ss))


@pytest.fixture(scope="module")
def world():
    cfg = phase2.load()
    a, b, c = np.random.SeedSequence(20261009).spawn(3)
    lg = build_league(cfg, _gen(a))
    sch = make_schedule(cfg, lg, _gen(b))
    return cfg, lg, list(zip(sch[:N_GAMES], c.spawn(N_GAMES)))


def _play(world, enabled: bool):
    cfg, lg, games = world
    old = box_cfg.ENABLED
    box_cfg.ENABLED = enabled
    try:
        n = len(lg.players)
        eng = PlayerGameEngine(cfg, lg, [[0] * B_NCOL for _ in range(n)], [[0] * P_NCOL for _ in range(n)])
        mgr = Manager(cfg)
        out = []
        for g, gs in games:
            s = GameSession(eng, _gen(gs), lg.teams[g.home], lg.teams[g.away], g.weekend, mgr, week=g.week, day=g.day,
                            date=g.date, log=True)
            s.run()
            out.append((hashlib.sha256(repr(s.log).encode()).hexdigest(), dict(s.st.score), copy.copy(s.st.box),
                        s.st.team_obj["home"].tid, s.st.team_obj["away"].tid, dict(s.st.sb_att)))
        return out, np.array(eng.bstats), np.array(eng.pstats)
    finally:
        box_cfg.ENABLED = old


@pytest.fixture(scope="module")
def runs(world):
    return _play(world, True), _play(world, False)


def test_logs_identical_with_and_without_bookkeeping(runs):
    (on, b_on, p_on), (off, b_off, p_off) = runs
    assert [x[0] for x in on] == [x[0] for x in off]
    assert [x[1] for x in on] == [x[1] for x in off]
    # every older column of the accumulators is identical too; the box columns are zero when off
    assert np.array_equal(b_on[:, :B_R], b_off[:, :B_R]) and np.array_equal(p_on[:, :P_W], p_off[:, :P_W])
    assert not b_off[:, B_R:].any() and not p_off[:, P_W:].any()


def test_box_counts_consistent(world, runs):
    (on, b, p), _ = runs
    _, lg, _ = world
    team_of = np.array([pl.team for pl in lg.players])
    runs_scored = {}
    attempts = {}
    for _h, score, box, home, away, sb_att in on:
        runs_scored[home] = runs_scored.get(home, 0) + score["home"]
        runs_scored[away] = runs_scored.get(away, 0) + score["away"]
        attempts[home] = attempts.get(home, 0) + sb_att["home"]
        attempts[away] = attempts.get(away, 0) + sb_att["away"]
        d = box.decisions
        assert d is not None
        win, lose = (home, away) if score["home"] > score["away"] else (away, home)
        assert lg.players[d["W"]].team == win and lg.players[d["L"]].team == lose
        assert d["SV"] is None or (d["SV"] != d["W"] and lg.players[d["SV"]].team == win)
        assert not set(d["HLD"]) & {d["W"], d["L"], d["SV"]}
    for t, r in runs_scored.items():
        assert b[team_of == t, B_R].sum() == r
        assert b[team_of == t, B_RBI].sum() <= r
        assert b[team_of == t, B_SB].sum() + b[team_of == t, B_CS].sum() <= attempts[t]
    assert p[:, P_W].sum() == p[:, P_L].sum() == len(on)
    assert p[:, P_SV].sum() <= len(on)
    # plausible shares (a sanity band, not a gate): most runs are batted in; saves in a minority of games
    assert 0.6 < b[:, B_RBI].sum() / b[:, B_R].sum() < 0.98
    assert 0.1 < p[:, P_SV].sum() / len(on) < 0.6
    assert p[:, P_HLD].sum() > 0
