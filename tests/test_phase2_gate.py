"""Phase 2 gate (player variance).

Simulates PHASE2_GATE_SEASONS full seasons (default 4; the report uses 20) of the
fictional league and checks every gate row of the realism report against
benchmarks.json: Phase 1 league totals unchanged, the per-game run histogram,
extra-innings frequency, home win pct and home run differential, the tier-vs-tier
scoring matrix, team R/G and RA/G spread overall and by tier, qualified-player
percentiles and the full-population leaderboard extremes. Tolerances combine the
benchmark's with the sim's standard error at the number of seasons run (see
engine.report2). Rows the project owner moved to the Phase 6 gate
(config.phase2.DEFERRED_TO_PHASE6: run-rule frequency, the 15+ runs bin, 50+ IP
pitchers, qualified K/9 p50/p90, P4 batting vs low pitching) are reported, not
gated here. Never xfail or widen these.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from engine.report2 import build_report  # noqa: E402

SEASONS = int(os.environ.get("PHASE2_GATE_SEASONS", "4"))
SEED = 20252000


@pytest.fixture(scope="module")
def status() -> dict:
    from run_phase2 import run
    agg, seeds = run(SEASONS, SEED, workers=min(4, os.cpu_count() or 1))
    _, st = build_report(agg, seeds)
    return st


GROUPS = {
    "phase1_league_totals": lambda k: k.startswith("league_") or k in ("big_inning", "pa_half", "half_inning_run_dist"),
    "run_histogram": lambda k: k == "run_histogram",
    "extra_innings": lambda k: k == "extra_innings",
    "home_field": lambda k: k in ("home_win_pct", "home_run_diff"),
    "tier_matrix": lambda k: k.startswith("tier_"),
    "team_strength": lambda k: k.startswith("team_"),
    "qualified_percentiles": lambda k: k.startswith("q_"),
    "leaderboards": lambda k: k.startswith("lb_"),
}


@pytest.mark.parametrize("group", list(GROUPS))
def test_phase2_gate(status: dict, group: str) -> None:
    rows = {k: v for k, v in status.items() if GROUPS[group](k) and v is not None}
    assert rows, f"no gate rows for {group}"
    failed = sorted(k for k, v in rows.items() if not v)
    assert not failed, f"{group}: outside tolerance: {failed} (see reports/phase2.md)"
