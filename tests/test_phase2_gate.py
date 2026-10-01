"""Phase 2 gate (player variance). Moved here from Phase 1 on 2026-10-01: the
per-game run histogram, extra-innings frequency and run-rule frequency depend on
team and pitcher variance that a league-average engine cannot carry. These tests
skip until a Phase 2 engine (engine.players) exists; never xfail or widen them.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE_GAMES = 10_000
SEED = 20250202
HISTOGRAM_BINS = 16


@pytest.fixture(scope="module")
def benchmarks() -> dict:
    return json.loads((ROOT / "benchmarks.json").read_text())


@pytest.fixture(scope="module")
def sim_result() -> dict:
    try:
        from engine.players import simulate_phase2_games  # type: ignore
    except ImportError as exc:
        pytest.skip(f"Phase 2 engine not implemented ({exc}); the per-game run histogram needs team and pitcher variance.")
    return simulate_phase2_games(n_games=GATE_GAMES, seed=SEED)


def test_run_histogram_within_tolerance(benchmarks: dict, sim_result: dict) -> None:
    hist = benchmarks["game_structure"]["run_distribution_per_team_game"]
    got, bins, tol = sim_result["run_histogram"], hist["bins"], hist["tol_per_bin"]
    assert len(got) == HISTOGRAM_BINS and abs(sum(got) - 1.0) < 1e-6
    misses = [f"P({i if i < 15 else '15+'}): sim {g:.4f} vs {b:.4f} ± {tol}" for i, (g, b) in enumerate(zip(got, bins)) if abs(g - b) > tol]
    assert not misses, "run histogram bins outside tolerance:\n  " + "\n  ".join(misses)
    tvd = 0.5 * sum(abs(g - b) for g, b in zip(got, bins))
    assert tvd <= hist["tol_total_variation"]


def test_extra_innings_frequency(benchmarks: dict, sim_result: dict) -> None:
    b = benchmarks["game_structure"]["extra_innings_freq"]
    assert abs(sim_result["extra_innings_freq"] - b["value"]) <= b["tol"]


def test_run_rule_frequency(benchmarks: dict, sim_result: dict) -> None:
    b = benchmarks["game_structure"]["run_rule_freq"]
    assert abs(sim_result["run_rule_freq"] - b["value"]) <= b.get("tol", 0.02)
