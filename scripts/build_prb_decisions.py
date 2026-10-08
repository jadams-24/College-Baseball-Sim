"""Bunts, intentional walks and the pitcher's hold (PR B, owner approval 2026-10-06/07), from the 2025 WMT
play-by-play. Steals by count: scripts/build_prb_steals.py.

Bunts.
  ai        P(the plate appearance is a bunt) for the AI manager: logistic on the base state when the plate
            appearance began (empty, first, second, first and second, third occupied), outs, the batting team's lead,
            the inning and the lineup slot (the play-by-play does not name it, but the batting order cycles, so a
            team's k-th plate appearance of a game is slot k mod 9).
  pitch     what a bunting batter's pitches do, by count before two strikes: ball, called strike, missed bunt
            (swinging strike), bunt foul, bunt in play, hit by pitch, from the bunt plate appearances' sequences.
            The sample is the plate appearances that ended in a bunt in play, so a bunt that was given up leaves no
            trace; at two strikes the bunt is taken off and the batter swings away (GUESS, GUESSES.md).
  outcome   the result and every runner's destination of a bunt in play, by outs and occupied bases at the bunt
            (sacrifice, bunt single, out with no advance, fielder's choice, error, double play), as rows of the
            engine's advancement encoding (r1, r2, r3, batter, outs on the play, errors).
Intentional walks.
  ai        P(intentional walk) at the start of a plate appearance, for the AI: logistic on first base open, the
            other bases, outs, the batting team's lead, the inning and the lineup slot. An intentional walk is
            awarded without pitches (381 in the sample, nearly all scored 0-0).
The pitcher's hold. Steal attempts and success against each pitcher (the pitcher of the plate appearance during
which the runner went), with the binomial noise removed (method of moments): the true spread across pitchers of
the attempt odds and of the success odds, and their correlation. The engine draws a hold rating per pitcher on
that spread.
Benchmarks for the gate (per team-game, the play-by-play's games): bunts, sacrifice hits, bunt singles,
intentional walks; and steal attempts per eligible plate appearance by the plate appearance's length and final
count (the observable form of "attempts by count").

Writes data/ncaa_2025/derived/prb_inputs.json.

    python3 scripts/build_prb_decisions.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from build_prb_steals import INNING_BUCKETS, SCORE_BUCKETS, bucket, eligible, final_count, load  # noqa: E402

OUT = ROOT / "data/ncaa_2025/derived/prb_inputs.json"
BASE_CLASSES = ("empty", "first", "second", "first_second", "third")
SLOT_GROUPS = ((1, 2), (3, 5), (6, 8), (9, 9))
BUNT_RES = {"SH": "SH", "1B": "1B", "2B": "2B", "GO": "IP_OUT", "FO": "IP_OUT", "DP": "IP_OUT", "GIDP": "IP_OUT", "FC": "FC",
            "ROE": "ROE", "SF": "SF"}
MIN_CELL = 20


def base_class(on1, on2, on3) -> int:
    if on3:
        return 4
    return {(0, 0): 0, (1, 0): 1, (0, 1): 2, (1, 1): 3}[(int(on1), int(on2))]


def logit_fit(X, y, ridge=1e-3, iters=60):
    beta = np.zeros(X.shape[1])
    R = np.diag(np.broadcast_to(np.asarray(ridge, float), (X.shape[1],)))
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(X @ beta)))
        H = X.T @ (X * (p * (1 - p))[:, None]) + R
        step = np.linalg.solve(H, X.T @ (y - p) - R @ beta)
        beta += step
        if np.abs(step).max() < 1e-9:
            break
    p = 1 / (1 + np.exp(-(X @ beta)))
    cov = np.linalg.inv(X.T @ (X * (p * (1 - p))[:, None]) + R)
    return beta, np.sqrt(np.diag(cov))


def features(df, lead_col, first_open: bool = False) -> tuple[np.ndarray, list]:
    """Intercept, base class (reference: empty), outs, lead bucket (reference: within one), inning bucket
    (reference: 1-3), slot group (reference: 1-2)."""
    cols, names = [np.ones(len(df))], ["intercept"]
    bc = df.base_class.values
    for k in range(1, len(BASE_CLASSES)):
        cols.append(bc == k); names.append(f"base_{BASE_CLASSES[k]}")
    if first_open:
        cols.append(df.first_open.values); names.append("first_open")
    for o in (1, 2):
        cols.append(df.outs0.values == o); names.append(f"outs_{o}")
    lb = df[lead_col].values
    for k in range(len(SCORE_BUCKETS)):
        if k != 2:
            cols.append(lb == k); names.append(f"lead_{SCORE_BUCKETS[k][0]}_{SCORE_BUCKETS[k][1]}")
    ib = df.inn_b.values
    for k in range(1, len(INNING_BUCKETS)):
        cols.append(ib == k); names.append(f"inning_{INNING_BUCKETS[k][0]}_{INNING_BUCKETS[k][1]}")
    sg = df.slot_g.values
    for k in range(1, len(SLOT_GROUPS)):
        cols.append(sg == k); names.append(f"slot_{SLOT_GROUPS[k][0]}_{SLOT_GROUPS[k][1]}")
    return np.column_stack(cols).astype(float), names


def selection_free(pa: pd.DataFrame) -> dict:
    """The gated steal-path sample (owner decision 2026-10-07): every plate appearance that began with a lead runner
    able to steal and has a ball or strike, whatever base running came first, so nothing is selected on what happened
    during it; an attempt is any steal or caught stealing during it (its own line, or written into the plate
    appearance's line on its last pitch), success that of the first. By length (8+ pooled) and final count. The
    first-event sample (scripts/build_prb_steals.py eligible()) leaves out the plate appearances in which a wild pitch,
    passed ball, pickoff or balk came first, more often long ones; it stays as a diagnostic."""
    d = pa[pa.pitch_seq.notna()].copy()
    on1, on2, on3 = d.on1_0.astype(bool), d.on2_0.astype(bool), d.on3_0.astype(bool)
    d = d[(on1 & ~on2) | (on2 & ~on3)].copy()
    seq, res = d.pitch_seq.astype(str), d.result
    nbks = seq.str.count("[BKS]") - ((res == "HBP") & seq.str[-1:].str.contains("[BKS]")).astype(int)
    d = d[nbks > 0].copy()
    re_ = pd.read_csv(ROOT / "data/ncaa_2025/pbp/parsed/runner_events_2025.csv.gz")
    allk = pa[["game_id", "group_id", "inning", "half"]].rename(columns={"group_id": "pa_gid", "inning": "pi", "half": "ph"}).sort_values("pa_gid")
    m = pd.merge_asof(re_.sort_values("group_id").rename(columns={"group_id": "gid"}), allk, left_on="gid", right_on="pa_gid",
                      by="game_id", direction="forward")
    m = m[(m.inning == m.pi) & (m.half == m.ph) & m.event.isin(["SB", "CS"])].sort_values(["pa_gid", "gid"])
    first = m.groupby("pa_gid").event.first()
    after = d.text.fillna("").str.split(r"\)|;", n=1, regex=True).str[1].fillna("")
    last = after.str.contains(r"stole|caught stealing", case=False)
    last_ok = after.str.contains("stole", case=False) & ~after.str.contains("caught stealing", case=False)
    ev = d.group_id.map(first)
    d["att"] = ev.notna() | last
    d["ok"] = np.where(ev.notna(), ev == "SB", last_ok)
    d["n"] = d.pitches.clip(upper=8)
    d["fc"] = [final_count(str(x)) for x in d.pitch_seq]
    by = lambda col: {str(int(k)) if col == "n" else k: {"pas": int(len(v)), "attempts": int(v.att.sum()), "steals": int((v.att & v.ok).sum())}
                      for k, v in d.groupby(col)}
    return {"by_length": by("n"), "by_final_count": by("fc"),
            "all": {"pas": int(len(d)), "attempts": int(d.att.sum()), "steals": int((d.att & d.ok).sum())}}


CELLS = [f"{o}|{a}{b}{c}" for o in range(3) for a in (0, 1) for b in (0, 1) for c in (0, 1)]
BUNT_CELL_RIDGE = 1.0      # GUESS: shrinkage of the outs x bases cells toward the empty-base no-out cell (prior SD 1 logit)


def cell_features(df, lead_col) -> tuple[np.ndarray, list]:
    """The bunt model's design: one cell per outs x occupied bases (reference: no out, bases empty), because what a
    team bunts for depends on both together (the sacrifice with runners on and nobody out, the squeeze with a runner
    on third and one out, the bunt for a hit with nobody on), which main effects of bases and outs cannot hold;
    then the lead, inning and slot buckets."""
    key = [f"{int(o)}|{int(a)}{int(b)}{int(c)}" for o, a, b, c in zip(df.outs0, df.on1_0, df.on2_0, df.on3_0)]
    cols, names = [np.ones(len(df))], ["intercept"]
    key = np.array(key)
    for c in CELLS[1:]:
        cols.append(key == c); names.append(f"cell_{c}")
    lb = df[lead_col].values
    for k in range(len(SCORE_BUCKETS)):
        if k != 2:
            cols.append(lb == k); names.append(f"lead_{SCORE_BUCKETS[k][0]}_{SCORE_BUCKETS[k][1]}")
    ib = df.inn_b.values
    for k in range(1, len(INNING_BUCKETS)):
        cols.append(ib == k); names.append(f"inning_{INNING_BUCKETS[k][0]}_{INNING_BUCKETS[k][1]}")
    sg = df.slot_g.values
    for k in range(1, len(SLOT_GROUPS)):
        cols.append(sg == k); names.append(f"slot_{SLOT_GROUPS[k][0]}_{SLOT_GROUPS[k][1]}")
    return np.column_stack(cols).astype(float), names


def dest(v) -> str:
    return "" if v == "" or pd.isna(v) else str(int(float(v)))


def main() -> None:
    pa = load()
    pa = pa.sort_values(["game_id", "group_id"]).reset_index(drop=True)
    # a bunt: the play-by-play's bunt flag, or a sacrifice hit written without the word "bunt" ("grounded out to
    # p, SAC"): 10% of sacrifice hits carry no bunt flag
    sac = pa.text.fillna("").str.contains(r"\bSAC\b(?!\s*fly)", case=False, regex=True) & (pa.result != "SF")
    pa["bunt"] = ((pa.bunt == 1) | sac | (pa.result == "SH")).astype(int)
    pa["k_team"] = pa.groupby(["game_id", "bat_team_id"]).cumcount()
    pa["slot"] = pa.k_team % 9 + 1
    pa["slot_g"] = [bucket(s, SLOT_GROUPS) for s in pa.slot]
    pa["outs0"] = pa.outs_0.astype(int)
    pa["base_class"] = [base_class(a, b, c) for a, b, c in zip(pa.on1_0, pa.on2_0, pa.on3_0)]
    lead = np.where(pa.half == "T", pa.away_score_0 - pa.home_score_0, pa.home_score_0 - pa.away_score_0)
    pa["lead_b"] = [bucket(v, SCORE_BUCKETS) for v in lead]
    pa["inn_b"] = [bucket(v, INNING_BUCKETS) for v in pa.inning]
    pa["first_open"] = (pa.on1_0 == 0).astype(float)
    team_games = int(pa.groupby(["game_id", "bat_team_id"]).ngroups)
    out = {"built": dt.date.today().isoformat(), "_note": __doc__, "team_games": team_games,
           "buckets": {"base_classes": BASE_CLASSES, "lead": SCORE_BUCKETS, "inning": INNING_BUCKETS, "slot_groups": SLOT_GROUPS}}
    # ---- bunts: the AI's rate ----
    ibb = pa.sub_type == "intentional walk"
    sw = pa[~ibb]
    X, names = cell_features(sw, "lead_b")
    y = (sw.bunt == 1).astype(float).values
    b, se = logit_fit(X, y, ridge=np.r_[1e-3, np.full(len(CELLS) - 1, BUNT_CELL_RIDGE), np.full(X.shape[1] - len(CELLS), 1e-3)])
    out["bunt_ai"] = {"names": names, "coef": b.round(5).tolist(), "se": se.round(5).tolist(), "n": int(len(sw)), "bunts": int(y.sum())}
    # ---- bunts: pitches by count before two strikes ----
    bp = pa[(pa.bunt == 1) & pa.pitch_seq.notna()]
    ev = defaultdict(Counter)
    for seq in bp.pitch_seq.astype(str):
        b_ = s_ = 0
        for c in seq:
            if s_ < 2:
                ev[f"{min(b_, 3)}-{s_}"][c] += 1
            if c == "B":
                b_ += 1
            elif c in "KS":
                s_ += 1
            elif c == "F" and s_ < 2:
                s_ += 1
    out["bunt_pitch"] = {"by_count": {k: dict(v) for k, v in sorted(ev.items())}, "events": "BKSFPHN",
                         "note": "before two strikes; at two strikes the bunt is taken off (GUESS)"}
    # ---- bunts: outcome and runner destinations, by the state at the bunt ----
    tab = defaultdict(Counter)
    for r in pa[pa.bunt == 1].itertuples(index=False):
        res = BUNT_RES.get(r.result)
        if res is None:
            continue
        bases = f"{int(r.on1)}{int(r.on2)}{int(r.on3)}"
        tup = ",".join([dest(r.r1_to), dest(r.r2_to), dest(r.r3_to), dest(r.batter_to), str(int(r.outs_on_play)), str(int(r.errors_on_play))])
        key = f"{res}|{tup}"
        tab[f"{int(r.outs)}|{bases}"][key] += 1
        tab[f"*|{bases}"][key] += 1
        tab["*|*"][key] += 1
    out["bunt_outcome"] = {"cells": {k: dict(v) for k, v in tab.items()}, "min_cell": MIN_CELL,
                           "encoding": "result|r1,r2,r3,batter,outs_on_play,errors (engine.tables advancement encoding)"}
    # ---- the batter's average share of bunts and intentional walks, by lineup slot: the swing-away law takes these
    # out of his season law (engine.game2 _forward), so his season totals stay at it ----
    out["by_slot"] = {"bunt": [round(float(sw[sw.slot == k].bunt.mean()), 5) for k in range(1, 10)],
                      "ibb": [round(float(ibb[pa.slot == k].mean()), 5) for k in range(1, 10)],
                      "note": "bunts in play per non-IBB plate appearance and intentional walks per plate appearance, slots 1-9"}
    # ---- intentional walks: the AI's rate ----
    X, names = features(pa, "lead_b", first_open=True)
    y = ibb.astype(float).values
    b, se = logit_fit(X, y)
    out["ibb_ai"] = {"names": names, "coef": b.round(5).tolist(), "se": se.round(5).tolist(), "n": int(len(pa)), "ibb": int(y.sum())}
    # ---- scoring: a runner picked off while breaking for the next base is charged a caught stealing (box scores
    # count it; the play-by-play files it as a pickoff, "caught stealing, picked off") ----
    re_ = pd.read_csv(ROOT / "data/ncaa_2025/pbp/parsed/runner_events_2025.csv.gz")
    po = re_[re_.event == "PO"]
    po_out = po[po.text.fillna("").str.contains(r"\bout\b|picked off", case=False)]
    cs = po_out.text.fillna("").str.contains("caught stealing", case=False)
    out["pickoff_scoring"] = {"pickoff_outs": int(len(po_out)), "caught_stealing": int(cs.sum()),
                              "cs_share": round(float(cs.mean()), 4)}
    # ---- the pitcher's hold ----
    d = eligible(pa.drop(columns=["outs0", "base_class", "lead_b", "inn_b", "first_open", "slot", "slot_g", "k_team"], errors="ignore"))
    d["pkey"] = d.pit_team_id.astype(str) + "|" + d.pitcher.astype(str).str.lower().str.replace(r"[^a-z]", "", regex=True)
    g = d.groupby("pkey").agg(n=("attempt", "size"), att=("attempt", "sum"), sb=("success", "sum"))     # pitcher_id is per game
    g = g[g.n >= 20]
    p_a = g.att.sum() / g.n.sum()
    ra = g.att / g.n
    w = g.n / g.n.sum()
    var_obs = float((w * (ra - p_a) ** 2).sum())
    noise = float((w * p_a * (1 - p_a) / g.n).sum())
    sd_att = np.sqrt(max(var_obs - noise, 0.0)) / (p_a * (1 - p_a))          # logit scale
    gs = g[g.att >= 5]
    p_s = gs.sb.sum() / gs.att.sum()
    rs = gs.sb / gs.att
    ws = gs.att / gs.att.sum()
    var_s = float((ws * (rs - p_s) ** 2).sum())
    noise_s = float((ws * p_s * (1 - p_s) / gs.att).sum())
    sd_suc = np.sqrt(max(var_s - noise_s, 0.0)) / (p_s * (1 - p_s))
    # correlation of the two pitcher effects (pitchers with both): covariance of the rates, no shared noise
    both = g[g.att >= 5]
    cov = float(np.average((both.att / both.n - p_a) * (both.sb / both.att - p_s), weights=both.att))
    corr = cov / (np.sqrt(max(var_obs - noise, 1e-12)) * np.sqrt(max(var_s - noise_s, 1e-12))) if var_obs > noise and var_s > noise_s else 0.0
    out["pitcher_hold"] = {"pitchers": int(len(g)), "pitchers_success": int(len(gs)), "attempt_rate": round(float(p_a), 5),
                           "success_rate": round(float(p_s), 4), "sd_attempt_logit": round(float(sd_att), 4),
                           "sd_success_logit": round(float(sd_suc), 4), "corr": round(float(max(-1.0, min(1.0, corr))), 3),
                           "note": "one hold rating per pitcher: attempt odds x exp(-sd_attempt z), success odds x exp(-sd_success z), z ~ N(0, 1)"}
    # ---- benchmarks for the gate ----
    bunts = pa.bunt == 1
    bench = {"team_games": team_games,
             "bunts_per_team_game": float(bunts.sum() / team_games),
             "sac_hits_per_team_game": float((pa.result == "SH").sum() / team_games),
             "bunt_hits_per_team_game": float((bunts & pa.result.isin(["1B", "2B"])).sum() / team_games),
             "ibb_per_team_game": float(ibb.sum() / team_games)}
    for k in list(bench):
        if k.endswith("per_team_game"):
            n = bench[k] * team_games
            bench[k + "_se"] = float(np.sqrt(n) / team_games)          # Poisson
    e = d.assign(n=d.pitches.clip(upper=8), fc=[final_count(str(x)) for x in d.pitch_seq])
    bench["steal_attempt_by_pa_length"] = {str(int(k)): {"pas": int(v.size), "attempts": int(v.sum())} for k, v in e.groupby("n").attempt}
    bench["steal_attempt_by_final_count"] = {k: {"pas": int(v.size), "attempts": int(v.sum())} for k, v in e.groupby("fc").attempt}
    bench["steal_success_by_pa_length"] = {str(int(k)): {"attempts": int(v.attempt.sum()), "steals": int(v.success.sum())} for k, v in e.groupby("n")}
    bench["steal_attempt_by_pa_length_all"] = selection_free(pa)
    bench["note"] = ("WMT play-by-play 2025 (54 programs and every other WMT-covered game); attempts by path: plate appearances that "
                     "begin with a lead runner able to steal and whose first base-running event is a steal or none, the steal "
                     "counted in the plate appearance it happened in (scripts/build_prb_steals.py eligible())")
    out["bench"] = bench
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, indent=1, default=float) + "\n")
    tmp.replace(OUT)                                   # atomic: a running simulation may be reading it
    print(json.dumps({k: v for k, v in bench.items() if not isinstance(v, dict)}, indent=1))
    print("pitcher hold", out["pitcher_hold"])
    print("bunt ai", dict(zip(out["bunt_ai"]["names"], out["bunt_ai"]["coef"])))
    print("ibb ai", dict(zip(out["ibb_ai"]["names"], out["ibb_ai"]["coef"])))
    print("bunt pitch counts", {k: sum(v.values()) for k, v in ev.items()})


if __name__ == "__main__":
    main()
