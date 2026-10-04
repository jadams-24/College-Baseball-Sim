"""Simulate seasons once and write every report: Phase 2 (every Phase 1 and Phase 2 gate row),
Phase 4 (the forward ratings test), Phase 5 (pitch-by-pitch) and Phase 6 (fielding, parks, fatigue,
bullpen, manager AI), all on the same run.
    python3 scripts/run_phase5.py            # the report's run: 40 seasons, seed 20251000
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import phase2  # noqa: E402
from config.phase5 import BIP_RESULTS, OUTCOMES  # noqa: E402
from config.phase5 import load as load_pitch, load_solved  # noqa: E402
from engine.league import load_location  # noqa: E402
from engine.matchup import matchup_probs  # noqa: E402
from engine.pitch import PitchModel  # noqa: E402
from engine.report2 import aggregate, build_report, season_metrics  # noqa: E402
from engine.report4 import aggregate4, build_report4, season_extract4  # noqa: E402
from engine.report5 import aggregate5, build_report5, season_extract5  # noqa: E402
from engine.report6 import aggregate6, build_report6, season_extract6  # noqa: E402
from engine.season import simulate_season  # noqa: E402
from run_phase2 import REPORT_SEASONS, REPORT_SEED  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def one(seed: int) -> tuple:
    res = simulate_season(phase2.load(), seed)
    return season_metrics(res), season_extract4(res), season_extract5(res), season_extract6(res)


def run(seasons: int, seed: int, workers: int) -> tuple:
    seeds = [seed + i for i in range(seasons)]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        out = list(ex.map(one, seeds))
    return (aggregate([o[0] for o in out]), aggregate4([o[1] for o in out]), aggregate5([o[2] for o in out]), aggregate6([o[3] for o in out]),
            seeds)


def chain_info(agg2: dict) -> dict:
    cfg = phase2.load()
    lp = matchup_probs(cfg, np.zeros(len(cfg.v_bat)), np.zeros(len(cfg.v_bat)), load_location())
    pm = PitchModel(load_pitch(), load_solved())
    cl = dict(zip(OUTCOMES, pm.chain_league))
    return {"J": np.round(pm.J, 3).tolist(),
            "chain_league": {"K": cl["K"], "BB": cl["BB"], "HBP": cl["HBP"], "BIP": sum(cl[o] for o in BIP_RESULTS)},
            "pa_league": {"K": lp["K"], "BB": lp["BB"], "HBP": lp["HBP"], "BIP": 1 - lp["K"] - lp["BB"] - lp["HBP"]},
            "p50ip": agg2["leaderboards"]["pitchers_50ip"]["mean"], "dir_response": pm.dir_response}


def reports(agg2, agg4, agg5, agg6, seeds) -> tuple:
    md2, st2 = build_report(agg2, seeds)
    md4, st4 = build_report4(agg4, seeds, st2)
    league_se = {k.split("/", 1)[1]: v for k, v in agg2["se"].items() if k.startswith("league/")}
    md5, st5 = build_report5(agg5, seeds, agg2["league"], league_se, st2, st4, chain_info(agg2))
    md6, st6 = build_report6(agg6, agg2, agg5, seeds, st2, st4, st5)
    return (md2, st2), (md4, st4), (md5, st5), (md6, st6)


def write(agg2, agg4, agg5, agg6, seeds) -> tuple:
    out = reports(agg2, agg4, agg5, agg6, seeds)
    for (md, st), agg, name in zip(out, (agg2, agg4, agg5, agg6), ("phase2", "phase4", "phase5", "phase6")):
        (ROOT / f"reports/{name}.md").write_text(md)
        (ROOT / f"reports/{name}.json").write_text(json.dumps({"aggregate": agg, "status": st, "values": getattr(st, "vals", {})}, indent=1, default=float) + "\n")
    return tuple(st for _, st in out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", type=int, default=REPORT_SEASONS)
    ap.add_argument("--seed", type=int, default=REPORT_SEED)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    t0 = time.time()
    agg2, agg4, agg5, agg6, seeds = run(a.seasons, a.seed, a.workers)
    st2, st4, st5, st6 = write(agg2, agg4, agg5, agg6, seeds)
    print((ROOT / "reports/phase6.md").read_text())
    ok = lambda st: all(v for v in st.values() if v is not None)
    print("phase2 gate", ok(st2), "| phase4 gate", ok(st4), "| phase5 gate", ok(st5), "| phase6 gate", ok(st6), f"({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
