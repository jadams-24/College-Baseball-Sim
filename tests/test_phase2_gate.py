"""Phase 2 gate (player variance).

Uses the reports' own run of the fictional league (tests/conftest.py: 20 seasons, the
same seeds as scripts/run_phase5.py), so CI and reports/phase2.md always agree, and checks
every gate row of the realism report against benchmarks.json: Phase 1 league totals unchanged, the per-game run histogram,
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


import pytest

from agreement import assert_agrees


@pytest.fixture(scope="module")
def status(gate_run) -> dict:
    return gate_run["phase2"]


def test_committed_report_agrees(status) -> None:
    """reports/phase2.json is the committed run of the same seeds on another machine: each gated row's
    value agrees with this run's within sampling error (tests/agreement.py). This run's own verdicts are
    the gate tests below."""
    assert_agrees("phase2", status)


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
