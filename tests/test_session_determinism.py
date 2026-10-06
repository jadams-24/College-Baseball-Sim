"""Game sessions: pause before any pitch, save and restore, switch who manages a team, sim ahead (engine
restructure, 2026-10-06; owner condition: the four-part determinism test).

1. Pause and restore: every game played uninterrupted and, separately, paused at a random pitch, saved, the
   original discarded, restored and resumed, gives the identical pitch-by-pitch event log. A few games are saved
   whole (engine included) and resumed in a fresh Python process.
2. Control switch: a scripted human who gives the answers the AI would give takes over random teams at random
   pitches and hands back (AI -> human -> AI), with sim-ahead stops in between; the log is identical to the
   uninterrupted AI game.
3. Equal odds: the same decisions given by a human controller and by an AI manager are resolved identically (the
   engine never sees who decided).
4. The 2-0 steal: a game can stop before a 2-0 pitch with a runner on first and second base open, and resume.
   Calling the steal there is PR B (steals become a pitch-level decision); that part is skipped here.
"""
from __future__ import annotations

import copy
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

from config import phase2
from engine.control import AIController, Controller
from engine.decider import Decision
from engine.game2 import B_NCOL, P_NCOL, STOPS, GameSession, PlayerGameEngine
from engine.league import build_league
from engine.manager import Manager
from engine.schedule import make_schedule

ROOT = Path(__file__).resolve().parents[1]
N_GAMES = 200          # games per test
N_FRESH_PROCESS = 3    # games resumed in a fresh process (full saves, engine included)


def _gen(ss):
    return np.random.Generator(np.random.PCG64(ss))


@pytest.fixture(scope="module")
def world():
    cfg = phase2.load()
    a, b, c = np.random.SeedSequence(20261006).spawn(3)
    lg = build_league(cfg, _gen(a))
    sch = make_schedule(cfg, lg, _gen(b))
    n = len(lg.players)
    eng = PlayerGameEngine(cfg, lg, [[0] * B_NCOL for _ in range(n)], [[0] * P_NCOL for _ in range(n)])
    mgr = Manager(cfg)
    games = list(zip(sch[:N_GAMES], c.spawn(N_GAMES)))
    return eng, mgr, lg, games


def _session(world, i, mgr=None, controllers=None):
    """A new session at the start of game i, with its own copy of the manager's season state."""
    eng, mgr0, lg, games = world
    g, gs = games[i]
    m = mgr if mgr is not None else copy.deepcopy(mgr0)
    return GameSession(eng, _gen(gs), lg.teams[g.home], lg.teams[g.away], g.weekend, m, week=g.week, day=g.day, date=g.date,
                       controllers=controllers(m) if controllers else None, log=True)


def _uninterrupted(world, i):
    s = _session(world, i)
    s.run()
    return s.log


def _pitches_in(log) -> int:
    return sum(1 for e in log if e[0] == "p")


class MirrorHuman(Controller):
    """A scripted human who answers what the AI would answer (he asks it, at the same decision point)."""

    def __init__(self, dec):
        self.ai = AIController(dec)

    def answer(self, kind, state, rng, *args):
        return self.ai.answer(kind, state, rng, *args)


# ---- 1. pause and restore ------------------------------------------------------------------
def test_pause_save_restore(world):
    eng = world[0]
    rng = np.random.default_rng(1)
    for i in range(N_GAMES):
        ref = _uninterrupted(world, i)
        k = int(rng.integers(0, _pitches_in(ref)))
        s = _session(world, i)
        pt = s.run(lambda x, k=k: _pitches_in(x.log) >= k)
        assert pt is not None and pt["count"] is not None
        blob = s.save(include_engine=False)
        del s                                       # the original is discarded
        r = GameSession.load(blob, engine=eng)
        assert r.run() is None
        assert r.log == ref, f"game {i}: resumed log differs from the uninterrupted game (paused before pitch {k})"


def test_restore_in_fresh_process(world):
    rng = np.random.default_rng(2)
    for i in range(N_FRESH_PROCESS):
        ref = _uninterrupted(world, i)
        k = int(rng.integers(0, _pitches_in(ref)))
        s = _session(world, i)
        s.run(lambda x, k=k: _pitches_in(x.log) >= k)
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "save.pkl"
            f.write_bytes(s.save())                  # complete save: engine and season accumulators included
            code = ("import sys, hashlib, pickle; sys.path.insert(0, %r); from engine.game2 import GameSession; "
                    "s = GameSession.load(open(%r, 'rb').read()); s.run(); "
                    "print(hashlib.sha256(repr(s.log).encode()).hexdigest())") % (str(ROOT), str(f))
            out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.strip()
        assert out == hashlib.sha256(repr(ref).encode()).hexdigest(), f"game {i}: fresh-process resume differs"


