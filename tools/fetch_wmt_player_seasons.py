"""Player-season panel from the WMT stats API (Phase 8 and Phase 10 input): development curves, retention
by class, stat-roster size and class composition, 2022-2026.

    python tools/fetch_wmt_player_seasons.py --work /path/outside/the/repo            # fetch (resumable)
    python tools/fetch_wmt_player_seasons.py --work /path/outside/the/repo --aggregate # aggregate only
    python tools/fetch_wmt_player_seasons.py --selftest                                # offline check

WMT (api.wmt.games, robots.txt allows all user agents; the project's play-by-play source) serves, for
each of its client schools and each season, the season statistics of every player on the team with
his class (Fr/So/Jr/Sr), position and a person id that is stable across seasons and schools:
    GET /api/statistics/teams?season_id=<id>&per_page=100           the season's teams (about 51 D1 clients)
    GET /api/statistics/teams/<team_id>/players?per_page=100&with[]=season_stats
One request per second, one at a time. The raw payloads (with names) and the per-player panel
(`panel.csv`: person id, team, season, class, position, stat totals; no names) stay in the working
directory outside the repository and are never committed (owner rule 2026-10-07: aggregated tables
only). The script writes to data/wmt_player_seasons/ only counts, rates and moments by season, tier,
class, role and playing-time tercile, and ends by scanning every output cell for any first or last
name in the panel (failing and deleting the output on a hit).

Season ids (probed 2026-10-10; the MBA season id of an academic year is found by probing
`teams?season_id=` around the previous year's id + 260 and is cached in state.json):
    2022 15860, 2023 16340, 2024 16580, 2025 16840.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from aggregate_rosters import class_year  # noqa: E402  (the same class parser as the roster aggregates)

API = "https://api.wmt.games/api/statistics"
HEADERS = {"Accept": "application/json", "Origin": "https://wmt.games",
           "User-Agent": "college-baseball-sim data pull (github.com/jadams-24/College-Baseball-Sim)"}
DELAY = 1.0
KNOWN_SEASONS = {2022: 15860, 2023: 16340, 2024: 16580, 2025: 16840}
SEASONS = [2022, 2023, 2024, 2025, 2026]
OUT = ROOT / "data/wmt_player_seasons"
P4 = {"SEC", "ACC", "Big 12", "Big Ten", "Pac-12"}      # Phase 0 tiers; the Pac-12 (through 2024) counted as P4
MIN_PA, MIN_BF = 50, 50                                   # both seasons of a pair (GUESS: a qualifying floor)
CLASSES = ["Fr", "So", "Jr", "Sr"]                        # WMT lists no graduate class; fifth-years are Sr
LABELS = {"all", "p4", "mid", "low", "non_d1", "batter", "pitcher", "Fr", "So", "Jr", "Sr", "unknown",
          "same_team", "other_client_team", "absent", "t1", "t2", "t3", "played", "rostered",
          "k_pct", "bb_pct", "hr_pct", "ba", "obp", "slg", "iso", "babip", "era", "h_pct", "ops",
          "logit", "raw", "mean", "sd", "min", "max", "p4->p4", "p4->mid", "mid->p4", "mid->mid",
          "p4->low", "low->p4", "mid->low", "low->mid", "low->low"}

# ------------------------------------------------------------------ HTTP
def get(url: str, retries: int = 4) -> dict | None:
    import requests
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=120)
        except requests.RequestException as e:          # network: wait and retry
            print(f"  network error {e}; retry {i + 1}", flush=True)
            time.sleep(5 * (i + 1))
            continue
        if r.status_code == 200:
            try:
                return r.json()
            except ValueError:
                return None
        if r.status_code in (404, 500):
            return None
        if r.status_code == 429:
            time.sleep(30 * (i + 1))
            continue
        print(f"  HTTP {r.status_code} {url}", flush=True)
        return None
    return None


def paged(url: str) -> list[dict]:
    """Follow WMT's cursor pagination (`meta.pagination.next_page`, passed back as `cursor=`)."""
    out, cursor = [], ""
    for _ in range(200):
        d = get(url + (f"&cursor={cursor}" if cursor else ""))
        time.sleep(DELAY)
        if not d or not isinstance(d.get("data"), list):
            break
        out.extend(d["data"])
        cursor = (d.get("meta") or {}).get("pagination", {}).get("next_page") or ""
        if not cursor:
            break
    return out


