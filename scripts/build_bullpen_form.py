"""Bullpen form (variance stage, owner decision 2026-10-09, option A): relief usage reacts to the reliever's recent results.

From the 2025 play-by-play, full-season teams (scripts/build_phase6_usage.py), writes
data/ncaa_2025/derived/bullpen_form_2025.json:

  relief_form  the relief choice's conditional logit refitted with recent-form terms by leverage, on the same choice
               events as usage6 relief (role x leverage, rest cells, back-to-back) plus, per alternative and leverage
               (late and close / blowout / other): his runs allowed in his last outing (runs scored on plate-appearance
               plays while he was in, capped at FORM_CAP), the mean of the same over his three outings before that, and a
               no-outing-yet indicator. The engine's AI uses these coefficients after scaling solved in the engine
               (scripts/solve_bullpen_form.py), so its within-pitcher slopes match the real ones below.
  gate         the gate values (engine/bullpen_metrics.py on the real outings; SE by a bootstrap over teams), for P4
               staffs and all full-season staffs: the next entry's blowout share and |margin| per run allowed in the
               previous outing (relief-only pitchers, within pitcher), and runs per batter faced against the staff mean by
               workload third.
    python3 scripts/build_bullpen_form.py
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
import build_phase6_usage as bu  # noqa: E402
from config.phase6 import CLOGIT_RIDGE, FORM_CAP, FORM_PRIOR_N, N_ROLE_RELIEVERS  # noqa: E402
from engine import bullpen_metrics as bm  # noqa: E402

OUT = ROOT / "data/ncaa_2025/derived/bullpen_form_2025.json"
N_BOOT = 400


def outings(pa: pd.DataFrame) -> pd.DataFrame:
    """Every appearance with its runs on plate-appearance plays, entry margin and inning, in season order per team."""
    a = bu.appearances(pa)
    runs = pa.groupby(["game_id", "pit_team_id", "pkey"]).runs_on_play.sum().rename("runs")
    a = a.join(runs, on=["game_id", "pit_team_id", "pkey"])
    a = a.sort_values(["pit_team_id", "d", "dh", "first"])
    a["seq"] = a.groupby("pit_team_id").cumcount()
    return a


def metric_frame(a: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"team": a.pit_team_id.values, "pid": (a.pit_team_id.astype(str) + "|" + a.pkey).values,
                         "seq": a.seq.values, "starter": a.start.values, "bf": a.bf.values, "runs": a.runs.values,
                         "margin": a.margin.values, "inning": a.inning.values})


def gate_values(o: pd.DataFrame, teams: set, rng) -> dict:
    o = o[o.team.isin(teams)]
    f, t = bm.feedback_slopes(o), bm.workload_terciles(o)
    tl = np.array(sorted(teams))
    by = {k: g for k, g in o.groupby("team")}
    boot = []
    for _ in range(N_BOOT):
        pick = rng.choice(tl, len(tl))
        parts = []
        for i, k in enumerate(pick):        # a team drawn twice counts as two teams (distinct ids)
            g = by[k].copy(); g["team"] = f"{k}#{i}"; g["pid"] = g.pid + f"#{i}"
            parts.append(g)
        b = pd.concat(parts)
        fb, tb = bm.feedback_slopes(b), bm.workload_terciles(b)
        boot.append([fb["blow"], fb["absm"], tb["low"], tb["mid"], tb["high"], tb["low_minus_high"]])
    se = np.array(boot).std(0, ddof=1)
    keys = ["blow", "absm", "low", "mid", "high", "low_minus_high"]
    val = [f["blow"], f["absm"], t["low"], t["mid"], t["high"], t["low_minus_high"]]
    return {"n_staffs": int(len(teams)), "n_pairs": f["n_pairs"], "n_pitchers": t["n_pitchers"],
            **{k: {"value": round(float(v), 5), "se": round(float(s), 5)} for k, v, s in zip(keys, val, se)}}


def form_values(h: list) -> tuple:
    """(last, prior3, none) from a pitcher's earlier outings [(day, pitches, runs)]."""
    if not h:
        return 0.0, 0.0, 1.0
    last = min(h[-1][2], FORM_CAP)
    prior = [min(x[2], FORM_CAP) for x in h[-1 - FORM_PRIOR_N:-1]]
    return float(last), float(np.mean(prior)) if prior else 0.0, 0.0


def choice_events(a: pd.DataFrame, role: pd.DataFrame) -> list:
    """build_phase6_usage.choice_data's relief events, each alternative with its form values."""
    a = a.merge(role, on=["pit_team_id", "pkey"])
    events = []
    for t, g in a.groupby("pit_team_id"):
        g = g.sort_values(["d", "dh", "first"])
        staff = g.drop_duplicates("pkey")[["pkey", "role"]].values.tolist()
        hist: dict = {p: [] for p, _ in staff}
        for gid, gg in g.groupby("game_id", sort=False):
            day = gg.d.iloc[0]
            used = set()
            starter = gg[gg.start].pkey.iloc[0] if gg.start.any() else None
            for _, r in gg.sort_values("first").iterrows():
                if not r.start:
                    lev = bu.leverage(int(r.inning), int(r.margin))
                    alts, chosen = [], None
                    for p, ro in staff:
                        if p in used or p == starter:
                            continue
                        h = hist[p]
                        if h:
                            last_day, last_p, _ = h[-1]
                            days = (day - last_day).days
                            b2b = len(h) >= 2 and (day - h[-1][0]).days == 1 and (day - h[-2][0]).days == 2
                        else:
                            days, last_p, b2b = np.nan, 0, False
                        alts.append((ro, lev, bu.rest_cell(days, last_p, b2b), b2b, form_values(h)))
                        if p == r.pkey:
                            chosen = len(alts) - 1
                    if chosen is not None:
                        events.append((alts, chosen))
                used.add(r.pkey)
            for _, r in gg.iterrows():
                hist[r.pkey].append((day, r.pitches, r.runs))
    return events


