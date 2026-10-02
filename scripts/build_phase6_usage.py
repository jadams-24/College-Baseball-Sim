"""Phase 6 pitcher-usage inputs from the 2025 play-by-play (full-season teams).

Writes the "usage6" block of data/ncaa_2025/derived/phase6_inputs_2025.json:

  calendar     the weekly game days: weekday of the midweek game and of the first game of the
               weekend series (Thu or Fri ...), from weeks with one midweek game and a three-game
               series
  relief       a conditional logit of who comes out of the bullpen. At each relief entry the
               choice set is the team's staff not yet used in the game (the game's starter
               excluded), in the engine's 13 roles: weekend rotation ranks wk1-wk3 (most series
               starts), midweek starters mid1-mid2 (most midweek starts among the rest), relievers
               r1-r8 (relief batters faced; the 8th and deeper share the role r8, each an
               alternative of its own, as the engine's 8th-13th relievers are). Utility = role x
               leverage (late and close / blowout / other) + rest state: days since the pitcher's
               last appearance (same day, 1, 2, 3 by the pitches of that outing, 4, 5, 6+) and
               having pitched on both of the two previous days.
  midweek      the same model for who starts a midweek (Mon-Wed) game, over the whole staff
  pull         proportional-hazards multipliers on the Phase 2 pull hazards: h' = 1 - (1 - h)^theta,
               theta by tier for weekend starters, midweek starters and relievers, and by season
               week for starters (fatigue and build-up over the season); maximum likelihood on every
               pull decision, baseline h from the pooled tables the engine uses
  benchmarks   usage gate values from the same teams: per team, the most appearances, appearances of
               the 5th and 10th busiest pitchers, relief-only pitchers (3 or fewer starts) with 40+
               and 60+ IP, and the top three pitchers' IP split (series starts, other starts, relief)

Weekend here means Thu-Sun (series days; a Thursday-to-Saturday series is a weekend series);
midweek is Mon-Wed.
    python3 scripts/build_phase6_usage.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from config.phase6 import (CLOGIT_RIDGE, FULL_SEASON_GAMES, INPUTS6, LEVERAGE_BLOWOUT, LEVERAGE_CLOSE, LEVERAGE_LATE_INNING, N_ROLE_RELIEVERS,  # noqa: E402
                           PITCH_BINS, REST_SPLIT_DAYS, ROLES)
from config.phase2 import SEASON_GAMES  # noqa: E402
from lib.players import load_pa  # noqa: E402

P = ROOT / "data/ncaa_2025/pbp/parsed"
TODAY = dt.date.today().isoformat()
SERIES_DAYS = {3, 4, 5, 6}     # Thu-Sun
MIDWEEK_DAYS = {0, 1, 2}       # Mon-Wed


def load() -> tuple:
    pa = load_pa()
    meta = pd.read_csv(P / "games_meta_2025.csv")
    teams = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    tier = dict(zip(teams.ncaa_team_id, teams.tier))
    pa = pa.merge(meta[["game_id", "local_date", "dbl_header_game_no"]], on="game_id", how="inner")
    pa["ord"] = np.arange(len(pa))
    g2 = pd.concat([meta[["game_id", "home_team_id"]].rename(columns={"home_team_id": "t"}),
                    meta[["game_id", "away_team_id"]].rename(columns={"away_team_id": "t"})])
    n = g2.groupby("t").game_id.nunique()
    full = set(n[n >= FULL_SEASON_GAMES].index)
    return pa, meta, tier, full


def appearances(pa: pd.DataFrame) -> pd.DataFrame:
    a = pa.groupby(["game_id", "pit_team_id", "pkey"]).agg(
        first=("ord", "min"), bf=("result", "size"), pitches=("pitches", "sum"), outs=("outs_on_play", "sum"),
        date=("local_date", "first"), dh=("dbl_header_game_no", "first"), inning=("inning", "first"), half=("half", "first"),
        hs=("home_score", "first"), as_=("away_score", "first")).reset_index()
    a["start"] = a.groupby(["game_id", "pit_team_id"])["first"].rank(method="first") == 1
    a["d"] = pd.to_datetime(a.date)
    a["wd"] = a.d.dt.dayofweek
    # margin from the pitching team's side at entry: pitching team is home when the top half is batting
    home_pitching = a.half == "T"
    a["margin"] = np.where(home_pitching, a.hs - a.as_, a.as_ - a.hs)
    return a


def roles(a: pd.DataFrame) -> pd.DataFrame:
    """Each pitcher's engine role on his team: wk1-3, mid1-2, r1-r8 (r8 = 8th and deeper relievers)."""
    out = []
    for t, g in a.groupby("pit_team_id"):
        ser = g[g.start & g.wd.isin(SERIES_DAYS)].groupby("pkey").size().sort_values(ascending=False)
        wk = list(ser.index[:3])
        mid = g[g.start & g.wd.isin(MIDWEEK_DAYS) & ~g.pkey.isin(wk)].groupby("pkey").size().sort_values(ascending=False)
        md = list(mid.index[:2])
        rest = g[~g.start & ~g.pkey.isin(wk + md)].groupby("pkey").bf.sum().sort_values(ascending=False)
        rp = list(rest.index)
        role = {p: f"wk{i + 1}" for i, p in enumerate(wk)}
        role.update({p: f"mid{i + 1}" for i, p in enumerate(md)})
        role.update({p: f"r{min(i + 1, N_ROLE_RELIEVERS)}" for i, p in enumerate(rp)})
        for p in g.pkey.unique():
            out.append((t, p, role.get(p, f"r{N_ROLE_RELIEVERS}")))
    return pd.DataFrame(out, columns=["pit_team_id", "pkey", "role"])


