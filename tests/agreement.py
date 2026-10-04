"""CI's run against the committed report (owner decision 2026-10-04).

The simulation is deterministic per machine but not across machines: CPU-dependent floating point
changes the draws, so CI's run of the report's seeds is a second, independent sample of the same
model. Each gate test therefore checks two things: CI's own run passes the gate (the status tests),
and its numbers agree with the committed report's within sampling error, row by row
(config.phase2.CI_AGREEMENT_Z combined standard errors). Verdicts are not compared one for one: a row
near its tolerance can pass on one machine and fail on another.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def assert_agrees(phase: str, status) -> None:
    from config.phase2 import CI_AGREEMENT_Z
    committed = json.loads((ROOT / f"reports/{phase}.json").read_text())
    old, new = committed.get("values", {}), status.vals
    assert old, f"reports/{phase}.json has no recorded values: re-run scripts/run_phase5.py"
    missing = sorted(set(old) ^ set(new))
    assert not missing, f"reports/{phase}.json and this run record different rows {missing[:8]}: re-run scripts/run_phase5.py"
    bad = []
    for key, (v_old, se_old) in old.items():
        v_new, se_new = new[key]
        z = abs(v_new - v_old) / math.sqrt(se_old ** 2 + se_new ** 2)
        if z > CI_AGREEMENT_Z:
            bad.append(f"{key}: committed {v_old:.4g} vs CI {v_new:.4g} ({z:.1f} SE)")
    assert not bad, f"reports/{phase}.json disagrees with this run beyond sampling error: " + "; ".join(bad)