def fit(events: list) -> dict:
    """Conditional logit by Newton-Raphson with the usage6 ridge: role x leverage (reference r8), rest (reference d6),
    back-to-back, and form x leverage (last, prior3, none)."""
    levs = ("late_close", "other", "blowout")
    role_keys = sorted({(ro, lev) for alts, _ in events for ro, lev, *_ in alts if ro != f"r{N_ROLE_RELIEVERS}"})
    rest_keys = sorted({rc for alts, _ in events for _, _, rc, *_ in alts if rc != "d6"})
    form_keys = [f"form_{k}|{lev}" for k in ("last", "prior3", "none") for lev in levs]
    names = [f"{ro}|{lev}" for ro, lev in role_keys] + [f"rest|{k}" for k in rest_keys] + ["b2b"] + form_keys
    ri = {k: i for i, k in enumerate(role_keys)}
    si = {k: len(role_keys) + i for i, k in enumerate(rest_keys)}
    fi = {k: len(role_keys) + len(rest_keys) + 1 + i for i, k in enumerate(form_keys)}
    k = len(names)
    X, C, starts = [], [], [0]
    for alts, ch in events:
        for ro, lev, rc, b2b, (last, prior, none) in alts:
            x = np.zeros(k)
            if (ro, lev) in ri:
                x[ri[(ro, lev)]] = 1
            if rc in si:
                x[si[rc]] = 1
            x[len(role_keys) + len(rest_keys)] = float(b2b)
            x[fi[f"form_last|{lev}"]] = last
            x[fi[f"form_prior3|{lev}"]] = prior
            x[fi[f"form_none|{lev}"]] = none
            X.append(x)
        C.append(starts[-1] + ch)
        starts.append(starts[-1] + len(alts))
    X = np.array(X)
    seg = np.repeat(np.arange(len(events)), np.diff(starts))
    lam = CLOGIT_RIDGE
    beta = np.zeros(k)

    def evaluate(b):
        u = X @ b
        m = np.maximum.reduceat(u, starts[:-1])
        e = np.exp(u - m[seg])
        s_ = np.add.reduceat(e, starts[:-1])
        return e, s_, float((u[C] - m - np.log(s_)).sum()) - 0.5 * lam * float(b @ b)
    e, s_, obj = evaluate(beta)
    for it in range(200):
        p = e / s_[seg]
        xbar = np.add.reduceat(p[:, None] * X, starts[:-1])
        g = X[C].sum(0) - xbar.sum(0) - lam * beta
        H = -(X.T @ (p[:, None] * X)) + xbar.T @ xbar - lam * np.eye(k)
        step = np.linalg.solve(H, -g)
        t = 1.0
        while True:
            nb = beta + t * step
            e2, s2, obj2 = evaluate(nb)
            if obj2 >= obj - 1e-9 or t < 1e-6:
                break
            t *= 0.5
        beta, e, s_, gain, obj = nb, e2, s2, obj2 - obj, obj2
        if abs(gain) < 1e-8 and np.abs(t * step).max() < 1e-6:
            break
    se = np.sqrt(np.clip(np.diag(np.linalg.inv(-H)), 0, None))
    ll = obj + 0.5 * lam * float(beta @ beta)
    print(f"relief_form: {len(events)} choices, log-lik {ll:.1f}, {it + 1} Newton steps")
    return {"n_choices": len(events), "loglik": round(ll, 2), "coef": {n: round(float(b), 4) for n, b in zip(names, beta)},
            "se": {n: round(float(v), 4) for n, v in zip(names, se)}}


def main() -> None:
    pa, meta, tier, full = bu.load()
    a = outings(pa)
    o = metric_frame(a)
    rng = np.random.default_rng(20261009)
    p4 = {t for t in full if tier.get(t) == "p4"}
    gate = {"p4": gate_values(o, p4, rng), "all_full_season": gate_values(o, full, rng)}
    af = a[a.pit_team_id.isin(full)].copy()
    role = bu.roles(af)
    rf = fit(choice_events(af, role))
    out = {"_note": __doc__, "built": dt.date.today().isoformat(), "form_cap": FORM_CAP, "form_prior_n": FORM_PRIOR_N,
           "relief_form": rf, "gate": gate}
    OUT.write_text(json.dumps(out, indent=1, default=float) + "\n")
    print(json.dumps(gate, indent=1))
    print({n: f"{b:+.3f}±{rf['se'][n]:.3f}" for n, b in rf["coef"].items() if n.startswith("form")})


if __name__ == "__main__":
    main()
