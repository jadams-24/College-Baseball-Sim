"""Report on teams seeded from their real programs (owner decision 2026-10-09; dynasty year 0): reports/team_seed.md.

For the report's league seeds (20251000+, the leagues the 40-season run plays), with seeding on and off:
  recovery     the correlation of each program's standardized prior (data/ncaa_2025/derived/team_seed_2025.json) with its
               drawn deviation within its conference, by tier, against the real target r (the correlation of a program's
               recent history with its next season's true strength); the same for conference effects within tier
  Omaha grade  year-0 agreement of the Omaha Contender grade the dynasty computes from its own teams (drawn strength o + d
               plus the program's real recent Omaha / super regional bonus, config.report_cards.omaha_score and
               grade_values, the function the UI calls) with the reference card's grade from real strength
               (data/schools/report_cards.csv): exact, within one step, rank correlation of the scores, and the 2021-2025
               Omaha teams graded B+ or better
Scripts may read the school files; the engine never does (tests/test_report_cards.py).
    python3 scripts/report_team_seed.py [--leagues 40]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from config import phase2  # noqa: E402
from config import report_cards as rc  # noqa: E402
import engine.league as L  # noqa: E402

REPORT_SEED = 20251000
OUT = ROOT / "reports/team_seed.md"


def league(seed: int, on: bool):
    phase2.SEED_FROM_PROGRAMS = on
    L._SEED_CACHE.clear()
    s_league = np.random.SeedSequence(seed).spawn(3)[0]
    return L.build_league(phase2.load(), np.random.Generator(np.random.PCG64(s_league)))


def ranks(x):
    return pd.Series(x).rank().values


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--leagues", type=int, default=40)
    a = ap.parse_args()
    seed = json.loads(phase2.TEAM_SEED.read_text())
    cfg = phase2.load()
    card = pd.read_csv(ROOT / "data/schools/report_cards.csv").set_index("ncaa_team_id")
    bonus = (card.omaha_contender_raw - card.strength_recent).fillna(0.0)
    real_grade = card.omaha_contender_grade
    order = rc.GRADES
    ids = [t[0] for t in cfg.teams]
    tiers = np.array([t[2] for t in cfg.teams])
    confs = np.array([t[1] for t in cfg.teams])
    z = np.array([seed["team"][str(i)]["z"] for i in ids])
    omaha_teams = set(card.index[card.n_omaha_recent > 0]) if "n_omaha_recent" in card else set()
    res = {}
    for on in (True, False):
        rec = {t: [] for t in ("p4", "mid", "low")}
        crec = {t: [] for t in ("p4", "mid", "low")}
        ex, w1, rho, om_ok, tmeans = [], [], [], [], []
        for k in range(a.leagues):
            lg = league(REPORT_SEED + k, on)
            o = np.array([lg.teams[i].o_total for i in range(len(ids))]); d = np.array([lg.teams[i].d_total for i in range(len(ids))])
            s = o + d
            tmeans.append([[o[tiers == t].mean(), d[tiers == t].mean()] for t in ("p4", "mid", "low")])
            # within-conference deviation of the drawn strength (independents excluded), by tier
            dfr = pd.DataFrame({"s": s, "z": z, "conf": confs, "tier": tiers})
            dfr = dfr[dfr.conf != "DI Independent"]
            dfr["dev"] = dfr.s - dfr.groupby("conf").s.transform("mean")
            for t, g in dfr.groupby("tier"):
                rec[t].append(
                    ((g.z - g.groupby("conf").z.transform("mean")).values, g.dev.values))
            cm = dfr.groupby(["conf", "tier"]).s.mean().reset_index()
            cm["zc"] = [seed["conference"][c]["z"] for c in cm.conf]
            for t, g in cm.groupby("tier"):
                if len(g) > 2:
                    crec[t].append(((g.zc - g.zc.mean()).values, (g.s - g.s.mean()).values))
            score = s + bonus.reindex(ids).values
            g0 = np.array(rc.grade_values(score))
            gr = real_grade.reindex(ids).values
            step = np.abs(np.array([order.index(x) for x in g0]) - np.array([order.index(x) for x in gr]))
            ex.append(float((step == 0).mean())); w1.append(float((step <= 1).mean()))
            rho.append(float(np.corrcoef(ranks(score), ranks(card.omaha_contender_raw.reindex(ids).values))[0, 1]))
            om = [order.index(g) <= order.index("B+") for i, g in zip(ids, g0) if i in omaha_teams]
            om_ok.append(float(np.mean(om)) if om else float("nan"))
        ms = lambda v: (float(np.nanmean(v)), float(np.nanstd(v, ddof=1) / np.sqrt(len(v))))      # noqa: E731

        def pooled(pairs):
            """Pooled correlation over leagues (centred within group), the solver's measure; SE by delete-one-league jackknife."""
            r = lambda ps: float(np.corrcoef(np.concatenate([a for a, _ in ps]), np.concatenate([b for _, b in ps]))[0, 1])  # noqa: E731
            full, n = r(pairs), len(pairs)
            jk = np.array([r(pairs[:i] + pairs[i + 1:]) for i in range(n)])
            return full, float(np.sqrt((n - 1) / n * ((jk - jk.mean()) ** 2).sum()))
        res[on] = {"rec": {t: pooled(v) for t, v in rec.items()}, "crec": {t: pooled(v) for t, v in crec.items() if v},
                   "exact": ms(ex), "within1": ms(w1), "rho": ms(rho), "omaha_bplus": ms(om_ok),
                   "tier_mean": {t: {"mean": np.array(tmeans)[:, i].mean(0).round(4).tolist(),
                                     "se": (np.array(tmeans)[:, i].std(0, ddof=1) / np.sqrt(len(tmeans))).round(4).tolist()}
                                 for i, t in enumerate(("p4", "mid", "low"))}}
    f = lambda m: f"{m[0]:.3f} ± {m[1]:.3f}"      # noqa: E731
    md = ["# Teams seeded from their real programs (dynasty year 0)", "",
          f"Owner decision 2026-10-09. {a.leagues} leagues (the report's league seeds, {REPORT_SEED}+). The drawn strength set is unchanged per "
          "tier and conference: conference effects are reordered among a tier's conferences and team deviations among a conference's teams, by "
          "a noisy version of each program's 2021-2025 strength (`scripts/build_team_seed.py`, `engine/league.py` seed_order). The noise is set so "
          "the prior's correlation with the year-0 strength equals the real correlation of a program's recent history with its next season's "
          "true strength (fitted on 2023-2025, each season from the seasons before it, divided by the square root of that season's reliability).", "",
          "## Recovery: prior against the drawn year-0 strength", "",
          "| Level | Tier | Real target r | Best achievable with the sets kept | Seeded | Unseeded |", "|---|---|---|---|---|---|"]
    for t in ("p4", "mid", "low"):
        md.append(f"| Teams within conference | {t} | {seed['r_team'][t]['r_true']:.3f} | {seed['sigma_team'][t]['max_achievable']:.3f} | "
                  f"{f(res[True]['rec'][t])} | {f(res[False]['rec'][t])} |")
    for t in ("p4", "mid", "low"):
        if t in res[True]["crec"]:
            md.append(f"| Conference means within tier | {t} | {seed['r_conf'][t]['r_true']:.3f} | {seed['sigma_conf'][t]['max_achievable']:.3f} | "
                      f"{f(res[True]['crec'][t])} | {f(res[False]['crec'][t])} |")
    md += ["", "The ranking noise is solved per tier and level on a simulation of the engine's own procedure, so the achieved correlation "
           "equals the real target where it can (teams within conference: all three tiers). Conference means cannot reach theirs: a "
           "conference's mean strength is its effect plus the mean of its members' team draws, and those draws are only reordered within "
           "the conference (the set per conference is kept), so that part stays random; P4 also has only four conferences to rank. The "
           "conference effects are therefore ordered with no noise, the closest the kept sets allow (best achievable column). Closing the "
           "rest would mean moving team draws across conferences within a tier (the tier's set kept, the conferences' not): owner decision.", "",
           "## Tier means (team-weighted o, d)", "",
           "The calibrated tier means are team-weighted averages of real teams. Real conference strength correlates with conference "
           "size (low tier -.45: the largest low-tier conferences are the weakest), so seeding alone would move the team-weighted mean; "
           "a per-tier offset solved by simulation of the same procedure restores it (owner approval 2026-10-10). Each tier's spread and "
           "ordering are unchanged.", "",
           "| Tier | Calibrated | Offset added | Seeded | Unseeded |", "|---|---|---|---|---|",
           *[f"| {t} | {tuple(round(x, 4) for x in cfg.team_draw[t]['mean'])} | {tuple(seed['tier_offset'][t]['offset'])} | "
             f"{tuple(res[True]['tier_mean'][t]['mean'])} ± {tuple(res[True]['tier_mean'][t]['se'])} | "
             f"{tuple(res[False]['tier_mean'][t]['mean'])} ± {tuple(res[False]['tier_mean'][t]['se'])} |" for t in ("p4", "mid", "low")], "",
           "## Omaha Contender, year 0 against the reference card", "",
           "The dynasty's grade: drawn strength (o + d) plus the program's real recent Omaha and super regional bonus, graded with "
           "`config.report_cards.omaha_score` and `grade_values` (the function the UI calls). Reference: the committed card (real 2021-2025 strength).", "",
           "| Agreement | Seeded | Unseeded |", "|---|---|---|",
           f"| Same grade | {f(res[True]['exact'])} | {f(res[False]['exact'])} |",
           f"| Within one step | {f(res[True]['within1'])} | {f(res[False]['within1'])} |",
           f"| Rank correlation of the scores | {f(res[True]['rho'])} | {f(res[False]['rho'])} |",
           f"| 2021-2025 Omaha teams graded B+ or better | {f(res[True]['omaha_bplus'])} | {f(res[False]['omaha_bplus'])} |", "",
           "Oregon St. (the one independent) is a group of one: its conference effect and deviation stay as drawn.", ""]
    OUT.write_text("\n".join(md))
    (ROOT / "reports/team_seed.json").write_text(json.dumps({str(k): v for k, v in res.items()}, indent=1) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
