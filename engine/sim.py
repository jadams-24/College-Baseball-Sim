"""Season-level driver: simulate n league-average games and aggregate the numbers
the Phase 1 gate and realism report need."""
from __future__ import annotations

from collections import Counter

import numpy as np

from config import phase1
from engine.decider import Decider, LeagueAverageDecider
from engine.game import Engine
from engine.rng import game_seeds
from engine.state import GameState

HIST_BINS = 16


def summarize(games: list[GameState], engine: Engine | None = None) -> dict:
    n = len(games)
    tallies = [g.away for g in games] + [g.home for g in games]
    tg = len(tallies)
    S = Counter()
    for t in tallies:
        for k, v in t.__dict__.items():
            S[k] += v
    ab, h, bb, hbp, sf = S["ab"], S["h"], S["bb"], S["hbp"], S["sf"]
    runs = [t.runs for t in tallies]
    hist = Counter(min(r, HIST_BINS - 1) for r in runs)
    out = {
        "n_games": n,
        "runs_per_team_game": S["runs"] / tg,
        "ba": h / ab, "obp": (h + bb + hbp) / (ab + bb + hbp + sf), "slg": S["tb"] / ab,
        "bb_pct": bb / S["pa"], "k_pct": S["k"] / S["pa"], "hbp_pct": hbp / S["pa"],
        "hr_per_team_game": S["hr"] / tg, "sb_per_team_game": S["sb"] / tg, "cs_per_team_game": S["cs"] / tg,
        "sb_success_rate": S["sb"] / max(1, S["sb"] + S["cs"]),
        "sh_per_team_game": S["sh"] / tg, "sf_per_team_game": S["sf"] / tg,
        "errors_per_team_game": S["errors_committed"] / tg, "pa_per_team_game": S["pa"] / tg,
        "roe_per_team_game": S["roe"] / tg, "fc_per_team_game": S["fc"] / tg, "lob_per_team_game": S["lob"] / tg,
        "run_histogram": [hist[i] / tg for i in range(HIST_BINS)],
        "extra_innings_freq": sum(1 for g in games if g.inning > phase1.load().rules.innings) / n,
        "run_rule_freq": sum(1 for g in games if g.ended_by_run_rule) / n,
        "innings_dist": {str(k): v / n for k, v in sorted(Counter(g.inning for g in games).items())},
        "home_win_pct": sum(1 for g in games if g.home.runs > g.away.runs) / n,
        "mean_margin": float(np.mean([abs(g.home.runs - g.away.runs) for g in games])),
    }
    if engine is not None:
        out["advancement_fallbacks"] = dict(engine.advance.fallbacks)
        out["collision_fixes"] = engine.collision_fixes
    return out


def simulate_league_average_games(n_games: int, seed: int, decider: Decider | None = None, cfg=None) -> dict:
    cfg = cfg or phase1.load()
    engine = Engine(cfg)
    decider = decider or LeagueAverageDecider()
    games = []
    for ss in game_seeds(seed, n_games):
        rng = np.random.Generator(np.random.PCG64(ss))
        games.append(engine.play(rng, decider))
    return summarize(games, engine)
