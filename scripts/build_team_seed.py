"""Seed teams from their real programs (owner decision 2026-10-09; dynasty year 0): the inputs engine/league.py needs to
assign the calibrated team-strength draws to programs by their recent real strength.

The league keeps its drawn strength set exactly as calibrated per tier and conference: the conference effects are reordered
among the conferences of a tier, and the team deviations among the teams of a conference. The order follows a noisy version
of real 2021-2025 strength, with the noise set so the prior's correlation with the year-0 strength equals the real
correlation of a program's recent history with its next season's true strength.

Per season 2021-2025: the scoreboard fit (scripts/build_phase2_teams.fit, no parks) on every D1-vs-D1 final; o + d per
program, with its estimation variance. Prior for a program: the recency-weighted mean (half-life HALF_LIFE seasons) of its
seasons. Within-conference deviation (2025 conference map) standardized by the tier's pooled SD; conference means relative to
the tier mean, standardized the same way.

Real predictability, fitted on 2023-2025 (each season predicted from the seasons before it): the correlation of the prior's
within-conference deviation with the season's fitted deviation, divided by the square root of that season's reliability (the
fit's estimation noise against the spread of fitted deviations), so it is the correlation with true strength, by tier; the
same for conference means within tier.

Noise solved, not assumed: the engine ranks a small fixed set (four P4 conferences, about ten teams a conference), and rank
assignment of a set loses correlation against a bivariate normal draw, so sigma = sqrt(1/r^2 - 1) undershoots. For each tier
and level, sigma is solved by bisection on a simulation of the engine's own procedure (engine/league.py seed_order on the
tier's team or conference draws, config.phase2 team_draw) so the pooled correlation of the prior with the assigned draw
equals the real target; where even sigma 0 cannot reach it, sigma is 0 and the shortfall is reported.

Tier offset (owner approval 2026-10-10): the calibrated tier means are team-weighted averages of real teams. Unseeded,
conference effects are independent of conference size, so the team-weighted mean of a tier's effects is 0 in expectation.
Seeded, they follow real conference strength, and real strength correlates with size (low tier: -.45, the largest low-tier
conferences are the weakest), so the team-weighted tier mean would move. offset[tier] = -E[sum_c n_c c_c / sum_c n_c] over
the seeded conferences, by simulation of the engine's procedure (N_OFFSET draws), added to every seeded conference effect of
the tier: each tier's spread and ordering are unchanged and its team-weighted mean is the calibrated one in expectation.

Writes data/ncaa_2025/derived/team_seed_2025.json, keyed by NCAA team id (the engine never reads data/schools).
    python3 scripts/build_team_seed.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from build_phase2_teams import fit  # noqa: E402
from config.phase2 import TEAM_SEED, TEAM_SEED_HALF_LIFE as HALF_LIFE  # noqa: E402

SEASONS = (2021, 2022, 2023, 2024, 2025)
FIT_TARGETS = (2023, 2024, 2025)            # seasons predicted from the seasons before them
MIN_CONF_ENTRIES = 50                       # a feed conference with this many team-game entries is Division I
NON_D1_CONF = "NON-NCAA ORG"                # the feed's non-NCAA opponents (2021-2024): never Division I
INDEPENDENT = "DI Independent"


def aliases() -> dict:
    a = pd.read_csv(ROOT / "data/schools/name_aliases.csv")
    return dict(zip(a.iloc[:, 0], a.iloc[:, 1]))


def season_fits(teams: pd.DataFrame) -> tuple[dict, dict]:
    """o + d and its estimation variance per program per season, programs named as in teams_2025.csv."""
    f25 = pd.read_csv(ROOT / "data/ncaa_2025/scoreboard/games_2025.csv")
    seo = dict(zip(f25.home, f25.home_seo)); seo.update(dict(zip(f25.away, f25.away_seo)))
    ours = set(teams.team)
    by_seo = {seo[n]: n for n in ours if n in seo}
    alias = aliases()
    S, N = {}, {}
    for y in SEASONS:
        d = pd.read_csv(ROOT / f"data/ncaa_{y}/scoreboard/games_{y}.csv")
        d = d[(d.state == "final") & d.home_score.notna() & d.away_score.notna() & (d.home_score != d.away_score)]
        if "url" in d:
            d = d.drop_duplicates("url")
        cn = pd.concat([d.away_conf, d.home_conf]).value_counts()
        d1c = set(cn[cn >= MIN_CONF_ENTRIES].index) - {NON_D1_CONF}
        d = d[d.home_conf.isin(d1c) & d.away_conf.isin(d1c)]
        key = lambda name, slug: by_seo.get(slug, alias.get(name, name))        # noqa: E731
        sb = pd.DataFrame({"home": [key(h, s) for h, s in zip(d.home, d.home_seo)], "away": [key(a, s) for a, s in zip(d.away, d.away_seo)]})
        sb["hw"] = d.home_score.values > d.away_score.values
        sb["nt"] = False
        sb["home_score"], sb["away_score"] = d.home_score.values, d.away_score.values
        names = sorted(set(sb.home) | set(sb.away))
        f = fit(sb, names, parks=False)
        S[y] = {t: float(o + dd) for t, o, dd in zip(names, f["o"], f["d"])}
        N[y] = {t: float(nz[0, 0] + nz[1, 1] + 2 * nz[0, 1]) for t, nz in zip(names, f["noise"])}
    return S, N


def prior(S: dict, team: str, before: int) -> tuple[float, int]:
    ys = [y for y in S if y < before and team in S[y]]
    if not ys:
        return float("nan"), 0
    w = np.array([0.5 ** ((before - 1 - y) / HALF_LIFE) for y in ys])
    return float(np.dot(w, [S[y][team] for y in ys]) / w.sum()), len(ys)


def predictability(S: dict, N: dict, teams: pd.DataFrame) -> tuple[dict, dict]:
    rows = []
    for t in FIT_TARGETS:
        for _, r in teams.iterrows():
            p, k = prior(S, r.team, t)
            if k and r.team in S[t]:
                rows.append((t, r.team, r.conference, r.tier, p, S[t][r.team], N[t][r.team]))
    df = pd.DataFrame(rows, columns=["t", "team", "conf", "tier", "pred", "target", "noise"])
    df["g"] = np.where(df.conf == INDEPENDENT, "I|" + df.tier, df.conf)
    for c in ("pred", "target"):
        df[c + "_w"] = df[c] - df.groupby(["t", "g"])[c].transform("mean")
    r_team = {}
    for tier, g in df.groupby("tier"):
        r = float(np.corrcoef(g.pred_w, g.target_w)[0, 1]); rel = float((g.target_w.var() - g.noise.mean()) / g.target_w.var())
        r_team[tier] = {"r_true": round(r / np.sqrt(rel), 4), "r_season": round(r, 4), "reliability": round(rel, 4), "n": int(len(g))}
    cm = df[df.conf != INDEPENDENT].groupby(["t", "conf", "tier"]).agg(pred=("pred", "mean"), target=("target", "mean"),
                                                                       noise=("noise", "mean"), k=("team", "size")).reset_index()
    for c in ("pred", "target"):
        cm[c + "_w"] = cm[c] - cm.groupby(["t", "tier"])[c].transform("mean")
    r_conf = {}
    for tier, g in cm.groupby("tier"):
        r = float(np.corrcoef(g.pred_w, g.target_w)[0, 1]); rel = float((g.target_w.var() - (g.noise / g.k).mean()) / g.target_w.var())
        r_conf[tier] = {"r_true": round(min(r / np.sqrt(rel), 0.999), 4), "r_season": round(r, 4), "reliability": round(rel, 4), "n": int(len(g))}
    return r_team, r_conf


N_SIM = 400          # simulated leagues per bisection step
N_OFFSET = 20000     # simulated conference draws for the tier offset


def tier_offset(z: list, sizes: list, conf_cov: np.ndarray, sigma: float) -> dict:
    """Expected team-weighted mean of the tier's seeded conference effects (o, d), its negative the offset, and its SE."""
    from engine.league import seed_order
    rng = np.random.default_rng(SOLVE_SEED + 2)
    w = np.asarray(sizes, float) / float(np.sum(sizes))
    m = np.empty((N_OFFSET, 2))
    for k in range(N_OFFSET):
        draws = list(rng.multivariate_normal(np.zeros(2), conf_cov, size=len(z), method="eigh"))
        got = np.array(seed_order(draws, z, 1.0, rng, sigma=sigma))
        m[k] = w @ got
    mean, se = m.mean(0), m.std(0, ddof=1) / np.sqrt(N_OFFSET)
    return {"offset": [round(-float(x), 5) for x in mean], "se": [round(float(x), 5) for x in se]}
