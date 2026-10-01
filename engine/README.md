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
| `league.py` | fictional D1 league: real conference count, sizes and tiers, invented names; 14 batters (9 regulars, 5 bench) and 13 pitchers (3 weekend starters, 2 midweek starters, 8 relievers) per team. One talent scale: each team draws (o, d), offense and run prevention in log runs, as tier mean + conference effect + team effect from the scoreboard decomposition; o and d become rate offsets along the engine's quality directions, plus a style term with no run value; players are drawn around their team. Nothing in a matchup knows a team's tier. |
| `matchup.py` | odds-ratio (generalized log5) batter vs pitcher outcome probabilities |
| `schedule.py` | 56 games: 14 weeks of a Fri-Sun series plus a midweek game; 10 conference weekends (round robin); nonconference pairs drawn from the real joint tier-pair mix; host drawn from the scoreboard hosting model (tier pair and strength gap) |
| `manager.py` | `Manager` Decider: lineup start shares by rank; weekend starters from real three-game rank patterns (rotation churn), midweek starters alternate; pull hazards from the play-by-play, with a rotation-rank leash for weekend starters; reliever choice by usage rank |
| `game2.py` | game with players: Phase 1 state machine, odds-ratio outcomes, home edge, pitch counts per PA from data; earned runs by reconstructing the inning (phantom outs, reliever rule, fielder's-choice responsibility) |
| `season.py`, `report2.py` | full seasons, player and team lines, Phase 2 metrics and realism report |

Run: `python3 scripts/run_phase2.py --seasons 20` writes `reports/phase2.md`.

Derived inputs are rebuilt in this order: `build_phase2_benchmarks.py`, `build_phase2_gate.py`,
`build_phase2_teams.py`, `build_phase2_run_scale.py`, `solve_phase2_game_scale.py`,
`solve_phase2_location.py`, `write_phase2_benchmarks.py`.

## Phase 4 — 20-80 ratings

| Module | Role |
|---|---|
| `ratings.py` | `RatingScale`: rating = 50 + 10 sign (z - m) / s for each rated rate (m, s: D1 PA/BF-weighted mean and true SD); `compose` rebuilds the true offsets from ratings plus hidden components; Stamina maps to the leash multiplier |
| `league.py` | players are generated as ratings: draw the Phase 2 true offsets, express them as ratings (exact, no change in any rate); pitchers draw a Stamina from the role's leash distribution |
| `manager.py` | the pull hazard of each pitcher is 1 - (1 - h)^theta, theta from Stamina; records each pitcher's pull decisions and expected pulls |
| `eb.py` | empirical Bayes on a grid: binomial, opponent-mixture binomial and hazard likelihoods; prior by marginal maximum likelihood |
| `report4.py` | the round trip. Gate (forward): each qualifying player-season's observed rate against his true rate, logit scale, using the exact expected count and binomial variance against the opponents faced (recorded by `game2.py`): slope, intercept, dispersion, by workload tercile; Stamina from the pull decisions. Also the distribution by tier and example player cards. Informational: the scouting estimator (empirical Bayes from box-score stats, Phase 9) |

Run: `python3 scripts/run_phase4.py` simulates the report's 20 seasons once and writes `reports/phase2.md` and `reports/phase4.md`.
Derived inputs: `build_phase4_inputs.py`, `build_phase4_scale.py`, `write_phase4_benchmarks.py`.
