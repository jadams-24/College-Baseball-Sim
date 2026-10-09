"""Round 3 of the variance-stage sizes (owner, 2026-10-08): the sim side of times through the order and mop-up pitching on the
final engine, both sides of plate-appearance length by base state and of platoon lineups, Phase 3's measured variance link,
and the running total. Sizes only, no fixes.

Inputs: the instrumented seasons of scripts/diag_round3_sim.py (runs/round3/<engine key>/); round 2's real-data estimates in
reports/diagnosis_sizes.json (linear weights, the TTO penalty and its covariance, the mop-up sizes); the 2025 WMT play-by-play
for plate-appearance length; data/ncaa_2025/roster_aggregates/lineup_by_starter_hand.csv for platoon lineups (when the roster
workflow has produced it; otherwise that row waits); reports/phase3.md's variance link (reports/phase3.json).

Common scale (rounds 1 and 2): the dispersion of runs per team-game around the scoreboard fit without parks. A component t_g of
a team-game's runs is worth dphi = mean(t^2 / mu) + 2 mean((r - t) t / mu) (scripts/diag_tto_mopup.py dphi_component). Here it
is measured on simulated team-games (mu from the same fit on each simulated season), so a size is what the mechanism would
add to the engine as it stands, its own hook and bullpen included; the missing amount is real minus this engine's dispersion.
SEs are between seasons (each season one independent sample) unless stated.

Sizes:
  3  times through the order: the sim's own penalty (the round 2 regression, team-game FE spec, on simulated plate
     appearances), then t_g = sum over the batting team's PAs against the starter of (real penalty - sim penalty)[tto]
  4  mop-up pitching: the sim's mop-up component (relief PAs after entries at |margin| >= 5: the reliever's leave-game-out
     rv per PA minus his team's relief mean, noise-corrected) against round 2's real +0.066; what a fix could add is the
     difference
  5  plate-appearance length by base state: pitches per PA with runners on minus bases empty, within the result (result
     fixed effects), real and sim; the starter's extra pitches per start, the batters it moves from the starter to the
     bullpen at the sim's pitches per batter, and their run value (team relief mean minus the starter's season rate) as t_g
  6  platoon lineups: the starting nine's left-handed share against right-handed minus left-handed starters within team,
     real and sim; the platoon-advantage share it adds, and t_g = PAs of the starting nine against the starter x (advantage
     gained x the platoon run value per PA - the lineup's quality cost), by the opposing starter's hand
    python3 scripts/diag_round3.py [--dir runs/round3/<key>]
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from build_phase2_teams import fit  # noqa: E402
from diag_tto_mopup import MIN_OTHER_BF, _codes, dphi_component, fe_ols  # noqa: E402

PBP = ROOT / "data/ncaa_2025/pbp/parsed"
AGG = ROOT / "data/ncaa_2025/roster_aggregates"
SIZES = ROOT / "reports/diagnosis_sizes.json"
OUT_MD = ROOT / "reports/diagnosis_sizes_round3.md"
OUT_JSON = ROOT / "reports/diagnosis_sizes_round3.json"
REAL_PHI = 2.6185          # team_talent_2025.dispersion_without_parks (rounds 1 and 2)
BLOWOUT = 5                # round 2's mop-up entries: |margin| >= 5
# the engine's result classes on round 2's linear weights; an in-play out takes the real outs' count-weighted mean
OUT_CLASSES = {"FO": 33654, "GO": 25932, "GIDP": 2236, "DP": 618}


def real_round2() -> dict:
    d = json.loads(SIZES.read_text())
    lw = d["item5_tto"]["linear_weights"]
    w = sum(OUT_CLASSES.values())
    lw = dict(lw, IP_OUT=sum(lw[k] * n for k, n in OUT_CLASSES.items()) / w, OUT=sum(lw[k] * n for k, n in OUT_CLASSES.items()) / w)
    reg = d["item5_tto"]["regressions"]["team_game_fe"]["rv"]
    return {"lw": lw, "tto": np.array([reg[f"tto{k}"]["b"] for k in (2, 3, 4)]),
            "tto_cov": np.array(d["item5_tto"]["regressions"]["team_game_fe"]["_cov_rv"]),
            "tto_dphi": (d["item5_tto"]["dphi"]["dphi"], d["item5_tto"]["dphi_se"]["dphi"]),
            "mopup": {k: (v["dphi_noise_corrected"], v["se"]["dphi_noise_corrected"]) for k, v in d["item6_mopup"]["dphi"].items()
                      if isinstance(v, dict) and "dphi_noise_corrected" in v},
            "running": d["running_total"]}


# ----------------------------------------------------------------------------------------------------------------------
# one simulated season
# ----------------------------------------------------------------------------------------------------------------------

def frames(r: dict, lw: dict) -> tuple:
    pa = pd.DataFrame(r["pa"])
    g = pd.DataFrame(r["games"], columns=["gid", "home", "away", "home_score", "away_score", "innings", "run_rule", "weekend",
                                          "tournament", "neutral", "half_innings"])
    pa = pa.sort_index()          # game order, plate appearances in order within the game
    unknown = sorted(set(pa.res) - set(lw))
    if unknown:
        raise ValueError(f"result classes without a linear weight: {unknown}")
    pa["rv"] = pa.res.map(lw).astype(float)
    pa["runners"] = (pa.on1 + pa.on2 + pa.on3) > 0
    k = ["gid", "pit_team"]
    pa["outing"] = (pa.pitcher != pa.groupby(k).pitcher.shift()).groupby([pa.gid, pa.pit_team]).cumsum()
    pa["is_sp"] = pa.outing == 1
    pa["bf"] = pa.groupby(k + ["outing"]).cumcount() + 1
    pa["tto"] = (pa.groupby(k + ["outing", "batter"]).cumcount() + 1).clip(upper=4)
    pa["pitches_before"] = pa.groupby(k + ["outing"]).pitches.cumsum() - pa.pitches
    pa["margin"] = pa.pit_score - pa.bat_score
    pa["pid"] = pa.pitcher.astype(str); pa["bid"] = pa.batter.astype(str)
    pa["game_id"] = pa.gid; pa["bat_team_id"] = pa.bat_team; pa["pit_team_id"] = pa.pit_team
    for y in ("K", "BB", "HBP", "HR"):
        pa[y] = (pa.res == y).astype(float)
    pa["OB"] = pa.res.isin(["1B", "2B", "3B", "HR", "BB", "HBP"]).astype(float)
    return pa, g


def team_games(pa: pd.DataFrame, g: pd.DataFrame) -> pd.DataFrame:
    """Runs R, expected mu (the scoreboard fit without parks on this season's regular-season games, as engine/report6.py),
    r = R - mu, and the split into half-innings begun by the fielding team's starter (rS, eS) and the rest, the expected runs
    spread over the half-innings by the season's inning shares (scripts/diag_sizes.py expected_runs)."""
    reg = g[~g.tournament]
    names = sorted(set(reg.home) | set(reg.away))
    f = fit(reg.rename(columns={}), names, parks=False)
    fo, fd = dict(zip(names, f["o"])), dict(zip(names, f["d"]))
    rows = []
    for x in reg.itertuples():
        for bat, pit, sgn, R in ((x.home, x.away, 0.5, x.home_score), (x.away, x.home, -0.5, x.away_score)):
            rows.append((x.gid, bat, pit, R, math.exp(f["a"] + fo[bat] - fd[pit] + f["h"] * sgn)))
    tg = pd.DataFrame(rows, columns=["gid", "bat_team", "pit_team", "R", "mu_g"]).set_index(["gid", "bat_team"])
    # half-innings: runs, begun by the starter or not
    hi = []
    first = pa.groupby(["gid", "inning", "half"]).agg(bat_team=("bat_team", "first"), sp=("is_sp", "first"))
    for x in reg.itertuples():
        for inn, half, runs, _n in x.half_innings:
            hi.append((x.gid, inn, 0 if half == "T" else 1, runs))
    hi = pd.DataFrame(hi, columns=["gid", "inning", "half", "runs"]).join(first, on=["gid", "inning", "half"]).dropna(subset=["bat_team"])
    inn = hi.inning.clip(upper=10)
    w = hi.groupby(inn).runs.mean() / hi.groupby(["gid", "bat_team"]).runs.sum().mean()
    hi["w"] = inn.map(w).values
    hi["mu_g"] = tg.mu_g.reindex(pd.MultiIndex.from_arrays([hi.gid, hi.bat_team])).values
    hi["e"] = hi.mu_g * hi.w
    hi["e"] *= hi.runs.sum() / hi.e.sum()
    hi["r"] = hi.runs - hi.e
    s = hi.assign(rS=np.where(hi.sp, hi.r, 0.0), eS=np.where(hi.sp, hi.e, 0.0)).groupby(["gid", "bat_team"]).agg(
        mu=("e", "sum"), r=("r", "sum"), rS=("rS", "sum"), eS=("eS", "sum"), R_hi=("runs", "sum"))
    tg = tg.join(s, how="inner")
    tg["rR"] = tg.r - tg.rS
    return tg, f


def tto_sim(pa: pd.DataFrame) -> dict:
    """Round 2's main specification on simulated plate appearances: rv on TTO dummies for the starter's PAs, batter FE +
    pitcher FE + team-game FE, every relief PA included."""
    d = pa
    t = np.where(d.is_sp, d.tto, 0)
    X = np.column_stack([(t == k).astype(float) for k in (2, 3, 4)])
    tg = d.gid.astype(str) + "|" + d.bat_team.astype(str)
    (b, se, V), = fe_ols(d[["rv"]].values.astype(float), X, [_codes(d.bid), _codes(d.pid), _codes(tg)], _codes(d.pid))
    return {"b": b, "se": se}


def exposure(pa: pd.DataFrame, tg: pd.DataFrame, delta: np.ndarray) -> np.ndarray:
    sp = pa[pa.is_sp]
    v = sp.tto.map({1: 0.0, 2: delta[0], 3: delta[1], 4: delta[2]})
    return v.groupby([sp.gid, sp.bat_team]).sum().reindex(tg.index).fillna(0.0).values


def mopup_sim(pa: pd.DataFrame, tg: pd.DataFrame) -> dict:
    """Round 2's mop-up component (scripts/diag_tto_mopup.py pa_gaps / mopup_dphi) on simulated plate appearances, every
    team being full-season."""
    pg = pa.groupby(["pid", "gid"]).agg(bf=("rv", "size"), rv=("rv", "sum"))
    season = pg.groupby("pid").sum()
    k = pd.MultiIndex.from_arrays([pa.pid, pa.gid])
    n_o = season.bf.reindex(pa.pid).values - pg.bf.reindex(k).values
    s_o = season.rv.reindex(pa.pid).values - pg.rv.reindex(k).values
    rl = ~pa.is_sp
    team_rl = pa[rl].groupby("pit_team").rv.mean()
    within = pa.rv - pa.groupby("pid").rv.transform("mean")
    sig2 = float((within ** 2).sum() / (len(pa) - pa.pid.nunique()))
    ok = rl & (n_o >= MIN_OTHER_BF)
    gap = np.where(ok, s_o / np.where(n_o > 0, n_o, 1) - pa.pit_team.map(team_rl).values, 0.0)
    noise = np.where(ok, sig2 / np.where(n_o > 0, n_o, 1), 0.0)
    entry = pa.groupby(["gid", "pit_team", "outing"]).margin.transform("first").abs()
    d = pa.assign(gap=gap, noise=noise, entry=entry)
    out = {}
    for name, lo in (("blowout_5plus", BLOWOUT), ("blowout_7plus_engine_bin", 7), ("blowout_8plus", 8), ("all_relief", 0)):
        x = d[rl & (d.entry >= lo)]
        t = x.groupby(["gid", "bat_team"]).gap.sum().reindex(tg.index).fillna(0.0).values
        pp = x.groupby(["gid", "bat_team", "pid"]).agg(n=("gap", "size"), nv=("noise", "first"))
        nv = (pp.n ** 2 * pp.nv).groupby(level=[0, 1]).sum().reindex(tg.index).fillna(0.0).values
        c = dphi_component(tg, t)
        c["noise_part"] = float(np.mean(nv / tg.mu.values))
        c["dphi_noise_corrected"] = c["dphi"] - c["noise_part"]
        # the quality gap itself: BF-weighted mean of the entering pitchers' leave-game-out rate minus the team relief mean
        xq = x[ok[x.index]]
        c["mean_gap_per_pa"] = float(xq.gap.mean()) if len(xq) else float("nan")
        c["relief_pa_share"] = float(len(x) / max(rl.sum(), 1))
        out[name] = c
    return out


def pa_length(pa: pd.DataFrame) -> float:
    """Pitches per PA with runners on minus bases empty, within the result (result fixed effects), intentional walks out."""
    d = pa[pa.pitches > 0]
    y = d.pitches.values.astype(float)
    (b, se, _), = fe_ols(y[:, None], d.runners.values.astype(float)[:, None], [_codes(d.res)], _codes(d.gid))
    return float(b[0])


def pa_length_size(pa: pd.DataFrame, tg: pd.DataFrame, delta: float) -> dict:
    """The starter's extra pitches per start if each PA with runners on took `delta` more pitches; the batters that moves to
    the bullpen at the start's pitches per batter (the hook reads pitch counts), and t_g = those batters x (the fielding
    team's relief rv per PA - the starter's season rv per PA), on the batting team's runs."""
    sp = pa[pa.is_sp]
    st = sp.groupby(["gid", "pit_team"]).agg(bat_team=("bat_team", "first"), pid=("pid", "first"), bf=("rv", "size"),
                                             pitches=("pitches", "sum"), on=("runners", "sum"))
    extra = delta * st.on
    moved = extra / (st.pitches / st.bf)
    q_sp = pa[pa.is_sp].groupby("pid").rv.mean()
    q_rl = pa[~pa.is_sp].groupby("pit_team").rv.mean()
    gapq = q_rl.reindex(st.index.get_level_values(1)).values - q_sp.reindex(st.pid).values
    t = pd.Series(moved.values * gapq, index=pd.MultiIndex.from_arrays([st.index.get_level_values(0), st.bat_team])).groupby(level=[0, 1]).sum()
    c = dphi_component(tg, t.reindex(tg.index).fillna(0.0).values)
    c.update({"extra_pitches_per_start": float(extra.mean()), "batters_moved_per_start": float(moved.mean()),
              "starter_bf_per_start": float(st.bf.mean()), "starter_pitches_per_start": float(st.pitches.mean()),
              "pas_with_runners_per_start": float(st.on.mean())})
    return c


def lineups_sim(pa: pd.DataFrame) -> pd.DataFrame:
    """The starting nine (first nine distinct batters of the team-game) by listed bats against the opposing starter's hand."""
    d = pa.drop_duplicates(["gid", "bat_team", "batter"])
    d = d[d.groupby(["gid", "bat_team"]).cumcount() < 9]
    sp = pa[pa.is_sp].groupby(["gid", "pit_team"]).throws.first()
    d = d.assign(sp=sp.reindex(pd.MultiIndex.from_arrays([d.gid, d.pit_team])).values)
    d = d[d.groupby(["gid", "bat_team"]).batter.transform("size") == 9]
    return d.groupby(["bat_team", "sp"]).agg(team_games=("gid", "nunique"), bats_L=("bats", lambda s: int((s == "L").sum())),
                                             bats_R=("bats", lambda s: int((s == "R").sum())), bats_S=("bats", lambda s: int((s == "S").sum())),
                                             starters=("bats", "size")).reset_index()


def within_team_L(df: pd.DataFrame, team="bat_team", hand="sp") -> dict:
    """The starting nine's left-handed (listed L) share against right-handed minus left-handed starters, within team
    (teams with starters of both hands; each team weighted by its harmonic number of team-games), and the platoon-advantage
    share of the starting nine against a fixed lineup (the team's own mean mix against both hands)."""
    p = df.pivot_table(index=team, columns=hand, values=["team_games", "starters", "bats_L", "bats_R", "bats_S"], aggfunc="sum").fillna(0)
    both = (p[("team_games", "L")] > 0) & (p[("team_games", "R")] > 0)
    p = p[both]
    sh = {h: p[("bats_L", h)] / p[("starters", h)] for h in "LR"}
    shr = {h: p[("bats_R", h)] / p[("starters", h)] for h in "LR"}
    w = 1 / (1 / p[("team_games", "L")] + 1 / p[("team_games", "R")])
    dL = float(np.average(sh["R"] - sh["L"], weights=w))
    dR = float(np.average(shr["L"] - shr["R"], weights=w))
    # advantage share: actual against a fixed lineup with the team's pooled mix
    nL, nR = p[("team_games", "L")], p[("team_games", "R")]
    poolL = (p[("bats_L", "L")] + p[("bats_L", "R")]) / (p[("starters", "L")] + p[("starters", "R")])
    poolR = (p[("bats_R", "L")] + p[("bats_R", "R")]) / (p[("starters", "L")] + p[("starters", "R")])
    act = (nR * sh["R"] + nL * shr["L"]) / (nL + nR)
    fixed = (nR * poolL + nL * poolR) / (nL + nR)
    gain = float(np.average(act - fixed, weights=nL + nR))
    return {"dL_share_vsR_minus_vsL": dL, "dR_share_vsL_minus_vsR": dR, "adv_gain_vs_fixed_lineup": gain, "n_teams": int(both.sum()),
            "share_vs_LHP": float(nL.sum() / (nL + nR).sum())}


def season_sizes(r: dict, real: dict, real_pa_delta: float) -> dict:
    pa, g = frames(r, real["lw"])
    tg, f = team_games(pa, g)
    out = {"phi": f["phi"], "resid_corr": f["residual_corr"], "n_team_games": int(len(tg)), "n_pa": int(len(pa))}
    ts = tto_sim(pa)
    out["tto_sim"] = ts["b"].tolist()
    out["tto_dphi_real_penalty"] = dphi_component(tg, exposure(pa, tg, real["tto"]))
    out["tto_dphi_added"] = dphi_component(tg, exposure(pa, tg, real["tto"] - ts["b"]))
    out["mopup"] = mopup_sim(pa, tg)
    out["pa_length_sim"] = pa_length(pa)
    out["pa_length_size"] = pa_length_size(pa, tg, real_pa_delta - out["pa_length_sim"])
    out["pa_length_runners_share"] = float(pa.runners.mean())
    out["pa_length_by_runners"] = pa[pa.pitches > 0].groupby("runners").pitches.mean().to_dict()
    out["lineups"] = within_team_L(lineups_sim(pa))
    out["adv_share_all_pa"] = float((pa.side != pa.throws).mean())
    out["_pa_cache"] = None
    return out, pa, tg


def mean_se(vals) -> tuple:
    a = np.array(vals, float)
    return float(a.mean()), float(a.std(ddof=1) / math.sqrt(len(a))) if len(a) > 1 else float("nan")


# ----------------------------------------------------------------------------------------------------------------------
# real side of the new candidates
# ----------------------------------------------------------------------------------------------------------------------

def real_pa_length() -> dict:
    pa = pd.read_csv(PBP / "pa_events_2025.csv.gz", usecols=["game_id", "on1", "on2", "on3", "result", "pitches"], low_memory=False)
    d = pa[pa.pitches.notna() & (pa.pitches > 0) & (pa.result != "IBB")]
    run = ((d.on1 + d.on2 + d.on3) > 0).values.astype(float)
    (b, se, _), = fe_ols(d[["pitches"]].values.astype(float), run[:, None], [_codes(d.result)], _codes(d.game_id))
    return {"delta": float(b[0]), "se": float(se[0]), "n_pa": int(len(d)), "missing_share": float(1 - len(d) / len(pa)),
            "raw": d.groupby(run.astype(bool)).pitches.mean().rename(index={False: "empty", True: "runners"}).to_dict()}


def real_lineups() -> dict | None:
    f = AGG / "lineup_by_starter_hand.csv"
    if not f.exists():
        return None
    df = pd.read_csv(f)
    out = {"all": within_team_L(df, team="bat_team_id", hand="starter_throws")}
    for t, g in df.groupby("bat_tier"):
        out[t] = within_team_L(g, team="bat_team_id", hand="starter_throws")
    # lineup quality: mean season rv per PA of the starting nine against L minus against R, within team
    p = df.pivot_table(index="bat_team_id", columns="starter_throws", values=["rv_sum", "rv_n", "team_games"], aggfunc="sum")
    p = p[(p[("rv_n", "L")] > 0) & (p[("rv_n", "R")] > 0)]
    q = p[("rv_sum", "L")] / p[("rv_n", "L")] - p[("rv_sum", "R")] / p[("rv_n", "R")]
    w = 1 / (1 / p[("team_games", "L")] + 1 / p[("team_games", "R")])
    out["quality_vsL_minus_vsR_per_starter"] = float(np.average(q, weights=w))
    out["quality_se"] = float(np.sqrt(np.average((q - np.average(q, weights=w)) ** 2, weights=w) / len(q)))
    return out


# ----------------------------------------------------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=None)
    a = ap.parse_args()
    if a.dir is None:
        from diag_round3_sim import out_dir
        a.dir = out_dir()
    a.dir = a.dir.resolve() if a.dir.is_absolute() else (ROOT / a.dir).resolve()
    real = real_round2()
    rpl = real_pa_length()
    per = []
    for f in sorted(a.dir.glob("season_*.pkl")):
        cache = f.with_suffix(".sizes.json")         # per-season results, so a rerun of the summary is cheap
        if cache.exists():
            s = json.loads(cache.read_text())
        else:
            s, _, _ = season_sizes(pickle.loads(f.read_bytes()), real, rpl["delta"])
            s.pop("_pa_cache")
            cache.write_text(json.dumps(s, default=float))
        per.append(s)
        print(f.name, f"phi {s['phi']:.3f}", "tto_sim", np.round(np.array(s["tto_sim"], float), 4), "mopup5", round(s["mopup"]["blowout_5plus"]["dphi_noise_corrected"], 4), flush=True)
    res = {"seasons": len(per), "dir": str(a.dir.relative_to(ROOT)), "per_season": per}
    res["real_pa_length"] = rpl
    res["real_lineups"] = real_lineups()
    OUT_JSON.write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "per_season"}, indent=1, default=float))


if __name__ == "__main__":
    main()
