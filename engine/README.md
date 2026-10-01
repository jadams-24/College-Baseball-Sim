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

## Phase 2 — player variance

| Module | Role |
|---|---|
| `league.py` | fictional D1 league: real conference count, sizes and tiers, invented names; 14 batters (9 regulars, 5 bench) and 13 pitchers (3 weekend starters, 2 midweek starters, 8 relievers) per team; true rates = league + intercept + group + tier + team + individual (logit scale) |
| `matchup.py` | odds-ratio (generalized log5) batter vs pitcher outcome probabilities |
| `schedule.py` | 56 games: 14 weeks of a Fri-Sun series plus a midweek game; 10 conference weekends; nonconference opponents by the real tier mix |
| `manager.py` | `Manager` Decider: lineup start shares by rank, rotation, pull hazards from the play-by-play, reliever choice by usage rank |
| `game2.py` | game with players: Phase 1 state machine, odds-ratio outcomes, pitch counts per PA from data, runners carry their responsible pitcher for earned runs |
| `season.py`, `report2.py` | full seasons, player and team lines, Phase 2 metrics and realism report |

Run: `python3 scripts/run_phase2.py --seasons 20` writes `reports/phase2.md`.
