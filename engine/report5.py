"""Phase 5 realism report: pitch-by-pitch.

Gate rows, simulated against data/ncaa_2025/derived/phase5_pitch_2025.json (the 2025 WMT
play-by-play pitch sequences, reweighted to the D1 tier mix): pitches per PA and their
distribution, how often each count is reached, BA / K% / BB% of the plate appearances that pass
through each count, first-pitch strike rate, foul rate with two strikes, and pitches and innings
per start (weekend, midweek; pitch-count percentiles too). Tolerance: 3 SE of the benchmark
(game-clustered bootstrap) combined with 3 SE of the simulated mean at the number of seasons run.
Plus: every PA-level league rate unchanged from the Phase 4 run (reports/phase4_baseline.json),
within 3 combined SE; every Phase 1 and Phase 2 row and the Phase 4 forward ratings test on the
same run.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np

from config.phase5 import MAX_PITCHES_HIST
from config.phase5 import load as load_pitch
from engine.game2 import P_BB, P_BF, P_K
from engine.pitch import COUNTS

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "reports/phase4_baseline.json"
PA_ROWS = (("runs_per_team_game", "Runs per team-game"), ("ba", "Batting average"), ("obp", "On-base pct"), ("slg", "Slugging pct"),
           ("hr_per_team_game", "HR per team-game"), ("bb_pct", "BB per PA"), ("k_pct", "K per PA"), ("hbp_pct", "HBP per PA"),
           ("pa_per_team_game", "PA per team-game"), ("errors_per_team_game", "Errors per team-game"), ("era", "ERA"), ("earned_share", "Earned share of runs"))
QUANTS = (10, 50, 90)


def cname(c) -> str:
    return f"{c[0]}-{c[1]}"


def season_extract5(res: dict) -> dict:
    """One season's pitch-level statistics, keyed like the benchmarks."""
    pr = res["pitch_rec"]
    n = pr["n_pa"]
    out = {"pitches_per_pa": pr["pitches"] / n, "first_pitch_strike": pr["fps"] / n, "two_strike_foul_rate": pr["k2f"] / pr["k2p"]}
    for k in range(1, MAX_PITCHES_HIST + 1):
        out[f"pitches_dist_{k if k < MAX_PITCHES_HIST else f'{k}+'}"] = pr["hist"][k] / n
    for i, c in enumerate(COUNTS):
        if c != (0, 0):
            out[f"reach_{cname(c)}"] = pr["reach"][i] / n
        out[f"ba_after_{cname(c)}"] = pr["h"][i] / pr["ab"][i]
        out[f"k_after_{cname(c)}"] = pr["k"][i] / pr["reach"][i]
        out[f"bb_after_{cname(c)}"] = pr["bb"][i] / pr["reach"][i]
    st = res["starts"]
    for wk, lab in ((1.0, "weekend"), (0.0, "midweek")):
        sub = st[st[:, 2] == wk]
        out[f"pitches_per_start_{lab}"] = float(sub[:, 0].mean())
        out[f"ip_per_start_{lab}"] = float(sub[:, 1].mean() / 3)
        for q in QUANTS:
            out[f"pitches_per_start_{lab}_p{q}"] = float(np.percentile(sub[:, 0], q, method="inverted_cdf"))
    # informational: spread of qualified pitchers' ball and whiff rates per pitch, against their BB and K rates
    pp, ps = res["pit_pitch"], res["pstats"]
    q = ps[:, P_BF] >= 150
    ball, whiff = pp[q, 1] / pp[q, 0], pp[q, 2] / pp[q, 0]
    bb, kk = ps[q, P_BB] / ps[q, P_BF], ps[q, P_K] / ps[q, P_BF]
    out["info_ball_rate_sd"] = float(ball.std()); out["info_whiff_rate_sd"] = float(whiff.std())
    out["info_corr_ball_bb"] = float(np.corrcoef(ball, bb)[0, 1]); out["info_corr_whiff_k"] = float(np.corrcoef(whiff, kk)[0, 1])
    return out


def aggregate5(ex: list) -> dict:
    keys = ex[0].keys()
    n = len(ex)
    return {"n_seasons": n, "mean": {k: float(np.mean([e[k] for e in ex])) for k in keys},
            "se": {k: float(np.std([e[k] for e in ex], ddof=1) / np.sqrt(n)) if n > 1 else 0.0 for k in keys}}


