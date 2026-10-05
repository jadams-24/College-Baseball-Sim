"""Cancellation rates of regular-season games, by month, from the WarrenNolan team schedules (the feed
does not list most canceled games). A scheduled game is canceled when the schedule shows it canceled and
it was never played; postponed games that were made up count as played. Regular season: games before
May 25 that are not conference tournament, NCAA tournament or other May/June tournament games.
Seasons: every data/ncaa_<season>/warrennolan/team_games_<season>.csv present (2025, 2026).
Rates are per team-game (each game counts once per team; the rate is the same per game).

Writes the "cancel7" block of data/ncaa_2025/derived/phase7_inputs.json and the games-per-team rows into
data/ncaa_2025/derived/phase7_benchmarks.json.

    python3 scripts/build_phase7_cancel.py
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
from config.phase7 import INPUTS7  # noqa: E402

BENCH = ROOT / "data/ncaa_2025/derived/phase7_benchmarks.json"
POST = "Tournament|Championship|Regional|Super|World Series"


def season(y: int) -> pd.DataFrame | None:
    f = ROOT / f"data/ncaa_{y}/warrennolan/team_games_{y}.csv"
    if not f.exists():
        return None
    t = pd.read_csv(f)
    t["date"] = pd.to_datetime(t.date)
    post = t.event.astype(str).str.contains(POST, case=False, na=False) & (t.date.dt.month >= 5)
    t = t[~post & (t.date < f"{y}-05-25")].copy()
    t["season"] = y
    return t


def main() -> None:
    T = pd.concat([x for x in (season(y) for y in (2025, 2026)) if x is not None], ignore_index=True)
    T["cx"] = T.status.astype(str).str.lower().eq("canceled")
    by_m = T.groupby(T.date.dt.month).cx.agg(["mean", "size"])
    rates = {str(int(m)): round(float(r["mean"]), 4) for m, r in by_m.iterrows()}
    rates["all"] = round(float(T.cx.mean()), 4)
    per = T.groupby(["season", "team"]).agg(sched=("cx", "size"), canceled=("cx", "sum"))
    per["played"] = per.sched - per.canceled
    seasons = sorted(T.season.unique().tolist())
    out = {"built": dt.date.today().isoformat(), "seasons": seasons, "rate_by_month": rates,
           "n_team_games": int(len(T)), "_note": __doc__, "conf": "B",
           "conf_note": "WarrenNolan lists canceled games it was given; games dropped from schedules long before may be missing (rates are a floor)"}
    cur = json.loads(INPUTS7.read_text()) if INPUTS7.exists() else {}
    cur["cancel7"] = out
    INPUTS7.write_text(json.dumps(cur, indent=1) + "\n")
    bench = json.loads(BENCH.read_text())
    g = per.groupby("season")
    bench["games"] = {"_note": "regular season per team (all opponents, WarrenNolan schedules): scheduled, canceled and played; the sim schedules "
                               "56 for every team (the NCAA maximum), so only the cancellation rate is modeled (owner decision: no shortened schedules)",
                      "conf": "B", "seasons": seasons,
                      "cancel_rate": {"value": rates["all"], "se": round(float(np.sqrt(rates["all"] * (1 - rates["all"]) / len(T))), 4), "by_month": rates},
                      "scheduled_per_team": {str(s): round(float(x.sched.mean()), 2) for s, x in g},
                      "canceled_per_team": {str(s): round(float(x.canceled.mean()), 2) for s, x in g},
                      "played_per_team": {str(s): round(float(x.played.mean()), 2) for s, x in g},
                      "share_scheduling_56": {str(s): round(float((x.sched >= 56).mean()), 3) for s, x in g}}
    BENCH.write_text(json.dumps(bench, indent=1) + "\n")
    print(json.dumps(out["rate_by_month"]), json.dumps(bench["games"], indent=0)[:900])


if __name__ == "__main__":
    main()