def rest_cell(days: float, last_pitches: float, b2b: bool) -> str:
    if np.isnan(days) or days >= 6:
        return "d6"
    d = int(days)
    if d in REST_SPLIT_DAYS:
        pb = int(np.searchsorted(PITCH_BINS, last_pitches, side="left"))
        return f"d{d}p{pb}"
    return f"d{d}"


def leverage(inning: int, margin: int) -> str:
    if abs(margin) >= LEVERAGE_BLOWOUT:
        return "blowout"
    if inning >= LEVERAGE_LATE_INNING and abs(margin) <= LEVERAGE_CLOSE:
        return "late_close"
    return "other"


def choice_data(a: pd.DataFrame, role: pd.DataFrame, kind: str) -> list:
    """Choice events: (alternatives' feature keys, index chosen). kind 'relief' or 'midweek'."""
    a = a.merge(role, on=["pit_team_id", "pkey"])
    events = []
    for t, g in a.groupby("pit_team_id"):
        g = g.sort_values(["d", "dh", "first"])
        staff = g.drop_duplicates("pkey")[["pkey", "role"]].values.tolist()
        size = g.drop_duplicates("pkey").role.value_counts().to_dict()
        hist: dict = {p: [] for p, _ in staff}          # pkey -> [(date, pitches)]
        for gid, gg in g.groupby("game_id", sort=False):
            day = gg.d.iloc[0]
            used = set()
            starter = gg[gg.start].pkey.iloc[0] if gg.start.any() else None
            for _, r in gg.sort_values("first").iterrows():
                is_choice = (kind == "relief" and not r.start) or (kind == "midweek" and r.start and r.wd in MIDWEEK_DAYS)
                if is_choice:
                    alts, chosen = [], None
                    lev = leverage(int(r.inning), int(r.margin)) if kind == "relief" else "start"
                    for p, ro in staff:
                        if p in used or p == starter and kind == "relief":
                            continue
                        h = hist[p]
                        if h:
                            last_day, last_p = h[-1]
                            days = (day - last_day).days
                            b2b = len(h) >= 2 and (day - h[-1][0]).days == 1 and (day - h[-2][0]).days == 2
                        else:
                            days, last_p, b2b = np.nan, 0, False
                        alts.append((ro, lev, rest_cell(days, last_p, b2b), b2b, size.get(ro, 1)))
                        if p == r.pkey:
                            chosen = len(alts) - 1
                    if chosen is not None:
                        events.append((alts, chosen))
                used.add(r.pkey)
            for _, r in gg.iterrows():
                hist[r.pkey].append((day, r.pitches))
    return events


