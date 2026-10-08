"""Phase 3 realism report: handedness and platoon splits (plan approved 2026-10-08, plans/phase3_plan_2026-10-08.md).

Gate rows (benchmarks.json handedness_platoon_2025):
  - left-handers among the pitchers who appeared, by role (a starter: half or more of his appearances are starts);
  - position players' bats (L / R / S) and throwing hand by position group (C, 1B, IF, OF, UT/DH);
  - the tier-gradient check: left-handers by tier and role, batters' L share by tier (standardized to each tier's real mix
    of position groups). Not fitted: no code path reads tier to set a hand (owner rule 2026-10-08). Tolerance: the
    conference-clustered 95% interval, combined with 3 SE of the simulated mean;
  - platoon splits: K, BB, HR per PA, BABIP and on base per PA against left-handers minus against right-handers, within tier,
    for batters hitting left, hitting right and switch hitters; plate appearances by batters hitting left and against
    left-handers and the platoon advantage (above random pairing, and raw) are reported: their real sampling error needs a
    clustering unit the aggregates do not have;
  - usage by hand (ratios on the pooled tables): pitching changes by the batter due up for each pitcher's hand, left-handers'
    share of relief entries by the batter due up, pinch hitters by the batter due up, the pinch hitters' platoon advantage;
  - every Phase 2, 4, 5, 6 and 7 gate on the same run (PR B's decision rows are in Phase 6).
Reported, not gated: the individual platoon spread (qualified players, against platoon_spread.csv), the fit's diagnostics
(talent slopes, the tier effect at equal talent, the run-value sensitivity check), the share of plate appearances against
left-handers by tier, and the size of the platoon effects on the watch item "offense extremes compressed" (owner
adjustment 5): margin SD, regional upset rate, the 15+ bin and the run rule against PR B's run.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

import numpy as np

from config.phase2 import GATE_SE_MULTIPLE, TIERS
from config.phase3 import BATTER_GROUPS, MIN_SPLIT, POS_GROUP, SPLIT_SMOOTH, STARTER_SHARE
from engine.game2 import P_G, P_GS
from engine.status import Status

ROOT = Path(__file__).resolve().parents[1]
# owner rule 2026-10-08: a failing tier-gradient row is not fixed with a tier term; it becomes a watch item and a Phase 9
# requirement ("recruiting values handedness beyond talent"), with the measured effect at equal talent
WATCH3: dict = {}
PAIRS = ("L|L", "L|R", "R|L", "R|R")
PLAT_RATES = ("K", "BB", "HR", "BABIP", "OB")
_K, _BB, _HBP, _HR, _1B, _2B, _3B, _ROE, _OUT = range(9)      # engine.game2 CELL_RESULTS


def _rates(v: np.ndarray) -> dict:
    """K, BB, HR per PA, BABIP (hits in play over balls in play less ROE), on base per PA from CELL_RESULTS counts."""
    pa = v.sum()
    h = v[_1B] + v[_2B] + v[_3B]
    bip = pa - v[_K] - v[_BB] - v[_HBP] - v[_HR] - v[_ROE]
    return {"K": v[_K] / pa, "BB": v[_BB] / pa, "HR": v[_HR] / pa, "BABIP": h / bip, "OB": (v[_BB] + v[_HBP] + h + v[_HR]) / pa}


def season_extract3(res: dict) -> dict:
    lg, ps, pl = res["league"], res["pstats"], res["platoon"]
    out = {}
    # pitchers who appeared, by observed role
    cnt = {}
    for p in lg.players:
        if p.side != "pit" or ps[p.pid][P_G] == 0:
            continue
        role = "starter" if ps[p.pid][P_GS] / ps[p.pid][P_G] >= STARTER_SHARE else "reliever"
        for key in (role, f"{lg.teams[p.team].tier}|{role}"):
            c = cnt.setdefault(key, [0, 0])
            c[0] += p.throws == "L"; c[1] += 1
    for k, (x, n) in cnt.items():
        out[f"lhp|{k}"] = x / n
    # position players by group (and by tier and group, for the standardized tier share)
    bc = {}
    for p in lg.players:
        if p.side != "bat":
            continue
        g = POS_GROUP.get(p.pos, "UT/DH")
        for key in (g, f"{lg.teams[p.team].tier}|{g}"):
            c = bc.setdefault(key, {"L": 0, "R": 0, "S": 0, "thrL": 0, "n": 0})
            c[p.bats] += 1; c["thrL"] += p.throws == "L"; c["n"] += 1
    for k, c in bc.items():
        for h in ("L", "R", "S"):
            out[f"bats|{k}|{h}"] = c[h] / c["n"]
        out[f"throwsL|{k}"] = c["thrL"] / c["n"]
    # platoon: per tier, the rates against each hand; splits (vs L minus vs R) within tier, tiers weighted as the benchmark
    # (handedness_platoon_2025.platoon.splits weights: the real hand-known PA of the tier); the levels pooled (reported)
    bp = _bench()["platoon"]
    cells = {}
    for ti, t in enumerate(TIERS):
        for si, side in enumerate("LR"):
            for hi, hand in enumerate("LR"):
                cells[(t, side, hand)] = pl["used"][ti, si, hi]
        for hi, hand in enumerate("LR"):
            cells[(t, "S", hand)] = pl["listed"][ti, 2, hi]
    for bh in ("L", "R", "S"):
        w = bp["splits"][f"{bh}|weights"]
        for r in PLAT_RATES:
            num = den = 0.0
            for t in TIERS:
                vl, vr = cells[(t, bh, "L")], cells[(t, bh, "R")]
                if vl.sum() == 0 or vr.sum() == 0:
                    continue
                num += w[t] * (_rates(vl)[r] - _rates(vr)[r]); den += w[t]
            out[f"split|{bh}|{r}"] = float(num / den)
        for hand in "LR":
            for r, v in _rates(sum(cells[(t, bh, hand)] for t in TIERS)).items():
                out[f"level|{bh}|{hand}|{r}"] = float(v)
    used = pl["used"].sum(axis=0)                     # side x hand x outcome, every tier
    tot = used.sum(axis=2)
    out["plat_adv_share"] = float((tot[0, 1] + tot[1, 0]) / tot.sum())
    out["side_L_share"] = float(tot[0].sum() / tot.sum())
    out["pa_vs_lhp|all"] = float(tot[:, 0].sum() / tot.sum())
    tw = _bench()["tier_weights_teams"]
    exc = 0.0
    for ti, t in enumerate(TIERS):
        u = pl["used"][ti].sum(axis=2)
        n_ = u.sum()
        adv, sl, hl = (u[0, 1] + u[1, 0]) / n_, u[0].sum() / n_, u[:, 0].sum() / n_
        exc += tw[t] * (adv - (sl * (1 - hl) + (1 - sl) * hl))
        out[f"pa_vs_lhp|{t}"] = float(hl)
    out["plat_adv_excess"] = float(exc / sum(tw.values()))
    # usage by hand (every tier, both inning buckets pooled)
    rel = pl["relief"].sum(axis=(0, 3))          # cur hand x bats (L, R, S) x [opportunities, to L, to R]
    rate = lambda c, b: (rel[c, b, 1] + rel[c, b, 2]) / rel[c, b, 0]
    out["use_change_ratio|L"] = float(rate(0, 1) / rate(0, 0))
    out["use_change_ratio|R"] = float(rate(1, 0) / rate(1, 1))
    shares = []
    for bi in (0, 1):
        r = rel[:, bi].sum(axis=0)
        shares.append(r[1] / (r[1] + r[2]))
    out["use_lhp_entry_diff"] = float(shares[0] - shares[1])
    ph = pl["ph"].sum(axis=(0, 3))               # pitcher hand x bats due up x [opportunities, PH L, R, S]
    same, other = ph[0, 0] + ph[1, 1], ph[0, 1] + ph[1, 0]
    out["use_ph_ratio"] = float((same[1:].sum() / same[0]) / (other[1:].sum() / other[0]))
    allph = ph.sum(axis=1)                        # pitcher hand x [opp, L, R, S]
    adv = allph[0, 2] + allph[0, 3] + allph[1, 1] + allph[1, 3]   # vs LHP: R or S; vs RHP: L or S
    out["use_ph_adv"] = float(adv / allph[:, 1:].sum())
    # individual platoon spread: the logit split (vs L minus vs R) of qualified players, noise variance subtracted
    out.update(_spread(pl["split"], lg))
    return out


_BENCH: dict = {}


def _bench() -> dict:
    if not _BENCH:
        _BENCH.update(json.loads((ROOT / "benchmarks.json").read_text())["handedness_platoon_2025"])
    return _BENCH




def _spread(split: np.ndarray, lg) -> dict:
    out = {}
    side_of = np.array([p.side for p in lg.players])
    for side, name in (("bat", "batter"), ("pit", "pitcher")):
        m = side_of == side
        for ri, rate in enumerate(("K", "BB", "HR", "OB", "BABIP")):
            x, n = split[m, :, ri, 0].astype(float), split[m, :, ri, 1].astype(float)
            pa = split[m, :, 0, 1]
            q = (pa[:, 0] >= MIN_SPLIT) & (pa[:, 1] >= MIN_SPLIT) & (n[:, 0] > 0) & (n[:, 1] > 0)
            if q.sum() < 10:
                continue
            x, n = x[q], n[q]
            lgt = np.log((x + SPLIT_SMOOTH) / (n + 1 - x - SPLIT_SMOOTH))
            d = lgt[:, 0] - lgt[:, 1]
            p_i = (x.sum(axis=1) + SPLIT_SMOOTH) / (n.sum(axis=1) + 1)
            noise = ((1 / n[:, 0] + 1 / n[:, 1]) / (p_i * (1 - p_i))).mean()
            obs = d.var(ddof=1)
            out[f"spread|{name}|{rate}|obs_var"] = float(obs)
            out[f"spread|{name}|{rate}|noise_var"] = float(noise)
            out[f"spread|{name}|{rate}|players"] = float(q.sum())
    return out


def aggregate3(ex: list) -> dict:
    n = len(ex)
    keys = sorted(set().union(*[e.keys() for e in ex]))
    mean = {k: float(np.nanmean([e.get(k, np.nan) for e in ex])) for k in keys}
    se = {k: float(np.nanstd([e.get(k, np.nan) for e in ex], ddof=1) / math.sqrt(n)) if n > 1 else 0.0 for k in keys}
    return {"n_seasons": n, "mean": mean, "se": se}


def build_report3(agg: dict, seeds: list, statuses: dict, agg2: dict, agg7: dict) -> tuple[str, Status]:
    bm = json.loads((ROOT / "benchmarks.json").read_text())
    b = bm["handedness_platoon_2025"]
    inp = json.loads((ROOT / "data/ncaa_2025/derived/phase3_inputs_2025.json").read_text())
    m, se, n = agg["mean"], agg["se"], agg["n_seasons"]
    k = GATE_SE_MULTIPLE
    st, rows = Status(), []

    def row(section, key, label, got, s_, real, tol, nd=3, note="", gate=True):
        t = float(math.sqrt(tol ** 2 + (k * s_) ** 2))
        ok = bool(abs(got - real) <= t)
        watch = key in WATCH3
        if gate:
            st[key] = None if watch else ok
            if not watch:
                st.record(key, got, s_)
        note = (f"watch item: {WATCH3[key]}. " if watch else "") + note
        verdict = ("pass" if ok else "FAIL") if gate and not watch else ("in range" if ok else "outside")
        rows.append((section, f"| {label} | {got:.{nd}f} | {real:.{nd}f} | ±{t:.{nd}f} | {'yes' if gate and not watch else 'report'} | {verdict} | {note} |"))

    for role in ("starter", "reliever"):
        x = b["lhp_share"][role]
        row("hands", f"p3_lhp_{role}", f"Left-handed pitchers, {role}s (D1)", m[f"lhp|{role}"], se[f"lhp|{role}"], x["value"], x["tol"])
    for g in BATTER_GROUPS:
        x = b["throws_L_by_group"][g]
        row("hands", f"p3_throwsL_{g}", f"Throws L, {g}", m[f"throwsL|{g}"], se[f"throwsL|{g}"], x["value"], x["tol"])
    for g in BATTER_GROUPS:
        for h in ("L", "R", "S"):
            x = b["bats_by_group"][g][h]
            row("hands", f"p3_bats_{g}_{h}", f"Bats {h}, {g}", m[f"bats|{g}|{h}"], se[f"bats|{g}|{h}"], x["value"], x["tol"])
    # tier gradient
    for t in TIERS:
        for role in ("starter", "reliever"):
            x = b["lhp_by_tier"][f"{t}|{role}"]
            row("tier", f"p3_lhp_tier_{t}_{role}", f"Left-handed {role}s, {t} (real interval {x['lo']:.3f}-{x['hi']:.3f})",
                m[f"lhp|{t}|{role}"], se[f"lhp|{t}|{role}"], x["value"], x["tol"])
    for t in TIERS:
        mix = b["group_mix_by_tier"][t]
        got = sum(mix[g] * m.get(f"bats|{t}|{g}|L", 0.0) for g in BATTER_GROUPS)
        s_ = math.sqrt(sum((mix[g] * se.get(f"bats|{t}|{g}|L", 0.0)) ** 2 for g in BATTER_GROUPS))
        x = b["bats_L_by_tier"][t]
        row("tier", f"p3_batsL_tier_{t}", f"Batters bats L, {t}, at the tier's position mix (real interval {x['lo']:.3f}-{x['hi']:.3f})",
            got, s_, x["value"], x["tol"])
    # platoon splits (gated) and levels (reported)
    pb = b["platoon"]
    lab = {"K": "K%", "BB": "BB%", "HR": "HR%", "BABIP": "BABIP", "OB": "on base / PA"}
    who = {"L": "batters hitting left", "R": "batters hitting right", "S": "switch hitters"}
    for bh in ("L", "R", "S"):
        for r in PLAT_RATES:
            x = pb["splits"][f"{bh}|{r}"]
            row("platoon", f"p3_plat_split_{bh}_{r}", f"{lab[r]} vs LHP minus vs RHP, {who[bh]}", m[f"split|{bh}|{r}"], se[f"split|{bh}|{r}"],
                x["value"], x["tol"], 4)
    # the plate-appearance mix: reported. Its real sampling error cannot be computed from the aggregates (a player's plate
    # appearances share his hand; the tables have no clustering unit), and the binomial one on plate appearances is several
    # times too small. The hands behind it are gated with conference-clustered intervals above.
    note_mix = "reported: binomial tolerance on plate appearances, too small (they cluster by player)"
    x = pb["side_L_share"]
    row("mix", "p3_plat_side_L", "Plate appearances by batters hitting left", m["side_L_share"], se["side_L_share"], x["value"], x["tol"],
        note=note_mix, gate=False)
    x = pb["pa_share_vs_lhp"]
    row("mix", "p3_plat_vs_lhp", "Plate appearances against left-handed pitchers", m["pa_vs_lhp|all"], se["pa_vs_lhp|all"], x["value"], x["tol"],
        note=note_mix, gate=False)
    x = pb["advantage_excess"]
    row("mix", "p3_plat_adv_excess", "Platoon advantage above random pairing (within tier)", m["plat_adv_excess"], se["plat_adv_excess"],
        x["value"], x["tol"], 4, note_mix + "; lineups, bullpens and pinch hitters make it", gate=False)
    x = pb["advantage_share"]
    row("mix", "p3_plat_adv_share", "Plate appearances with the platoon advantage", m["plat_adv_share"], se["plat_adv_share"], x["value"], x["tol"],
        gate=False)
    for bh in ("L", "R", "S"):
        for hand in "LR":
            for r in PLAT_RATES:
                x = pb["levels"][f"{bh}|{hand}|{r}"]
                row("levels", f"p3_level_{bh}{hand}_{r}", f"{lab[r]}, {who[bh]} vs {hand}HP", m[f"level|{bh}|{hand}|{r}"], se[f"level|{bh}|{hand}|{r}"],
                    x["value"], x["tol"], 4, gate=False)
    # usage by hand (relative rows on the pooled tables)
    u = b["usage"]
    for cur, labl in (("L", "left-hander pitching: RHB due up over LHB"), ("R", "right-hander pitching: LHB due up over RHB")):
        x = u["change_ratio"][cur]
        row("usage", f"p3_use_change_ratio_{cur}", f"Pitching changes per PA, {labl}", m[f"use_change_ratio|{cur}"], se[f"use_change_ratio|{cur}"],
            x["value"], x["tol"])
    x = u["lhp_entry_diff"]
    row("usage", "p3_use_lhp_entry_diff", "Relief entries by left-handers: LHB due up minus RHB due up", m["use_lhp_entry_diff"], se["use_lhp_entry_diff"],
        x["value"], x["tol"])
    x = u["ph_ratio"]
    row("usage", "p3_use_ph_ratio", "Pinch hitters per opportunity: batter due up of the pitcher's hand over the other", m["use_ph_ratio"], se["use_ph_ratio"],
        x["value"], x["tol"])
    x = u["ph_advantage_share"]
    row("usage", "p3_use_ph_adv", "Pinch hitters with the platoon advantage", m["use_ph_adv"], se["use_ph_adv"], x["value"], x["tol"])
    for ph in ("phase2", "phase4", "phase5", "phase6", "phase7"):
        s_ = statuses.get(ph)
        if s_ is not None:
            st[f"{ph}_gate"] = all(v for v in s_.values() if v is not None)

    # ---- reported sections
    hp, hc, hb = inp["hands_pitchers"], inp["hand_checks"], inp["hands_batters"]
    te = hc["lhp_tier_effect_at_equal_talent"]
    sens = hc["sensitivity_run_value"]

    def odds_to_share(base_share, d):
        lo = math.log(base_share / (1 - base_share)) + d
        return 1 / (1 + math.exp(-lo))
    fit_lines = [
        f"- Pitchers, P(throws L) = expit(a + b s), s the true K-BB per BF against an average batter, standardized within role: "
        f"b = {hp['b']['starter']:+.3f} ± {hp['b_se']['starter']:.3f} (starters), {hp['b']['reliever']:+.3f} ± {hp['b_se']['reliever']:.3f} "
        f"(relievers) per SD; a = {hp['a']['starter']:+.3f} / {hp['a']['reliever']:+.3f} (set so the D1 shares match).",
        f"- Same fit with a tier term (the effect of tier at equal talent, mid the reference): P4 {te['tier_logodds_vs_mid']['p4']:+.3f} ± "
        f"{te['tier_logodds_se']['p4']:.3f}, low {te['tier_logodds_vs_mid']['low']:+.3f} ± {te['tier_logodds_se']['low']:.3f} log-odds; "
        f"P4 against low {te['tier_p4_minus_low']['logodds']:+.3f} ± {te['tier_p4_minus_low']['se']:.3f} "
        f"(at a .25 base share: {odds_to_share(.25, te['tier_logodds_vs_mid']['p4']):.3f} P4, .250 mid, "
        f"{odds_to_share(.25, te['tier_logodds_vs_mid']['low']):.3f} low).",
        f"- Run-value index instead of K-BB (sensitivity check, owner adjustment 1): b = {sens['fit']['b']['starter']:+.3f} ± {sens['fit']['b_se']['starter']:.3f} "
        f"/ {sens['fit']['b']['reliever']:+.3f} ± {sens['fit']['b_se']['reliever']:.3f}; predicted LHP shares by tier "
        + "; ".join(f"{role}s " + " / ".join(f"{sens['predicted_by_tier'][role][t]:.3f}" for t in TIERS) for role in ("starter", "reliever"))
        + f" (K-BB: " + "; ".join(f"{role}s " + " / ".join(f"{hc['lhp_predicted_by_tier'][role][t]:.3f}" for t in TIERS) for role in ("starter", "reliever"))
        + f"); P4 against low at equal talent {sens['tier_term_fit']['tier_p4_minus_low']['logodds']:+.3f} ± {sens['tier_term_fit']['tier_p4_minus_low']['se']:.3f}.",
        f"- Batters: bats L against R {hb['bL']:+.3f} ± {hb['bL_se']:.3f}, S against R {hb['bS']:+.3f} ± {hb['bS_se']:.3f} per SD of true run value per PA.",
    ]
    # individual platoon spread
    import pandas as pd
    sp = pd.read_csv(ROOT / "data/ncaa_2025/roster_aggregates/platoon_spread.csv")
    spread_rows = []
    for name in ("batter", "pitcher"):
        for rate in ("K", "BB", "HR", "OB", "BABIP"):
            kk = f"spread|{name}|{rate}"
            if f"{kk}|obs_var" not in m:
                continue
            sim_sd = math.sqrt(max(0.0, m[f"{kk}|obs_var"] - m[f"{kk}|noise_var"]))
            r_ = sp[(sp.side == name) & (sp.rate == rate) & (sp.listed_hand == "all")].iloc[0]
            spread_rows.append(f"| {name} | {rate} | {m[f'{kk}|players']:.0f} | {sim_sd:.3f} | {int(r_.players)} | {r_.true_sd_net:.3f} | {r_.true_sd:.3f} | "
                               f"{r_.obs_var:.3f} ± {r_.obs_var_se:.3f} |")
    # variance link (owner adjustment 5)
    base = json.loads((ROOT / "reports/phase3_baseline_prb.json").read_text())
    gs = bm["game_structure"]
    sw = bm["season_world_2015_2026"]
    pb = agg7["pooled"]["hf_regional_no_host_better_seed"]
    now = {"run_histogram_15plus": (agg2["run_histogram"][15], agg2["se"]["run_histogram"][15], gs["run_distribution_per_team_game"]["bins"][15]),
           "run_rule_freq": (agg2["run_rule_freq"], agg2["se"]["run_rule_freq"], gs["run_rule_freq"]["value"]),
           "p4mid_margin_sd": (agg7["mean"]["p4mid_margin_sd"], agg7["se"]["p4mid_margin_sd"], sw["current"]["rows"]["p4_vs_mid/margin_sd"]["value"]),
           "regional_upset_rate": (1 - pb["value"], pb["se"], 1 - sw["home_field"]["regional_no_host_better_seed"]["value"])}
    var_rows = []
    for kk, labl in (("p4mid_margin_sd", "P4 vs mid nonconference margin SD"), ("regional_upset_rate", "Regional upset rate (games without the host)"),
                     ("run_histogram_15plus", "Runs per team-game, 15+ bin"), ("run_rule_freq", "Run-rule frequency")):
        v, s_, real = now[kk]
        b0, s0 = base[kk]["value"], base[kk]["se"]
        gap0 = real - b0
        closed = (v - b0) / gap0 if gap0 else float("nan")
        closed_se = math.sqrt(s_ ** 2 + s0 ** 2) / abs(gap0) if gap0 else float("nan")
        var_rows.append(f"| {labl} | {real:.4f} | {b0:.4f} | {v:.4f} | {v - b0:+.4f} ± {math.sqrt(s_ ** 2 + s0 ** 2):.4f} | {100 * closed:.0f}% ± {100 * closed_se:.0f}% |")
    sec = {}
    for s_, line in rows:
        sec.setdefault(s_, []).append(line)
    head = "| Row | Sim | Real | Tolerance | Gated | Verdict | Note |\n|---|---|---|---|---|---|---|"
    ok_all = all(v for v in st.values() if v is not None)
    md = [f"# Phase 3 realism report: handedness and platoon splits", "",
          f"Generated {dt.date.today().isoformat()}, {n} seasons (seeds {seeds[0]}-{seeds[-1]}), the same run as the Phase 2, 4, 5, 6 and 7 reports. "
          f"Gate: {'PASS' if ok_all else 'FAIL'}.", "",
          "Hands are drawn per player from his talent and role (pitchers) or position (batters), never from his tier (owner rule 2026-10-08); "
          "matchups shift by the batter's side and the pitcher's hand (fitted net of who faced whom, centred on the league mix); the AI's "
          "pitching changes and pinch hitters use the hands of the batter due up and of the pitcher (scripts/build_phase3_*.py). "
          "Tolerances: the benchmark's (benchmarks.json handedness_platoon_2025) combined with 3 SE of the simulated mean.", "",
          "## Handedness shares", "", head, *sec.get("hands", []), "",
          "## Tier gradient (check: not fitted)", "",
          "The real gradient (P4 more left-handed) has to come from where the talent is. Tolerance: the conference-clustered 95% interval.", "",
          head, *sec.get("tier", []), "",
          "Fit behind the draw (scripts/build_phase3_hands.py; deconvolved through the noise of the observed talent bins):", "", *fit_lines, "",
          "Plate appearances against left-handers by tier (reported): " + ", ".join(f"{t} {m[f'pa_vs_lhp|{t}']:.3f}" for t in TIERS)
          + f", all {m['pa_vs_lhp|all']:.3f}.", "",
          "## Platoon splits", "", "Splits (rate against left-handed pitchers minus against right-handed) within each batting tier, the tiers "
          "weighted by their hand-known plate appearances in the real data (the engine's shift is one number for every tier). Batters hitting "
          "left or right count switch hitters on the side they used; the switch-hitter rows are by listed bats.", "", head, *sec.get("platoon", []), "",
          "Plate-appearance mix (reported, not gated: the plan gated the platoon-advantage share; its real sampling error needs a "
          "clustering unit the aggregates do not have, so it waits for a by-conference platoon table):", "", head, *sec.get("mix", []), "",
          "Levels (reported, not gated): the hand-known plate appearances of a tier are not a sample of that tier (low-tier batters in the "
          "play-by-play face mostly P4 pitching, the schedules of the teams it covers), so the real levels, tier-weighted, carry their "
          "opponents; the league's levels are gated in Phase 2.", "", head, *sec.get("levels", []), "",
          "## Usage by hand (AI manager)", "", head, *sec.get("usage", []), "",
          "## Earlier phases on the same run", "", "| Phase | Gate |", "|---|---|",
          *[f"| {ph} | {'PASS' if st.get(f'{ph}_gate') else 'FAIL'} |" for ph in ("phase2", "phase4", "phase5", "phase6", "phase7") if f"{ph}_gate" in st], "",
          "## Individual platoon spread (reported, not gated)", "",
          "SD of the true logit split (vs L minus vs R) across qualified players (50+ trials against each hand), noise variance subtracted. "
          "The engine has league-level shifts only (GUESSES.md: individual spread zero), so its spread is what the shifts and the "
          "opponents' mix leave. Real: platoon_spread.csv (play-by-play, permutation null in true_sd_net).", "",
          "| Side | Rate | Sim players / season | Sim true SD | Real players | Real true SD (net of null) | Real true SD | Real obs. var |", "|---|---|---|---|---|---|---|---|",
          *spread_rows, "",
          "## Platoon effects and the watch item 'offense extremes compressed' (owner adjustment 5)", "",
          "Against PR B's 40-season run (reports/phase3_baseline_prb.json). Gap closed: (this run - PR B) / (real - PR B).", "",
          "| Row | Real | PR B | Phase 3 | Change | Gap closed |", "|---|---|---|---|---|---|", *var_rows, ""]
    st.vals["_report"] = 0.0
    st.vals.pop("_report")
    return "\n".join(md) + "\n", st
