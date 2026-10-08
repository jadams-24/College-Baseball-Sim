"""Simulate seasons once and write every report: Phase 2 (every Phase 1 and Phase 2 gate row),
Phase 4 (the forward ratings test), Phase 5 (pitch-by-pitch), Phase 6 (fielding, parks, fatigue,
bullpen, manager AI), Phase 7 (season and world: cancellations, conference tournaments, RPI,
selection, the NCAA tournament) and Phase 3 (handedness and platoon splits), all on the same run.
    python3 scripts/run_phase5.py            # the report's run: 40 seasons, seed 20251000
"""
from __future__ import annotations

import argparse
import json
import pickle
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
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
from engine.report3 import aggregate3, build_report3, season_extract3  # noqa: E402
from engine.report4 import aggregate4, build_report4, season_extract4  # noqa: E402
from engine.report5 import aggregate5, build_report5, season_extract5  # noqa: E402
from engine.report6 import aggregate6, build_report6, season_extract6  # noqa: E402
from engine.report7 import aggregate7, build_report7, season_extract7  # noqa: E402
from engine.season import simulate_season  # noqa: E402
from run_phase2 import REPORT_SEASONS, REPORT_SEED  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def one(seed: int) -> tuple:
    res = simulate_season(phase2.load(), seed)
    return season_metrics(res), season_extract4(res), season_extract5(res), season_extract6(res), season_extract7(res), season_extract3(res)


def _code_id() -> str | None:
    """The commit the simulation code comes from, or None when the code is not exactly a commit (uncommitted changes
    to anything the seasons read: engine, config, scripts, data, benchmarks)."""
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "engine", "config", "scripts", "data", "benchmarks.json"],
                               cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return None if dirty else head


def run(seasons: int, seed: int, workers: int, checkpoint: bool = False) -> tuple:
    """Simulate the seasons. checkpoint (the command line's default): each finished season is saved under
    runs/<commit>/ and a restart skips the seeds already there. Only when the code is exactly a commit; a run on
    another commit, or on uncommitted code, never reads another run's seasons."""
    seeds = [seed + i for i in range(seasons)]
    done, cdir = {}, None
    if checkpoint:
        code = _code_id()
        if code is None:
            print("checkpoints off: uncommitted changes to the simulation code (commit them to make the run resumable)", flush=True)
        else:
            cdir = ROOT / "runs" / code
            cdir.mkdir(parents=True, exist_ok=True)
            others = [d.name for d in (ROOT / "runs").iterdir() if d.is_dir() and d.name != code]
            if others:
                print(f"not resuming from runs of other commits ({', '.join(o[:8] for o in others)}): the code changed", flush=True)
            for sd in seeds:
                f = cdir / f"season_{sd}.pkl"
                if f.exists():
                    done[sd] = pickle.loads(f.read_bytes())
            if done:
                print(f"resuming on {code[:8]}: {len(done)} of {len(seeds)} seasons already done", flush=True)
    todo = [sd for sd in seeds if sd not in done]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(one, sd): sd for sd in todo}
        for fu in as_completed(futs):
            sd = futs[fu]
            done[sd] = fu.result()
            if cdir is not None:
                tmp = cdir / f"season_{sd}.tmp"
                tmp.write_bytes(pickle.dumps(done[sd]))
                tmp.replace(cdir / f"season_{sd}.pkl")
            print(f"season {sd} done ({len(done)} of {len(seeds)})", flush=True)
    out = [done[sd] for sd in seeds]
    return (aggregate([o[0] for o in out]), aggregate4([o[1] for o in out]), aggregate5([o[2] for o in out]), aggregate6([o[3] for o in out]),
            aggregate7([o[4] for o in out]), aggregate3([o[5] for o in out]), seeds)


def chain_info(agg2: dict) -> dict:
    cfg = phase2.load()
    lp = matchup_probs(cfg, np.zeros(len(cfg.v_bat)), np.zeros(len(cfg.v_bat)), load_location())
    pm = PitchModel(load_pitch(), load_solved())
    cl = dict(zip(OUTCOMES, pm.chain_league))
    return {"J": np.round(pm.J, 3).tolist(),
            "chain_league": {"K": cl["K"], "BB": cl["BB"], "HBP": cl["HBP"], "BIP": sum(cl[o] for o in BIP_RESULTS)},
            "pa_league": {"K": lp["K"], "BB": lp["BB"], "HBP": lp["HBP"], "BIP": 1 - lp["K"] - lp["BB"] - lp["HBP"]},
            "p50ip": agg2["leaderboards"]["pitchers_50ip"]["mean"], "dir_response": pm.dir_response}


def reports(agg2, agg4, agg5, agg6, agg7, agg3, seeds) -> tuple:
    md2, st2 = build_report(agg2, seeds)
    md4, st4 = build_report4(agg4, seeds, st2)
    league_se = {k.split("/", 1)[1]: v for k, v in agg2["se"].items() if k.startswith("league/")}
    md5, st5 = build_report5(agg5, seeds, agg2["league"], league_se, st2, st4, chain_info(agg2))
    md6, st6 = build_report6(agg6, agg2, agg5, seeds, st2, st4, st5)
    md7, st7 = build_report7(agg7, seeds, {"phase2": st2, "phase4": st4, "phase5": st5, "phase6": st6})
    md3, st3 = build_report3(agg3, seeds, {"phase2": st2, "phase4": st4, "phase5": st5, "phase6": st6, "phase7": st7}, agg2, agg7)
    return (md2, st2), (md4, st4), (md5, st5), (md6, st6), (md7, st7), (md3, st3)


NAMES = ("phase2", "phase4", "phase5", "phase6", "phase7", "phase3")


def write(agg2, agg4, agg5, agg6, agg7, agg3, seeds) -> tuple:
    out = reports(agg2, agg4, agg5, agg6, agg7, agg3, seeds)
    for (md, st), agg, name in zip(out, (agg2, agg4, agg5, agg6, agg7, agg3), NAMES):
        (ROOT / f"reports/{name}.md").write_text(md)
        (ROOT / f"reports/{name}.json").write_text(json.dumps({"aggregate": agg, "status": st, "values": getattr(st, "vals", {})}, indent=1, default=float) + "\n")
    return tuple(st for _, st in out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", type=int, default=REPORT_SEASONS)
    ap.add_argument("--seed", type=int, default=REPORT_SEED)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-resume", action="store_true", help="do not save or reuse finished seasons (runs/<commit>/)")
    ap.add_argument("--from-reports", action="store_true",
                    help="rebuild every report from the aggregates saved in reports/*.json (no simulation): a change to a "
                         "report's rows or gating, on the committed run")
    a = ap.parse_args()
    t0 = time.time()
    if a.from_reports:
        aggs = [json.loads((ROOT / f"reports/{n}.json").read_text())["aggregate"] for n in NAMES]
        agg2, agg4, agg5, agg6, agg7, agg3, seeds = (*aggs, [a.seed + i for i in range(a.seasons)])
    else:
        agg2, agg4, agg5, agg6, agg7, agg3, seeds = run(a.seasons, a.seed, a.workers, checkpoint=not a.no_resume)
    sts = write(agg2, agg4, agg5, agg6, agg7, agg3, seeds)
    print((ROOT / "reports/phase3.md").read_text())
    ok = lambda st: all(v for v in st.values() if v is not None)
    print(" | ".join(f"{name} gate {ok(st)}" for name, st in zip(NAMES, sts)), f"({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
