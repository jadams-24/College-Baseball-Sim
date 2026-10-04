"""Write the Phase 6 block of benchmarks.json (usage_phase6_2025) from
data/ncaa_2025/derived/phase6_inputs_2025.json (scripts/build_phase6_usage.py, build_phase6_subs.py):
pitcher usage on the 50 full-season teams of the 2025 play-by-play at a 56-game equivalent
(appearances of a team's busiest, 5th and 10th busiest pitchers; relief-only pitchers, 3 or fewer
starts, with 40+ and 60+ IP; the top three pitchers' innings and their split into Fri-Sun starts,
other starts and relief), and distinct batters per team-game. Tolerance 3 SE (bootstrap over teams,
or over games for batters). Errors and stolen bases are gated on their existing league_totals_2025
rows; the deferred rows on their existing blocks. Two existing rows change (PHASE0_NOTES, Phase 6):
  league_totals_2025.sb_per_team_game  1.29 (FanGraphs unweighted conference means, Phase 0) -> the WMT
      box-total value reweighted to the full-season matchup mix (league_totals_2025_team_weighted_wmt),
      the source of the attempt and success rows it is the product of; full-season Sidearm team totals
      (data/ncaa_2025/sidearm/team_totals_2025.csv) agree.
  leaderboards_2025.pitchers_50ip      gains value_56g: the raw full-population count x the ratio of the
      56-game-equivalent count to the raw count on the WMT full-season teams (the sim plays 56 games, real
      teams 57-72 with the postseason), as for the individual-leader rows.
Every write is recorded in data/ncaa_2025/derived/benchmark_changes_phase6.json.

    python3 scripts/write_phase6_benchmarks.py      (after scripts/write_phase2_benchmarks.py, which rewrites leaderboards_2025)
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_pbp_benchmarks import dumps_compact  # noqa: E402

D = ROOT / "data/ncaa_2025/derived"
BENCH = ROOT / "benchmarks.json"
GATED = ("app_max", "app_5th", "app_10th", "relief_only_40ip", "relief_only_60ip", "ip_rank1", "ip_rank2", "ip_rank3")


def main() -> None:
    inp = json.loads((D / "phase6_inputs_2025.json").read_text())
    u, sb = inp["usage6"]["benchmarks"], inp["subs6"]
    new = {"_note": ("Phase 6 gate: pitcher usage of the 2025 full-season teams (WMT play-by-play, data/ncaa_2025/pbp; 50 teams, 57.2 games "
                     "on average) at a 56-game equivalent (each team's counts x 56 / its games), mean over teams; tolerance 3 SE (bootstrap "
                     "over teams). The top three pitchers' innings split (Fri-Sun starts, other starts, relief) is reported, not gated. "
                     "Batters per team-game: distinct batters with a plate appearance, tolerance 3 SE (bootstrap over games)."),
           "conf": "B", "src": "WMT stats API play-by-play 2025, data/ncaa_2025/pbp (fetched 2026-09-30 to 2026-10-01)",
           "n_teams": u["teams"], "team_games_mean": u["team_games_mean"]}
    for k, v in u.items():
        if isinstance(v, dict) and "value" in v and k != "pitchers_50ip_ratio_56g":
            new[k] = {"value": v["value"], "tol": round(3 * v["se"], 3), **({} if k in GATED else {"gate": "report"})}
    new["batters_per_team_game"] = {"value": sb["batters_per_team_game"]["value"], "tol": round(3 * sb["batters_per_team_game"]["se"], 3)}
    # earned share of runs (the Phase 5 run held it to the Phase 4 run; Phase 6 fielding moves it): tolerance 3 SE, bootstrap over games
    rc = pd.read_csv(ROOT / "data/ncaa_2025/pbp/parsed/runs_charged_2025.csv.gz")
    g = rc.groupby("game_id").agg(n=("unearned", "size"), u=("unearned", "sum"))
    rng = np.random.default_rng(6)
    bs = [1 - g.u.values[i].sum() / g.n.values[i].sum() for i in (rng.integers(0, len(g), len(g)) for _ in range(1000))]
    new["earned_run_share"] = {"value": round(float(1 - g.u.sum() / g.n.sum()), 4), "tol": round(3 * float(np.std(bs, ddof=1)), 4),
                               "src": "runs charged by inning reconstruction of the WMT play-by-play (data/ncaa_2025/pbp/parsed/runs_charged_2025.csv.gz)"}
    b = json.loads(BENCH.read_text())
    changes = []

    def put(path, old, val):
        if json.loads(json.dumps(old)) != json.loads(json.dumps(val)):
            changes.append({"path": path, "old": old, "new": val})
    put("usage_phase6_2025", b.get("usage_phase6_2025"), new)
    b["usage_phase6_2025"] = new
    # stolen bases per team-game: attempts x success on the same box totals
    lt, wmt = b["league_totals_2025"], b["league_totals_2025_team_weighted_wmt"]
    sd = pd.read_csv(ROOT / "data/ncaa_2025/sidearm/team_totals_2025.csv")
    sd = sd[sd.side == "Totals"]
    sb_new = {"value": wmt["reweighted"]["sb_per_team_game"], "tol": lt["sb_per_team_game"]["tol"], "conf": "B",
              "src": ("WMT stats API box totals, 2259 2025 D1-vs-D1 games, reweighted by tier x opponent-tier cell to the full-season matchup mix "
                      "(league_totals_2025_team_weighted_wmt; raw sample 1.058), the source of sb_attempts_per_team_game and sb_success_rate. "
                      f"Full-season Sidearm team totals agree: {len(sd)} teams, {sd.h_stolenBases.sum() / sd.h_gamesPlayed.sum():.3f} per team-game "
                      "(data/ncaa_2025/sidearm/team_totals_2025.csv). Replaces 1.29, the FanGraphs unweighted mean of conference tables (Phase 0)."),
              "phase0_value": 1.29}
    put("league_totals_2025.sb_per_team_game", lt["sb_per_team_game"], sb_new)
    lt["sb_per_team_game"] = sb_new
    # pitchers with 50+ IP at a 56-game equivalent
    r = inp["usage6"]["benchmarks"]["pitchers_50ip_ratio_56g"]
    p50 = dict(b["leaderboards_2025"]["pitchers_50ip"])
    p50_new = {**{k: v for k, v in p50.items() if k not in ("value_56g", "ratio_56g", "note_56g")}, "value_56g": round(p50["value"] * r["value"], 1),
               "ratio_56g": r,
               "note_56g": ("Gated value: the raw count x the ratio of 56-game-equivalent to raw 50+ IP counts on the 50 WMT full-season teams "
                            "(each pitcher's IP x 56 / his team's games; scripts/build_phase6_usage.py). The sim plays 56 games with no postseason.")}
    put("leaderboards_2025.pitchers_50ip", p50, p50_new)
    b["leaderboards_2025"]["pitchers_50ip"] = p50_new
    BENCH.write_text(dumps_compact(b) + "\n")
    if changes:
        log = D / "benchmark_changes_phase6.json"
        prior = json.loads(log.read_text()) if log.exists() else []
        log.write_text(json.dumps(prior + [{**c, "date": datetime.date.today().isoformat()} for c in changes], indent=1, default=str) + "\n")
    print("wrote", [c["path"] for c in changes])


if __name__ == "__main__":
    main()