SOLVE_SEED = 20261010


def achieved(groups: list, cov: np.ndarray, sigma: float, rng) -> float:
    """Pooled correlation of z with the assigned draw's o + d (deviation from its group's mean when a group has several
    members, as the report measures it) over N_SIM simulated draws of the engine's procedure."""
    from engine.league import seed_order
    zs, vs = [], []
    for _ in range(N_SIM):
        for z in groups:
            draws = list(rng.multivariate_normal(np.zeros(2), cov, size=len(z), method="eigh"))
            got = seed_order(draws, z, 1.0, rng, sigma=sigma)
            v = np.array([g[0] + g[1] for g in got])
            zs.append(np.asarray(z) - np.mean(z)); vs.append(v - v.mean())
    return float(np.corrcoef(np.concatenate(zs), np.concatenate(vs))[0, 1])


def achieved_conf(z: list, sizes: list, conf_cov: np.ndarray, team_cov: np.ndarray, sigma: float, rng) -> float:
    """Conference level, measured as the target is: the conference's mean strength, its effect plus the mean of its members'
    team draws (reordered only within the conference, so that mean stays as drawn), against z."""
    from engine.league import seed_order
    zs, vs = [], []
    for _ in range(N_SIM):
        draws = list(rng.multivariate_normal(np.zeros(2), conf_cov, size=len(z), method="eigh"))
        got = seed_order(draws, z, 1.0, rng, sigma=sigma)
        v = np.array([g[0] + g[1] + rng.multivariate_normal(np.zeros(2), team_cov, size=k, method="eigh").sum(1).mean() for g, k in zip(got, sizes)])
        zs.append(np.asarray(z) - np.mean(z)); vs.append(v - v.mean())
    return float(np.corrcoef(np.concatenate(zs), np.concatenate(vs))[0, 1])


