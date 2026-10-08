"""Phase 3 gate (handedness and platoon splits).

On the reports' own run (tests/conftest.py): left-handed pitchers by role; position players' bats and throwing hand by
position group; the tier-gradient check (left-handers by tier and role, batters' L share by tier: not fitted, no code path
reads tier to set a hand); platoon splits by the batter's side and the pitcher's hand, switch hitters, the platoon-advantage
share; the AI's pitching changes and pinch hitters by hand; every Phase 2, 4, 5, 6 and 7 gate on the same run.
Named watch items (engine/report3.WATCH3) are reported, not gated. Never xfail or widen these.
"""
from __future__ import annotations

import pytest

from agreement import assert_agrees

GROUPS = {
    "handedness_shares": lambda k: k.startswith(("p3_lhp_starter", "p3_lhp_reliever", "p3_throwsL_", "p3_bats_")),
    "tier_gradient_check": lambda k: k.startswith(("p3_lhp_tier_", "p3_batsL_tier_")),
    "platoon_splits": lambda k: k.startswith("p3_plat_"),
    "usage_by_hand": lambda k: k.startswith("p3_use_"),
    "earlier_phases_unchanged": lambda k: k in ("phase2_gate", "phase4_gate", "phase5_gate", "phase6_gate", "phase7_gate"),
}


@pytest.fixture(scope="module")
def status(gate_run) -> dict:
    return gate_run["phase3"]


def test_committed_report_agrees(status) -> None:
    """reports/phase3.json is the committed run of the same seeds on another machine: each gated row's value agrees with
    this run's within sampling error (tests/agreement.py)."""
    assert_agrees("phase3", status)


@pytest.mark.parametrize("group", list(GROUPS))
def test_phase3_gate(status: dict, group: str) -> None:
    rows = {k: v for k, v in status.items() if GROUPS[group](k) and v is not None}
    if group == "tier_gradient_check" and not rows:
        pytest.skip("every tier-gradient row is a watch item (engine/report3.WATCH3; owner rule 2026-10-08)")
    assert rows, f"no gate rows for {group}"
    failed = sorted(k for k, v in rows.items() if not v)
    assert not failed, f"{group}: outside tolerance: {failed} (see reports/phase3.md)"
