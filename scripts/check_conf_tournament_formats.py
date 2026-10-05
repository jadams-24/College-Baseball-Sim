"""Conference tournament formats inferred from the 2025 game sequence, checked against the published ones.

Inference uses only the scoreboard feed (data/ncaa_2025/scoreboard): regular-season conference games
come in series (the same pair three times within four days), tournament games do not. For each
conference the regular season ends with its last series game; same-conference games after it, through
May 26 (selection day), are tournament games. (A tournament played as best-of-three series, the Patriot
League's, reads as a series and is reported as not found.)
From them: teams taking part, games, the champion (winner of the last game), losses of each eliminated
team (1: single elimination, 2: double elimination; pool play shows teams leaving with 1 or 2 losses),
and the site (one listed home team for nearly every game: a host's park or a neutral site's designated
home team rotates, so the distinct home teams are reported).
Published: data/conf_tournaments/formats_2025.json (teams, format code, games_min / games_max).
Champion: the conference's automatic bid in data/ncaa_brackets/brackets_2015_2025.json.

    python3 scripts/check_conf_tournament_formats.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.brackets import brackets, feed_name, name_map  # noqa: E402

SELECTION = "2025-05-26"
OUT = ROOT / "data/conf_tournaments/format_check_2025.json"


def main() -> None:
    teams = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    conf_of = dict(zip(teams.team, teams.conference))
    d = pd.read_csv(ROOT / "data/ncaa_2025/scoreboard/games_2025.csv")
    d = d[(d.state == "final")].drop_duplicates("url")
    d["date"] = pd.to_datetime(d.date)
    d = d[d.home.isin(conf_of) & d.away.isin(conf_of) & (d.date <= SELECTION)]
    d = d[d.home.map(conf_of) == d.away.map(conf_of)]
    pub = json.loads((ROOT / "data/conf_tournaments/formats_2025.json").read_text())["conferences"]
    br = brackets()["2025"]; m = name_map()
    autos = {t["conference"]: t["team"] for t in br["teams"] if t["bid"] == "auto"}
    out = {}
    for conf, p in sorted(pub.items()):
        g = d[d.home.map(conf_of) == conf].sort_values("date")
        # series games: the pair plays at least three times within four days
        pair = g.apply(lambda r: tuple(sorted((r.home, r.away))), axis=1)
        series = [((pair == pr) & ((g.date - dt).abs() <= pd.Timedelta(days=3))).sum() >= 3 for pr, dt in zip(pair, g.date)]
        end = g.date[pd.Series(series, index=g.index)].max()
        t = g[g.date > end]
        if t.empty:
            out[conf] = {"inferred": None, "published": p.get("format")}
            continue
        part = sorted(set(t.home) | set(t.away))
        losses = {x: 0 for x in part}
        for _, r in t.iterrows():
            losses[r.away if r.home_score > r.away_score else r.home] += 1
        last = t.iloc[-1]
        champ = last.home if last.home_score > last.away_score else last.away
        elim = [losses[x] for x in part if x != champ]
        inf = {"teams": len(part), "games": int(len(t)), "dates": [t.date.min().date().isoformat(), t.date.max().date().isoformat()],
               "champion": champ, "losses_of_eliminated": {str(k): elim.count(k) for k in sorted(set(elim))},
               "champion_losses": losses[champ], "distinct_home_teams": int(t.home.nunique())}
        if max(elim, default=0) <= 1:
            kind = "single elimination"
        elif min(elim) >= 2:
            kind = "double elimination"
        else:
            kind = "mixed (pool play, play-in or byes before double elimination, or series)"
        inf["kind"] = kind
        auto = autos.get(conf) or next((v for k, v in autos.items() if k.lower().startswith(conf.lower()[:4])), None)
        feed = set(d.home) | set(d.away)
        auto_feed = feed_name(auto, feed, m) if auto else None
        gmin, gmax = p.get("games_min"), p.get("games_max")
        out[conf] = {"inferred": inf, "published": {k: p.get(k) for k in ("teams", "format", "site", "games_min", "games_max")},
                     "teams_match": inf["teams"] == p.get("teams"),
                     "games_in_published_range": (gmin is None or gmin <= inf["games"]) and (gmax is None or inf["games"] <= gmax),
                     "champion_is_auto_bid": auto_feed == champ, "auto_bid": auto}
    ok = {k: sum(1 for v in out.values() if v.get(k)) for k in ("teams_match", "games_in_published_range", "champion_is_auto_bid")}
    OUT.write_text(json.dumps({"summary": ok, "conferences": out}, indent=1) + "\n")
    print("conferences:", len(out), ok)
    for c, v in out.items():
        i = v["inferred"]
        if i is None:
            print(f"  {c}: no tournament games found after the regular season")
            continue
        flag = "" if (v["teams_match"] and v["games_in_published_range"] and v["champion_is_auto_bid"]) else "  <-- check"
        print(f"  {c}: inferred {i['teams']} teams, {i['games']} games, {i['kind']}, eliminated losses {i['losses_of_eliminated']}, "
              f"home teams {i['distinct_home_teams']} | published {v['published']['teams']} teams, {v['published']['format']}, "
              f"games {v['published']['games_min']}-{v['published']['games_max']} | champion {i['champion']} (auto {v['auto_bid']}){flag}")


if __name__ == "__main__":
    main()
