"""Simulate full seasons of the fictional league and collect player and team lines.

Phase 7 (config.phase7.FEATURES["world"]): each team schedules the real number of games (midweek games
dropped to its drawn target), scheduled regular-season games are canceled at the real rate by month, and after the regular season come the conference tournaments, selection and the NCAA tournament
(engine.world). The returned lines (bstats, pstats, team rows, Phase 4-6 records) are the regular season's,
copied before the postseason, so every Phase 1-6 report reads the regular season; res["post"] carries the
postseason and full-season lines for the Phase 7 report.
"""
from __future__ import annotations

import copy
from collections import Counter

import numpy as np

from config import phase7
from config.phase2 import Phase2Config
from engine.game2 import B_NCOL, P_ER, P_G, P_GS, P_NCOL, P_OUTS, PlayerGameEngine
from engine.league import build_league
from engine.manager import Manager
from engine.schedule import make_schedule


def simulate_season(cfg: Phase2Config, seed: int) -> dict:
    ss = np.random.SeedSequence(seed)
    s_league, s_sched, s_games = ss.spawn(3)
    league = build_league(cfg, np.random.Generator(np.random.PCG64(s_league)))
    schedule = make_schedule(cfg, league, np.random.Generator(np.random.PCG64(s_sched)))
    world = phase7.on("world")
    if world:
        from engine.world import cancel_mask, schedule_mask
        s_cancel, s_post, s_len = ss.spawn(3)    # after the first three: league, schedule and game draws are unchanged
        dropped = schedule_mask(schedule, len(league.teams), np.random.Generator(np.random.PCG64(s_len)))
        canceled = cancel_mask(schedule, np.random.Generator(np.random.PCG64(s_cancel))) & ~dropped
    else:
        dropped = canceled = np.zeros(len(schedule), bool)
    n = len(league.players)
    bstats = [[0] * B_NCOL for _ in range(n)]
    pstats = [[0] * P_NCOL for _ in range(n)]
    eng = PlayerGameEngine(cfg, league, bstats, pstats)
    mgr = Manager(cfg)
    team_games = Counter()
    tg_rows, game_rows, halves, reg_games = [], [], [], []
    game_decisions = []          # per regular-season game, aligned with "games": {"W", "L", "SV", "HLD"} pids (engine/boxscore.py)
    for g, gss, cx in zip(schedule, s_games.spawn(len(schedule)), canceled | dropped):
        if cx:
            continue
        rng = np.random.Generator(np.random.PCG64(gss))
        home, away = league.teams[g.home], league.teams[g.away]
        st = eng.play(rng, home, away, g.weekend, mgr, week=g.week, day=g.day, date=g.date)
        team_games[g.home] += 1; team_games[g.away] += 1
        game_rows.append((g.home, g.away, st.score["home"], st.score["away"], st.inning, st.ended_by_run_rule, g.weekend))
        reg_games.append((g.date, g.home, g.away, st.score["home"], st.score["away"], False, "regular"))
        game_decisions.append(st.box.decisions if st.box is not None else None)
        for side, tm, opp in (("home", home, "away"), ("away", away, "home")):
            # runs in innings 1-3 and 4-6 (game-level persistence diagnostics, reports/phase6.md)
            seg = [sum(r for inn, h, r, _ in st.half_innings if (h == "T") == (side == "away") and lo <= inn <= hi) for lo, hi in ((1, 3), (4, 6))]
            tg_rows.append((tm.tid, st.score[side], st.score[opp], st.hits[side], st.ab[side], st.hr[side],
                            st.er_allowed[side], st.outs_pitched[side], st.errors[side], st.pa[side], len(st.batted[side]),
                            st.sb_att[side], st.sb_ok[side], *seg))
        halves.extend(st.half_innings)
    res = {"league": league, "roe": eng.roe_count, "bstats": np.array(bstats), "pstats": np.array(pstats), "team_games": team_games,
           "team_game_rows": np.array(tg_rows, dtype=float), "games": game_rows, "game_decisions": game_decisions, "half_innings": halves,
           "team_cell": eng.team_cell.copy(), "opp_trials": eng.opp_trials.copy(), "exp_trials": eng.exp_trials.copy(),
           "leash_survive": copy.deepcopy(mgr.leash_survive), "leash_pulls": copy.deepcopy(mgr.leash_pulls),
           "leash_expected": copy.deepcopy(mgr.leash_expected), "leash_var": copy.deepcopy(mgr.leash_var),
           "pitch_rec": copy.deepcopy(eng.pitch_rec), "sb": list(eng.sb), "decisions": _decision_counts(eng), "outings": np.array(eng.outings, dtype=np.int32),
           "outing_lines": np.array(eng.outing_lines, dtype=np.int32), "player_pitch": eng.player_pitch.copy(), "starts": np.array(eng.starts, dtype=float),
           "scheduled_games": Counter([g.home for i, g in enumerate(schedule) if not dropped[i]] + [g.away for i, g in enumerate(schedule) if not dropped[i]]),
           "canceled": int(canceled.sum()), "platoon": {"used": eng.plat_used.copy(), "listed": eng.plat_listed.copy(),
                                                               "relief": eng.relief_rec.copy(), "ph": eng.ph_rec.copy(),
                                                               "split": eng.split_rec.copy()}}
    if world:
        res["post"] = _postseason(cfg, league, eng, mgr, reg_games, max(g.date for g in schedule), s_post, team_games, bstats, pstats)
    res["bullpen_rows"] = np.array(eng.bullpen_rows, dtype=np.int32).reshape(-1, 8)   # engine/bullpen_metrics.py COLUMNS
    return res


