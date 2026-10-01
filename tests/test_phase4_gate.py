"""Phase 4 gate (20-80 ratings).

Forward round trip on the reports' own run (tests/conftest.py): players generated from
ratings, 20 seasons; per rated rate, each qualifying player-season's opponent-adjusted
observed rate regressed on his true rate, logit scale (engine/report4.py): slope 1,
intercept 0 and dispersion 1 (residual variance equal to the predicted binomial variance
against the opponents faced), each within sampling error across folds; P4 everyday players
above 50 and low-tier below on every rate rating; every Phase 1 and Phase 2 gate row
unchanged on the same run. The scouting estimator (ratings from stats) is informational
and not tested here. Never xfail or widen these.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from config.phase4 import BATTER_RATINGS, PITCHER_RATINGS

RATINGS = [n for n, _, _ in BATTER_RATINGS + PITCHER_RATINGS] + ["stamina"]


@pytest.fixture(scope="module")
def status(gate_run) -> dict:
    return gate_run["phase4"]


def test_committed_report_matches(status: dict) -> None:
    committed = json.loads((Path(__file__).resolve().parents[1] / "reports/phase4.json").read_text())["status"]
    assert committed == status, "reports/phase4.md is stale: re-run scripts/run_phase5.py"


@pytest.mark.parametrize("rating", RATINGS)
def test_round_trip(status: dict, rating: str) -> None:
    failed = [k for k in (f"fw_{rating}_intercept", f"fw_{rating}_slope", f"fw_{rating}_dispersion") if not status[k]]
    assert not failed, f"{rating}: {failed} outside sampling error (see reports/phase4.md)"


def test_rating_distributions_by_tier(status: dict) -> None:
    failed = sorted(k for k, v in status.items() if k.startswith("dist_") and v is False)
    assert not failed, f"tier ordering of everyday players: {failed} (see reports/phase4.md)"


def test_phase1_and_phase2_rows_unchanged(gate_run) -> None:
    assert gate_run["phase4"]["phase2_gate"], "a Phase 1 or Phase 2 gate row fails on the Phase 4 engine (see reports/phase2.md)"
