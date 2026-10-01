"""One simulated run shared by the Phase 2 and Phase 4 gate tests: the reports' own run
(scripts/run_phase4.py: 20 seasons, seed 20251000), so CI and reports/phase2.md and
reports/phase4.md always agree."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


@pytest.fixture(scope="session")
def gate_run() -> dict:
    from run_phase2 import REPORT_SEASONS, REPORT_SEED
    from run_phase4 import run
    from engine.report2 import build_report
    from engine.report4 import build_report4
    agg2, agg4, seeds = run(REPORT_SEASONS, REPORT_SEED, workers=min(4, os.cpu_count() or 1))
    _, st2 = build_report(agg2, seeds)
    _, st4 = build_report4(agg4, seeds, st2)
    return {"phase2": st2, "phase4": st4}
