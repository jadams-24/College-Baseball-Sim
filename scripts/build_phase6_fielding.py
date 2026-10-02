"""Phase 6 fielding and speed inputs from the 2025 play-by-play.

Fielder identity: the fielder credits of every play (fielding_2025, scripts/build_phase6_events.py),
player keys by team and canonical name (scripts/lib/players.py). The fielder at a position in a
team-game is the player with most fielder credits there (the starter, usually).

Error (per fielder): errors per chance (putouts + assists + errors) at his position. League rate by
position; tier effect (log-odds, all positions pooled); individual true SD on the logit scale by
position by method of moments (players with MIN_FIELD_CHANCES chances or more; binomial noise
removed).

Range: hit rate of balls in play hit to the fielder's zone (hit_to_position 1-9, home runs and
reached-on-error excluded). A team's pitchers and park act on every fielder of the team alike, so
range is measured within team: each fielder's rate against his team's rate at the same position,
true SD by method of moments.

Arm: outfielders, runners taking the extra base on a single to the fielder's zone (first to third
or home, second to home), within team as range; catchers, stolen-base success against while he
catches (all runners), around the league rate.

Speed (per runner): stolen-base attempts per opportunity (on first, second open, at the start of a
play), success per attempt, and extra bases taken on singles (first to third or home, second to
home) and doubles (first to home), each with its true SD on the logit scale by method of moments,
and the correlations of the noise-free components (one Speed rating drives all three if they move
together).
Writes the "fielding6" block of data/ncaa_2025/derived/phase6_inputs_2025.json.

    python3 scripts/build_phase6_fielding.py
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
from config.phase6 import INPUTS6, MIN_FIELD_CHANCES, MIN_RUNNER_OPP  # noqa: E402
from lib.players import name_map  # noqa: E402

P = ROOT / "data/ncaa_2025/pbp/parsed"
POS = ("p", "c", "1b", "2b", "3b", "ss", "lf", "cf", "rf")
ZONE = {1: "p", 2: "c", 3: "1b", 4: "2b", 5: "3b", 6: "ss", 7: "lf", 8: "cf", 9: "rf"}
HITS = ("1B", "2B", "3B")


def logit(p):
    return np.log(p / (1 - p))


def mom(n: np.ndarray, x: np.ndarray, base: np.ndarray | None = None) -> dict:
    """True variance of rates x/n around `base` (default: the pooled rate), binomial noise removed;
    on the logit scale at the pooled rate."""
    p = x / n
    pbar = x.sum() / n.sum()
    b = pbar if base is None else base
    w = n / n.sum()
    dev2 = float((w * (p - b) ** 2).sum())
    q = b if np.ndim(b) else np.full(len(n), b)
    noise = float((w * q * (1 - q) / n).sum())
    var = max(dev2 - noise, 0.0)
    return {"n_units": int(len(n)), "trials": int(n.sum()), "rate": round(float(pbar), 5),
            "sd_logit": round(float(np.sqrt(var) / (pbar * (1 - pbar))), 4), "var_obs": dev2, "var_noise": noise}


def team_error(err: dict) -> dict:
    """Team error rate per chance (box scores, teams with 8+ games in the sample) against the team's
    run prevention d (scoreboard fit with parks): log-odds slope, and the residual team SD with noise
    removed; the part of it the fielders' own spreads explain (each position weighted by its share
    of errors, the weight of a position's log-odds in the team's), and the team residual left."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_phase2_teams import fit, load
    sb, names, tier, conf = load()
    ff = fit(sb, names)
    fd = dict(zip(names, ff["d"]))
    var_d = float(np.var(ff["d"]) - ff["noise"][:, 1, 1].mean())          # true spread of run prevention over D1
    teams = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    id2 = dict(zip(teams.ncaa_team_id, teams.team))
    sg = pd.read_csv(P / "schedule_games_2025.csv")
    t = pd.concat([pd.DataFrame({"team": sg[f"{s_}_team_id"].map(id2), "e": sg[f"{s_}_e"], "po": sg[f"{s_}_po"], "a": sg[f"{s_}_a"]})
                   for s_ in ("home", "away")]).dropna()
    t = t[t.team.isin(fd)]
    g = t.groupby("team").agg(e=("e", "sum"), po=("po", "sum"), a=("a", "sum"), n=("e", "size"))
    g = g[g.n >= 8]
    g["ch"] = g.po + g.a + g.e
    p = g.e.sum() / g.ch.sum()
    y = logit((g.e / g.ch).clip(1e-4, 1 - 1e-4)) - logit(p)
    w = (g.ch * p * (1 - p)).values
    X = np.column_stack([np.ones(len(g)), g.index.map(fd).values])
    b = np.linalg.solve(X.T @ (w[:, None] * X), X.T @ (w * y.values))
    res = y.values - X @ b
    var_obs = float((w * res ** 2).sum() / w.sum())
    noise = float((w / (g.ch.values * p * (1 - p))).sum() / w.sum())
    var_true = max(var_obs - noise, 0.0)
    eshare = {pos: v["league_rate"] for pos, v in err["by_position"].items()}
    tot = sum(err["chances_share"][pos] * eshare[pos] for pos in POS)
    share = {pos: err["chances_share"][pos] * eshare[pos] / tot for pos in POS}
    ind = sum(share[pos] ** 2 * (err["by_position"][pos]["sd_logit"] if np.isfinite(err["by_position"][pos]["sd_logit"]) else 0.0) ** 2 for pos in POS)
    return {"n_teams": int(len(g)), "rate_per_chance": round(float(p), 5), "slope_d": round(float(b[1]), 4),
            "resid_sd_true": round(float(np.sqrt(var_true)), 4), "fielders_sd": round(float(np.sqrt(ind)), 4),
            "team_sd": round(float(np.sqrt(max(var_true - ind, 0.0))), 4), "error_share": {k: round(v, 4) for k, v in share.items()},
            "total_sd": round(float(np.sqrt(var_true + b[1] ** 2 * max(var_d, 0.0))), 4)}


