"""Phase 6 gate (fielding, parks, fatigue, bullpen, manager AI).

On the reports' own run (tests/conftest.py): errors per team-game, stolen bases and steal success;
pitcher usage at a 56-game equivalent (appearances of the busiest, 5th and 10th busiest pitchers,
relief-only pitchers with 40+ and 60+ IP, the top three pitchers' innings) and distinct batters per
team-game; earned share of runs; the rows deferred from Phases 2 and 5 (qualified K/9 p50 and p90,
midweek starter p10, P4 batting vs low pitching); each tier's recovered mean offense
and run prevention against the drawn ratings; the bullpen form rows (the next relief entry's blowout share and margin per
run allowed last outing, runs per batter faced by workload third; P4 staffs); every Phase 1, 2, 4 and 5 gate on the same run.
Named watch items, reported but not gated (engine/report6.WATCH6): the run rule and the 15+ runs bin
("offense extremes compressed"), the 2nd pitcher's IP and pitchers with 50+ IP ("top starters'
innings", re-checked in Phase 7). Never xfail or widen these.
"""
from __future__ import annotations


import pytest

from agreement import assert_agrees

GROUPS = {
    "fielding_and_base_running": lambda k: k in ("p6_errors_per_team_game", "p6_sb_per_team_game", "p6_sb_success_rate", "p6_earned_share",
                                                    "p6_pa_per_team_game"),
    "pitcher_usage": lambda k: k.startswith("p6_app_") or k.startswith("p6_relief_only") or k.startswith("p6_ip_rank") or k == "p6_batters_per_team_game",
    "deferred_rows": lambda k: k in ("p6_run_rule", "p6_run_histogram_15plus", "p6_q_K9_p50", "p6_q_K9_p90", "p6_tier_p4_low", "p6_midweek_p10",
                                     "p6_pitchers_50ip"),
    "team_strength_recovery": lambda k: k.startswith("p6_rec_"),
    "bullpen_form": lambda k: k.startswith("bp_"),
    "phases_1_to_5_unchanged": lambda k: k in ("phase2_gate", "phase4_gate", "phase5_gate"),
}


@pytest.fixture(scope="module")
def status(gate_run) -> dict:
    return gate_run["phase6"]


def test_committed_report_agrees(status) -> None:
    """reports/phase6.json is the committed run of the same seeds on another machine: each gated row's
    value agrees with this run's within sampling error (tests/agreement.py). This run's own verdicts are
    the gate tests below."""
    assert_agrees("phase6", status)


@pytest.mark.parametrize("group", list(GROUPS))
def test_phase6_gate(status: dict, group: str) -> None:
    rows = {k: v for k, v in status.items() if GROUPS[group](k) and v is not None}
    assert rows, f"no gate rows for {group}"
    failed = sorted(k for k, v in rows.items() if not v)
    assert not failed, f"{group}: outside tolerance: {failed} (see reports/phase6.md)"