def find_season_id(year: int, state: dict) -> int | None:
    key = f"season_id_{year}"
    if key in state:
        return state[key]
    if year in KNOWN_SEASONS:
        state[key] = KNOWN_SEASONS[year]
        return state[key]
    base = max(v for v in KNOWN_SEASONS.values()) + 260 * (year - max(KNOWN_SEASONS))
    for sid in range(base - 120, base + 400, 10):
        d = get(f"{API}/teams?season_id={sid}&per_page=1")
        time.sleep(DELAY)
        rows = (d or {}).get("data") or []
        if rows and rows[0].get("sport_code") == "MBA" and rows[0].get("season_academic_year") == year:
            state[key] = sid
            return sid
    state[key] = None
    return None


# ------------------------------------------------------------------ extraction (no names leave this function)
def season_stat(p: dict) -> dict:
    s = p.get("statistic")
    if isinstance(s, dict):
        s = s.get("data")
    if isinstance(s, dict):
        s = s.get("season")
    if not isinstance(s, dict):
        return {}
    cols = s.get("columns") or []
    out = {"games_played": s.get("gamesPlayed") or 0, "games_started": s.get("gamesStarted") or 0}
    for c in cols:
        if c.get("period") in (0, None):
            st = c.get("statistic") or {}
            for k, v in st.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    out[k] = v
            break
    return out


def extract(team: dict, players: list[dict], year: int) -> list[dict]:
    rows = []
    for p in players:
        st = season_stat(p)
        rows.append({
            "season": year, "team_id": team["id"], "team": team.get("name_tabular"),
            "conference": team.get("conference_name_tabular"), "division": team.get("division"),
            "person_id": p.get("person_id"), "player_id": p.get("id"),
            "class": class_year(p.get("class_short_descr") or ""), "class_raw": p.get("class_short_descr") or "",
            "grade_level_id": p.get("grade_level_id"), "position": (p.get("position_code") or "").upper(),
            "height_in": (p.get("height_ft") or 0) * 12 + (p.get("height_in") or 0) if p.get("height_ft") else None,
            **{k: v for k, v in st.items()}})
    return rows


def fetch(work: Path, years: list[int]) -> None:
    work.mkdir(parents=True, exist_ok=True)
    (work / "raw").mkdir(exist_ok=True)
    state_p = work / "state.json"
    state = json.loads(state_p.read_text()) if state_p.exists() else {"done": [], "names": []}
    panel_p = work / "panel.csv"
    rows_all = pd.read_csv(panel_p) if panel_p.exists() else pd.DataFrame()
    for year in years:
        sid = find_season_id(year, state)
        state_p.write_text(json.dumps(state))
        if sid is None:
            print(f"{year}: no MBA season id found (season not on WMT yet)", flush=True)
            continue
        teams = paged(f"{API}/teams?season_id={sid}&per_page=100")
        teams = [t for t in teams if t.get("sport_code") == "MBA"]
        print(f"{year}: season {sid}, {len(teams)} teams", flush=True)
        state.setdefault("teams", {})[str(year)] = [{"id": t["id"], "team": t.get("name_tabular"),
                                                     "conference": t.get("conference_name_tabular"),
                                                     "division": t.get("division")} for t in teams]
        for t in teams:
            key = f"{year}:{t['id']}"
            if key in state["done"]:
                continue
            players = paged(f"{API}/teams/{t['id']}/players?per_page=100&with[]=season_stats")
            with gzip.open(work / "raw" / f"{year}_{t['id']}.json.gz", "wt") as g:
                json.dump(players, g)
            rows = extract(t, players, year)
            rows_all = pd.concat([rows_all, pd.DataFrame(rows)], ignore_index=True) if rows else rows_all
            rows_all.to_csv(panel_p, index=False)
            for p in players:                      # names kept only for the leak check, in the work dir
                for k in ("first_name", "last_name"):
                    v = (p.get(k) or "").strip()
                    if len(v) >= 4 and v not in state["names"]:
                        state["names"].append(v)
            state["done"].append(key)
            state_p.write_text(json.dumps(state))
            print(f"  {year} {t.get('name_tabular')}: {len(players)} players", flush=True)


