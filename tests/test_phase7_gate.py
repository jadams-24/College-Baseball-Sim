"""Phase 7 gate (season and world).

On the reports' own run (tests/conftest.py): the RPI formula against the NCAA's published pre-selection RPI
(2026); the cancellation rate and games played per team; win% spread by tier and the best record; the RPI
distribution; the field
(at-large bids by tier, multi-bid conferences, worst RPI rank given an at-large bid, best left out); seed
rates (hosts winning regionals, national seeds reaching Omaha, CWS slots by tier); postseason home field;
conference tournaments won by the regular-season champion; the NCAA's same-conference bracketing rule; every
Phase 1, 2, 4, 5 and 6 gate on the same run. The field, RPI distribution and tier win% spreads are benchmarked on
2025-2026 (the current conference map) with season-to-season variation in the tolerance. Reported, not gated:
the scheduled-games distribution, P4 vs mid margins, the RPI of the teams ranked 32 and 64 (watch item "offense
extremes compressed", 2026-10-05 and 2026-10-07), the champion's tier and the watch-item re-checks. Never xfail or widen
these.
"""
from __future__ import annotations

import pytest

from agreement import assert_agrees

GROUPS = {
    "rpi": lambda k: k.startswith("p7_rpi") or k.startswith("p7_mean_rpi"),
    "season_and_standings": lambda k: k in ("p7_cancel_rate", "p7_games_per_team", "p7_best_win_pct") or k.startswith("p7_win_pct_sd"),
    "field": lambda k: k.startswith("p7_at_large") or k in ("p7_conferences_multi_bid", "p7_worst_rpi_rank_at_large", "p7_best_rpi_rank_left_out"),
    "seeds_and_results": lambda k: k in ("p7_host_wins_regional", "p7_top8_in_cws", "p7_top16_in_cws") or k.startswith("p7_cws_"),
    "postseason_home_field": lambda k: k.startswith("p7_hf_"),
    "conference_tournaments_and_bracketing": lambda k: k in ("p7_conf_champ_rs", "p7_same_conf_rule"),
    "phases_1_to_6_unchanged": lambda k: k in ("phase2_gate", "phase4_gate", "phase5_gate", "phase6_gate"),
}


@pytest.fixture(scope="module")
def status(gate_run) -> dict:
    return gate_run["phase7"]


def test_committed_report_agrees(status) -> None:
    """reports/phase7.json is the committed run of the same seeds on another machine: each gated row's
    value agrees with this run's within sampling error (tests/agreement.py)."""
    assert_agrees("phase7", status)


@pytest.mark.parametrize("group", list(GROUPS))
def test_phase7_gate(status: dict, group: str) -> None:
    rows = {k: v for k, v in status.items() if GROUPS[group](k) and v is not None}
    assert rows, f"no gate rows for {group}"
    failed = sorted(k for k, v in rows.items() if not v)
    assert not failed, f"{group}: outside tolerance: {failed} (see reports/phase7.md)"
