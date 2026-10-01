"""Phase 1 gate.

Runs the league-average PA engine for GATE_GAMES games and checks that the
league totals, the runs-per-half-inning distribution, the big-inning frequency
and PA per half-inning fall inside the tolerances in benchmarks.json. The
per-game run histogram, extra-innings and run-rule frequencies need team and
pitcher variance and are the Phase 2 gate (tests/test_phase2_gate.py). There is no engine yet, so the simulation tests skip with an
explicit reason; the benchmark-shape tests run regardless. Once engine/sim.py
exists the skip disappears and the gate is enforced. Never widen a tolerance here.

Engine contract (Phase 1, see CLAUDE.md):

    from engine.sim import simulate_league_average_games
    result = simulate_league_average_games(n_games=GATE_GAMES, seed=SEED)

`result` is a mapping with per-team-game rates and a run histogram:

    result["runs_per_team_game"]  float
    result["ba"], result["obp"], result["slg"]  float
    result["bb_pct"], result["k_pct"], result["hbp_pct"]  float, per PA
    result["hr_per_team_game"], result["sb_per_team_game"],
    result["sh_per_team_game"], result["sf_per_team_game"]  float
    result["half_inning_run_dist"]  list of 6 probabilities P(0)..P(4), P(5+) runs per half-inning
    result["big_inning_freq"]  float, share of half-innings with 3+ runs
    result["pa_per_half_inning"]  float
    result["run_histogram"], result["extra_innings_freq"], result["run_rule_freq"]  Phase 2 gate (tests/test_phase2_gate.py)
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

HALF_BINS = 6  # P(0)..P(4), P(5+) runs per half-inning


@pytest.fixture(scope="module")
def benchmarks() -> dict:
    with BENCHMARKS.open() as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def sim_result() -> dict:
    try:
        from engine.sim import simulate_league_average_games  # type: ignore
    except ImportError as exc:
        # No engine yet. Skip loudly rather than fail so CI on data-only PRs stays
        # green; the moment engine/sim.py exists these tests run for real.
        pytest.skip(
            "Phase 1 engine is not implemented: engine.sim.simulate_league_average_games "
            f"could not be imported ({exc}). Gate cannot be evaluated yet."
        )
    return simulate_league_average_games(n_games=GATE_GAMES, seed=SEED)


def test_benchmarks_file_is_well_formed(benchmarks: dict) -> None:
    assert benchmarks["_meta"]["reference_season"] == 2025
    totals = benchmarks["league_totals_2025"]
    for key in LEAGUE_TOTAL_KEYS:
        assert key in totals, f"league_totals_2025 is missing {key}"
        assert {"value", "tol"} <= set(totals[key]), f"{key} needs value and tol"


def test_half_inning_benchmark_is_populated(benchmarks: dict) -> None:
    hb = benchmarks["half_inning_2025"]
    assert len(hb["bins"]) == HALF_BINS and len(hb["bin_tol"]) == HALF_BINS
    assert abs(sum(hb["bins"]) - 1.0) < 1e-3
    assert hb["conf"] in {"A", "B"}


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


def test_half_inning_run_distribution_within_tolerance(benchmarks: dict, sim_result: dict) -> None:
    hb = benchmarks["half_inning_2025"]
    got = sim_result["half_inning_run_dist"]
    assert len(got) == HALF_BINS and abs(sum(got) - 1.0) < 1e-6
    misses = [f"P({i if i < 5 else '5+'}): sim {g:.4f} vs {b:.4f} ± {t}"
              for i, (g, b, t) in enumerate(zip(got, hb["bins"], hb["bin_tol"])) if abs(g - b) > t]
    assert not misses, "runs-per-half-inning bins outside tolerance:\n  " + "\n  ".join(misses)


def test_big_inning_frequency(benchmarks: dict, sim_result: dict) -> None:
    b = benchmarks["half_inning_2025"]["big_inning_freq"]
    assert abs(sim_result["big_inning_freq"] - b["value"]) <= b["tol"], f"sim {sim_result['big_inning_freq']:.4f} vs {b['value']} ± {b['tol']}"


def test_pa_per_half_inning(benchmarks: dict, sim_result: dict) -> None:
    b = benchmarks["half_inning_2025"]["pa_per_half_inning"]
    assert abs(sim_result["pa_per_half_inning"] - b["value"]) <= b["tol"], f"sim {sim_result['pa_per_half_inning']:.3f} vs {b['value']} ± {b['tol']}"
