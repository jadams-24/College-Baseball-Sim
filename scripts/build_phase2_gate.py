"""Phase 2 gate benchmarks and schedule inputs.

  team_strength_2025      team R/G and RA/G spread across all D1 teams and by tier, from the
                          full-season scoreboard (every 2025 D1-vs-D1 final). Conf A.
  schedule_mix            opponent-tier mix of nonconference games by own tier, weekend vs
                          midweek, from the same scoreboard (written to phase2_inputs).
  qualified_players_2025  percentiles of BA, OBP, ISO, K%, BB% (qualified batters: NCAA rule,
                          2.0 PA per team game and 75% of team games) and ERA, K/9 (1 IP per
                          team game), pooled from WMT full-season teams and the 13 Sidearm
                          season pages, reweighted to the D1 tier mix (sparse tiers pooled with their nearest tier first,
                          scripts/lib/pooling.py). Tolerances 3 SE from a
                          team-cluster bootstrap within tier. Conf B.
  leaderboards_2025       full-population extremes from FanGraphs (pitchers >= 50 IP, team ERA,
                          team BA, team HR; conf A) and, informationally, sample tops for BA/HR.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.players import load_pa, name_map  # noqa: E402
from lib.pooling import describe, pool_cells  # noqa: E402
from sidearm_totals import hydrate  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.benchmarks import MIN_CELL_N_PERCENTILE  # noqa: E402

TIERS = ("p4", "mid", "low")
INPUTS = Path("data/ncaa_2025/derived/phase2_inputs_2025.json")
OUT = Path("data/ncaa_2025/derived/phase2_gate_2025.json")
BOOT = 400
RNG = np.random.default_rng(20251001)
SIDEARM_TEAMS = {"rolltide.com": "Alabama", "hailstate.com": "Mississippi St.", "calbears.com": "California", "pittsburghpanthers.com": "Pittsburgh",
                 "baylorbears.com": "Baylor", "troytrojans.com": "Troy", "gobearkats.com": "Sam Houston", "missouristatebears.com": "Missouri St.",
                 "gopoly.com": "Cal Poly", "sfajacks.com": "SFA", "bucknellbison.com": "Bucknell", "tommiesports.com": "St. Thomas (MN)", "brownbears.com": "Brown"}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def ip_from_text(v) -> float:
    v = num(v)
    if np.isnan(v):
        return np.nan
    whole = int(v)
    return whole + round(v - whole, 1) * 10 / 3


def team_strength(teams: pd.DataFrame) -> tuple[dict, dict]:
    sb = pd.read_csv("data/ncaa_2025/scoreboard/games_2025.csv")
    sb = sb[(sb.state == "final") & sb.home_score.notna() & sb.away_score.notna()].drop_duplicates("url").copy()
    tier = dict(zip(teams.team, teams.tier))
    conf = dict(zip(teams.team, teams.conference))
    sb["wd"] = pd.to_datetime(sb.date).dt.dayofweek
    rows = []
    for side, opp in (("home", "away"), ("away", "home")):
        rows.append(pd.DataFrame({"team": sb[side], "opp": sb[opp], "r": sb[f"{side}_score"].astype(float), "ra": sb[f"{opp}_score"].astype(float),
                                  "wd": sb.wd, "conf_game": (sb.home_conf == sb.away_conf) & (sb.home_conf != "DI Independent")}))
    tg = pd.concat(rows)
    tg = tg[tg.team.isin(tier) & tg.opp.isin(tier)].copy()
    tg["tier"] = tg.team.map(tier); tg["otier"] = tg.opp.map(tier)
    per = tg.groupby("team").agg(g=("r", "size"), rg=("r", "mean"), rag=("ra", "mean"), rvar=("r", "var"), ravar=("ra", "var"), tier=("tier", "first"))
    out = {"_note": "Every 2025 D1-vs-D1 final in the NCAA scoreboard feed (data/ncaa_2025/scoreboard). Team season runs scored and allowed per game; SDs across teams include each team's game-to-game sampling noise, as the simulated seasons do. Tolerances are 3 SE of the real statistic. Gate for Phase 2.",
           "conf": "A", "n_teams": int(len(per)), "games_per_team_mean": round(per.g.mean(), 2)}

    def block(d: pd.DataFrame) -> dict:
        n = len(d)
        res = {"n_teams": int(n)}
        for col, name in (("rg", "r_per_game"), ("rag", "ra_per_game")):
            sd = d[col].std(ddof=1)
            noise = (d["rvar" if col == "rg" else "ravar"] / d.g).mean()
            res[name] = {"mean": round(d[col].mean(), 3), "mean_tol": round(3 * sd / np.sqrt(n), 3),
                         "sd": round(sd, 3), "sd_tol": round(3 * sd / np.sqrt(2 * (n - 1)), 3),
                         "sd_true": round(float(np.sqrt(max(sd ** 2 - noise, 0))), 3)}
        return res
    out["all"] = block(per)
    out["by_tier"] = {t: block(per[per.tier == t]) for t in TIERS}
    # schedule mix for nonconference games
    nc = tg[~tg.conf_game]
    mix = {}
    for daytype, d in (("weekend", nc[nc.wd.isin([3, 4, 5, 6])]), ("midweek", nc[~nc.wd.isin([3, 4, 5, 6])])):
        mix[daytype] = {t: {o: round(v, 4) for o, v in d[d.tier == t].otier.value_counts(normalize=True).items()} for t in TIERS}
        # joint share of nonconference games by unordered tier pair (each game appears once per side above)
        pr = Counter("|".join(sorted((a, b), key=TIERS.index)) for a, b in zip(d.tier, d.otier))
        mix[f"{daytype}_pairs"] = {k: round(v / sum(pr.values()), 4) for k, v in sorted(pr.items())}
    mix["conference_games_share"] = round(float(tg.conf_game.mean()), 4)
    mix["home_win_pct"] = round(float((sb.home_score > sb.away_score).mean()), 4)
    return out, mix


def qualified(teams: pd.DataFrame) -> tuple[dict, dict]:
    pa = load_pa()
    gm = pd.read_csv("data/ncaa_2025/pbp/parsed/games_2025.csv")
    rev = pd.read_csv("data/ncaa_2025/pbp/parsed/runner_events_2025.csv.gz")
    rc = pd.read_csv("data/ncaa_2025/pbp/parsed/runs_charged_2025.csv.gz")
    tier_id = dict(zip(teams.ncaa_team_id, teams.tier))
    name_id = dict(zip(teams.team, teams.ncaa_team_id))
    g2 = pd.concat([gm[["game_id", "home_team_id"]].rename(columns={"home_team_id": "t"}), gm[["game_id", "away_team_id"]].rename(columns={"away_team_id": "t"})])
    gpt = g2.groupby("t").game_id.nunique()
    full = set(gpt[gpt >= 40].index)
    r = pa.result
    pa["H"] = r.isin(["1B", "2B", "3B", "HR"]); pa["TB"] = r.map({"1B": 1, "2B": 2, "3B": 3, "HR": 4}).fillna(0)
    pa["BBx"] = r.isin(["BB", "IBB"]); pa["AB"] = ~r.isin(["BB", "IBB", "HBP", "CI", "SF", "SH"])
    b = pa[pa.bat_team_id.isin(full)].groupby(["bat_team_id", "bkey"]).agg(
        pa=("result", "size"), ab=("AB", "sum"), h=("H", "sum"), tb=("TB", "sum"), bb=("BBx", "sum"), hbp=("result", lambda s: (s == "HBP").sum()),
        sf=("result", lambda s: (s == "SF").sum()), k=("result", lambda s: (s == "K").sum()), hr=("result", lambda s: (s == "HR").sum()), g=("game_id", "nunique")).reset_index()
    b["tg"] = b.bat_team_id.map(gpt); b["tier"] = b.bat_team_id.map(tier_id); b["team"] = b.bat_team_id.astype(str); b["src"] = "wmt"
    # pitchers: outs from plate appearances plus base-running outs while on the mound
    pa = pa.sort_values(["game_id", "group_id"])
    rev = rev.merge(pa[["game_id", "group_id", "pkey", "pit_team_id"]], on=["game_id", "group_id"], how="left") if "pkey" not in rev else rev
    seq = pd.concat([pa[["game_id", "group_id", "pit_team_id", "pkey", "half", "inning"]].assign(outs=pa.outs_on_play, k=(pa.result == "K").astype(int)),
                     rev.drop_duplicates(["group_id", "from_base"])[["game_id", "group_id", "half", "inning"]].assign(outs=(rev.drop_duplicates(["group_id", "from_base"]).to_base == 0).astype(int), k=0)])
    seq = seq.sort_values(["game_id", "group_id"])
    seq[["pit_team_id", "pkey"]] = seq.groupby(["game_id", "inning", "half"])[["pit_team_id", "pkey"]].ffill()
    seq = seq[seq.pkey.notna()]
    pm = name_map(rc.rename(columns={"pitcher": "pname"}), "pit_team_id", "pname")
    rc["pkey"] = [pm[(t, n)] for t, n in zip(rc.pit_team_id, rc.pitcher)]
    # charged-run names come from the same scorers, so map them onto the PA keys of the same team
    pk = pa.groupby("pit_team_id").pkey.unique().apply(set).to_dict()
    def align(t, k):
        ks = pk.get(t, set())
        if k in ks:
            return k
        cand = [x for x in ks if set(k.split()) <= set(x.split()) or set(x.split()) <= set(k.split())]
        return cand[0] if len(cand) == 1 else k
    rc["pkey"] = [align(t, k) for t, k in zip(rc.pit_team_id, rc.pkey)]
    er = rc[rc.unearned == 0].groupby(["pit_team_id", "pkey"]).size().rename("er")
    p = seq[seq.pit_team_id.isin(full)].groupby(["pit_team_id", "pkey"]).agg(outs=("outs", "sum"), k=("k", "sum")).join(er).reset_index()
    p["er"] = p.er.fillna(0); p["ip"] = p.outs / 3; p["tg"] = p.pit_team_id.map(gpt); p["tier"] = p.pit_team_id.map(tier_id); p["team"] = p.pit_team_id.astype(str); p["src"] = "wmt"
    # Sidearm full-season individual lines for teams not already full-season in WMT
    sb_rows, sp_rows = [], []
    for dom, tname in SIDEARM_TEAMS.items():
        tid = name_id.get(tname)
        if tid in full:
            continue
        h = gzip.open(f"data/ncaa_2025/sidearm/raw/{dom}.html.gz", "rt").read()
        root = hydrate(json.loads(re.search(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', h, re.S).group(1)))
        lists = {}
        def find(o, path=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    if isinstance(v, list) and v and isinstance(v[0], dict) and "playerName" in v[0]:
                        if "Conference" not in path + k and k not in lists:
                            lists[k] = v
                    else:
                        find(v, path + "/" + k)
            elif isinstance(o, list):
                for v in o:
                    find(v, path)
        find(root)
        hit, pit = lists.get("individualHittingStats", []), lists.get("individualPitchingStats", [])
        tot = next((x for x in hit if x.get("playerName") == "Totals"), None) or next((x for x in lists.get("individualFieldingStats", []) if x.get("playerName") == "Totals"), {})
        # team games: the most games any batter played is a lower bound; Totals row of hitting carries it
        team_g = max(num(x.get("gamesPlayed")) for x in hit if x.get("playerName") not in ("Totals", "Opponents") and not np.isnan(num(x.get("gamesPlayed"))))
        for x in hit:
            if x.get("playerName") in ("Totals", "Opponents"):
                continue
            ab, bb, hbp, sf, sh = (num(x.get(k)) for k in ("atBats", "walks", "hitByPitch", "sacrificeFlies", "sacrificeHits"))
            hh, d2, d3, hr, k = (num(x.get(k)) for k in ("hits", "doubles", "triples", "homeRuns", "strikeouts"))
            vals = [0 if np.isnan(v) else v for v in (ab, bb, hbp, sf, sh, hh, d2, d3, hr, k)]
            ab, bb, hbp, sf, sh, hh, d2, d3, hr, k = vals
            sb_rows.append({"team": dom, "tier": tier_id.get(tid), "pa": ab + bb + hbp + sf + sh, "ab": ab, "h": hh, "tb": hh + d2 + 2 * d3 + 3 * hr, "bb": bb, "hbp": hbp, "sf": sf,
                            "k": k, "hr": hr, "g": num(x.get("gamesPlayed")), "tg": team_g, "src": "sidearm"})
        for x in pit:
            if x.get("playerName") in ("Totals", "Opponents"):
                continue
            sp_rows.append({"team": dom, "tier": tier_id.get(tid), "ip": ip_from_text(x.get("inningsPitched")), "er": num(x.get("earnedRunsAllowed")),
                            "k": num(x.get("strikeouts")), "tg": team_g, "src": "sidearm"})
    b = pd.concat([b, pd.DataFrame(sb_rows)], ignore_index=True)
    p = pd.concat([p, pd.DataFrame(sp_rows)], ignore_index=True)
    qb = b[(b.pa >= 2 * b.tg) & (b.g >= 0.75 * b.tg)].copy()
    qb["BA"] = qb.h / qb.ab; qb["OBP"] = (qb.h + qb.bb + qb.hbp) / (qb.ab + qb.bb + qb.hbp + qb.sf); qb["ISO"] = (qb.tb - qb.h) / qb.ab
    qb["K_pct"] = qb.k / qb.pa; qb["BB_pct"] = qb.bb / qb.pa
    qp = p[(p.ip >= p.tg)].copy()
    qp["ERA"] = 9 * qp.er / qp.ip; qp["K9"] = 9 * qp.k / qp.ip
    d1 = teams.tier.value_counts(normalize=True).to_dict()
    QS = (10, 25, 50, 75, 90)

    def wpct(v, w, q):
        o = np.argsort(v); v, w = v[o], w[o]; c = np.cumsum(w) / w.sum()
        return float(np.interp(q / 100, c, v))

    def dist(df, cols):
        # each tier counts by its share of D1 teams; a tier with fewer than MIN_CELL_N_PERCENTILE qualified
        # players is pooled with its nearest tier first (scripts/lib/pooling.py), fixed from the full sample
        group_of, groups = pool_cells(df.tier.value_counts().to_dict(), {t: d1[t] for t in TIERS}, MIN_CELL_N_PERCENTILE)
        def weights(frame, pooled):
            # a player's weight: his group's share of D1 teams over its share of the sample's teams (each team
            # counts by its tier's D1 share). Unpooled, the groups are the tiers (the previous method).
            key = frame.tier.map(group_of) if pooled else frame.tier
            share = (lambda k: groups[k]["weight"]) if pooled else (lambda k: d1[k])
            tshare = frame.groupby(key).team.nunique() / frame.team.nunique()
            return key.map(lambda k: share(k) / tshare[k]).values
        res = {"pooled_groups": describe(groups), "unpooled": {}}
        teams_by_tier = {t: df[df.tier == t].team.unique() for t in TIERS}
        for col in cols:
            v = df[col].values.astype(float)
            point = {f"p{q}": round(wpct(v, weights(df, True), q), 4) for q in QS}
            res["unpooled"][col] = {f"p{q}": round(wpct(v, weights(df, False), q), 4) for q in QS}
            boots = []
            for _ in range(BOOT):    # same draws, in the same order, as before the pooling rule
                pick = pd.concat([df[df.team == tm] for t in TIERS for tm in RNG.choice(teams_by_tier[t], size=len(teams_by_tier[t]), replace=True)])
                boots.append([wpct(pick[col].values.astype(float), weights(pick, True), q) for q in QS])
            se = np.std(np.array(boots), axis=0, ddof=1)
            res[col] = {**point, "tol": {f"p{q}": round(float(3 * s), 4) for q, s in zip(QS, se)}}
        return res
    comp_b = {t: int(qb[qb.tier == t].team.nunique()) for t in TIERS}
    comp_p = {t: int(qp[qp.tier == t].team.nunique()) for t in TIERS}
    out = {
        "_note": "Qualified batters (NCAA rule: 2.0 PA per team game and 75% of team games) and pitchers (1 IP per team game) on WMT full-season teams plus the Sidearm full-season pages, reweighted so each tier counts by its share of D1 teams (a tier with fewer than 50 qualified players is pooled with its nearest tier first, see pooled_groups). Tolerances 3 SE from a team-cluster bootstrap within tier. Conf B: 72% of sample teams are P4 and the low tier rests on few teams, so low-tier tails carry the most uncertainty.",
        "conf": "B", "qualification": {"batter": "PA >= 2.0 x team games and games >= 0.75 x team games", "pitcher": "IP >= 1.0 x team games"},
        "batters": {"n": int(len(qb)), "teams_by_tier": comp_b, "per_team": round(len(qb) / qb.team.nunique(), 2), **dist(qb, ["BA", "OBP", "ISO", "K_pct", "BB_pct"])},
        "pitchers": {"n": int(len(qp)), "teams_by_tier": comp_p, "per_team": round(len(qp) / qp.team.nunique(), 2), **dist(qp, ["ERA", "K9"])},
        "sample_tops": {"BA_max": round(qb.BA.max(), 3), "HR_max": int(b.hr.max()), "ERA_min_qualified": round(qp.ERA.min(), 2),
                        "note": "Maxima of a sample of ~60 teams, not the 303-team population; informational only"},
    }
    return out, {"qualified_batters_per_team": out["batters"]["per_team"], "qualified_pitchers_per_team": out["pitchers"]["per_team"]}


def main() -> None:
    teams = pd.read_csv("data/ncaa_2025/pbp/teams_2025.csv")
    strength, mix = team_strength(teams)
    qual, qcount = qualified(teams)
    b = json.loads(Path("benchmarks.json").read_text())
    pd25, bd25 = b["pitching_distribution_2025"], b["batting_distribution_2025"]
    lead = {
        "_note": "Full-population extremes for the Phase 2 gate. The sim passes a row if the real value falls inside the central 95% of the simulated seasons. FanGraphs rows are conf A (all D1 pitchers and teams); individual BA and HR tops have no full-population source here (stats.ncaa.org not available), so they are informational.",
        "pitchers_50ip": {"value": pd25["pitchers_50ip"], "conf": "A"},
        "pitchers_50ip_era_under_2": {"value": pd25["era_under_2_00"]["count"], "conf": "A"},
        "pitchers_50ip_era_under_3": {"value": pd25["era_under_3_00"]["count"], "conf": "A"},
        "teams_era_under_4": {"value": pd25["teams_with_era_under_4_00"]["count"], "conf": "A"},
        "best_team_era": {"value": pd25["best_team_era_2025"]["value"], "conf": "A"},
        "team_ba_max": {"value": bd25["team_ba_range_2025"]["max"], "conf": "A"},
        "team_hr_per_game_max": {"value": round(bd25["team_hr_max_2025"]["value"] / bd25["team_hr_max_2025"]["games"], 3), "conf": "A", "note": f"{bd25['team_hr_max_2025']['team']} {bd25['team_hr_max_2025']['value']} HR in {bd25['team_hr_max_2025']['games']} games; gated through team_leaders_2024_2026"},
        "individual_ba_top": {"value": None, "conf": "D", "sample_max": qual["sample_tops"]["BA_max"], "note": "needs stats.ncaa.org individual table"},
        "individual_hr_top": {"value": None, "conf": "D", "sample_max": qual["sample_tops"]["HR_max"], "note": "needs stats.ncaa.org individual table"},
    }
    OUT.write_text(json.dumps({"team_strength_2025": strength, "qualified_players_2025": qual, "leaderboards_2025": lead, "schedule_mix": mix, "counts": qcount}, indent=1, default=float) + "\n")
    inp = json.loads(INPUTS.read_text()); inp["schedule_mix"] = mix; INPUTS.write_text(json.dumps(inp, indent=1, default=float) + "\n")
    print(json.dumps({"team_strength_all": strength["all"], "by_tier": strength["by_tier"]}, indent=0)[:1500])
    print("mix:", json.dumps(mix)[:600])
    print("qualified batters", qual["batters"]["n"], qual["batters"]["teams_by_tier"], {k: qual["batters"][k] for k in ("BA", "OBP", "ISO", "K_pct", "BB_pct")})
    print("qualified pitchers", qual["pitchers"]["n"], qual["pitchers"]["teams_by_tier"], {k: qual["pitchers"][k] for k in ("ERA", "K9")})
    print("tops", qual["sample_tops"])


if __name__ == "__main__":
    main()
