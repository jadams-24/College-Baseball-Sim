"""The 20-80 scale: percentiles of the D1 distribution of each rated true rate.

A rating is 50 + 10 * sign * Phi^-1(F(z)) (engine/ratings.py), F the D1 distribution of the
true logit offset z: every D1 player, all tiers together, weighted by plate appearances
(batters) or batters faced (pitchers). The true-talent distribution is the Phase 2 one (tier
means, conference and team spreads, individual spreads with their fitted shapes, sampling
noise removed), as the league generator draws it. Usage weights come from simulated seasons:
the mean PA (BF) of each roster slot (tier, role group, order) over CAL_SEASONS calibration
seasons (seeds 940001+). F is then the slot-weighted distribution of z over SCALE_LEAGUES
generated leagues (seeds 950001+, no games needed), enough draws to place the table out to
normal score +-SCALE_MAX_SCORE; beyond it the map continues linearly.
The scale does not change any simulated outcome: ratings are an exact re-expression of the
true rates. Output: data/ncaa_2025/derived/phase4_rating_scale_2025.json (quantile table plus
the weighted mean and SD of z, kept as descriptive values).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import phase2  # noqa: E402
from config.phase4 import BATTER_RATINGS, PITCHER_RATINGS, SCALE, SCALE_LEAGUES, SCALE_MAX_SCORE, SCALE_SCORE_STEP  # noqa: E402
from engine.game2 import B_PA, P_BF  # noqa: E402
from engine.league import build_league  # noqa: E402
from engine.ratings import IDX  # noqa: E402
from engine.season import simulate_season  # noqa: E402

CAL_SEASONS = 8
SEED = 940001
LEAGUE_SEED = 950001
WORKERS = 4


def _slot(team: dict, p) -> tuple:
    return (team[p.team].tier, p.side, p.group, p.order)


def _season(seed: int) -> dict:
    res = simulate_season(phase2.load(), seed)
    team = {t.tid: t for t in res["league"].teams}
    out = defaultdict(list)
    for p in res["league"].players:
        w = res["bstats"][p.pid][B_PA] if p.side == "bat" else res["pstats"][p.pid][P_BF]
        out[_slot(team, p)].append(float(w))
    return dict(out)


def _league(seed: int) -> dict:
    lg = build_league(phase2.load(), np.random.default_rng(seed))
    team = {t.tid: t for t in lg.teams}
    out = {"bat": {"slot": [], "z": []}, "pit": {"slot": [], "z": []}}
    for p in lg.players:
        out[p.side]["slot"].append(_slot(team, p))
        out[p.side]["z"].append(p.z.tolist())
    return out


def weighted_quantiles(v: np.ndarray, w: np.ndarray, probs: np.ndarray) -> np.ndarray:
    o = np.argsort(v)
    v, w = v[o], w[o]
    c = (np.cumsum(w) - 0.5 * w) / w.sum()          # mid-point plotting positions
    return np.interp(probs, c, v)


def _phi(x: np.ndarray) -> np.ndarray:
    from math import erf, sqrt
    return np.array([0.5 * (1 + erf(t / sqrt(2))) for t in x])


def main() -> None:
    with ProcessPoolExecutor(WORKERS) as ex:
        seasons = list(ex.map(_season, [SEED + i for i in range(CAL_SEASONS)]))
        leagues = list(ex.map(_league, [LEAGUE_SEED + i for i in range(SCALE_LEAGUES)]))
    pool = defaultdict(list)
    for s in seasons:
        for k, v in s.items():
            pool[k] += v
    slot_w = {k: float(np.mean(v)) for k, v in pool.items()}
    scores = np.round(np.arange(-SCALE_MAX_SCORE, SCALE_MAX_SCORE + SCALE_SCORE_STEP / 2, SCALE_SCORE_STEP), 4)
    probs = _phi(scores)
    scale = {}
    for side, defs in (("bat", BATTER_RATINGS), ("pit", PITCHER_RATINGS)):
        w = np.array([slot_w.get(k, 0.0) for lg in leagues for k in lg[side]["slot"]])
        z = np.concatenate([np.array(lg[side]["z"]) for lg in leagues])
        scale[side] = {}
        for _, rate, _ in defs:
            v = z[:, IDX[rate]]
            m = float(np.average(v, weights=w))
            sd = float(np.sqrt(np.average((v - m) ** 2, weights=w)))
            q = weighted_quantiles(v, w, probs)
            scale[side][rate] = {"mean": round(m, 5), "sd": round(sd, 5), "median": round(float(np.interp(0.5, probs, q)), 5),
                                 "quantiles": {"normal_scores": scores.tolist(), "z": [round(float(x), 5) for x in q]}}
    n_players = {side: int(sum(len(lg[side]["z"]) for lg in leagues)) for side in ("bat", "pit")}
    SCALE.write_text(json.dumps({"_note": __doc__, "built": dt.date.today().isoformat(), "seeds": {"usage": [SEED, SEED + CAL_SEASONS - 1],
                                 "leagues": [LEAGUE_SEED, LEAGUE_SEED + SCALE_LEAGUES - 1]}, "players": n_players,
                                 "weights": "mean PA (batters) / BF (pitchers) of the roster slot (tier, group, order) in simulated seasons",
                                 "scale": scale}, indent=1) + "\n")
    for side in scale:
        for rate, e in scale[side].items():
            qz = dict(zip(e["quantiles"]["normal_scores"], e["quantiles"]["z"]))
            lin = lambda s_: e["mean"] + s_ * e["sd"]
            print(f"{side} {rate}: mean {e['mean']:+.3f} sd {e['sd']:.3f} median {e['median']:+.3f} | z at 20/50/60/70/80: "
                  + " ".join(f"{qz[s_]:+.3f}(lin {lin(s_):+.3f})" for s_ in (-3.0, 0.0, 1.0, 2.0, 3.0)))


if __name__ == "__main__":
    main()