# ------------------------------------------------------------------ aggregation
def tier_of(conf: str, division) -> str:
    if division not in (1, "1", 1.0):
        return "non_d1"
    if conf in P4:
        return "p4"
    tiers = {r["league"]: r["tier"] for r in pd.read_csv(ROOT / "data/phase0/conf2025.csv").to_dict("records")}
    alias = {"The American": "American", "CUSA": "C-USA", "CAA": "Colonial", "ASUN": "Atlantic Sun",
             "MVC": "Missouri Valley", "OVC": "Ohio Valley", "NEC": "Northeast", "Patriot": "Patriot League",
             "Summit League": "Summit", "DI Independent": "Independent", "IND": "Independent"}
    return tiers.get(alias.get(conf, conf), tiers.get(conf, "mid"))


def g(df: pd.DataFrame, k: str) -> pd.Series:
    return pd.to_numeric(df[k], errors="coerce").fillna(0) if k in df else pd.Series(0.0, index=df.index)


def batting(df: pd.DataFrame) -> pd.DataFrame:
    ab, h, bb, hbp = g(df, "sAtBats"), g(df, "sHits"), g(df, "sWalks"), g(df, "sHitByPitch")
    sf, sh, k = g(df, "sSacrificeFlies"), g(df, "sSacrificeBunts"), g(df, "sStrikeoutsHitting")
    d2, d3, hr = g(df, "sDoubles"), g(df, "sTriples"), g(df, "sHomeRuns")
    pa = ab + bb + hbp + sf + sh
    tb = h + d2 + 2 * d3 + 3 * hr
    out = pd.DataFrame({"pa": pa, "n": pa})
    with np.errstate(divide="ignore", invalid="ignore"):
        out["k_pct"] = k / pa
        out["bb_pct"] = bb / pa
        out["hr_pct"] = hr / pa
        out["ba"] = h / ab
        out["obp"] = (h + bb + hbp) / (ab + bb + hbp + sf)
        out["slg"] = tb / ab
        out["iso"] = (tb - h) / ab
        out["babip"] = (h - hr) / (ab - k - hr + sf)
        out["ops"] = out["obp"] + out["slg"]
    return out


def pitching(df: pd.DataFrame) -> pd.DataFrame:
    bf, k, bb, hr = g(df, "sBattersFaced"), g(df, "sStrikeouts"), g(df, "sBasesOnBallsAllowed"), g(df, "sHomeRunsAllowed")
    h, er, ip = g(df, "sHitsAllowed"), g(df, "sEarnedRuns"), g(df, "sInningsPitched")
    ipf = np.floor(ip) + (ip - np.floor(ip)) * 10 / 3            # 63.2 -> 63 2/3
    out = pd.DataFrame({"bf": bf, "n": bf})
    with np.errstate(divide="ignore", invalid="ignore"):
        out["k_pct"] = k / bf
        out["bb_pct"] = bb / bf
        out["hr_pct"] = hr / bf
        out["h_pct"] = h / bf
        out["era"] = 9 * er / ipf
    return out


BAT_RATES = ["k_pct", "bb_pct", "hr_pct", "ba", "obp", "slg", "iso", "babip", "ops"]
PIT_RATES = ["k_pct", "bb_pct", "hr_pct", "h_pct", "era"]
LOGIT = {"k_pct", "bb_pct", "hr_pct", "ba", "obp", "babip", "h_pct"}


