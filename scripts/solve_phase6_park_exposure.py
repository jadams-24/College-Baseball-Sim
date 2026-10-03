"""How the scoreboard fit without parks absorbs parks into team ratings (Phase 6).

Team totals (o, d) come from the fit without parks; the engine draws them and nets out the parks.
A team's total absorbs its home park and the parks it visits. On simulated seasons, where the net
ratings and every park are known, the same fit without parks is run and the recovered ratings minus the
drawn net ones are regressed on the team's home park and the mean of the parks of its road games
(scoreboard log runs, centred): o_total - o_net = b_oh p_home + b_or p_road, likewise for d. The
coefficients are a property of the fit on this schedule design, not of the netting (calibration seeds
940001-940004). The engine nets each team by them, with p_road its expected road park.

    python3 scripts/solve_phase6_park_exposure.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from config import phase2, phase6  # noqa: E402
from config.phase6 import INPUTS6  # noqa: E402

SEEDS = (940001, 940002, 940003, 940004)


def _season(seed: int) -> list:
    from build_phase2_teams import fit
    from engine.season import simulate_season
    pk6 = phase6.load()["parks6"]
    w, k_o = np.array(pk6["w"]), pk6["k_o"]
    res = simulate_season(phase2.load(), seed)
    T = {t.tid: t for t in res["league"].teams}
    run = {tid: float(w @ t.park) / k_o for tid, t in T.items()}
    gd = pd.DataFrame(res["games"], columns=["home", "away", "home_score", "away_score", "inn", "rr", "wk"])
    names = sorted(set(gd.home) | set(gd.away))
    f = fit(gd, names, parks=False)
    rows = []
    for i, n in enumerate(names):
        rows.append((f["o"][i] - T[n].o, f["d"][i] - T[n].d, run[n], float(gd[gd.away == n].home.map(run).mean())))
    d = pd.DataFrame(rows, columns=["do", "dd", "ph", "pr"])
    d = d - d.mean()
    X = d[["ph", "pr"]].values
    return [*np.linalg.lstsq(X, d["do"].values, rcond=None)[0], *np.linalg.lstsq(X, d["dd"].values, rcond=None)[0]]


def main() -> None:
    with ProcessPoolExecutor(4) as ex:
        b = np.array(list(ex.map(_season, SEEDS)))
    m, se = b.mean(0), b.std(0, ddof=1) / np.sqrt(len(SEEDS))
    keys = ["o_home", "o_road", "d_home", "d_road"]
    blk = {"_note": __doc__, "built": dt.date.today().isoformat(), "seeds": list(SEEDS),
           **{k: round(float(v), 4) for k, v in zip(keys, m)}, "se": {k: round(float(v), 4) for k, v in zip(keys, se)}}
    cur = json.loads(INPUTS6.read_text())
    cur["park_exposure"] = blk
    INPUTS6.write_text(json.dumps(cur, indent=1, default=float) + "\n")
    print(json.dumps({k: v for k, v in blk.items() if k != "_note"}, indent=1))


if __name__ == "__main__":
    main()
