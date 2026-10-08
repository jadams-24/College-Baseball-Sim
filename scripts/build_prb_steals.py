"""Steals as a pitch-level decision (PR B, owner approval 2026-10-06/07): attempt and success rates by count and
game state, fitted from the 2025 WMT play-by-play, validated on the games that record the exact pitch of a steal.

The data. The play-by-play records a steal (SB, CS) as its own line between two plate appearances' results, but for
about 89% of steals not the pitch it happened on: the line is stamped with the pitcher's pitch count at the end of
the plate appearance. What each plate appearance does record is its pitch sequence (balls, called and swinging
strikes, fouls, the ball in play). A steal is resolved on a pitch the batter did not hit: a ball or a strike, not a
foul (the runner returns) and not a ball in play (the play is a hit or an out with the runner moving). So a steal
attempt sits on one of the plate appearance's ball / called strike / swinging strike pitches, which one unknown.

The model. Before each of those pitches, with the lead runner able to steal (runner on first with second open, else
on second with third open; engine.game2 _lead_stealer), an attempt starts with probability
    a = expit(alpha_count + beta . x),   x: outs, which base, score difference, inning (buckets below),
and succeeds with probability s = expit(gamma_count + delta . z), z: outs, which base. A plate appearance with no
attempt contributes prod_j (1 - a_j) over its eligible pitches; one whose first base-running event is an attempt on
an unknown eligible pitch j contributes sum_j [prod_{i<j} (1 - a_i)] a_j s_j^(SB) (1 - s_j)^(CS). Fitted by EM (the
E-step weights the candidate pitches; the M-steps are weighted logistic regressions, Newton-Raphson). The count
effects are identified because plate appearances pass through different count paths.

Left out: plate appearances whose first base-running event is not a steal (a wild pitch, pickoff, balk: the base
state changes at an unknown pitch; 5% of eligible plate appearances), and everything after the first steal of a
plate appearance (the base state changed).

Steals on the last pitch. A steal on the pitch that ends the plate appearance (strike three or ball four) is written
into the plate appearance's own line ("... struck out swinging (3-2 BBBKFS); X caught stealing"), so its pitch is
known exactly: it enters the fit with its position known.

Inning-ending caught stealing. A runner caught stealing for the third out leaves no plate appearance (the batter
leads off the next inning with a new count), so those attempts have no pitch path. The count effects come from the
plate appearances; the two-out levels of attempt and success are then set so that the fitted model reproduces every
two-out steal and caught stealing in the data (runner_events), the inning-ending ones included.

Validation. The checks by plate-appearance length and final count are confounded: a steal changes the rest of its
plate appearance (with the runner in scoring position pitchers throw more balls; in the play-by-play, plate
appearances with no base running run 3.61 pitches with a runner on first only and 3.72 with one on second only), so
plate appearances with an attempt end longer and in ball-heavy counts, which a per-pitch hazard on the path before
the attempt does not describe. The unconfounded check is the steals on the last pitch, whose count is exact.

No game records the pitch of a steal that happens in the middle of a plate appearance (the pitch count on
a steal line is the count at the end of the plate appearance for every steal linked here; an earlier reading of 41
games with live stamps was an artifact of matching steals written into the previous batter's line). So the model is
checked out of sample: fitted on 80% of the games, it predicts, in the other 20%, the share of eligible plate
appearances with an attempt by the plate appearance's number of pitches and final count, and the attempts written on
the last pitch by its count (the exact ones).

Writes data/ncaa_2025/derived/prb_steals.json and reports/prb_steals.md.

    python3 scripts/build_prb_steals.py
"""
from __future__ import annotations

import datetime as dt
import glob
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
P = ROOT / "data/ncaa_2025/pbp/parsed"
OUT = ROOT / "data/ncaa_2025/derived/prb_steals.json"
COUNTS = [(b, s) for b in range(4) for s in range(3)]
CI = {c: i for i, c in enumerate(COUNTS)}
SCORE_BUCKETS = ((-99, -4), (-3, -2), (-1, 1), (2, 3), (4, 99))     # batting team's lead
INNING_BUCKETS = ((1, 3), (4, 6), (7, 8), (9, 99))
STEAL_EVENTS = ("SB", "CS")
PITCH_NO_MAX = 0          # pitch number within the plate appearance: not used (nearly collinear with the count; tried 2026-10-07)


