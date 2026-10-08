"""The UI connector (app/connector.py) against the engine run directly (owner conditions, 2026-10-08).

1. The two-team exhibition engine plays the same game as the full-league engine.
2. Autopilot with no orders is the AI's game: the runner, stepping with random sim targets, gives the same event
   log as PlayerGameEngine.play with the AI manager (equal odds through the connector).
3. Questions ("ask me" on every kind): a scripted policy answers every question through the runner; the same
   policy, as a Controller answering the engine directly, gives the same log. Random sim targets.
4. Orders at boundaries (the default, non-blocking flow): the policy's orders for a window are queued at the
   boundary stop; the same orders given by a scripted Controller at its first ask of each window give the same log.
5. Save and load replay identically, in-process at random steps and in a fresh process.
6. The catalogue covers every kind in engine.control.DECISIONS; values round-trip through validation.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

from app import catalogue as cat
from app.connector import GameRunner, window_of
from app.world import World
from engine.control import DECISIONS, AIController, Controller
from engine.game2 import STOPS, GameSession
from engine.manager import Manager

ROOT = Path(__file__).resolve().parents[1]
N_GAMES = 12
PAIRS = [(5, 200), (12, 61), (300, 7), (150, 151), (64, 65), (0, 306), (33, 210), (99, 100), (250, 20), (180, 45), (77, 8), (2, 130)]


@pytest.fixture(scope="module")
def world():
    return World()


# ---- 1. the runner's game is the engine's game -------------------------------------------------------
def test_runner_matches_engine_session(world):
    lg = world.league
    for i, (h, a) in enumerate(PAIRS[:4]):
        ref = GameSession(world.eng, np.random.Generator(np.random.PCG64(100 + i)), lg.teams[h], lg.teams[a], True, Manager(world.cfg),
                          week=1, day=0, date=11, log=True)
        ref.run()
        r = GameRunner.new(world, h, a, "home", 100 + i)
        r.step("game")
        assert r.base.log == ref.log


# ---- 2. autopilot is the AI's game ------------------------------------------------------------------
def _ai_game(world, h, a, seed):
    r = GameRunner.new(world, h, a, "away", seed)        # the user side is irrelevant: no orders, all auto
    r.step("game")
    return r.base.log


def test_autopilot_equals_ai(world):
    rng = np.random.default_rng(1)
    for i, (h, a) in enumerate(PAIRS):
        ref = _ai_game(world, h, a, 200 + i)
        r = GameRunner.new(world, h, a, str(rng.choice(["home", "away"])), 200 + i)
        while not r.over:
            r.step(STOPS[int(rng.integers(0, len(STOPS)))])
            if rng.random() < .2:
                r.recommend()                              # the bench coach never touches the live game
        assert r.base.log == ref, f"game {i}"
        assert r.marks() and r.base.st.score == {"away": ref[-1][2], "home": ref[-1][3]}
        lines = r.lines()
        assert sum(lines[p][0][1] for p in lines) == r.base.st.pa["away"] + r.base.st.pa["home"]     # PA by batter = PA in the game


# ---- a scripted policy, usable through the runner and as a Controller -----------------------------------
class Policy:
    """Deterministic in the state at the ask (what both paths see)."""

    @staticmethod
    def value(kind, state, side):
        w = window_of(state)
        bench = cat.bench(state, side)
        unused = cat.unused_pitchers(state, side)
        if kind == "pitching_change":
            o = state.outing.get(side)
            return {"yes": True, "reliever": unused[0].pid} if o and o["pitches"] >= 70 and unused else "no"
        if kind == "relief_pitcher":
            return "auto"                                  # the reliever comes with the pitching change
        if kind == "pinch_hit":
            return bench[-1].pid if (w % 9 == 4 and bench) else None
        if kind == "pinch_runner":
            return bench[0].pid if (w % 7 == 2 and bench) else None
        if kind == "steal_attempt":
            return "no" if state.inning % 2 else "league_rate"
        if kind == "bunt":
            return "yes" if (w % 5 == 0 and state.outs == 0) else "league_rate"
        if kind == "intentional_walk":
            return "yes" if w % 11 == 3 else "league_rate"
        if kind == "defensive_subs":
            return [[8, bench[0].pid]] if (state.inning == 7 and bench) else []
        if kind == "starting_pitcher":
            return cat.staff(state.team_obj[side])[1].pid
        return "auto"

    @classmethod
    def window_orders(cls, state, side) -> dict:
        return {k: cls.value(k, state, side) for k in DECISIONS}


class ScriptedHuman(Controller):
    """Answers the engine directly: per ask (questions mode), or from orders fixed at its first ask of each window
    with the connector's order rules (a repeating kind's order covers every ask of the window; another kind's is
    consumed by its first ask; a persistent kind's orders queue up until asked, oldest first; a pitching change
    carries its reliever)."""

    def __init__(self, side, decider, per_window: bool):
        self.side, self.ai, self.per_window = side, AIController(decider), per_window
        self.cache: dict = {}
        self.fifo: dict = {}
        self.used: set = set()

    def _value(self, kind, state):
        if not self.per_window:
            if kind == "relief_pitcher":                       # the reliever named with the pitching change, when one was
                v, self.pending_reliever = getattr(self, "pending_reliever", None), None
                return v if v is not None else "auto"
            v = Policy.value(kind, state, self.side)
            if kind == "pitching_change" and isinstance(v, dict) and v.get("yes") and v.get("reliever") is not None:
                self.pending_reliever = v["reliever"]
            return v
        w = window_of(state)
        if w not in self.cache:
            vals = self.cache[w] = Policy.window_orders(state, self.side)
            for k, v in vals.items():
                if v == "auto":
                    continue
                if cat.CATALOGUE[k].persistent:
                    self.fifo.setdefault(k, []).append(v)
                if k == "pitching_change" and isinstance(v, dict) and v.get("yes") and v.get("reliever") is not None:
                    self.fifo.setdefault("relief_pitcher", []).append(v["reliever"])
        d = cat.CATALOGUE[kind]
        if d.persistent:
            return self.fifo[kind].pop(0) if self.fifo.get(kind) else "auto"
        if not d.repeat:
            if (w, kind) in self.used:
                return "auto"
            self.used.add((w, kind))
        return self.cache[w].get(kind, "auto")

    def answer(self, kind, state, rng, *args):
        value = self._value(kind, state)
        if value == "auto":
            return self.ai.answer(kind, state, rng, *args)
        if kind == "pitching_change" and isinstance(value, dict):
            value = "yes" if value["yes"] else "no"
        try:
            return cat.CATALOGUE[kind].to_engine(value, state, self.side)
        except ValueError:
            return self.ai.answer(kind, state, rng, *args)


def _scripted_game(world, h, a, user, seed, per_window):
    home, away = world.team(h), world.team(a)
    mgr = Manager(world.cfg)
    opp = "home" if user == "away" else "away"
    s = GameSession(world.eng, np.random.Generator(np.random.PCG64(seed)), home, away, True, mgr, week=1, day=0, date=11,
                    controllers={user: ScriptedHuman(user, mgr, per_window), opp: AIController(mgr)}, log=True)
    s.run()
    return s.log


# ---- 3. questions ----------------------------------------------------------------------------------
def test_questions_match_scripted_controller(world):
    rng = np.random.default_rng(2)
    for i, (h, a) in enumerate(PAIRS):
        user = str(rng.choice(["home", "away"]))
        ref = _scripted_game(world, h, a, user, 300 + i, per_window=False)
        r = GameRunner.new(world, h, a, user, 300 + i)
        for k in DECISIONS:
            r.set_mode(k, "ask")
        tr = r.step(STOPS[int(rng.integers(0, len(STOPS)))])
        n_q = 0
        while not r.over:
            if tr["phase"] == "question":
                n_q += 1
                kind = tr["pending"]["kind"]
                tr = r.answer(kind, Policy.value(kind, r.current.st, user))
            else:
                tr = r.step(STOPS[int(rng.integers(0, len(STOPS)))])
        assert n_q > 50
        assert r.base.log == ref, f"game {i}: answers through the runner differ from the scripted controller"


# ---- 4. orders at boundaries -----------------------------------------------------------------------
def test_orders_at_boundaries_match_scripted_controller(world):
    rng = np.random.default_rng(3)
    for i, (h, a) in enumerate(PAIRS):
        user = str(rng.choice(["home", "away"]))
        ref = _scripted_game(world, h, a, user, 400 + i, per_window=True)
        r = GameRunner.new(world, h, a, user, 400 + i)
        tr = r.turn()
        for k, v in Policy.window_orders(r.current.st, user).items():       # the pregame window
            if v != "auto":
                r.queue(k, v)
        n_b = 0
        while not r.over:
            tr = r.step("pitch" if rng.random() < .5 else "pa")
            if tr["phase"] == "boundary":
                n_b += 1
                for k, v in Policy.window_orders(r.current.st, user).items():
                    if v == "auto":
                        continue
                    try:
                        r.queue(k, v)
                    except ValueError:
                        pass                           # illegal now (the scripted controller falls back to the AI too)
        assert n_b > 30
        assert r.base.log == ref, f"game {i}: orders at boundaries differ from the scripted controller"


# ---- 5. save and load --------------------------------------------------------------------------
def test_save_load_replays(world):
    rng = np.random.default_rng(4)
    for i, (h, a) in enumerate(PAIRS[:6]):
        user = "home"
        ref = _scripted_game(world, h, a, user, 500 + i, per_window=False)
        r = GameRunner.new(world, h, a, user, 500 + i)
        for k in DECISIONS:
            r.set_mode(k, "ask")
        tr = r.step("pa")
        n = 0
        while not r.over:
            n += 1
            if n % 17 == 0 and tr["phase"] != "question":
                data = r.save_bytes()
                r = GameRunner.load_bytes(world, data)
                tr = r.turn()
            if tr["phase"] == "question":
                kind = tr["pending"]["kind"]
                tr = r.answer(kind, Policy.value(kind, r.current.st, user))
            else:
                tr = r.step(STOPS[int(rng.integers(0, len(STOPS)))])
        assert r.base.log == ref, f"game {i}: a loaded game diverged"


def test_save_load_fresh_process(world):
    h, a = PAIRS[0]
    ref = _ai_game(world, h, a, 600)
    r = GameRunner.new(world, h, a, "home", 600)
    r.step("three_innings")
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "save.bin"
        f.write_bytes(r.save_bytes())
        code = ("import sys, hashlib; sys.path.insert(0, %r); from app.world import World; from app.connector import GameRunner; "
                "r = GameRunner.load_bytes(World(), open(%r, 'rb').read()); r.step('game'); "
                "print(hashlib.sha256(repr(r.base.log).encode()).hexdigest())") % (str(ROOT), str(f))
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.strip()
    assert out == hashlib.sha256(repr(ref).encode()).hexdigest()


# ---- 6. the catalogue --------------------------------------------------------------------------
def test_catalogue_covers_engine_decisions(world):
    assert set(cat.CATALOGUE) == set(DECISIONS)
    for k in DECISIONS:
        assert cat.CATALOGUE[k].to_json()["kind"] == k
    assert cat.GENERIC_KINDS == [], f"kinds on the generic descriptor (fine, but give them one): {cat.GENERIC_KINDS}"


def test_catalogue_validates(world):
    r = GameRunner.new(world, 5, 200, "home", 7)
    r.step("inning")
    st = r.current.st
    bench = cat.bench(st, "home")
    assert cat.CATALOGUE["pinch_hit"].to_engine(bench[0].pid, st, "home") is bench[0]
    with pytest.raises(ValueError):
        cat.CATALOGUE["pinch_hit"].to_engine(st.lineup["home"][0].pid, st, "home")      # already in the game
    with pytest.raises(ValueError):
        cat.CATALOGUE["pinch_runner"].to_engine(cat.staff(st.team_obj["home"])[0].pid, st, "home")   # a pitcher
    with pytest.raises(ValueError):
        cat.CATALOGUE["relief_pitcher"].to_engine(st.pitcher["home"].pid, st, "home")   # already used
    with pytest.raises(ValueError):
        cat.CATALOGUE["lineup"].to_engine([p.pid for p in st.team_obj["home"].batters[:8]], st, "home")
    assert cat.CATALOGUE["steal_attempt"].to_engine("no", st, "home").name == "NO"
    with pytest.raises(ValueError):
        cat.CATALOGUE["bunt"].to_engine("maybe", st, "home")
