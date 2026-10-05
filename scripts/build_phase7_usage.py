"""Phase 7 tournament pitching: who starts a conference tournament or NCAA tournament game.

The same conditional logit as the Phase 6 midweek start (scripts/build_phase6_usage.py): at each start
the choice set is the team's whole staff in the engine's roles (weekend rotation wk1-wk3, midweek starters
mid1-mid2, relievers r1-r8), utility = role + rest state (days since the last appearance, split by that
outing's pitches for 1-3 days; pitched on both previous days). Roles come from the regular season
(games before TOURNAMENT_START), so tournament usage does not define them. Choices: every start on or
after TOURNAMENT_START (2025-05-20, the first day of conference tournament week) by the full-season
teams of the 2025 play-by-play.

Writes the "usage7" block of data/ncaa_2025/derived/phase7_inputs.json.

    python3 scripts/build_phase7_usage.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from build_phase6_usage import appearances, choice_data, fit_clogit, load, roles  # noqa: E402
from config.phase7 import INPUTS7, TOURNAMENT_START  # noqa: E402


def main() -> None:
    pa, meta, tier, full = load()
    a = appearances(pa)
    af = a[a.pit_team_id.isin(full)].copy()
    since = pd.Timestamp(TOURNAMENT_START)
    role = roles(af[af.d < since])
    ev = choice_data(af, role, "tournament", since=since)
    teams = af[af.d >= since].pit_team_id.nunique()
    out = {"_note": __doc__, "built": dt.date.today().isoformat(), "tournament_start": TOURNAMENT_START, "teams": int(teams),
           "start": fit_clogit(ev, "tournament")}
    cur = json.loads(INPUTS7.read_text()) if INPUTS7.exists() else {}
    cur["usage7"] = out
    INPUTS7.write_text(json.dumps(cur, indent=1, default=float) + "\n")
    print({n: f"{b:+.2f}±{out['start']['se'][n]:.2f}" for n, b in out["start"]["coef"].items()})


if __name__ == "__main__":
    main()