def main() -> None:
    meta = pd.read_csv(P / "games_meta_2025.csv")
    teams = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    tier = dict(zip(teams.ncaa_team_id, teams.tier))
    f = pd.read_csv(P / "fielding_2025.csv.gz")
    f = f[f.game_id.isin(meta.game_id) & f.position.isin(POS)].copy()
    fm = name_map(f, "team_id", "name")
    f["fkey"] = [fm[(t, n)] for t, n in zip(f.team_id, f.name)]
    f["ch"] = f.put_outs + f.assists + f.errors
    out = {"_note": __doc__, "built": dt.date.today().isoformat()}

    # ---- error -------------------------------------------------------------------------------
    pl = f.groupby(["team_id", "fkey", "position"]).agg(ch=("ch", "sum"), e=("errors", "sum")).reset_index()
    pl["tier"] = pl.team_id.map(tier)
    err = {}
    for pos in POS:
        g = pl[(pl.position == pos) & (pl.ch >= MIN_FIELD_CHANCES)]
        err[pos] = mom(g.ch.values.astype(float), g.e.values.astype(float))
        err[pos]["league_rate"] = round(float(pl[pl.position == pos].e.sum() / pl[pl.position == pos].ch.sum()), 5)
    # tier log-odds shift, pooled over positions (each position's rate by tier against its league rate)
    tshift = {}
    for t in ("p4", "mid", "low"):
        num = den = 0.0
        for pos in POS:
            g = pl[(pl.position == pos) & (pl.tier == t)]
            if g.ch.sum() == 0:
                continue
            r, r0 = g.e.sum() / g.ch.sum(), err[pos]["league_rate"]
            wgt = g.ch.sum() * r0 * (1 - r0)
            num += wgt * (logit(max(r, 1e-6)) - logit(r0)); den += wgt
        tshift[t] = round(num / den, 4)
    out["error"] = {"by_position": err, "tier_logodds": tshift,
                    "chances_share": {pos: round(float(pl[pl.position == pos].ch.sum() / pl.ch.sum()), 4) for pos in POS}}

    # ---- range (within team) -------------------------------------------------------------------
    pa = pd.read_csv(P / "pa_events_2025.csv.gz", low_memory=False,
                     usecols=["game_id", "group_id", "bat_team_id", "pit_team_id", "result", "hit_to", "on1", "on2", "on3",
                              "r1_to", "r2_to", "batter_to"])
    pa = pa[pa.game_id.isin(meta.game_id)]
    modal = (f.groupby(["game_id", "team_id", "position", "fkey"]).size().rename("n").reset_index()
             .sort_values("n").drop_duplicates(["game_id", "team_id", "position"], keep="last"))
    bip = pa[pa.hit_to.between(1, 9) & ~pa.result.isin(["HR", "ROE", "K", "BB", "IBB", "HBP"])].copy()
    bip["position"] = bip.hit_to.astype(int).map(ZONE)
    bip["hit"] = bip.result.isin(HITS).astype(int)
    bip = bip.merge(modal.rename(columns={"team_id": "pit_team_id"}), on=["game_id", "pit_team_id", "position"], how="inner")
    rng_ = {}
    for pos in POS[1:]:
        g = bip[bip.position == pos].groupby(["pit_team_id", "fkey"]).agg(n=("hit", "size"), x=("hit", "sum")).reset_index()
        tp = g.groupby("pit_team_id").agg(tn=("n", "sum"), tx=("x", "sum"))
        g = g.join(tp, on="pit_team_id")
        g = g[(g.n >= MIN_FIELD_CHANCES) & (g.tn > g.n)]           # teams with another fielder at the position
        base = (g.tx - g.x) / (g.tn - g.n)                          # the rest of the team at this position
        rng_[pos] = mom(g.n.values.astype(float), g.x.values.astype(float), base.values)
        rng_[pos]["league_rate"] = round(float(bip[bip.position == pos].hit.mean()), 5)
    out["range"] = {"by_position": rng_, "note": "within team: each fielder against the rest of his team at the position"}

    # ---- arm --------------------------------------------------------------------------------
    sing = pa[(pa.result == "1B") & pa.hit_to.between(7, 9)].copy()
    sing["position"] = sing.hit_to.astype(int).map(ZONE)
    rows = []
    for col, base0, extra in (("r1_to", 1, (3, 4)), ("r2_to", 2, (4,))):
        s = sing[sing[f"on{base0}"] == 1].copy()
        dest = pd.to_numeric(s[col], errors="coerce")
        s = s[dest.notna() & (dest > 0)]
        s["xb"] = pd.to_numeric(s[col], errors="coerce").isin(extra).astype(int)
        rows.append(s[["game_id", "pit_team_id", "position", "xb"]])
    out["of_zone_share"] = {k: round(float(v), 4) for k, v in sing.position.value_counts(normalize=True).reindex(["lf", "cf", "rf"]).items()}
    arm_ev = pd.concat(rows).merge(modal.rename(columns={"team_id": "pit_team_id"}), on=["game_id", "pit_team_id", "position"])
    g = arm_ev.groupby(["pit_team_id", "fkey"]).agg(n=("xb", "size"), x=("xb", "sum")).reset_index()
    out["arm_of"] = mom(g[g.n >= MIN_RUNNER_OPP].n.values.astype(float), g[g.n >= MIN_RUNNER_OPP].x.values.astype(float))
    r = pd.read_csv(P / "runners_2025.csv.gz")
    r = r[r.game_id.isin(meta.game_id) & (r.kind != "out")].copy()      # runner actions carry the runner's team
    hm = dict(zip(meta.game_id, meta.home_team_id)); aw = dict(zip(meta.game_id, meta.away_team_id))
    r["pit_team_id"] = np.where(r.team_id.values == r.game_id.map(hm).values, r.game_id.map(aw).values, r.game_id.map(hm).values)
    link = pa[["group_id", "result"]].rename(columns={"group_id": "play_by_play_id"})
    r = r.merge(link, on="play_by_play_id", how="left")                 # the plate appearance's result, where the play is one
    sb = r[r.kind.isin(["stolen base", "caught stealing"])].copy()
    sb["ok"] = (sb.kind == "stolen base").astype(int)
    cm = modal[modal.position == "c"].rename(columns={"team_id": "pit_team_id", "fkey": "catcher"})[["game_id", "pit_team_id", "catcher"]]
    sbc = sb.merge(cm, on=["game_id", "pit_team_id"], how="inner")
    g = sbc.groupby(["pit_team_id", "catcher"]).agg(n=("ok", "size"), x=("ok", "sum")).reset_index()
    out["arm_c"] = mom(g[g.n >= MIN_RUNNER_OPP].n.values.astype(float), g[g.n >= MIN_RUNNER_OPP].x.values.astype(float))

    # ---- speed (runners) ----------------------------------------------------------------------
    rm = name_map(r, "team_id", "name")
    r["rkey"] = [rm[(t, n)] for t, n in zip(r.team_id, r.name)]
    ob = r[r.kind == "onbase"]
    occ2 = set(ob[ob.on_base == 2].play_by_play_id)
    opp = ob[(ob.on_base == 1) & ~ob.play_by_play_id.isin(occ2)].groupby(["team_id", "rkey"]).size().rename("opp")
    att_ev = r[r.kind.isin(["stolen base", "caught stealing"]) & (r.on_base == 1)]
    att = att_ev.groupby(["team_id", "rkey"]).size().rename("att")
    suc = att_ev[att_ev.kind == "stolen base"].groupby(["team_id", "rkey"]).size().rename("sb")
    # extra bases: the runner's final destination on a single (from first: 3rd/home; from second: home)
    # and on a double (from first: home); taken from the play's runner advance with the largest to_base
    adv = r[r.kind.isin(["advances", "onbase"]) & r.result.isin(["1B", "2B"])].copy()
    adv["to"] = pd.to_numeric(adv.to_base, errors="coerce").fillna(adv.on_base)
    last = adv.groupby(["play_by_play_id", "team_id", "rkey", "result"]).agg(frm=("on_base", "min"), to=("to", "max")).reset_index()
    last = last[last.frm.isin([1, 2])]
    last["xb"] = np.where(last.result == "1B", np.where(last.frm == 1, last.to >= 3, last.to >= 4), np.where(last.frm == 1, last.to >= 4, np.nan))
    last = last[last.xb.notna() & ~((last.result == "2B") & (last.frm == 2))]
    xb = last.groupby(["team_id", "rkey"]).agg(xbn=("xb", "size"), xbx=("xb", "sum"))
    run = pd.concat([opp, att, suc, xb], axis=1).fillna(0)
    speed = {"attempt": mom(run[run.opp >= MIN_RUNNER_OPP].opp.values, run[run.opp >= MIN_RUNNER_OPP].att.values),
             "success": mom(run[run.att >= 5].att.values, run[run.att >= 5].sb.values),
             "extra_base": mom(run[run.xbn >= 5].xbn.values, run[run.xbn >= 5].xbx.values)}
    # correlation of the noise-free components (covariance of the rate deviations; sampling noise of
    # different event types is independent, so the cross moments need no correction)
    q = run[(run.opp >= MIN_RUNNER_OPP) & (run.att >= 3) & (run.xbn >= 5)].copy()
    comps = {"attempt": q.att / q.opp, "success": q.sb / q.att, "extra_base": q.xbx / q.xbn}
    names = list(comps)
    cm_ = np.cov(np.column_stack([comps[k] for k in names]).T)
    corr = {}
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if j <= i:
                continue
            va = max(cm_[i, i] - speed[a]["var_noise"], 1e-12); vb = max(cm_[j, j] - speed[b]["var_noise"], 1e-12)
            corr[f"{a}|{b}"] = round(float(np.clip(cm_[i, j] / np.sqrt(va * vb), -1, 1)), 3)
    speed["corr"] = corr
    speed["n_runners_corr"] = int(len(q))
    out["speed"] = speed
    out["team_error"] = team_error(out["error"])
    cur = json.loads(INPUTS6.read_text()) if INPUTS6.exists() else {}
    cur["fielding6"] = out
    INPUTS6.write_text(json.dumps(cur, indent=1, default=float) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "_note"}, indent=1, default=float)[:6000])


if __name__ == "__main__":
    main()