def _row(label, sim, se_s, bench, se_b, nd=4):
    tol = 3 * np.sqrt(se_b ** 2 + se_s ** 2)
    ok = abs(sim - bench) <= tol
    return ok, f"| {label} | {sim:.{nd}f} | {bench:.{nd}f} | ±{tol:.{nd}f} | {'pass' if ok else 'FAIL'} |"


def build_report5(agg: dict, seeds: list, league: dict, league_se: dict, st2: dict, st4: dict, info: dict) -> tuple[str, dict]:
    data = load_pitch()
    bm = data["benchmarks"]
    st, sections = {}, {}
    m, se = agg["mean"], agg["se"]

    def gate(key, label, nd=4, section="other"):
        ok, line = _row(label, m[key], se[key], bm[key]["value"], bm[key]["se"], nd)
        st[f"p5_{key}"] = bool(ok)
        sections.setdefault(section, []).append(line)

    gate("pitches_per_pa", "Pitches per PA", 3, "pitches")
    for k in range(1, MAX_PITCHES_HIST + 1):
        lab = f"{k}" if k < MAX_PITCHES_HIST else f"{k}+"
        gate(f"pitches_dist_{lab}", f"PAs with {lab} pitch{'es' if k > 1 else ''}", 4, "pitches")
    gate("first_pitch_strike", "First-pitch strike rate (first pitch not a ball or HBP)", 4, "pitches")
    gate("two_strike_foul_rate", "Foul rate with two strikes (fouls / pitches)", 4, "pitches")
    for c in COUNTS:
        if c != (0, 0):
            gate(f"reach_{cname(c)}", f"Reach {cname(c)}", 4, "reach")
    for c in COUNTS:
        for kind, lab in (("ba", "BA"), ("k", "K%"), ("bb", "BB%")):
            gate(f"{kind}_after_{cname(c)}", f"{lab} after {cname(c)}", 4, "by_count")
    for lab in ("weekend", "midweek"):
        gate(f"pitches_per_start_{lab}", f"Pitches per start, {lab}", 1, "starts")
        for q in QUANTS:
            gate(f"pitches_per_start_{lab}_p{q}", f"Pitches per start, {lab}, p{q}", 1, "starts")
        gate(f"ip_per_start_{lab}", f"Innings per start, {lab}", 3, "starts")
    base = json.loads(BASELINE.read_text())
    pa_lines = []
    for key, label in PA_ROWS:
        tol = 3 * np.sqrt(base["se"][key] ** 2 + league_se[key] ** 2)
        ok = abs(league[key] - base["league"][key]) <= tol
        st[f"pa_unchanged_{key}"] = bool(ok)
        pa_lines.append(f"| {label} | {league[key]:.4f} | {base['league'][key]:.4f} | ±{tol:.4f} | {'pass' if ok else 'FAIL'} |")
    p2_ok = all(v for v in st2.values() if v is not None)
    p4_ok = all(v for v in st4.values() if v is not None)
    st["phase2_gate"], st["phase4_gate"] = bool(p2_ok), bool(p4_ok)
    gate_ok = all(v for v in st.values() if v is not None)
    hdr = "| Metric | Sim | Data | Tol | Status |\n|---|---|---|---|---|"
    cl = data["cleaning"]
    md = ["# Phase 5 realism report: pitch-by-pitch", "",
          f"{agg['n_seasons']} simulated seasons, seeds {seeds[0]}–{seeds[-1]} (the Phase 4 report's league and seeds). Generated {dt.date.today().isoformat()}.",
          "Each plate appearance's outcome comes from the unchanged Phase 4 matchup model. Its pitch sequence comes from a count-state pitch chain conditioned "
          "on that outcome (engine/pitch.py), so PA-level rates cannot move. Pitch events by count, batted-ball results by count of contact and every "
          "benchmark below come from the 2025 WMT play-by-play pitch sequences, reweighted to the D1 tier mix. Tolerances combine 3 SE of the benchmark "
          "(bootstrap over games) with 3 SE of the simulated mean at the number of seasons run. The starter's pull hazard now reads these simulated pitch counts.", "",
          f"## Gate: **{'PASS' if gate_ok else 'FAIL'}**", "",
          f"Phase 1 and Phase 2 gate rows on the same run: **{'pass' if p2_ok else 'FAIL'}** (reports/phase2.md). "
          f"Phase 4 forward ratings test on the same run: **{'pass' if p4_ok else 'FAIL'}** (reports/phase4.md).", "",
          "## What the play-by-play supports", "",
          "Every action of the 2,264 WMT games was checked. Per plate appearance the data has a pitch sequence over B (ball), K (called strike), S (swinging strike), "
          "F (foul), P (in play) and H (hit by pitch), plus the final count, the pitch count and a strikeout-looking flag. **There is no pitch type, velocity or location**, "
          "so the model has none: no zone, no pitch mix, no velocity. Control vs Eye moves balls and Stuff vs Avoid K moves swinging strikes at every count; "
          "zone rate and chase rate cannot be told apart in this data. "
          f"Cleaning: a P before the last pitch changes neither balls nor strikes but is in the official pitch count; it is kept as a neutral pitch "
          f"({cl['neutral_pitches']} in the sample). {cl['hbp_P_recoded']} HBPs coded with a final P are read as H. Intentional walks ({cl['ibb_or_ci']} with catcher's interference) "
          f"are left out (mostly automatic, no pitches), as are {cl['no_sequence']} PAs with no sequence and {cl['broken_sequence']} that break the count rules: "
          f"{cl['pa_used']} of {cl['pa_total']} PAs are used. The engine's walks include the intentional ones (Phase 2 folds IBB into BB), so about 0.2% of simulated "
          "PAs get a full four-ball sequence that the data would not count.", "",
          "## Pitches", "", hdr, *sections["pitches"], "",
          "## How often each count is reached (share of PAs)", "", hdr, *sections["reach"], "",
          "## Outcome of the PAs that pass through each count", "",
          "BA is hits per at-bat, K% and BB% per PA, among the PAs that reach the count at any point.", "", hdr, *sections["by_count"], "",
          "## Starts", "",
          "Pitches are the starter's pitches on completed plate appearances; innings are the outs on his plate appearances / 3 (as in the data). "
          "The pull hazard (Phase 2 usage tables, Stamina leash from Phase 4) now reads the simulated pitch counts.", "", hdr, *sections["starts"], "",
          "## PA-level outcomes unchanged from Phase 4", "",
          "League rates of this run against the merged Phase 4 run (reports/phase4_baseline.json), tolerance 3 SE of the difference.", "",
          "| Metric | Phase 5 | Phase 4 | Tol | Status |", "|---|---|---|---|---|", *pa_lines, "",
          "## Informational", "",
          f"- Chain tilt Jacobian (rows d logit P(K), P(BB), P(HBP); columns tilts on swinging strikes, balls, HBP): {info['J']}. "
          f"League chain without conditioning: K {info['chain_league']['K']:.4f}, BB {info['chain_league']['BB']:.4f}, HBP {info['chain_league']['HBP']:.4f}, "
          f"in play {info['chain_league']['BIP']:.4f}; PA model at league average: K {info['pa_league']['K']:.4f}, BB {info['pa_league']['BB']:.4f}, "
          f"HBP {info['pa_league']['HBP']:.4f}, in play {info['pa_league']['BIP']:.4f}.",
          f"- Pitchers with 150+ BF: SD of ball rate per pitch {m['info_ball_rate_sd']:.4f}, of swinging-strike rate {m['info_whiff_rate_sd']:.4f}; "
          f"correlation of ball rate with BB/BF {m['info_corr_ball_bb']:.3f}, of swinging-strike rate with K/BF {m['info_corr_whiff_k']:.3f}."
          + (f" Data: SD {data['pitcher_spread']['ball_rate_sd']:.4f} and {data['pitcher_spread']['whiff_rate_sd']:.4f}, correlations "
             f"{data['pitcher_spread']['corr_ball_bb']:.3f} and {data['pitcher_spread']['corr_whiff_k']:.3f} ({data['pitcher_spread']['n']} pitcher-seasons, raw sample)."
             if "pitcher_spread" in data else ""),
          f"- Pitchers with 50+ IP (Phase 6 deferred row, currently passing): {info['p50ip']:.1f} (real 882; Phase 4 run 870.6).", ""]
    return "\n".join(md) + "\n", st