def bucket(v, buckets) -> int:
    for k, (lo, hi) in enumerate(buckets):
        if lo <= v <= hi:
            return k
    return len(buckets) - 1


# ---- data ------------------------------------------------------------------------------------------------
def load() -> pd.DataFrame:
    pa = pd.read_csv(P / "pa_events_2025.csv.gz")
    re_ = pd.read_csv(P / "runner_events_2025.csv.gz")
    pa = pa.sort_values(["game_id", "group_id"]).reset_index(drop=True)
    # each runner event belongs to the next plate appearance of the same game and half-inning
    re_ = re_.sort_values("group_id")
    keys = pa[["game_id", "group_id", "inning", "half"]].rename(columns={"group_id": "pa_gid", "inning": "pi", "half": "ph"}).sort_values("pa_gid")
    m = pd.merge_asof(re_.rename(columns={"group_id": "gid"}), keys, left_on="gid", right_on="pa_gid", by="game_id", direction="forward")
    m = m[(m.inning == m.pi) & (m.half == m.ph)].sort_values(["pa_gid", "gid"])
    first = m.groupby("pa_gid").first()
    pa["first_ev"] = pa.group_id.map(first.event)
    pa["first_ev_gid"] = pa.group_id.map(first.gid)
    pa["first_ev_from"] = pa.group_id.map(first.from_base)
    # the plate appearance's own line carries the state after the base running during it; the first runner
    # event carries the state before it, which is the state when the plate appearance began
    for c in ("on1", "on2", "on3", "outs", "away_score", "home_score"):
        pa[c + "_0"] = pa.group_id.map(first[c]).fillna(pa[c])
    return pa


def eligible(pa: pd.DataFrame) -> pd.DataFrame:
    """Plate appearances that start with a lead runner able to steal and a pitch sequence; the eligible pitches."""
    d = pa[pa.pitch_seq.notna()].copy()
    on1, on2, on3 = d.on1_0.astype(bool), d.on2_0.astype(bool), d.on3_0.astype(bool)
    d["steal_base"] = np.where(on1 & ~on2, 2, np.where(on2 & ~on3, 3, 0))
    d = d[d.steal_base > 0].copy()
    d["outs"] = d.outs_0.astype(int)
    lead = np.where(d.half == "T", d.away_score_0 - d.home_score_0, d.home_score_0 - d.away_score_0)
    d["score_b"] = [bucket(v, SCORE_BUCKETS) for v in lead]
    d["inn_b"] = [bucket(v, INNING_BUCKETS) for v in d.inning]
    # the first base-running event: a steal (by the lead runner), something else (left out), or none
    steal_first = d.first_ev.isin(STEAL_EVENTS)          # by the lead runner or, in a double steal, the trailer
    other_first = d.first_ev.notna() & ~steal_first
    # a steal on the last pitch, written into the plate appearance's own line
    after = d.text.fillna("").str.split(r"\)|;", n=1, regex=True).str[1].fillna("")
    last = d.first_ev.isna() & after.str.contains(r"stole|caught stealing", case=False)
    d["attempt"] = (steal_first | last).astype(int)
    d["success"] = ((d.first_ev == "SB") | (last & after.str.contains("stole", case=False) & ~after.str.contains("caught stealing", case=False))).astype(int)
    d["known_last"] = last.astype(int)
    d.attrs["left_out_other_event_first"] = int(other_first.sum())
    d = d[~other_first].copy()
    paths = []
    for seq, res in zip(d.pitch_seq.astype(str), d.result):
        b = s = 0
        el = []                                   # (count, pitch number) of each ball / called strike / swinging strike
        n = len(seq)
        for k, c in enumerate(seq):
            last = k == n - 1
            if c in "BKS" and not (last and res == "HBP"):
                el.append((CI[(min(b, 3), min(s, 2))], k))
            if c == "B":
                b += 1
            elif c in "KS":
                s += 1
            elif c == "F" and s < 2:
                s += 1
        paths.append(el)
    d["path"] = paths
    left = d.attrs["left_out_other_event_first"]
    d = d[[len(p) > 0 for p in d.path]].reset_index(drop=True)
    d.attrs["left_out_other_event_first"] = left
    return d


