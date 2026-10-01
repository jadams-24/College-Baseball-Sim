# engine/ — Phase 1: league-average plate-appearance engine

Headless, deterministic given a seed, no players. Every plate appearance draws its
result from the single outcome table (`benchmarks.json: pa_outcome_table_league_avg`);
a base-out state machine then moves runners with the empirical joint advancement
tables built from the 2025 WMT play-by-play (`data/ncaa_2025/derived/engine_tables_2025.json`).
Stolen-base attempts, wild pitches, passed balls, pickoffs and balks are drawn before
each plate appearance at the empirical per-PA rate for the base-out state.

| Module | Role |
|---|---|
| `rng.py` | master seed → one independent stream per game; fixed-order categorical sampler |
| `decider.py` | `Decider` interface: steal, bunt, intentional walk, pitching change, pinch hitter, lineup. `LeagueAverageDecider` answers "league rate" or "no action". The engine never decides. |
| `state.py` | `GameState` (inning, half, outs, bases, score) and `TeamTally` |
| `tables.py` | samplers over the config tables: outcome table with state-conditioned in-play subtype (plain out / SF / SH / FC), joint advancement with pooled and marginal fallbacks, pre-PA events |
| `game.py` | one game: half-innings, walk-offs, extra innings, run rule |
| `sim.py` | `simulate_league_average_games(n_games, seed)` → aggregates the gate and report need |
| `report.py` | realism report against `benchmarks.json` |

Run: `python3 scripts/run_phase1.py --games 10000 --seed 20250101` writes `reports/phase1.md`.
No numeric rate lives in this package; `tests/test_engine_phase1.py` enforces it.
Constants are in `config/phase1.py`; the few that are not benchmark values are in `GUESSES.md`.
