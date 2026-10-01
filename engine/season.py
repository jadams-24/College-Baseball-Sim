"""Simulate full seasons of the fictional league and collect player and team lines."""
from __future__ import annotations

from collections import Counter

import numpy as np

from config.phase2 import Phase2Config
from engine.game2 import B_AB, B_BB, B_G, B_H, B_HBP, B_HR, B_K, B_PA, B_SF, B_2B, B_3B, P_BF, P_ER, P_K, P_OUTS, PlayerGameEngine
from engine.league import build_league
from engine.manager import Manager
from engine.schedule import make_schedule


def simulate_season(cfg: Phase2Config, seed: int) -> dict:
    ss = np.random.SeedSequence(seed)
    s_league, s_sched, s_games = ss.spawn(3)
    league = build_league(cfg, np.random.Generator(np.random.PCG64(s_league)))
    schedule = make_schedule(cfg, league, np.random.Generator(np.random.PCG64(s_sched)))
    n = len(league.players)
    bstats = [[0] * 12 for _ in range(n)]
    pstats = [[0] * 12 for _ in range(n)]
    eng = PlayerGameEngine(cfg, league, bstats, pstats)
    mgr = Manager(cfg)
    team_games = Counter()
    midweek_count = Counter()
    tg_rows, game_rows, halves = [], [], []
    for g, gss in zip(schedule, s_games.spawn(len(schedule))):
        rng = np.random.Generator(np.random.PCG64(gss))
        home, away = league.teams[g.home], league.teams[g.away]
        starters = {}
        for side, tm in (("home", home), ("away", away)):
            if g.weekend:
                starters[side] = tm.weekend_sp[g.day]
            else:
                starters[side] = tm.midweek_sp[midweek_count[tm.tid] % len(tm.midweek_sp)]
                midweek_count[tm.tid] += 1
        st = eng.play(rng, home, away, g.weekend, starters, mgr)
        team_games[g.home] += 1; team_games[g.away] += 1
        game_rows.append((g.home, g.away, st.score["home"], st.score["away"], st.inning, st.ended_by_run_rule, g.weekend))
        for side, tm, opp in (("home", home, "away"), ("away", away, "home")):
            tg_rows.append((tm.tid, st.score[side], st.score[opp], st.hits[side], st.ab[side], st.hr[side],
                            st.er_allowed[side], st.outs_pitched[side], st.errors[side], st.pa[side]))
        halves.extend(st.half_innings)
    return {"league": league, "roe": eng.roe_count, "bstats": np.array(bstats), "pstats": np.array(pstats), "team_games": team_games,
            "team_game_rows": np.array(tg_rows, dtype=float), "games": game_rows, "half_innings": halves}
