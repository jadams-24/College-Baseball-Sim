"""Check engine.rpi against the NCAA's published RPI before the 2026 field was selected.

Published: https://www.ncaa.com/rankings/baseball/d1/rpi, "Through Games May. 24 2026" (the page froze
there; the field was announced May 25), saved in data/ncaa_2026/rpi/. It gives each team's rank and its
road / neutral / home Division I records and non-Division I record, but not the RPI value.
Results: WarrenNolan.com team schedules through May 24, 2026 (data/ncaa_2026/warrennolan/games_2026.csv,
scripts/parse_warrennolan_2026.py), names mapped in data/ncaa_2026/team_name_map.csv.

Reports how many teams' published road/neutral/home records the results reproduce, then the rank
agreement of the computed RPI with the published ranks (Spearman, exact rank matches, largest gaps), and
the same with unweighted WP (site weighting off) as a check that the weighting is in the published RPI.

    python3 scripts/check_rpi_2026.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import phase7  # noqa: E402
from engine.rpi import rpi  # noqa: E402

THROUGH = "2026-05-24"
OUT = ROOT / "data/ncaa_2026/rpi/rpi_check_2026.json"


def wl(s: str) -> tuple[int, int]:
    w, l = str(s).split("-")[:2]
    return int(w), int(l)


def main() -> None:
    pub = pd.read_csv(ROOT / "data/ncaa_2026/rpi/ncaa_rpi_through_2026-05-24.csv")
    g = pd.read_csv(ROOT / "data/ncaa_2026/warrennolan/games_2026.csv")
    nm = pd.read_csv(ROOT / "data/ncaa_2026/team_name_map.csv")
    cols = list(nm.columns)
    to_ncaa = dict(zip(nm[cols[1]], nm[cols[0]])) if "ncaa" in cols[0].lower() else dict(zip(nm[cols[0]], nm[cols[1]]))
    g = g[(g.date <= THROUGH) & (g.status.astype(str).str.lower() == "final")]
    g = g[g.home_d1.astype(bool) & g.away_d1.astype(bool)].copy()
    g["home"] = g.home.map(lambda x: to_ncaa.get(x, x)); g["away"] = g.away.map(lambda x: to_ncaa.get(x, x))
    g = g[g.home_score != g.away_score]
    games = [(h, a, hs > as_, bool(n)) for h, a, hs, as_, n in zip(g.home, g.away, g.home_score, g.away_score, g.neutral)]
    # records by site, against the published splits
    rec = {}
    for h, a, hw, n in games:
        for t, won, site in ((h, hw, "neutral" if n else "home"), (a, not hw, "neutral" if n else "road")):
            r = rec.setdefault(t, {"road": [0, 0], "neutral": [0, 0], "home": [0, 0]})
            r[site][0 if won else 1] += 1
    match = sum(all(tuple(rec.get(s, {}).get(k, [0, 0])) == wl(row[k]) for k in ("road", "neutral", "home"))
                for s, row in pub.set_index("school").iterrows())
    out = {"teams_published": int(len(pub)), "teams_records_match": int(match), "games": len(games)}
    for label, weights in (("weighted", dict(phase7.RPI_SITE_WEIGHT)), ("unweighted", {k: 1.0 for k in phase7.RPI_SITE_WEIGHT})):
        saved = dict(phase7.RPI_SITE_WEIGHT)
        phase7.RPI_SITE_WEIGHT.update(weights)
        r = rpi(games)
        phase7.RPI_SITE_WEIGHT.update(saved)
        calc = pd.Series({t: v["rpi"] for t, v in r.items()}).rank(ascending=False, method="min")
        p = pub.set_index("school")["rank"]
        common = p.index.intersection(calc.index)
        d = (calc[common] - p[common]).abs()
        out[label] = {"teams": int(len(common)), "spearman": float(pd.Series(calc[common]).corr(p[common], method="spearman")),
                      "exact_rank": int((d == 0).sum()), "within_1": int((d <= 1).sum()), "within_3": int((d <= 3).sum()),
                      "top64_exact": int(((d == 0) & (p[common] <= 64)).sum()),
                      "largest_gaps": {t: [int(p[t]), int(calc[t])] for t in d.sort_values(ascending=False).index[:8]}}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
