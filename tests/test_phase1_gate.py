"""Phase 1 gate.

Runs the league-average PA engine for GATE_GAMES games and checks that the
league totals and the runs-per-team-game histogram fall inside the tolerances in
benchmarks.json. There is no engine yet, so every test here fails. That is the
expected state until Phase 1 is built; do not skip or xfail these.

Engine contract (Phase 1, see CLAUDE.md):

    from engine.sim import simulate_league_average_games
    result = simulate_league_average_games(n_games=GATE_GAMES, seed=SEED)

`result` is a mapping with per-team-game rates and a run histogram:

    result["runs_per_team_game"]  float
    result["ba"], result["obp"], result["slg"]  float
    result["bb_pct"], result["k_pct"], result["hbp_pct"]  float, per PA
    result["hr_per_team_game"], result["sb_per_team_game"],
    result["sh_per_team_game"], result["sf_per_team_game"]  float
    result["run_histogram"]  list of 16 probabilities P(0)..P(14), P(15+); sums to 1
    result["extra_innings_freq"]  float, share of games past 9 innings
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "benchmarks.json"
GATE_GAMES = 10_000
SEED = 20250101

# Keys in league_totals_2025 that the Phase 1 engine must reproduce, mapped to
# the key the engine reports them under.
LEAGUE_TOTAL_KEYS = {
    "runs_per_team_game": "runs_per_team_game",
    "ba": "ba",
    "obp": "obp",
    "slg": "slg",
    "bb_pct": "bb_pct",
    "k_pct": "k_pct",
    "hbp_pct": "hbp_pct",
    "hr_per_team_game": "hr_per_team_game",
    "sb_per_team_game": "sb_per_team_game",
    "sh_per_team_game": "sh_per_team_game",
    "sf_per_team_game": "sf_per_team_game",
}

# Fallbacks only; benchmarks.json carries tol_per_bin and tol_total_variation.
DEFAULT_BIN_TOL = 0.01
MAX_TOTAL_VARIATION = 0.04
HISTOGRAM_BINS = 16  # P(0) .. P(14), P(15+)


@pytest.fixture(scope="module")
def benchmarks() -> dict:
    with BENCHMARKS.open() as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def sim_result() -> dict:
    try:
        from engine.sim import simulate_league_average_games  # type: ignore
    except ImportError as exc:
        pytest.fail(
            "Phase 1 engine is not implemented: engine.sim.simulate_league_average_games "
            f"could not be imported ({exc}). This gate is expected to fail until Phase 1 is built."
        )
    return simulate_league_average_games(n_games=GATE_GAMES, seed=SEED)


def test_benchmarks_file_is_well_formed(benchmarks: dict) -> None:
    assert benchmarks["_meta"]["reference_season"] == 2025
    totals = benchmarks["league_totals_2025"]
    for key in LEAGUE_TOTAL_KEYS:
        assert key in totals, f"league_totals_2025 is missing {key}"
        assert {"value", "tol"} <= set(totals[key]), f"{key} needs value and tol"


def test_run_histogram_benchmark_is_populated(benchmarks: dict) -> None:
    """The gate cannot be evaluated until the Phase 1 data pull fills this in."""
    hist = benchmarks["game_structure"]["run_distribution_per_team_game"]
    bins = hist.get("bins")
    assert bins is not None, (
        "game_structure.run_distribution_per_team_game has no 'bins'. It is still the "
        "conf D placeholder; the Phase 1 data pull must compute P(0)..P(15+) from PBP."
    )
    assert len(bins) == HISTOGRAM_BINS
    assert abs(sum(bins) - 1.0) < 1e-3
    assert hist.get("conf") in {"A", "B"}, "histogram must come from real PBP, not a placeholder"


@pytest.mark.parametrize("bench_key,sim_key", sorted(LEAGUE_TOTAL_KEYS.items()))
def test_league_total_within_tolerance(
    benchmarks: dict, sim_result: dict, bench_key: str, sim_key: str
) -> None:
    target = benchmarks["league_totals_2025"][bench_key]
    got = sim_result[sim_key]
    assert abs(got - target["value"]) <= target["tol"], (
        f"{bench_key}: sim {got:.4f} vs benchmark {target['value']} ± {target['tol']} "
        f"(conf {target.get('conf', '?')})"
    )


def test_run_histogram_within_tolerance(benchmarks: dict, sim_result: dict) -> None:
    hist = benchmarks["game_structure"]["run_distribution_per_team_game"]
    bins = hist.get("bins")
    assert bins is not None, "benchmark histogram not populated; see test_run_histogram_benchmark_is_populated"
    got = sim_result["run_histogram"]
    assert len(got) == HISTOGRAM_BINS
    assert abs(sum(got) - 1.0) < 1e-6

    tol = hist.get("tol_per_bin", DEFAULT_BIN_TOL)
    tols = hist.get("bin_tol") or [tol] * HISTOGRAM_BINS
    misses = [
        f"P({i if i < 15 else '15+'}): sim {g:.4f} vs {b:.4f} ± {t}"
        for i, (g, b, t) in enumerate(zip(got, bins, tols))
        if abs(g - b) > t
    ]
    assert not misses, "run histogram bins outside tolerance:\n  " + "\n  ".join(misses)

    max_tvd = hist.get("tol_total_variation", MAX_TOTAL_VARIATION)
    tvd = 0.5 * sum(abs(g - b) for g, b in zip(got, bins))
    assert tvd <= max_tvd, f"total variation distance {tvd:.4f} > {max_tvd}"


def test_extra_innings_frequency(benchmarks: dict, sim_result: dict) -> None:
    bench = benchmarks["game_structure"]["extra_innings_freq"]
    assert bench.get("conf") in {"A", "B"}, "extra_innings_freq is still a placeholder (conf D)"
    tol = bench.get("tol", 0.015)
    assert abs(sim_result["extra_innings_freq"] - bench["value"]) <= tol