# ---- the model -------------------------------------------------------------------------------------------
def design(d: pd.DataFrame) -> tuple:
    """Pitch-level rows: plate appearance index, candidate position, count, and the attempt / success covariates."""
    rows_pa, rows_pos, rows_c, rows_k = [], [], [], []
    for i, p in enumerate(d.path):
        for j, (c, k) in enumerate(p):
            rows_pa.append(i); rows_pos.append(j); rows_c.append(c); rows_k.append(k)
    rows_k = np.minimum(np.array(rows_k, dtype=int), PITCH_NO_MAX)
    rows_pa, rows_pos, rows_c = np.array(rows_pa, dtype=int), np.array(rows_pos, dtype=int), np.array(rows_c, dtype=int)
    outs = d.outs.values[rows_pa].astype(int)
    third = (d.steal_base.values[rows_pa] == 3).astype(float)
    sc = d.score_b.values[rows_pa]
    inn = d.inn_b.values[rows_pa]
    Xc = np.column_stack([np.ones(len(rows_c)), np.eye(12)[rows_c]])     # intercept, then one deviation per count
    Xa = np.column_stack([Xc, outs == 1, outs == 2, third] + [sc == k for k in range(len(SCORE_BUCKETS)) if k != 2]
                         + [inn == k for k in range(1, len(INNING_BUCKETS))] + [rows_k == k for k in range(1, PITCH_NO_MAX + 1)]).astype(float)
    Xs = np.column_stack([Xc, outs == 1, outs == 2, third]).astype(float)
    names_a = ["intercept"] + [f"count_{b}-{s}" for b, s in COUNTS] + ["outs_1", "outs_2", "steal_third"] + \
              [f"lead_{lo}_{hi}" for k, (lo, hi) in enumerate(SCORE_BUCKETS) if k != 2] + [f"inning_{lo}_{hi}" for lo, hi in INNING_BUCKETS[1:]] + \
              [f"pitch_no_{k + 1}" + ("+" if k == PITCH_NO_MAX else "") for k in range(1, PITCH_NO_MAX + 1)]
    names_s = ["intercept"] + [f"count_{b}-{s}" for b, s in COUNTS] + ["outs_1", "outs_2", "steal_third"]
    return rows_pa, rows_pos, rows_c, Xa, Xs, names_a, names_s


RIDGE_COUNT = {"attempt": 2.0, "success": 8.0}    # GUESS: shrinkage of the per-count deviations (logit; prior SD 1/sqrt)


def ridge_vec(n, lam):
    r = np.full(n, 1e-6)
    r[1:13] = lam                                    # the count deviations; not the intercept or the covariates
    return r


def wlogit(X, y, w, beta, ridge, iters=50):
    """Weighted logistic regression, Newton-Raphson with a ridge vector (per coefficient). Returns beta, cov."""
    R = np.diag(ridge)
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(X @ beta)))
        W = w * p * (1 - p)
        H = X.T @ (X * W[:, None]) + R
        step = np.linalg.solve(H, X.T @ (w * (y - p)) - ridge * beta)
        beta = beta + step
        if np.abs(step).max() < 1e-9:
            break
    p = 1 / (1 + np.exp(-(X @ beta)))
    H = X.T @ (X * (w * p * (1 - p))[:, None]) + R
    return beta, np.linalg.inv(H)


