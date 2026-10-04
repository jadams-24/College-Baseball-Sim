"""Parse the NCAA.com national leader pages (data/ncaa_leaders/raw/) into ncaa_leaders.json.

Pages: https://www.ncaa.com/stats/baseball/d1/{year}/individual/{stat}, page 1 (the top 50
and ties). NCAA.com labels a season by the academic year it starts: /2023/ is the 2024
season, /2024/ is 2025, /2025/ is 2026. Stats: 470 home runs, 200 batting average,
205 ERA, 356 strikeouts, 863 appearances. The 2023 season (no tables at /2022/) comes from
the NCAA record book's 2023 leaders, transcribed below.

Team pages (data/ncaa_leaders/raw_team/, fetched 2026-10-04): https://www.ncaa.com/stats/baseball/d1/{year}/team/{stat},
page 1 (top 50) for 210 batting average, 211 ERA and 323 home runs per game, URL years 2023-2025
(/2022/ has no tables). The year mapping is checked against the 2025 scoreboard: the /2024/ table's
games match each listed team's 2025 games (Coastal Carolina 69, Georgia 60, Northeastern 60).

    python3 scripts/parse_ncaa_leaders.py
"""
from __future__ import annotations

import gzip
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/ncaa_leaders/raw"
OUT = ROOT / "data/ncaa_leaders/ncaa_leaders.json"
URL = "https://www.ncaa.com/stats/baseball/d1/{year}/individual/{stat}"
SEASON_OF_URL_YEAR = {2023: 2024, 2024: 2025, 2025: 2026}
STATS = {470: ("hr", "HR"), 200: ("ba", "BA"), 205: ("era", "ERA"), 356: ("k", "SO"), 863: ("app", "App")}
RAW_TEAM = ROOT / "data/ncaa_leaders/raw_team"
TEAM_URL = "https://www.ncaa.com/stats/baseball/d1/{year}/team/{stat}"
TEAM_STATS = {210: "team_ba", 211: "team_era", 323: "team_hr_pg"}
RECORD_BOOK_2023 = {
    "source": "NCAA Division I baseball record book, 2024 edition, 2023 individual leaders: http://fs.ncaa.org/Docs/stats/baseball_RB/2024/D1.pdf",
    "hr": [{"name": "Jac Caglianone", "team": "Florida", "G": 71, "HR": 33}, {"name": "Brock Wilken", "team": "Wake Forest", "G": 66, "HR": 31}],
    "ba": [{"name": "JJ Wetherholt", "team": "West Virginia", "G": 55, "AB": 225, "H": 101, "BA": 0.449}],
    "k": [{"name": "Paul Skenes", "team": "LSU", "IP": 122.2, "SO": 209}],
}


def table(path: Path) -> list[dict]:
    text = gzip.decompress(path.read_bytes()).decode("utf-8")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S)
    cells = [[html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)] for r in rows]
    head, body = cells[0], [c for c in cells[1:] if len(c) == len(cells[0])]
    return [dict(zip(head, c)) for c in body]


def num(v: str) -> float:
    return float(v.replace(",", ""))


def main() -> None:
    out = {"_note": "Top 50 (and ties) per stat from NCAA.com's national leader pages, fetched 2026-10-01; "
                    "season = the year the season is played (NCAA.com URL year + 1). Qualification is NCAA.com's: "
                    "BA 2.0 PA per team game and 75% of team games; ERA 1 IP per team game.",
           "seasons": {}}
    for url_year, season in SEASON_OF_URL_YEAR.items():
        s = {}
        for stat, (key, col) in STATS.items():
            rows = table(RAW / f"s{stat}_{url_year}.html.gz")
            s[key] = {"url": URL.format(year=url_year, stat=stat), "rows": rows}
            vals = [num(r[col]) for r in rows]
            if key == "hr":
                s["hr_top5"] = sorted(vals, reverse=True)[:5]
                s["n_hr_30"] = sum(v >= 30 for v in vals)
                s["n_hr_25"] = sum(v >= 25 for v in vals)
                s["hr_list_min"] = min(vals)
            elif key == "era":
                s["era_low5"] = sorted(vals)[:5]
            elif key in ("ba", "k"):
                s[f"{key}_top5"] = sorted(vals, reverse=True)[:5]
            else:
                s["app_max"] = max(vals)
        out["seasons"][str(season)] = s
    out["seasons"]["2023"] = RECORD_BOOK_2023
    # team leaders: best BA, best ERA, most HR per game (recomputed from HR and G), and the teams
    # with ERA under 4.00 (all inside each season's top 50, whose last ERA is above 4.7)
    out["team_seasons"] = {}
    for url_year, season in SEASON_OF_URL_YEAR.items():
        s = {}
        for stat, key in TEAM_STATS.items():
            s[key] = {"url": TEAM_URL.format(year=url_year, stat=stat), "rows": table(RAW_TEAM / f"s{stat}_{url_year}.html.gz")}
        ba, era, hr = s["team_ba"]["rows"], s["team_era"]["rows"], s["team_hr_pg"]["rows"]
        eras = [num(r["ERA"]) for r in era]
        assert max(eras) >= 4.0, "teams under 4.00 ERA run past the top 50"
        top_ba = max(ba, key=lambda r: num(r["BA"])); top_era = min(era, key=lambda r: num(r["ERA"]))
        top_hr = max(hr, key=lambda r: num(r["HR"]) / num(r["G"]))
        s["team_ba_max"] = {"value": num(top_ba["BA"]), "team": top_ba["Team"], "G": int(num(top_ba["G"]))}
        s["best_team_era"] = {"value": num(top_era["ERA"]), "team": top_era["Team"], "G": int(num(top_era["G"]))}
        s["team_hr_per_game_max"] = {"value": round(num(top_hr["HR"]) / num(top_hr["G"]), 3), "team": top_hr["Team"],
                                     "HR": int(num(top_hr["HR"])), "G": int(num(top_hr["G"]))}
        s["teams_era_under_4"] = {"value": int(sum(e < 4.0 for e in eras))}
        out["team_seasons"][str(season)] = s
    OUT.write_text(json.dumps(out, indent=1))
    for season, s in sorted(out["seasons"].items()):
        if "hr_top5" in s:
            print(season, "HR", s["hr_top5"], "30+", s["n_hr_30"], "25+", s["n_hr_25"], "BA", s["ba_top5"], "ERA", s["era_low5"], "K", s["k_top5"], "App max", s["app_max"])
    for season, s in sorted(out["team_seasons"].items()):
        print(season, {k: s[k] for k in ("team_ba_max", "best_team_era", "team_hr_per_game_max", "teams_era_under_4")})


if __name__ == "__main__":
    main()
