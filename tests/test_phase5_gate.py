"""Phase 5 gate (pitch-by-pitch).

On the reports' own run (tests/conftest.py): pitches per PA and their distribution, count
reach, BA / K% / BB% after each count, first-pitch strike rate, foul rate with two strikes,
pitches (mean and percentiles) and innings per start, weekend and midweek, against the 2025
play-by-play (data/ncaa_2025/derived/phase5_pitch_2025.json); every PA-level league rate
unchanged from the Phase 4 run (reports/phase4_baseline.json); every Phase 1 and Phase 2 row and
the Phase 4 forward ratings test on the same run. Never xfail or widen these.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

GROUPS = {
    "pitches_per_pa": lambda k: k.startswith("p5_pitches_per_pa") or k.startswith("p5_pitches_dist"),
    "first_pitch_and_two_strike_fouls": lambda k: k in ("p5_first_pitch_strike", "p5_two_strike_foul_rate"),
    "count_reach": lambda k: k.startswith("p5_reach_"),
    "outcome_by_count": lambda k: "_after_" in k,
    "starts": lambda k: "per_start" in k,
    "pa_outcomes_unchanged": lambda k: k.startswith("pa_unchanged_"),
    "phase1_phase2_phase4_unchanged": lambda k: k in ("phase2_gate", "phase4_gate"),
}


@pytest.fixture(scope="module")
def status(gate_run) -> dict:
    return gate_run["phase5"]


def test_committed_report_matches(status: dict) -> None:
    committed = json.loads((Path(__file__).resolve().parents[1] / "reports/phase5.json").read_text())["status"]
    assert committed == status, "reports/phase5.md is stale: re-run scripts/run_phase5.py"


@pytest.mark.parametrize("group", list(GROUPS))
def test_phase5_gate(status: dict, group: str) -> None:
    rows = {k: v for k, v in status.items() if GROUPS[group](k) and v is not None}
    assert rows, f"no gate rows for {group}"
    failed = sorted(k for k, v in rows.items() if not v)
    assert not failed, f"{group}: outside tolerance: {failed} (see reports/phase5.md)"


def test_every_row_grouped(status: dict) -> None:
    loose = [k for k in status if not any(f(k) for f in GROUPS.values())]
    assert not loose, f"gate rows not in any test group: {loose}"
