"""The 20-80 scale: D1 mean and true-talent SD of each rated rate.

50 is the D1 average and 10 points one true-talent SD. "D1 average" is the league-average
player: true logit offsets weighted by plate appearances (batters) or batters faced
(pitchers), across every D1 player, all tiers together. The true-talent distribution is
the Phase 2 one (tier means, conference and team spreads, individual spreads, all with
sampling noise removed), as the league generator draws it; usage weights come from
simulated seasons, so the weights are the engine's own PA and BF shares. Pooled over
CAL_SEASONS calibration seasons (seeds 940001+, disjoint from every other run).
The scale does not change any simulated outcome: ratings are an exact re-expression of
the true rates. Output: data/ncaa_2025/derived/phase4_rating_scale_2025.json
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import phase2  # noqa: E402
from config.phase4 import BATTER_RATINGS, PITCHER_RATINGS, SCALE  # noqa: E402
from engine.game2 import B_PA, P_BF  # noqa: E402
from engine.ratings import IDX  # noqa: E402
from engine.season import simulate_season  # noqa: E402

CAL_SEASONS = 8
SEED = 940001
WORKERS = 4


def _season(seed: int) -> dict:
    res = simulate_season(phase2.load(), seed)
    out = {"bat": {"w": [], "z": []}, "pit": {"w": [], "z": []}}
    for p in res["league"].players:
        w = res["bstats"][p.pid][B_PA] if p.side == "bat" else res["pstats"][p.pid][P_BF]
        out[p.side]["w"].append(float(w))
        out[p.side]["z"].append(p.z.tolist())
    return out


def main() -> None:
    with ProcessPoolExecutor(WORKERS) as ex:
        seasons = list(ex.map(_season, [SEED + i for i in range(CAL_SEASONS)]))
    scale = {}
    for side, defs in (("bat", BATTER_RATINGS), ("pit", PITCHER_RATINGS)):
        w = np.concatenate([s[side]["w"] for s in seasons])
        z = np.concatenate([np.array(s[side]["z"]) for s in seasons])
        scale[side] = {}
        for _, rate, _ in defs:
            v = z[:, IDX[rate]]
            m = float(np.average(v, weights=w))
            sd = float(np.sqrt(np.average((v - m) ** 2, weights=w)))
            scale[side][rate] = {"mean": round(m, 5), "sd": round(sd, 5)}
    SCALE.write_text(json.dumps({"_note": __doc__, "built": dt.date.today().isoformat(), "seeds": [SEED, SEED + CAL_SEASONS - 1],
                                 "weights": "PA (batters), BF (pitchers), simulated seasons", "scale": scale}, indent=1) + "\n")
    print(json.dumps(scale, indent=1))


if __name__ == "__main__":
    main()
