"""tools/aggregate_rosters.py on synthetic rosters built from the committed play-by-play names
(fake hands, hometowns, classes and origins): every table is built, the name match recovers
the synthetic players, the platoon noise model fits fake (outcome-independent) hands, and the
name-leak check passes on the outputs and catches injected names (owner decision 2026-10-07)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import aggregate_rosters  # noqa: E402


def test_roster_aggregates_selftest():
    assert aggregate_rosters.selftest() == 0