def em(d, rows_pa, rows_pos, Xa, Xs, iters=200, tol=1e-7):
    n_pa = len(d)
    att = d.attempt.values
    suc = d.success.values
    ba = np.zeros(Xa.shape[1]); ba[0] = -3.0
    bs = np.zeros(Xs.shape[1]); bs[0] = 1.0
    ra, rs_ = ridge_vec(Xa.shape[1], RIDGE_COUNT["attempt"]), ridge_vec(Xs.shape[1], RIDGE_COUNT["success"])
    ll_old = -np.inf
    starts = np.r_[0, np.cumsum(np.bincount(rows_pa, minlength=n_pa))[:-1]]
    known = d.known_last.values
    final = final_rows(d, rows_pa)
    # a steal on the pitch that ends the plate appearance is written into its own line (known_last); a steal on a
    # line of its own was therefore on an earlier pitch
    allowed = np.where(known[rows_pa] == 1, final, ~final).astype(float)
    for it in range(iters):
        a = 1 / (1 + np.exp(-(Xa @ ba)))
        s = 1 / (1 + np.exp(-(Xs @ bs)))
        # log prob of no attempt before position j within the plate appearance
        la = np.log1p(-a)
        cum = np.cumsum(la)
        before = cum - la - np.repeat(cum[starts] - la[starts], np.bincount(rows_pa, minlength=n_pa))
        # probability that the first attempt is at j, with the observed result
        rs = np.where(suc[rows_pa] == 1, s, 1 - s)
        pj = np.exp(before) * a * rs * allowed
        tot_att = np.bincount(rows_pa, weights=pj, minlength=n_pa)
        no_att = np.exp(np.bincount(rows_pa, weights=la, minlength=n_pa))
        lik = np.where(att == 1, tot_att, no_att)
        ll = float(np.log(np.maximum(lik, 1e-300)).sum())
        # E-step: weight of "the attempt was at j" for attempted plate appearances
        post = np.where(att[rows_pa] == 1, pj / np.maximum(tot_att[rows_pa], 1e-300), 0.0)
        # rows before the attempt are "no attempt" with weight P(attempt later than j | ...): sum of post over later j
        rev = np.r_[np.cumsum(post[::-1])[::-1], 0.0]        # sum of post from row i to the end
        next_start = np.r_[starts[1:], len(post)]
        tail = rev[:-1] - np.repeat(rev[next_start], np.bincount(rows_pa, minlength=n_pa))
        later = tail - post                                  # the attempt is at a later position of the same PA
        w_noatt = np.where(att[rows_pa] == 1, later, 1.0)    # never attempted (no-attempt PAs), or attempt still to come
        # M-steps
        ya = np.r_[np.ones(len(post)), np.zeros(len(post))]
        Xa2 = np.vstack([Xa, Xa])
        wa = np.r_[post, w_noatt]
        keep = wa > 1e-12
        ba, cov_a = wlogit(Xa2[keep], ya[keep], wa[keep], ba, ra)
        keep_s = post > 1e-12
        bs, cov_s = wlogit(Xs[keep_s], suc[rows_pa][keep_s].astype(float), post[keep_s], bs, rs_)
        if abs(ll - ll_old) < tol * abs(ll):
            break
        ll_old = ll
    return ba, cov_a, bs, cov_s, ll, it + 1


def final_rows(d, rows_pa) -> np.ndarray:
    """Rows that are the pitch ending the plate appearance (its last pitch is a ball or strike: a walk or strikeout)."""
    is_last = np.r_[rows_pa[1:] != rows_pa[:-1], True]
    ends_bk = d.result.isin(["K", "BB"]).values[rows_pa] & np.array([str(x)[-1:] in "BKS" for x in d.pitch_seq.values[rows_pa]])
    return is_last & ends_bk


def predict(d, rows_pa, Xa, Xs, ba, bs):
    a = 1 / (1 + np.exp(-(Xa @ ba)))
    s = 1 / (1 + np.exp(-(Xs @ bs)))
    n = len(d)
    la = np.log1p(-a)
    p_none = np.exp(np.bincount(rows_pa, weights=la, minlength=n))
    is_last = final_rows(d, rows_pa)
    cum = np.cumsum(la)
    starts = np.r_[0, np.cumsum(np.bincount(rows_pa, minlength=n))[:-1]]
    before = cum - la - np.repeat(cum[starts] - la[starts], np.bincount(rows_pa, minlength=n))
    p_last = np.bincount(rows_pa, weights=np.where(is_last, np.exp(before) * a, 0.0), minlength=n)
    return 1 - p_none, p_last


def chi2_p(obs, exp):
    from statistics import NormalDist
    obs, exp = np.asarray(obs, float), np.asarray(exp, float)
    k = exp > 0
    stat = float(((obs[k] - exp[k]) ** 2 / exp[k]).sum())
    df = int(k.sum())
    z = ((stat / df) ** (1 / 3) - (1 - 2 / (9 * df))) / np.sqrt(2 / (9 * df))
    return stat, df, float(1 - NormalDist().cdf(z))


def final_count(seq: str) -> str:
    b = st = 0
    for c in seq[:-1]:
        if c == "B":
            b += 1
        elif c in "KS":
            st += 1
        elif c == "F" and st < 2:
            st += 1
    return f"{min(b, 3)}-{min(st, 2)}"


