"""Conference tournament formats inferred from the 2025 game sequences, checked against the published ones.

Sequences: WarrenNolan 2025 team schedules (data/ncaa_2025/warrennolan/team_games_2025.csv), whose event
label marks each conference tournament game ("SEC Tournament - Game 7"). The NCAA scoreboard feed cannot be
used: most of its 2025 tournament games are placeholders against "TBA" without a score.
From the sequence alone, per conference: teams taking part, games, champion (winner of the last game, or of
the last series), losses of each eliminated team (1: single elimination, 2: double elimination; pool play and
play-ins mix them), and whether the games were at one park (one listed home team for the host's games, the
rest neutral) or on campuses.
Published: data/conf_tournaments/formats_2025.json (teams, format code, games_min / games_max, site).
Champion: the conference's automatic bid in data/ncaa_brackets/brackets_2015_2025.json.

    python3 scripts/check_conf_tournament_formats.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.brackets import brackets, name_map  # noqa: E402

OUT = ROOT / "data/conf_tournaments/format_check_2025.json"


def norm(x: str) -> str:
    return str(x).lower().replace(".", "").replace("state", "st").replace("–", "-").replace(" ", "")


def main() -> None:
    teams = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    conf_of = {norm(t): c for t, c in zip(teams.team, teams.conference)}
    nm = pd.read_csv(ROOT / "data/ncaa_2026/team_name_map.csv")
    wn_to_ncaa = dict(zip(nm.warrennolan_name, nm.ncaa_name))
    conf = lambda wn: conf_of.get(norm(wn_to_ncaa.get(wn, wn)))
    t = pd.read_csv(ROOT / "data/ncaa_2025/warrennolan/team_games_2025.csv")
    t["date"] = pd.to_datetime(t.date)
    t = t[t.event.astype(str).str.contains("Tournament|Championship", case=False, na=False) & (t.date.dt.month == 5) & (t.status == "final")].copy()
    t["tourn"] = t.event.str.replace(r" - .*", "", regex=True)
    pub = json.loads((ROOT / "data/conf_tournaments/formats_2025.json").read_text())["conferences"]
    m = name_map()
    autos = {}                                   # 2025 conference (as in teams_2025.csv) -> its automatic bid
    for x in brackets()["2025"]["teams"]:
        if x["bid"] == "auto":
            c_ = conf_of.get(norm(m.get(x["team"], x["team"]))) or conf_of.get(norm(x["team"]))
            autos[c_] = x["team"]
    out = {}
    for name, g in t.groupby("tourn"):
        c = Counter(conf(x) for x in g.team).most_common(1)[0][0]
        # one row per game: the home side's page entry (or the first team alphabetically at a neutral site)
        g = g.assign(gno=g.event.str.extract(r"Game (\d+)", expand=False).astype(float).fillna(999))   # "Championship Game" last
        g = g.sort_values(["date", "gno", "team"])
        games = g.drop_duplicates(["date", "event"], keep="first")
        part = sorted(set(g.team) | set(g.opp))          # both sides: a team without a 2025 page appears only as an opponent
        loss = Counter(r.team if r.wl == "L" else r.opp for r in games.itertuples())
        last = games.iloc[-1]
        champ = last.team if last.wl == "W" else last.opp
        elim = [loss[x] for x in part if x != champ]
        kind = "single elimination" if max(elim, default=0) <= 1 else ("double elimination" if min(elim) >= 2 else "mixed")
        sites = Counter(g.site)
        hosts = Counter(g[g.site == "home"].team)
        p = pub.get(c, {})
        auto = autos.get(c)
        out[c] = {"event": name, "inferred": {"teams": len(part), "games": int(len(games)), "kind": kind, "champion": champ,
                                              "losses_of_eliminated": {str(kk): elim.count(kk) for kk in sorted(set(elim))},
                                              "site_labels": dict(sites), "teams_playing_at_home": dict(hosts)},
                  "published": {kk: p.get(kk) for kk in ("teams", "format", "site_detail", "games_min", "games_max")},
                  "teams_match": len(part) == p.get("teams"),
                  "games_in_published_range": p.get("games_min", 0) <= len(games) <= p.get("games_max", 99),
                  "champion_is_auto_bid": bool(auto) and conf(champ) == c and norm(m.get(auto, auto)) in (norm(wn_to_ncaa.get(champ, champ)), norm(champ)),
                  "auto_bid": auto}
    ok = {kk: sum(1 for v in out.values() if v[kk]) for kk in ("teams_match", "games_in_published_range", "champion_is_auto_bid")}
    OUT.write_text(json.dumps({"source": "WarrenNolan 2025 schedules (event labels)", "summary": ok, "conferences": out}, indent=1) + "\n")
    print("conferences:", len(out), ok)
    for c, v in sorted(out.items()):
        i, p = v["inferred"], v["published"]
        flag = "" if v["teams_match"] and v["games_in_published_range"] and v["champion_is_auto_bid"] else "  <-- check"
        print(f"  {c}: {i['teams']} teams, {i['games']} games, {i['kind']} {i['losses_of_eliminated']}, home-labelled {i['teams_playing_at_home']} | "
              f"published {p['teams']} teams, {p['format']}, {p['games_min']}-{p['games_max']}, {p['site_detail']} | champion {i['champion']} (auto {v['auto_bid']}){flag}")


if __name__ == "__main__":
    main()
