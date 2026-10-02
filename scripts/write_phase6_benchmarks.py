"""Write the Phase 6 block of benchmarks.json (usage_phase6_2025) from
data/ncaa_2025/derived/phase6_inputs_2025.json (scripts/build_phase6_usage.py, build_phase6_subs.py):
pitcher usage on the 50 full-season teams of the 2025 play-by-play at a 56-game equivalent
(appearances of a team's busiest, 5th and 10th busiest pitchers; relief-only pitchers, 3 or fewer
starts, with 40+ and 60+ IP; the top three pitchers' innings and their split into Fri-Sun starts,
other starts and relief), and distinct batters per team-game. Tolerance 3 SE (bootstrap over teams,
or over games for batters). Errors and stolen bases are gated on their existing league_totals_2025
rows; the deferred rows on their existing blocks. Every write is recorded in
data/ncaa_2025/derived/benchmark_changes_phase6.json.

    python3 scripts/write_phase6_benchmarks.py
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

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
        if isinstance(v, dict) and "value" in v:
            new[k] = {"value": v["value"], "tol": round(3 * v["se"], 3), **({} if k in GATED else {"gate": "report"})}
    new["batters_per_team_game"] = {"value": sb["batters_per_team_game"]["value"], "tol": round(3 * sb["batters_per_team_game"]["se"], 3)}
    b = json.loads(BENCH.read_text())
    changes = []
    if json.loads(json.dumps(b.get("usage_phase6_2025"))) != json.loads(json.dumps(new)):
        changes.append({"path": "usage_phase6_2025", "old": b.get("usage_phase6_2025"), "new": new})
    b["usage_phase6_2025"] = new
    BENCH.write_text(dumps_compact(b) + "\n")
    if changes:
        log = D / "benchmark_changes_phase6.json"
        prior = json.loads(log.read_text()) if log.exists() else []
        log.write_text(json.dumps(prior + [{**c, "date": datetime.date.today().isoformat()} for c in changes], indent=1, default=str) + "\n")
    print("wrote", [c["path"] for c in changes])


if __name__ == "__main__":
    main()
