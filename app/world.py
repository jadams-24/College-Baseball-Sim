"""The exhibition world: one fixed fictional league and one engine per process.

The league is the determinism test's (seed 20261006), built once at startup; the engine is built once over it and
plays every game of the process, as a season does. (One engine per game is not an option: engine/tables.py keeps
module-level caches keyed by id() of its table objects, so a freed engine's addresses can be reused by the next
one and a stale cache entry changes a draw. One live engine per process never frees a table.)

The engine's accumulators (bstats, pstats) therefore run across games; a game's lines are differences against
the rows copied when the game was created (GameRunner), and a snapshot carries the game's rows only.
"""
from __future__ import annotations

import numpy as np

from config import phase2
from engine.game2 import B_NCOL, P_NCOL, PlayerGameEngine
from engine.league import build_league
from engine.ratings import display, rating_names

LEAGUE_SEED = 20261006          # tests/test_session_determinism.py builds the same league
# An exhibition is a Friday series opener in season week 1: the AI's game-1 weekend starter, the week-1 pull
# tables (engine.manager: starting_pitcher, pitching_change).
EXHIBITION = {"weekend": True, "week": 1, "day": 0, "date": 11}

BAT_RATINGS = ("contact", "gap", "power", "eye", "avoid_k", "speed", "glove", "arm")
PIT_RATINGS = ("stuff", "control", "movement", "stamina")
POS_LABEL = {"c": "C", "1b": "1B", "2b": "2B", "3b": "3B", "ss": "SS", "lf": "LF", "cf": "CF", "rf": "RF", "dh": "DH"}


def staff(team) -> list:
    """The 13-man staff in the engine's role order: weekend starters, midweek starters, relievers."""
    return list(team.weekend_sp) + list(team.midweek_sp) + list(team.relievers)


def role_label(p) -> str:
    if p.side == "bat":
        return "regular" if p.group == "regular" else "bench"
    return {"sp_weekend": "SP", "sp_midweek": "MW", "rp": "RP"}.get(p.group, p.group) + str(p.order + 1)


def player_json(p) -> dict:
    names = BAT_RATINGS if p.side == "bat" else PIT_RATINGS
    return {"pid": p.pid, "name": p.name, "side": p.side, "group": p.group, "role": role_label(p),
            "pos": POS_LABEL.get(p.pos, p.pos.upper()) if p.pos else ("P" if p.side == "pit" else ""),
            "bat_order": p.bat_order if p.side == "bat" else None,
            "ratings": {k: int(display(p.ratings[k])) for k in names if k in p.ratings}}


class World:
    def __init__(self, seed: int = LEAGUE_SEED):
        self.cfg = phase2.load()
        self.seed = seed
        self.league = build_league(self.cfg, np.random.Generator(np.random.PCG64(seed)))
        n = len(self.league.players)
        self.eng = PlayerGameEngine(self.cfg, self.league, [[0] * B_NCOL for _ in range(n)], [[0] * P_NCOL for _ in range(n)])
        self.rating_names = {"bat": [n for n in rating_names("bat")] + ["glove", "arm"], "pit": rating_names("pit")}

    # ---- lookups -----------------------------------------------------------------------
    def teams(self) -> list:
        out = []
        for t in self.league.teams:
            conf = self.league.conferences[t.conference]
            out.append({"tid": t.tid, "name": t.name, "conference": conf[0], "tier": t.tier})
        return out

    def team(self, tid: int):
        if not isinstance(tid, int) or not 0 <= tid < len(self.league.teams):
            raise KeyError(tid)
        return self.league.teams[tid]

    def roster(self, tid: int) -> dict:
        t = self.team(tid)
        conf = self.league.conferences[t.conference]
        return {"tid": t.tid, "name": t.name, "conference": conf[0], "tier": t.tier,
                "batters": [player_json(p) for p in t.batters], "pitchers": [player_json(p) for p in staff(t)]}

    def game_pids(self, home, away) -> list:
        return [p.pid for t in (home, away) for p in t.batters + staff(t)]
