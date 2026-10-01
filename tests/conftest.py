"""One simulated run shared by the Phase 2, Phase 4 and Phase 5 gate tests: the reports' own run
(scripts/run_phase5.py: 20 seasons, seed 20251000), so CI and reports/phase2.md, phase4.md and
phase5.md always agree."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


@pytest.fixture(scope="session")
def gate_run() -> dict:
    from run_phase2 import REPORT_SEASONS, REPORT_SEED
    from run_phase5 import reports, run
    agg2, agg4, agg5, seeds = run(REPORT_SEASONS, REPORT_SEED, workers=min(4, os.cpu_count() or 1))
    (_, st2), (_, st4), (_, st5) = reports(agg2, agg4, agg5, seeds)
    return {"phase2": st2, "phase4": st4, "phase5": st5}
