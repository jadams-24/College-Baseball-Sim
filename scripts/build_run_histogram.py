"""Build the runs-per-team-game distribution from the season scoreboard table
and write it into benchmarks.json (game_structure.run_distribution_per_team_game).

Only games in state "final" with both scores present count, each game once.
A team-game is counted only for the D1 side(s): teams tagged with a D1
conference (or "DI Independent"). Non-D1 opponents' run totals are dropped.

Run from the repo root after scripts/pull_scoreboard.py:
    python3 scripts/build_run_histogram.py --season 2025
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import json
import statistics
from pathlib import Path

D1_CONFERENCES = {
    "ACC", "America East", "ASUN", "Atlantic 10", "Big 12", "Big East", "Big South",
    "Big Ten", "Big West", "CAA", "CUSA", "DI Independent", "Horizon", "Ivy League",
    "MAAC", "MAC", "Mountain West", "MVC", "NEC", "OVC", "Patriot", "SEC", "SoCon",
    "Southland", "Summit League", "Sun Belt", "SWAC", "The American", "WAC", "WCC",
}
BINS = 16  # P(0)..P(14), P(15+)
TOL_PER_BIN = 0.01          # ~4 sampling SEs at 16k team-games; leaves room for model error
TOL_TOTAL_VARIATION = 0.04


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, required=True)
    ap.add_argument("--benchmarks", default="benchmarks.json")
    a = ap.parse_args()
    base = Path(f"data/ncaa_{a.season}")
    games_csv = base / "scoreboard" / f"games_{a.season}.csv"
    manifest = json.loads((base / "scoreboard" / "manifest.json").read_text())

    seen, games = set(), []
    for r in csv.DictReader(games_csv.open()):
        if r["state"] != "final" or r["home_score"] == "" or r["away_score"] == "":
            continue
        if r["url"] in seen:
            continue
        seen.add(r["url"])
        games.append(r)

    runs, by_conf = [], collections.defaultdict(list)
    for g in games:
        for side in ("home", "away"):
            conf = g[f"{side}_conf"]
            if conf in D1_CONFERENCES:
                x = int(g[f"{side}_score"])
                runs.append(x)
                by_conf[conf].append(x)
    n = len(runs)
    counts = collections.Counter(min(x, BINS - 1) for x in runs)
    bins = [round(counts[i] / n, 4) for i in range(BINS)]
    margins = [abs(int(g["home_score"]) - int(g["away_score"])) for g in games]

    result = {
        "conf": "A",
        "src": "data.ncaa.com scoreboard JSON, every D1 game day of the season; see data/ncaa_%d/scoreboard/manifest.json" % a.season,
        "fetched": manifest["fetched_on"],
        "n_games": len(games),
        "n_team_games": n,
        "mean_runs_per_team_game": round(sum(runs) / n, 3),
        "sd_runs_per_team_game": round(statistics.pstdev(runs), 3),
        "bins": bins,
        "counts": [counts[i] for i in range(BINS)],
        "tol_per_bin": TOL_PER_BIN,
        "tol_total_variation": TOL_TOTAL_VARIATION,
        "share_games_margin_10plus": round(sum(m >= 10 for m in margins) / len(margins), 4),
        "home_win_pct": round(sum(int(g["home_score"]) > int(g["away_score"]) for g in games) / len(games), 4),
        "note": "Bins are P(0)..P(14), P(15+) per D1 team-game, final games only, run-rule games included as played. margin_10plus is an upper bound on run-rule frequency, not the rate itself.",
    }
    per_conf = {c: {"n_team_games": len(v), "r_g": round(sum(v) / len(v), 3)} for c, v in sorted(by_conf.items())}
    out = {"run_distribution_per_team_game": result, "runs_per_team_game_by_conference": per_conf}
    (base / f"run_distribution_{a.season}.json").write_text(json.dumps(out, indent=2) + "\n")

    # Replace only the one benchmark line; leave every other byte of the file alone.
    text = Path(a.benchmarks).read_text()
    old = '    "run_distribution_per_team_game": {"conf": "D", "note": "compute histogram P(0),P(1),...,P(15+) from PBP in Phase 1; required for gate"}'
    if old not in text:
        # Already replaced: swap the existing block between its key and the closing "  }" of game_structure.
        start = text.index('    "run_distribution_per_team_game": ')
        end = text.index("\n  }", start)
        old = text[start:end]
    compact = {k: (json.dumps(v) if isinstance(v, list) else v) for k, v in result.items()}
    body = json.dumps(compact, indent=6).replace("\n}", "\n    }")
    for k in ("bins", "counts"):  # arrays on one line
        body = body.replace(json.dumps(compact[k]), compact[k])
    new_block = "    \"run_distribution_per_team_game\": " + body
    assert text.count(old) == 1
    Path(a.benchmarks).write_text(text.replace(old, new_block))
    json.loads(Path(a.benchmarks).read_text())  # must still parse
    print(json.dumps(result, indent=1))
    print("per conference R/G:", {c: v["r_g"] for c, v in per_conf.items()})


if __name__ == "__main__":
    main()