# ---- 2. control switch -----------------------------------------------------------------------
def test_control_switch_and_sim_ahead(world):
    rng = np.random.default_rng(3)
    for i in range(N_GAMES):
        ref = _uninterrupted(world, i)
        s = _session(world, i)
        mgr = s.book
        ai = {side: s.ctrl[side] for side in ("away", "home")}
        human = {side: MirrorHuman(mgr) for side in ("away", "home")}
        while s.phase != "over":
            pt = s.sim_ahead(STOPS[int(rng.integers(0, len(STOPS) - 1))],      # never "game" before the last step
                             ai_side=str(rng.choice(["away", "home"])) if rng.random() < .5 else None, ai=AIController(mgr))
            if pt is None:
                break
            side = str(rng.choice(["away", "home"]))
            s.set_controller(side, human[side] if s.ctrl[side] is ai[side] else ai[side])
            if rng.random() < .1:
                s.run()
        assert s.log == ref, f"game {i}: switching control changed the game"


def test_sim_ahead_stops(world):
    s = _session(world, 0)
    pt = s.run(lambda x: True)                      # the first pitch
    assert pt["pa_serial"] == 1 and pt["count"] == (0, 0)
    pt2 = s.sim_ahead("pa")
    assert pt2["pa_serial"] == 2 and pt2["count"] == (0, 0)
    pt3 = s.sim_ahead("half")
    assert (pt3["inning"], pt3["half"]) == (1, "B")
    pt4 = s.sim_ahead("inning")
    assert (pt4["inning"], pt4["half"]) == (2, "B")
    pt5 = s.sim_ahead("three_innings")
    assert (pt5["inning"], pt5["half"]) == (5, "B")
    assert s.sim_ahead("game") is None and s.phase == "over"


# ---- 3. equal odds -------------------------------------------------------------------------
class _Policy:
    """A fixed policy: no pinch hitters, no pinch runners, no defensive changes; the pitcher stays in until 100
    pitches, then the AI picks the reliever."""

    @staticmethod
    def decide(kind, state, base):
        if kind in ("pinch_hit", "pinch_runner"):
            return None
        if kind == "defensive_subs":
            return []
        if kind == "pitching_change":
            o = state.outing[state.fielding_side]
            return Decision.YES if o["pitches"] >= 100 and state.bullpen_left(state.fielding_side) else Decision.NO
        return base()


class PolicyHuman(Controller):
    def __init__(self, dec):
        self.ai = AIController(dec)

    def answer(self, kind, state, rng, *args):
        return _Policy.decide(kind, state, lambda: self.ai.answer(kind, state, rng, *args))


class PolicyManager(Manager):
    """The same policy as an AI manager."""

    def pinch_hit(self, state, team, slot):
        return None

    def pinch_runner(self, state, team, slot):
        return None

    def defensive_subs(self, state, team):
        return []

    def pitching_change(self, state):
        return _Policy.decide("pitching_change", state, None)


def test_equal_odds_human_and_ai(world):
    eng, mgr0, lg, games = world
    for i in range(N_GAMES // 2):
        human = _session(world, i, controllers=lambda m: {s: PolicyHuman(m) for s in ("away", "home")})
        human.run()
        pm = PolicyManager.__new__(PolicyManager)
        pm.__dict__.update(copy.deepcopy(mgr0).__dict__)
        ai = _session(world, i, mgr=pm)
        ai.run()
        assert human.log == ai.log, f"game {i}: the same decisions resolved differently for a human and the AI"


# ---- 4. the 2-0 steal ---------------------------------------------------------------------
def _at_2_0_runner_on_first(x) -> bool:
    return x.pa["b"] == 2 and x.pa["s"] == 0 and x.st.bases[0] is not None and x.st.bases[1] is None


def test_pause_before_2_0_pitch_with_runner_on_first(world):
    eng = world[0]
    for i in range(N_GAMES):
        s = _session(world, i)
        pt = s.run(_at_2_0_runner_on_first)
        if pt is None:
            continue
        assert pt["count"] == (2, 0) and pt["bases"][0] == "1" and pt["bases"][1] == "0"
        r = GameSession.load(s.save(include_engine=False), engine=eng)
        assert r.point() == pt
        r.run()
        return
    pytest.fail("no 2-0 count with a runner on first and second open in the sample")


@pytest.mark.skip(reason="PR B: steals become a pitch-level decision; the called steal on 2-0 goes live there")
def test_steal_on_2_0():
    raise NotImplementedError