def fit_clogit(events: list, kind: str) -> dict:
    """Conditional logit by Newton-Raphson. Features: role x leverage (reference r8 in each leverage
    level), rest cells (reference d6), back-to-back."""
    role_keys = sorted({(ro, lev) for alts, _ in events for ro, lev, *_ in alts if ro != f"r{N_ROLE_RELIEVERS}"})
    rest_keys = sorted({rc for alts, _ in events for _, _, rc, *_ in alts if rc != "d6"})
    names = [f"{ro}|{lev}" for ro, lev in role_keys] + [f"rest|{k}" for k in rest_keys] + ["b2b"]
    ri = {k: i for i, k in enumerate(role_keys)}
    si = {k: len(role_keys) + i for i, k in enumerate(rest_keys)}
    k = len(names)
    X, O, C, starts = [], [], [], [0]
    for alts, ch in events:
        for j, (ro, lev, rc, b2b, sz) in enumerate(alts):
            x = np.zeros(k)
            if (ro, lev) in ri:
                x[ri[(ro, lev)]] = 1
            if rc in si:
                x[si[rc]] = 1
            x[-1] = float(b2b)
            X.append(x)
            O.append(0.0)
        C.append(starts[-1] + ch)
        starts.append(starts[-1] + len(alts))
    X, O = np.array(X), np.array(O)
    beta = np.zeros(k)
    seg = np.repeat(np.arange(len(events)), np.diff(starts))
    lam = CLOGIT_RIDGE

    def evaluate(b):
        u = X @ b + O
        m = np.maximum.reduceat(u, starts[:-1])
        e = np.exp(u - m[seg])
        s_ = np.add.reduceat(e, starts[:-1])
        return u, m, e, s_, float((u[C] - m - np.log(s_)).sum()) - 0.5 * lam * float(b @ b)
    u, m, e, s_, obj = evaluate(beta)
    for it in range(200):
        p = e / s_[seg]
        xbar = np.add.reduceat(p[:, None] * X, starts[:-1])
        g = X[C].sum(0) - xbar.sum(0) - lam * beta
        H = -(X.T @ (p[:, None] * X)) + xbar.T @ xbar - lam * np.eye(k)
        step = np.linalg.solve(H, -g)
        t = 1.0
        while True:                       # backtracking: accept only an increase of the objective
            nb = beta + t * step
            u2, m2, e2, s2, obj2 = evaluate(nb)
            if obj2 >= obj - 1e-9 or t < 1e-6:
                break
            t *= 0.5
        beta, u, m, e, s_, gain, obj = nb, u2, m2, e2, s2, obj2 - obj, obj2
        if abs(gain) < 1e-8 and np.abs(t * step).max() < 1e-6:
            break
    ll = obj + 0.5 * lam * float(beta @ beta)
    se = np.sqrt(np.clip(np.diag(np.linalg.inv(-H)), 0, None))
    print(f"{kind}: {len(events)} choices, {len(X)} alternatives, log-lik {ll:.1f}, {it + 1} Newton steps")
    return {"n_choices": len(events), "loglik": round(ll, 2), "coef": {n: round(float(b), 4) for n, b in zip(names, beta)},
            "se": {n: round(float(v), 4) for n, v in zip(names, se)}}


def calendar(a: pd.DataFrame) -> dict:
    """Weekly pattern of game days, from team-weeks with one midweek game and three series games."""
    g = a[a.start].drop_duplicates(["game_id", "pit_team_id"]).copy()
    g["week"] = g.d.dt.isocalendar().week.astype(int)
    pats = {}
    for (t, w), x in g.groupby(["pit_team_id", "week"]):
        mid = sorted(x[x.wd.isin(MIDWEEK_DAYS)].wd)
        ser = sorted(x[x.wd.isin(SERIES_DAYS)].wd)
        if len(mid) == 1 and len(ser) == 3:
            pats[(mid[0], ser[0], ser[1], ser[2])] = pats.get((mid[0], ser[0], ser[1], ser[2]), 0) + 1
    tot = sum(pats.values())
    return {"n_team_weeks": tot, "patterns": {"|".join(map(str, k)): round(v / tot, 4) for k, v in sorted(pats.items(), key=lambda kv: -kv[1])},
            "note": "weekday numbers: 0 Mon ... 6 Sun; (midweek day, series day 1, 2, 3); equal days are doubleheaders"}


