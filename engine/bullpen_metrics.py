"""Bullpen deployment metrics (variance stage, 2026-10-09; owner decision: option A, relief usage reacts to results).

One definition for the 2025 play-by-play (scripts/build_bullpen_form.py) and the engine's outings (engine/report6.py), so
the gate compares like with like. An outing: team, pitcher, its order in the team's season, whether it was a start,
batters faced, runs scored on plate-appearance plays while he was in (inherited runners included; base-running runs
between plate appearances are not counted on either side), and the margin (his team's score minus the opponent's) and
inning when he entered, and the game.

  feedback_slopes   relief-only pitchers (no start all season), each relief outing after his first: the next entry's
                    blowout indicator (|margin| >= BLOWOUT) and |margin| on the runs he allowed in his previous outing,
                    both demeaned within pitcher, controlling for the previous entry's |margin| (game states persist);
                    OLS slopes per run
  workload_terciles relief-only pitchers with at least MIN_BF batters faced: runs per batter faced minus his staff's mean,
                    averaged by workload third within the staff (batters faced rank); positive = worse than the staff
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BLOWOUT = 7          # config.phase6 LEVERAGE_BLOWOUT: the relief choice's blowout bin
MIN_BF = 20

COLUMNS = ["team", "pid", "seq", "starter", "bf", "runs", "margin", "inning", "game"]


def relief_only(o: pd.DataFrame) -> pd.DataFrame:
    sp = set(o.loc[o.starter.astype(bool), "pid"])
    return o[~o.pid.isin(sp)]


def feedback_slopes(o: pd.DataFrame) -> dict:
    r = relief_only(o).sort_values(["pid", "seq"]).copy()
    r["absm"] = r.margin.abs().astype(float)
    r["blow"] = (r.absm >= BLOWOUT).astype(float)
    g = r.groupby("pid")
    r["prev_runs"] = g.runs.shift().astype(float)
    r["prev_absm"] = g.absm.shift()
    r = r.dropna(subset=["prev_runs"])
    out = {"n_pairs": int(len(r))}
    if len(r) < 10:
        return out
    dm = lambda s: s - s.groupby(r.pid).transform("mean")        # noqa: E731
    X = np.column_stack([dm(r.prev_runs), dm(r.prev_absm)])
    XtX_inv = np.linalg.inv(X.T @ X)
    for y in ("blow", "absm"):
        yy = dm(r[y]).values
        b = XtX_inv @ (X.T @ yy)
        res = yy - X @ b
        out[y] = float(b[0])
        out[y + "_se"] = float(np.sqrt(res.var() * XtX_inv[0, 0]))
    return out


def workload_terciles(o: pd.DataFrame, min_bf: int = MIN_BF) -> dict:
    r = relief_only(o)
    s = r.groupby(["team", "pid"]).agg(bf=("bf", "sum"), runs=("runs", "sum"))
    s = s[s.bf >= min_bf].copy()
    s["q"] = s.runs / s.bf
    s["dq"] = s.q - s.groupby(level=0).q.transform("mean")
    s["wr"] = s.groupby(level=0).bf.rank(pct=True)
    out = {"n_pitchers": int(len(s))}
    for lab, lo, hi in (("low", 0.0, 1 / 3), ("mid", 1 / 3, 2 / 3), ("high", 2 / 3, 1.0)):
        out[lab] = float(s[(s.wr > lo) & (s.wr <= hi)].dq.mean())
    out["low_minus_high"] = out["low"] - out["high"]
    return out


def frame(rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=COLUMNS)


ENTRY_BUCKETS = (("0-1", 0, 1), ("2-3", 2, 3), ("4", 4, 4), ("5-7", 5, 7), ("8+", 8, 999))
GAME_COL = "game"


def entry_quality(o: pd.DataFrame, min_other_bf: int = MIN_BF) -> dict:
    """Relief entries by |margin| at entry: the entering pitcher's runs per batter faced in his other games (his season minus
    this game; at least min_other_bf batters faced elsewhere) minus his staff's relief runs per batter faced, BF-weighted. The
    frame needs a game column (outings of one pitcher in one game are one entry's game). Positive = a worse arm than the staff's
    relief average."""
    r = o[~o.starter.astype(bool)].copy()
    g = r.groupby(["pid", GAME_COL]).agg(bf=("bf", "sum"), runs=("runs", "sum"))
    s = g.groupby(level=0).sum()
    key = pd.MultiIndex.from_arrays([r.pid, r[GAME_COL]])
    n_o = s.bf.reindex(r.pid).values - g.bf.reindex(key).values
    x_o = s.runs.reindex(r.pid).values - g.runs.reindex(key).values
    team = r.groupby("team").runs.sum() / r.groupby("team").bf.sum()
    ok = n_o >= min_other_bf
    gap = np.where(ok, x_o / np.maximum(n_o, 1), np.nan) - r.team.map(team).values
    am = r.margin.abs().values
    out = {}
    for lab, lo, hi in ENTRY_BUCKETS:
        k = ok & (am >= lo) & (am <= hi)
        w = r.bf.values[k]
        out[lab] = float(np.sum(gap[k] * w) / np.sum(w)) if w.sum() else float("nan")
    return out
