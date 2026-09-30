# College Baseball Sim — project rules

Read this before doing anything. These rules exist because five previous attempts at this engine failed at realism. They are not suggestions.

## What this is
A college baseball simulation engine, built in phases. Long-term it becomes a full program-management game (OOTP-depth on-field sim + CFB-style roster building + facilities). Right now it is a statistical engine that must match real NCAA Division I numbers before anything else is built.

## The two rules
1. **Every sim run prints a realism report against `benchmarks.json`.** Nothing is tuned by watching box scores or by feel. If a number is off, the fix is traced to a rate or a model, not a fudge constant.
2. **Every constant lives in `config/`.** If a number in the code cannot be traced to an entry in `benchmarks.json` (or to a source noted in `PHASE0_NOTES.md`), it is a guess. Guesses are allowed but must be marked `# GUESS` and listed in `GUESSES.md`.

## Phase gates
Phases advance only when the gate passes. Do not build ahead of the current phase.

- **Phase 0 — Yardstick.** `benchmarks.json`. Done. Entries marked conf C or D are to be replaced with real data before Phase 1's gate.
- **Phase 1 — League-average PA engine.** One outcome table, base-out state machine with real runner-advancement tables, no players. *Gate:* 10,000 games; R/G, BA, OBP, SLG and the run-per-game histogram within tolerance.
- **Phase 2 — Player variance.** Fictional players sampled from empirical distributions with realistic correlations. *Gate:* leaderboard spreads match real percentiles; league totals unchanged.
- **Phase 3 — Batter-vs-pitcher.** Log5/odds-ratio interaction. *Gate:* league totals unchanged; good/bad pitchers move outcomes by realistic margins.
- **Phase 4 — 20–80 ratings layer.** Ratings map to rates, nothing more. *Gate:* round-trip ratings → season → recovered ratings.
- **Phase 5 — Pitch-by-pitch.** *Gate:* pitches/PA and count distributions match; PA-level totals unchanged from Phase 3.
- **Phase 6 — Fielding, parks, fatigue, bullpen, manager AI.** *Gate:* error, SB, pitcher-usage benchmarks.
- **Phase 7 — Season/world.** Schedule, conferences, RPI, tournaments.
- Phases 8–12 (roster rules, recruiting, development, program/facilities, UI) come later and are not to be started.

## Architecture constraints
- **The engine never makes a decision; it asks for one.** Every choice point (lineup, pitching change, steal, bunt, pinch hit, IBB) goes through a `Decider` interface. An AI manager answers it now; a human answers the same call later.
- **Deterministic given a seed.** Every game and season takes an RNG seed and reproduces exactly.
- **Engine is headless.** No UI code in the engine package. Reports are markdown/HTML written to `reports/`.
- **Data is committed.** Scraped NCAA tables and play-by-play go in `data/` and are committed, not re-fetched each session. Record the fetch date and source URL in `data/README.md`.

## Stack
- Python 3.11+, `numpy`, `pandas`, `pytest`. Add dependencies only when needed and pin them in `requirements.txt`.
- Tests in `tests/`. Each phase gate is a pytest test that loads `benchmarks.json` and fails outside tolerance. CI runs them on every push.

## Workflow
- Work on a branch, open a PR. The PR description includes the realism report for the current phase.
- Never edit `benchmarks.json` values without a new source and a note in `PHASE0_NOTES.md`.
- When a gate fails, report why before proposing a fix. Do not silently widen a tolerance.