def main() -> None:
    pa = load()
    d = eligible(pa)
    # ---- out-of-sample check: fit on 80% of the games, predict the other 20% ----
    rng = np.random.default_rng(20261007)
    games = np.array(sorted(d.game_id.unique()))
    test_games = set(rng.choice(games, size=len(games) // 5, replace=False))
    tr = d[~d.game_id.isin(test_games)].reset_index(drop=True)
    te = d[d.game_id.isin(test_games)].reset_index(drop=True)
    r_tr = design(tr)
    ba_t, _, bs_t, _, _, _ = em(tr, r_tr[0], r_tr[1], r_tr[3], r_tr[4])
    r_te = design(te)
    p_att, p_last = predict(te, r_te[0], r_te[3], r_te[4], ba_t, bs_t)
    te = te.assign(p_att=p_att, p_last=p_last, n=te.pitches.clip(upper=8), fc=[final_count(str(x)) for x in te.pitch_seq])
    by_len = te.groupby("n").agg(obs=("attempt", "sum"), pred=("p_att", "sum"), pas=("attempt", "size"))
    by_fc = te.groupby("fc").agg(obs=("attempt", "sum"), pred=("p_att", "sum"), pas=("attempt", "size"))
    lastk = te.groupby("fc").agg(obs=("known_last", "sum"), pred=("p_last", "sum"))
    v_len, v_fc, v_last = chi2_p(by_len.obs, by_len.pred), chi2_p(by_fc.obs, by_fc.pred), chi2_p(lastk.obs, lastk.pred)
    # ---- the fit on every game ----
    rows_pa, rows_pos, rows_c, Xa, Xs, na, ns = design(d)
    ba, cov_a, bs, cov_s, ll, its = em(d, rows_pa, rows_pos, Xa, Xs)
    se_a, se_s = np.sqrt(np.diag(cov_a)), np.sqrt(np.diag(cov_s))
    # ---- two outs: inning-ending caught stealing has no plate appearance ----
    re_ = pd.read_csv(P / "runner_events_2025.csv.gz")
    st = re_[re_.event.isin(STEAL_EVENTS)]
    emb = d[d.known_last == 1]
    direct = {o: int((st.outs == o).sum() + (emb.outs == o).sum()) for o in (0, 1, 2)}
    direct_sb = {o: int(((st.outs == o) & (st.event == "SB")).sum() + ((emb.outs == o) & (emb.success == 1)).sum()) for o in (0, 1, 2)}
    linked = {o: int(d.attempt[d.outs == o].sum()) for o in (0, 1, 2)}
    ratio01 = (direct[0] + direct[1]) / (linked[0] + linked[1])          # steals outside the fitted states (all outs)
    k2 = direct[2] / linked[2] / ratio01                                  # inning-ending attempts missing at two outs
    i_o2a = na.index("outs_2")
    ba[i_o2a] += np.log(k2)
    # success at two outs: the direct rate, over the fitted posterior of the attempts' counts
    s2 = direct_sb[2] / direct[2]
    a_ = 1 / (1 + np.exp(-(Xa @ ba)))
    two = d.outs.values[rows_pa] == 2
    w = np.where(two, a_, 0.0)
    i_o2s = ns.index("outs_2")
    base = Xs @ bs - bs[i_o2s] * Xs[:, i_o2s]          # every term but the two-out level
    lo, hi = -5.0, 5.0
    for _ in range(60):
        mid = (lo + hi) / 2
        m = float((w * (1 / (1 + np.exp(-(base + mid))))).sum() / w.sum())
        lo, hi = (mid, hi) if m < s2 else (lo, mid)
    bs[i_o2s] = (lo + hi) / 2
    se_s[i_o2s] = float(np.sqrt(s2 * (1 - s2) / direct[2]) / (s2 * (1 - s2)))
    res = {
        "built": dt.date.today().isoformat(), "_note": __doc__,
        "sample": {"eligible_pa": int(len(d)), "attempts": int(d.attempt.sum()), "steals": int(d.success.sum()),
                   "attempts_last_pitch_known": int(d.known_last.sum()), "eligible_pitches": int(len(rows_pa)),
                   "left_out_other_event_first": d.attrs.get("left_out_other_event_first"),
                   "direct_attempts_by_outs": direct, "direct_steals_by_outs": direct_sb, "linked_attempts_by_outs": linked,
                   "two_out_attempt_factor": round(float(k2), 4), "two_out_success_direct": round(float(s2), 4)},
        "attempt": {"names": na, "coef": ba.round(5).tolist(), "se": se_a.round(5).tolist()},
        "success": {"names": ns, "coef": bs.round(5).tolist(), "se": se_s.round(5).tolist()},
        "buckets": {"lead": SCORE_BUCKETS, "inning": INNING_BUCKETS, "lead_reference": list(SCORE_BUCKETS[2]), "inning_reference": list(INNING_BUCKETS[0])},
        "loglik": ll, "em_iterations": its,
        "validation_20pct_games": {
            "games": len(test_games), "eligible_pa": int(len(te)),
            "by_pa_length": {str(k): {"obs": int(r.obs), "pred": round(float(r.pred), 1), "pas": int(r.pas)} for k, r in by_len.iterrows()},
            "by_final_count": {k: {"obs": int(r.obs), "pred": round(float(r.pred), 1), "pas": int(r.pas)} for k, r in by_fc.iterrows()},
            "last_pitch_by_count": {k: {"obs": int(r.obs), "pred": round(float(r.pred), 1)} for k, r in lastk.iterrows()},
            "chi2": {"by_pa_length": v_len, "by_final_count": v_fc, "last_pitch_by_count": v_last}},
        "conf": "B",
    }
    OUT.write_text(json.dumps(res, indent=1, default=float) + "\n")
    att_rate = {f"{b}-{s}": float(1 / (1 + np.exp(-(ba[0] + ba[1 + CI[(b, s)]])))) for b, s in COUNTS}
    suc_rate = {f"{b}-{s}": float(1 / (1 + np.exp(-(bs[0] + bs[1 + CI[(b, s)]])))) for b, s in COUNTS}
    md = ["# Steals by count (PR B)", "",
          f"Fit: {len(d):,} plate appearances that begin with a lead runner able to steal, {int(d.attempt.sum()):,} attempts "
          f"({int(d.success.sum()):,} stolen; {int(d.known_last.sum())} on the last pitch, position known), {len(rows_pa):,} eligible pitches; "
          f"EM {its} iterations. Two outs: the attempt odds are scaled by {k2:.3f} and the success level set to the direct rate "
          f"{s2:.3f} for the inning-ending caught stealing that has no plate appearance.", "",
          "| Count | Attempt per pitch (reference state) | SE (logit) | Success (reference state) | SE (logit) |", "|---|---|---|---|---|"]
    for b, s_ in COUNTS:
        i = 1 + CI[(b, s_)]
        md.append(f"| {b}-{s_} | {att_rate[f'{b}-{s_}']:.4f} | {se_a[i]:.3f} | {suc_rate[f'{b}-{s_}']:.3f} | {se_s[i]:.3f} |")
    md += ["", "Reference state: no outs, steal of second, score within one run, innings 1-3.", "",
           "| Covariate | Attempt (logit) | SE | Success (logit) | SE |", "|---|---|---|---|---|"]
    for k, name in enumerate(na[13:], start=13):
        sk = ns.index(name) if name in ns else None
        md.append(f"| {name} | {ba[k]:+.3f} | {se_a[k]:.3f} | " + (f"{bs[sk]:+.3f} | {se_s[sk]:.3f} |" if sk is not None else "— | — |"))
    md += ["", f"Out of sample: fitted on 80% of the games, predicting the other {len(test_games)} games ({len(te):,} eligible plate appearances).", "",
           "| Plate appearance length (pitches) | Plate appearances | Attempts observed | Predicted |", "|---|---|---|---|"]
    md += [f"| {k if k < 8 else '8+'} | {int(r.pas)} | {int(r.obs)} | {r.pred:.1f} |" for k, r in by_len.iterrows()]
    md += ["", f"Chi-square {v_len[0]:.1f} on {v_len[1]} cells (p {v_len[2]:.3f}).", "",
           "| Final count | Plate appearances | Attempts observed | Predicted | Last-pitch attempts observed | Predicted |", "|---|---|---|---|---|---|"]
    md += [f"| {k} | {int(r.pas)} | {int(r.obs)} | {r.pred:.1f} | {int(lastk.obs[k])} | {lastk.pred[k]:.1f} |" for k, r in by_fc.iterrows()]
    md += ["", f"By final count: chi-square {v_fc[0]:.1f} on {v_fc[1]} cells (p {v_fc[2]:.3f}); last-pitch attempts by count: {v_last[0]:.1f} "
           f"on {v_last[1]} cells (p {v_last[2]:.3f}).", ""]
    (ROOT / "reports/prb_steals.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