def team_usage(per: pd.DataFrame, g: float) -> dict:
    """One team's usage values at a 56-game equivalent (counts x 56 / its games)."""
    f = SEASON_GAMES / g
    app = np.sort(per.G.values * f)[::-1]
    ip = np.sort(per.outs.values / 3 * f)[::-1]
    rel = per.GS.values <= 3
    out = {"app_max": app[0], "app_5th": app[4] if len(app) > 4 else 0.0, "app_10th": app[9] if len(app) > 9 else 0.0,
           "relief_only_40ip": float((rel & (per.outs.values / 3 * f >= 40)).sum()), "relief_only_60ip": float((rel & (per.outs.values / 3 * f >= 60)).sum())}
    for k in range(3):
        out[f"ip_rank{k + 1}"] = ip[k] if len(ip) > k else 0.0
    top = per.assign(ipx=per.outs / 3 * f).sort_values("ipx", ascending=False).head(3)
    for k, (_, r) in enumerate(top.iterrows()):
        out[f"ip_rank{k + 1}_fri_sun_starts"] = r.fs_outs / 3 * f
        out[f"ip_rank{k + 1}_other_starts"] = r.os_outs / 3 * f
        out[f"ip_rank{k + 1}_relief"] = r.rl_outs / 3 * f
    return out


def benchmarks(a: pd.DataFrame, full: set) -> dict:
    """Usage gate values, per team at a 56-game equivalent, mean over the full-season teams, with
    SEs from a bootstrap over teams. Starts split as in usage_2025: Fri-Sun starts, other starts,
    relief."""
    a = a[a.pit_team_id.isin(full)].copy()
    a["fs"] = a.start & a.wd.isin([4, 5, 6])
    a["fs_outs"] = np.where(a.fs, a.outs, 0); a["os_outs"] = np.where(a.start & ~a.fs, a.outs, 0); a["rl_outs"] = np.where(~a.start, a.outs, 0)
    per = a.groupby(["pit_team_id", "pkey"]).agg(G=("game_id", "size"), GS=("start", "sum"), outs=("outs", "sum"),
                                                 fs_outs=("fs_outs", "sum"), os_outs=("os_outs", "sum"), rl_outs=("rl_outs", "sum")).reset_index()
    tg = a.groupby("pit_team_id").game_id.nunique()
    vals = pd.DataFrame({t: team_usage(per[per.pit_team_id == t], tg[t]) for t in tg.index}).T
    rng = np.random.default_rng(6)
    boot = np.array([vals.values[rng.integers(0, len(vals), len(vals))].mean(0) for _ in range(1000)])
    out = {"teams": int(len(tg)), "team_games_mean": round(float(tg.mean()), 2), "season_games": SEASON_GAMES,
           "app_max_overall_raw": int(per.G.max())}
    for i, k in enumerate(vals.columns):
        out[k] = {"value": round(float(vals[k].mean()), 3), "se": round(float(boot[:, i].std(ddof=1)), 3)}
    return out


def main() -> None:
    pa, meta, tier, full = load()
    a = appearances(pa)
    af = a[a.pit_team_id.isin(full)].copy()
    role = roles(af)
    ev_r = choice_data(af, role, "relief")
    ev_m = choice_data(af, role, "midweek")
    out = {"_note": __doc__, "built": TODAY, "full_season_teams": len(full),
           "calendar": calendar(af), "relief": fit_clogit(ev_r, "relief"), "midweek": fit_clogit(ev_m, "midweek"),
           "roles": {"names": ROLES, "staff_size_mean": round(float(role.groupby("pit_team_id").size().mean()), 2)},
           "benchmarks": benchmarks(a, full)}
    cur = json.loads(INPUTS6.read_text()) if INPUTS6.exists() else {}
    cur["usage6"] = out
    INPUTS6.write_text(json.dumps(cur, indent=1, default=float) + "\n")
    print(json.dumps({k: out[k] for k in ("calendar", "benchmarks")}, indent=1)[:3000])
    for k in ("relief", "midweek"):
        print(k, {n: f"{b:+.2f}±{out[k]['se'][n]:.2f}" for n, b in out[k]["coef"].items()})


if __name__ == "__main__":
    main()