def _decision_counts(eng) -> dict:
    """PR B: bunts, sacrifice hits, bunt hits and intentional walks, and the steal paths (plate appearances that began
    with a lead runner able to steal: pitches, final count, attempt, steal) aggregated by length (8+ pooled) and final
    count, as the play-by-play's benchmark (scripts/build_prb_decisions.py)."""
    by_len, by_fc = {}, {}
    for n, fc, att, ok, _known in eng.path_rec:
        a = by_len.setdefault(min(n, 8), [0, 0, 0])
        a[0] += 1; a[1] += att; a[2] += ok
        b = by_fc.setdefault(fc, [0, 0, 0])
        b[0] += 1; b[1] += att; b[2] += ok
    by_len_all, by_fc_all = {}, {}
    for n, fc, att, ok in eng.path_all_rec:
        for d, k in ((by_len_all, min(n, 8)), (by_fc_all, fc)):
            a = d.setdefault(k, [0, 0, 0])
            a[0] += 1; a[1] += att; a[2] += ok
    return {"path_all_by_len": by_len_all, "path_all_by_fc": by_fc_all, "bunts": eng.bunt_rec["bunts"], "SH": eng.bunt_rec["SH"], "bunt_hits": eng.bunt_rec["hits"], "ibb": eng.ibb_count,
            "path_by_len": by_len, "path_by_fc": by_fc}


def _postseason(cfg, league, eng, mgr, reg_games, last_date, s_post, team_games, bstats, pstats) -> dict:
    from engine.world import World
    s_world, s_play = s_post.spawn(2)
    w = World(cfg, league, np.random.Generator(np.random.PCG64(s_world)))
    games, lines, decisions = [], [], []
    post_games = Counter()

    def play_game(h, a, date, neutral, stage):
        rng = np.random.Generator(np.random.PCG64(s_play.spawn(1)[0]))
        st = eng.play(rng, league.teams[h], league.teams[a], True, mgr, week=date // 7, day=0, date=date, neutral=neutral, tournament=True)
        games.append((date, h, a, st.score["home"], st.score["away"], neutral, stage))
        decisions.append(st.box.decisions if st.box is not None else None)
        post_games[h] += 1; post_games[a] += 1
        for side, tid in (("home", h), ("away", a)):
            # columns: team, ER allowed, outs pitched, runs allowed, hits, at bats, home runs, errors made, runs scored
            lines.append((tid, st.er_allowed[side], st.outs_pitched[side], st.score["away" if side == "home" else "home"],
                          st.hits[side], st.ab[side], st.hr[side], st.errors[side], st.score[side]))
        return st.score["home"], st.score["away"]
    off = phase7.POST_OFFSETS
    conf = w.conference_tournaments(reg_games, last_date + off["conf"], play_game)
    autos = {c: v["champion"] for c, v in conf.items()}
    f = w.field(reg_games + [g for g in games if g[6] == "conf"], autos)
    regs = w.bracket(f)
    ncaa = w.ncaa(f, regs, {k: last_date + v for k, v in off.items()}, play_game)
    rpi_rank = f["rank"]
    real_conf = w.real_conf
    same_conf = 0                       # teams sharing a regional with a conference mate (bracketing principles: none)
    for reg in regs:
        cs = [real_conf[t] for t in reg if real_conf[t] != "DI Independent"]
        same_conf += len(cs) - len(set(cs))
    rv = sorted((v["rpi"] for v in f["rpi"].values()), reverse=True)
    return {
        "standings": {t: v for t, v in World.records(reg_games).items()},
        "conference": conf,
        "field": {"auto": f["auto"], "at_large": f["at_large"], "national_seeds": f["national_seeds"],
                  "rank": {t: rpi_rank[t] for t in rpi_rank}, "rpi_at": {k: rv[k - 1] for k in (1, 16, 32, 64)},
                  "rpi": {t: f["rpi"][t]["rpi"] for t in f["rpi"]}},
        "regionals": regs, "same_conf_in_regional": int(same_conf), "ncaa": ncaa, "games": games, "game_decisions": decisions,
        "post_games": dict(post_games), "post_lines": np.array(lines, dtype=float),
        # full season (regular + postseason) pitcher lines for the watch-item re-checks
        "pstats_full": np.array(pstats)[:, [P_G, P_GS, P_OUTS, P_ER]], "team_games_full": dict(team_games + post_games),
        # the full season's box-score lines, every column (engine.game2 B_* and P_*; R, RBI, SB, CS, W, L, SV, HLD included)
        "bstats_box_full": np.array(bstats), "pstats_box_full": np.array(pstats),
    }
