"""Real 2025 team pitching against fielding, for the "teams under 4.00 ERA" watch item (owner request 2026-10-05):
is a team's run prevention from pitching correlated with its fielding, and how many errors do the best run-prevention
teams make?

Tables (data/ncaa_leaders/team_era_2025.csv and team_fielding_2025.csv): extracted from the NCAA.com team pages
https://www.ncaa.com/stats/baseball/d1/2024/team/211[/pN] (team ERA: G, IP, R, ER, ERA) and .../team/212[/pN]
(fielding percentage: G, PO, A, E, PCT), every page, every Division I team, fetched 2026-10-05. URL year 2024 is the
2025 season. Full seasons, postseason included, every game (non-Division I opponents included). The raw pages were removed
on 2026-10-08 (www.ncaa.com now disallows AI agents; owner decision: extracted tables only, never refetched).

Rows: correlation across teams of ERA with errors per game and with fielding percentage; errors per game and
earned share for the 50 best run-prevention teams (by runs allowed per game, and by ERA) against all teams.
Writes the "era_fielding" block of data/ncaa_2025/derived/phase7_benchmarks.json.

    python3 scripts/build_phase7_era_fielding.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from engine.report7 import era_fielding_measures as measures  # noqa: E402
TABLES = {211: ROOT / "data/ncaa_leaders/team_era_2025.csv", 212: ROOT / "data/ncaa_leaders/team_fielding_2025.csv"}
BENCH = ROOT / "data/ncaa_2025/derived/phase7_benchmarks.json"


def pages(stat: int) -> pd.DataFrame:
    d = pd.read_csv(TABLES[stat], dtype=str, keep_default_na=False).drop_duplicates("Team")
    for c in d.columns:
        if c not in ("Team", "Rank"):
            d[c] = pd.to_numeric(d[c].str.replace(",", ""), errors="coerce")
    return d


def ip_outs(ip: float) -> int:
    whole = int(ip); return 3 * whole + int(round(10 * (ip - whole)))


def main() -> None:
    p, f = pages(211), pages(212)
    d = p.merge(f, on="Team", suffixes=("", "_f"))
    d["outs"] = d.IP.map(ip_outs)
    out = measures(27 * d.ER / d.outs, d.R / d.G, d.E / d.G_f, d.PCT, d.ER / d.R)
    out.update({"n_teams": int(len(d)), "n_era_page": int(len(p)), "n_fielding_page": int(len(f)), "season": "2025",
                "source": "NCAA.com team pages 211 (ERA) and 212 (fielding %), URL year 2024, every page, fetched 2026-10-05",
                "note": "means over teams (earned share: mean of team ER/R)"})
    bench = json.loads(BENCH.read_text())
    bench["era_fielding"] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in out.items()}
    BENCH.write_text(json.dumps(bench, indent=1) + "\n")
    for k, v in out.items():
        print(f"{k:28s} {v}")


if __name__ == "__main__":
    main()