def logit(p: pd.Series, n: pd.Series) -> pd.Series:
    q = (p * n + 0.5) / (n + 1)
    return np.log(q / (1 - q))


def role_frames(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """One frame per role with the player's rates, the season's playing time and his tercile within
    season (by PA or BF among players over the floor)."""
    out = {}
    for role, fn, floor, rates in (("batter", batting, MIN_PA, BAT_RATES), ("pitcher", pitching, MIN_BF, PIT_RATES)):
        r = fn(panel)
        f = pd.concat([panel[["season", "team_id", "tier", "person_id", "class", "position"]], r], axis=1)
        f = f[f["n"] >= floor].copy()
        f["tercile"] = f.groupby("season")["n"].transform(
            lambda s: pd.qcut(s.rank(method="first"), 3, labels=["t1", "t2", "t3"]).astype(str))
        f["role"] = role
        out[role] = f
    return out


def paired(f: pd.DataFrame, rates: list[str]) -> pd.DataFrame:
    """Consecutive-season pairs of the same person (any client team), both seasons over the floor."""
    a = f.copy()
    b = f.copy()
    b["season"] = b["season"] - 1
    m = a.merge(b, on=["person_id", "season"], suffixes=("", "_next"))
    rows = []
    for scope, groups in (("class", m.groupby("class")), ("class_tier", m.groupby(["class", "tier"])),
                          ("class_tercile", m.groupby(["class", "tercile"])), ("all", [("all", m)])):
        for key, gdf in groups:
            key = key if isinstance(key, tuple) else (key, "all")
            for rate in rates:
                x, y = gdf[rate], gdf[f"{rate}_next"]
                ok = np.isfinite(x) & np.isfinite(y)
                x, y, n0, n1 = x[ok], y[ok], gdf["n"][ok], gdf["n_next"][ok]
                if len(x) == 0:
                    continue
                if rate in LOGIT:
                    d = logit(y, n1) - logit(x, n0)
                    scale = "logit"
                else:
                    d = y - x
                    scale = "raw"
                w = 1 / (1 / n0 + 1 / n1)
                rows.append({"scope": scope, "class": key[0], "group": key[1], "role": gdf["role"].iloc[0], "rate": rate,
                             "scale": scale, "players": int(len(x)), "level_t": float(np.average(x, weights=n0)),
                             "level_t1": float(np.average(y, weights=n1)), "delta_mean": float(d.mean()),
                             "delta_sd": float(d.std(ddof=1)) if len(d) > 1 else float("nan"),
                             "delta_se": float(d.std(ddof=1) / math.sqrt(len(d))) if len(d) > 1 else float("nan"),
                             "delta_weighted": float(np.average(d, weights=w)),
                             "delta_median": float(d.median()), "pairs_pa_mean": float(n0.mean())})
    return pd.DataFrame(rows)


def levels(f: pd.DataFrame, rates: list[str]) -> pd.DataFrame:
    rows = []
    for (season, tier, cls), gdf in f.groupby(["season", "tier", "class"]):
        for rate in rates:
            ok = np.isfinite(gdf[rate])
            if ok.sum() == 0:
                continue
            rows.append({"season": season, "tier": tier, "class": cls, "role": gdf["role"].iloc[0], "rate": rate,
                         "players": int(ok.sum()), "n_sum": float(gdf["n"][ok].sum()),
                         "weighted_mean": float(np.average(gdf[rate][ok], weights=gdf["n"][ok])),
                         "player_sd": float(gdf[rate][ok].std(ddof=1)) if ok.sum() > 1 else float("nan")})
    return pd.DataFrame(rows)


def retention(panel: pd.DataFrame, frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    # WMT team ids are per season, so the same program is recognised by its name (name_tabular)
    nxt = panel[["person_id", "season", "team", "tier"]].copy()
    nxt["season"] -= 1
    nxt = nxt.drop_duplicates(["person_id", "season"]).rename(columns={"team": "team_next", "tier": "tier_next"})
    p = panel.merge(nxt, on=["person_id", "season"], how="left")
    last = panel["season"].max()
    p = p[p["season"] < last]                                   # the last season has no next season to look in
    p["status"] = np.where(p["team_next"].isna(), "absent",
                           np.where(p["team_next"] == p["team"], "same_team", "other_client_team"))
    p["move"] = np.where(p["status"] == "other_client_team", p["tier"] + "->" + p["tier_next"].fillna("unknown"), "")
    p["played"] = np.where(pd.to_numeric(p.get("games_played", 0), errors="coerce").fillna(0) > 0, "played", "rostered")
    tb = frames["batter"][["person_id", "season", "tercile"]].rename(columns={"tercile": "tercile_bat"})
    tp = frames["pitcher"][["person_id", "season", "tercile"]].rename(columns={"tercile": "tercile_pit"})
    p = p.merge(tb, on=["person_id", "season"], how="left").merge(tp, on=["person_id", "season"], how="left")
    p["role"] = np.where(p["position"].str.contains("P", na=False) & ~p["position"].str.contains("/", na=False),
                         "pitcher", "batter")
    p["tercile"] = np.where(p["role"] == "pitcher", p["tercile_pit"], p["tercile_bat"]).astype(object)
    p["tercile"] = pd.Series(p["tercile"]).fillna("unknown")
    rows = []
    for scope, groups in (("class", p.groupby(["season", "class"])), ("class_tier", p.groupby(["season", "class", "tier"])),
                          ("class_role_tercile", p.groupby(["season", "class", "role", "tercile"])),
                          ("class_played", p.groupby(["season", "class", "played"]))):
        for key, gdf in groups:
            key = tuple(key) + ("all",) * (4 - len(key))
            c = gdf["status"].value_counts()
            rows.append({"scope": scope, "season": key[0], "class": key[1], "group": key[2], "group2": key[3],
                         "players": int(len(gdf)), "same_team": int(c.get("same_team", 0)),
                         "other_client_team": int(c.get("other_client_team", 0)), "absent": int(c.get("absent", 0))})
    moves = p[p["status"] == "other_client_team"].groupby(["season", "move"]).size().rename("count").reset_index()
    moves = moves.reindex(columns=["season", "move", "count"])
    return pd.DataFrame(rows), moves


def composition(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    panel = panel.copy()
    panel["played"] = np.where(pd.to_numeric(panel.get("games_played", 0), errors="coerce").fillna(0) > 0, "played", "rostered")
    panel["pos_group"] = np.where(panel["position"].str.contains("P", na=False), "P", "position")
    comp = panel.groupby(["season", "tier", "class", "pos_group", "played"]).size().rename("count").reset_index()
    sizes = panel.groupby(["season", "tier", "team_id"]).agg(players=("person_id", "size"),
                                                             pitchers=("pos_group", lambda s: int((s == "P").sum())),
                                                             played=("played", lambda s: int((s == "played").sum())))
    size = sizes.groupby(["season", "tier"]).agg(teams=("players", "size"), roster_mean=("players", "mean"),
                                                 roster_sd=("players", "std"), roster_min=("players", "min"),
                                                 roster_max=("players", "max"), pitchers_mean=("pitchers", "mean"),
                                                 played_mean=("played", "mean")).reset_index()
    return comp, size


def leak_check(out: Path, names: list[str]) -> list[str]:
    hits = []
    keys = {n.lower() for n in names if len(n) >= 4}
    for f in sorted(out.glob("*.csv")):
        try:
            df = pd.read_csv(f, dtype=str, keep_default_na=False)
        except pd.errors.EmptyDataError:
            continue
        for col in df.columns:
            if col in ("team", "conference"):           # team and conference names are allowed (never player names)
                continue
            for v in df[col].unique():
                for tok in re.split(r"[^A-Za-z]+", str(v)):
                    if tok.lower() in keys and tok not in LABELS:
                        hits.append(f"{f.name}:{col}")
                        break
    return sorted(set(hits))


def aggregate(work: Path, out: Path = OUT, names: list[str] | None = None) -> dict:
    panel = pd.read_csv(work / "panel.csv", low_memory=False)
    panel["class"] = panel["class"].fillna("unknown")
    panel["position"] = panel["position"].fillna("").astype(str)
    panel["tier"] = [tier_of(c, d) for c, d in zip(panel["conference"], panel["division"])]
    panel = panel.drop_duplicates(["season", "team_id", "person_id"])
    frames = role_frames(panel)
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.csv"):
        f.unlink()
    cov = panel.groupby(["season", "tier"]).agg(teams=("team_id", "nunique"), players=("person_id", "size"),
                                                share_class_known=("class", lambda s: float((s != "unknown").mean()))).reset_index()
    cov["batters_over_floor"] = [int(((frames["batter"].season == s) & (frames["batter"].tier == t)).sum()) for s, t in zip(cov.season, cov.tier)]
    cov["pitchers_over_floor"] = [int(((frames["pitcher"].season == s) & (frames["pitcher"].tier == t)).sum()) for s, t in zip(cov.season, cov.tier)]
    cov.to_csv(out / "coverage.csv", index=False)
    teams = panel[["season", "team_id", "team", "conference", "tier"]].drop_duplicates().sort_values(["season", "team"])
    teams.to_csv(out / "teams.csv", index=False)
    pd.concat([paired(frames["batter"], BAT_RATES), paired(frames["pitcher"], PIT_RATES)], ignore_index=True).round(5)\
        .to_csv(out / "aging_curves.csv", index=False)
    pd.concat([levels(frames["batter"], BAT_RATES), levels(frames["pitcher"], PIT_RATES)], ignore_index=True).round(5)\
        .to_csv(out / "levels_by_class.csv", index=False)
    ret, moves = retention(panel, frames)
    ret.to_csv(out / "retention_by_class.csv", index=False)
    moves.to_csv(out / "tier_moves.csv", index=False)
    comp, size = composition(panel)
    comp.to_csv(out / "class_composition.csv", index=False)
    size.round(3).to_csv(out / "roster_size.csv", index=False)
    with open(out / "README.md", "w") as fh:
        fh.write(README)
    if names is None:
        st = work / "state.json"
        names = json.loads(st.read_text()).get("names", []) if st.exists() else []
    hits = leak_check(out, names)
    if hits:
        for f in out.glob("*.csv"):
            f.unlink()
        raise SystemExit(f"name leak in {hits}; output deleted")
    b = frames["batter"]
    nb = b.copy()
    nb["season"] -= 1
    return {"players": int(len(panel)), "pairs_batters": int(len(b.merge(nb, on=["person_id", "season"]))),
            "seasons": sorted(panel["season"].unique().tolist())}


README = """# data/wmt_player_seasons/ — player-season aggregates from the WMT stats API, 2022–2026

Built by `tools/fetch_wmt_player_seasons.py` (fetch dates and season ids in `coverage.csv` and the commit
message). Source: `https://api.wmt.games/api/statistics/teams?season_id=<id>` (the season's client teams)
and `/teams/<team_id>/players?with[]=season_stats` (every rostered player's season totals with class and
position). Only WMT's client schools (about 51 D1 programs a season, P4-heavy) have players; a player who
leaves for a non-client school disappears from the panel. No names, no player rows: the panel stays in the
fetch's working directory.

| File | Content |
|---|---|
| `coverage.csv` | teams, players, share with a known class, batters with 50+ PA and pitchers with 50+ BF, by season and tier |
| `teams.csv` | the client teams by season (team, conference, tier) |
| `aging_curves.csv` | consecutive-season pairs of the same person (both seasons over the floor, any client team): by class in the first season (and by tier, by playing-time tercile), role and rate: players, PA-weighted level in each season, mean, SD, SE, precision-weighted mean and median of the change (logit scale for rates, raw for ERA/SLG/ISO/OPS). Survivors only: a player must play both seasons |
| `levels_by_class.csv` | cross-sectional PA- or BF-weighted level of each rate by season, tier and class, with the between-player SD |
| `retention_by_class.csv` | each player-season's status the next season: same team, another client team, absent (left for a non-client school, drafted, graduated, cut, or not rostered), by class, tier, role x playing-time tercile and played/rostered |
| `tier_moves.csv` | moves between client teams by tier pair |
| `class_composition.csv` | players by season, tier, class, pitcher/position and played/rostered (stat rosters: everyone WMT lists, including players without a game) |
| `roster_size.csv` | stat-roster size per team by season and tier (mean, SD, min, max), pitchers and players with a game |
"""


# ------------------------------------------------------------------ selftest
def selftest() -> int:
    import tempfile
    rng = np.random.default_rng(7)
    rows = []
    pid = 0
    for season in (2023, 2024, 2025):
        for tid, conf in ((1, "SEC"), (2, "Sun Belt")):
            for i in range(36):
                pid = pid + 1 if season == 2023 else (i + 1) + (0 if tid == 1 else 36)
                cls = CLASSES[min(3, (i % 4) + (season - 2023))]
                pitcher = i % 3 == 0
                r = {"season": season, "team_id": tid, "team": f"Team{tid}", "conference": conf, "division": 1,
                     "person_id": pid, "player_id": pid * 10 + season % 10, "class": cls, "class_raw": cls + ".",
                     "grade_level_id": 1, "position": "P" if pitcher else "OF", "games_played": int(rng.integers(0, 50))}
                if pitcher:
                    bf = int(rng.integers(20, 300))
                    r.update(sBattersFaced=bf, sStrikeouts=int(bf * .22), sBasesOnBallsAllowed=int(bf * .1),
                             sHomeRunsAllowed=int(bf * .02), sHitsAllowed=int(bf * .22), sEarnedRuns=int(bf * .12),
                             sInningsPitched=round(bf / 4.3, 1))
                else:
                    ab = int(rng.integers(20, 250))
                    r.update(sAtBats=ab, sHits=int(ab * .28), sWalks=int(ab * .12), sHitByPitch=int(ab * .03),
                             sSacrificeFlies=1, sSacrificeHits=1, sStrikeoutsHitting=int(ab * .2), sDoubles=int(ab * .05),
                             sTriples=0, sHomeRuns=int(ab * .03))
                rows.append(r)
    with tempfile.TemporaryDirectory() as td:
        work, out = Path(td) / "work", Path(td) / "out"
        work.mkdir()
        pd.DataFrame(rows).to_csv(work / "panel.csv", index=False)
        s = aggregate(work, out, names=["Nobody"])
        files = sorted(f.name for f in out.glob("*.csv"))
        assert "aging_curves.csv" in files and "retention_by_class.csv" in files, files
        ac = pd.read_csv(out / "aging_curves.csv")
        assert (ac.players > 0).all() and ac.rate.nunique() >= 10
        # the leak check must catch a name planted in an output
        pd.DataFrame({"x": ["Planted Surname"]}).to_csv(out / "leak.csv", index=False)
        assert leak_check(out, ["Surname"]) == ["leak.csv:x"], "leak check missed a planted name"
        assert leak_check(out, ["Nobody"]) == []
    print("selftest passed", s)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", help="working directory for the raw fetch and the panel (outside the repository)")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--seasons", default=",".join(map(str, SEASONS)))
    ap.add_argument("--aggregate", action="store_true", help="aggregate an existing panel without fetching")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.work:
        ap.error("--work is required")
    work = Path(a.work).resolve()
    if ROOT in work.parents or work == ROOT:
        ap.error("--work must be outside the repository (player rows are never committed)")
    if not a.aggregate:
        fetch(work, [int(s) for s in a.seasons.split(",")])
    print(aggregate(work, Path(a.out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