def solve_sigma(groups: list, cov: np.ndarray, target: float, fn=None) -> dict:
    fn = fn or (lambda sg, rng: achieved(groups, cov, sg, rng))
    rng = np.random.default_rng(SOLVE_SEED)
    top = fn(0.0, rng)
    if top <= target:
        return {"sigma": 0.0, "achieved": round(top, 4), "max_achievable": round(top, 4)}
    lo, hi = 0.0, 3.0
    for _ in range(18):
        mid = (lo + hi) / 2
        a = fn(mid, np.random.default_rng(SOLVE_SEED))
        lo, hi = (mid, hi) if a > target else (lo, mid)
    sig = (lo + hi) / 2
    return {"sigma": round(sig, 4), "achieved": round(fn(sig, np.random.default_rng(SOLVE_SEED + 1)), 4),
            "max_achievable": round(top, 4)}


def main() -> None:
    teams = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    teams = teams[teams.tier.notna() & (teams.tier != "")]
    S, N = season_fits(teams)
    r_team, r_conf = predictability(S, N, teams)
    # year-0 prior: every season 2021-2025
    teams = teams.copy()
    pr = [prior(S, t, max(SEASONS) + 1) for t in teams.team]
    teams["prior"], teams["n_seasons"] = [p for p, _ in pr], [k for _, k in pr]
    missing = teams[teams.n_seasons == 0].team.tolist()
    # a program with no season: its conference's mean (no information beyond its conference)
    teams["prior"] = teams.prior.fillna(teams.groupby("conference").prior.transform("mean"))
    grp = np.where(teams.conference == INDEPENDENT, "I|" + teams.tier, teams.conference)
    teams["dev"] = teams.prior - teams.groupby(grp).prior.transform("mean")
    sd_dev = teams[teams.conference != INDEPENDENT].groupby("tier").dev.std()
    teams["z_team"] = teams.dev / teams.tier.map(sd_dev)
    conf = teams[teams.conference != INDEPENDENT].groupby(["conference", "tier"]).prior.mean().reset_index()
    conf["dev"] = conf.prior - conf.groupby("tier").prior.transform("mean")
    conf["z_conf"] = conf.dev / conf.tier.map(conf.groupby("tier").dev.std())
    out = {"_note": __doc__, "built": dt.date.today().isoformat(), "half_life": HALF_LIFE, "seasons": list(SEASONS),
           "fit_targets": list(FIT_TARGETS), "r_team": r_team, "r_conf": r_conf,
           "team": {str(int(r.ncaa_team_id)): {"z": round(float(r.z_team), 4), "prior": round(float(r.prior), 4), "n_seasons": int(r.n_seasons)}
                    for r in teams.itertuples()},
           "conference": {r.conference: {"z": round(float(r.z_conf), 4), "prior": round(float(r.prior), 4)} for r in conf.itertuples()},
           "no_season": missing}
    # noise solved on the engine's own procedure (see above)
    from config import phase2
    cfg = phase2.load()
    out["sigma_team"], out["sigma_conf"] = {}, {}
    for tier in ("p4", "mid", "low"):
        sub_t = teams[(teams.tier == tier) & (teams.conference != INDEPENDENT)]
        groups = [g.z_team.tolist() for _, g in sub_t.groupby("conference")]
        out["sigma_team"][tier] = solve_sigma(groups, np.array(cfg.team_draw[tier]["team_cov"]), r_team[tier]["r_true"])
        ct = conf[conf.tier == tier]
        cz = ct.z_conf.tolist()
        sizes = [int((teams.conference == c).sum()) for c in ct.conference]
        cc, tc = np.array(cfg.team_draw[tier]["conf_cov"]), np.array(cfg.team_draw[tier]["team_cov"])
        out["sigma_conf"][tier] = solve_sigma([cz], cc, r_conf[tier]["r_true"],
                                              fn=lambda sg, rng: achieved_conf(cz, sizes, cc, tc, sg, rng))
        out.setdefault("tier_offset", {})[tier] = tier_offset(cz, sizes, cc, out["sigma_conf"][tier]["sigma"])
        print(tier, "team", out["sigma_team"][tier], "conf", out["sigma_conf"][tier], "offset", out["tier_offset"][tier], flush=True)
    TEAM_SEED.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"r_team": r_team, "r_conf": r_conf, "no_season": missing}, indent=1))


if __name__ == "__main__":
    main()
