"""Dynasty mode (app/dynasty.py, app/dynasty_api.py) against the engine's own season run (owner condition, 2026-10-08).

1. A dynasty with every game simmed (the user's games by the AI) equals engine.season.simulate_season for the same
   seed: every regular-season game's score and length in schedule order, every postseason game, the field and the
   champion. The dynasty plays the schedule game by game with the engine's per-game seeds and runs the postseason
   pipeline over recorded results (snapshot and replay at the tournament level).
2. A dynasty season played through the API with decisions (the user's first games on the manager screen with the
   scripted policy of tests/test_app_connector.py answering every question, the rest simmed; sims run as the API's
   background jobs; a save and reload in the middle) equals the engine's loop with the same scripted controller
   for those games (engine.season's loop and postseason with `controllers` for the user's games).
Both run a full D1 season twice (about 20 minutes each on the development machine).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_app_connector import Policy, ScriptedHuman  # noqa: E402

from app import dynasty as dm                        # noqa: E402
from config import phase2                            # noqa: E402
from engine import season                            # noqa: E402
from engine.control import DECISIONS, AIController   # noqa: E402
from engine.game2 import B_NCOL, P_NCOL, PlayerGameEngine  # noqa: E402
from engine.league import build_league               # noqa: E402
from engine.manager import Manager                   # noqa: E402
from engine.schedule import make_schedule            # noqa: E402
from engine.world import cancel_mask, schedule_mask  # noqa: E402

TID = 5


def _dyn_rows(d: dm.Dynasty):
    reg = [(r["home"], r["away"], r["hr"], r["ar"], r["inning"], r["run_rule"], r["weekend"]) for i, r in sorted(d.results.items())]
    post = [(r["date"], r["home"], r["away"], r["hr"], r["ar"], r["neutral"], r["stage"]) for r in d.post_calls]
    return reg, post


def test_dynasty_equals_the_engines_season_run():
    cfg = phase2.load()
    seed = 7
    d = dm.Dynasty(cfg, seed, "t")
    d.start(TID)
    d.advance("end", pause_mine=False)
    assert d.stage == "done" and d.pending is None
    ref = season.simulate_season(cfg, seed)
    reg, post = _dyn_rows(d)
    assert reg == ref["games"]
    assert post == ref["post"]["games"]
    assert d.post["ncaa"]["champion"] == ref["post"]["ncaa"]["champion"]
    assert d.post["field"]["national_seeds"] == ref["post"]["field"]["national_seeds"]
    assert sorted(d.post["field"]["at_large"]) == sorted(ref["post"]["field"]["at_large"])


def _reference_season(cfg, seed, tid, n_scripted):
    """engine.season's loop with the scripted controller on the user's first n_scripted games."""
    ss = np.random.SeedSequence(seed)
    s_league, s_sched, s_games = ss.spawn(3)
    league = build_league(cfg, np.random.Generator(np.random.PCG64(s_league)))
    schedule = make_schedule(cfg, league, np.random.Generator(np.random.PCG64(s_sched)))
    s_cancel, s_post, s_len = ss.spawn(3)
    dropped = schedule_mask(schedule, len(league.teams), np.random.Generator(np.random.PCG64(s_len)))
    canceled = cancel_mask(schedule, np.random.Generator(np.random.PCG64(s_cancel))) & ~dropped
    n = len(league.players)
    bstats = [[0] * B_NCOL for _ in range(n)]
    pstats = [[0] * P_NCOL for _ in range(n)]
    eng = PlayerGameEngine(cfg, league, bstats, pstats)
    mgr = Manager(cfg)
    from collections import Counter
    team_games = Counter()
    rows, reg_games, k = [], [], 0
    for g, gss, cx in zip(schedule, s_games.spawn(len(schedule)), canceled | dropped):
        if cx:
            continue
        rng = np.random.Generator(np.random.PCG64(gss))
        home, away = league.teams[g.home], league.teams[g.away]
        ctrl = None
        if tid in (g.home, g.away) and k < n_scripted:
            user = "home" if g.home == tid else "away"
            opp = "away" if user == "home" else "home"
            ctrl = {user: ScriptedHuman(user, mgr, False), opp: AIController(mgr)}
            k += 1
        st = eng.play(rng, home, away, g.weekend, mgr, week=g.week, day=g.day, date=g.date, controllers=ctrl)
        team_games[g.home] += 1; team_games[g.away] += 1
        rows.append((g.home, g.away, st.score["home"], st.score["away"], st.inning, st.ended_by_run_rule, g.weekend))
        reg_games.append((g.date, g.home, g.away, st.score["home"], st.score["away"], False, "regular"))
    post = season._postseason(cfg, league, eng, mgr, reg_games, max(g.date for g in schedule), s_post, team_games, bstats, pstats)
    return rows, post


def _wait(client, did):
    for _ in range(100000):
        p = client.get(f"/api/dynasties/{did}/progress").json()
        if not p["running"]:
            assert p["error"] is None, p["error"]
            return p["hub"]
        time.sleep(0.05)
    raise AssertionError("the sim did not finish")


def _play_pending_with_policy(client, did):
    t = client.post(f"/api/dynasties/{did}/game/open", json={"modes": {k: "ask" for k in DECISIONS}}).json()
    gid, user = t["game_id"], t["user_side"]
    from app import api as api_mod
    t = client.post(f"/api/games/{gid}/sim", json={"target": "game"}).json()
    while t["phase"] != "over":
        assert t["phase"] == "question", t["phase"]
        kind = t["pending"]["kind"]
        value = Policy.value(kind, api_mod.store.games[gid].current.st, user)
        t = client.post(f"/api/games/{gid}/decide", json={"kind": kind, "value": value}).json()
    return client.post(f"/api/dynasties/{did}/game/finish").json()


def test_dynasty_with_decisions_through_the_api_equals_the_scripted_engine_run(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app import api as api_mod, dynasty_api
    monkeypatch.setattr(dynasty_api, "SAVE_DIR", tmp_path / "saves")      # the server saves go to a temporary directory
    seed, n_scripted = 11, 2
    with TestClient(api_mod.app) as c:
        w = api_mod.store.world
        r = c.post("/api/dynasties", json={"seed": seed, "name": "t"}).json()
        did = r["id"]
        assert any(t["tid"] == TID for t in r["teams"]) and all("off" in t and "def" in t for t in r["teams"])
        h = c.post(f"/api/dynasties/{did}/start", json={"tid": TID}).json()
        assert h["record"] == [0, 0] and h["stage"] == "regular"
        played = 0
        while True:
            assert c.post(f"/api/dynasties/{did}/sim", json={"target": "game", "pause_mine": True}).status_code == 200
            h = _wait(c, did)
            if h["pending"] is None:
                break
            if played < n_scripted:
                h = _play_pending_with_policy(c, did)
            else:
                h = c.post(f"/api/dynasties/{did}/game/sim").json()
            played += 1
            if played == 5:                               # a save and reload in the middle of the season
                sv = c.get(f"/api/dynasties/{did}/save").json()
                api_mod.store.dynasties.pop(did)
                h = c.post("/api/dynasties/load", json={"save": sv["save"]}).json()
                did = h["id"]
            if h["stage"] != "regular":
                break
        assert h["stage"] in ("conf", "selection", "ncaa", "done")
        assert c.post(f"/api/dynasties/{did}/sim", json={"target": "end", "pause_mine": False}).status_code == 200
        h = _wait(c, did)
        assert h["stage"] == "done"
        d = api_mod.store.dynasties[did]
        sched = c.get(f"/api/dynasties/{did}/schedule").json()["games"]
        assert sum(1 for g in sched if g["status"] == "played") == len(d.my_games()) + sum(1 for r in d.post_calls if TID in (r["home"], r["away"]))
        box = c.get(f"/api/dynasties/{did}/games/{d.my_games()[0]}").json()
        assert box["box"]["batting"]["home"] and box["user"]
        st = c.get(f"/api/dynasties/{did}/standings").json()
        assert st["my_rank"] and len(st["national"]) >= 64
    reg, post = _dyn_rows(d)
    ref_rows, ref_post = _reference_season(phase2.load(), seed, TID, n_scripted)
    assert reg == ref_rows
    assert post == ref_post["games"]
    assert d.post["ncaa"]["champion"] == ref_post["ncaa"]["champion"]
