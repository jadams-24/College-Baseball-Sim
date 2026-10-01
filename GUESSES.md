# Guesses

Constants in `config/` or `engine/` that cannot be traced to a value in
`benchmarks.json` or to a source in `PHASE0_NOTES.md`. Each entry: where, what,
why it is a guess, and what would replace it. Everything else the engine uses is
a rate read from `benchmarks.json` or from `data/ncaa_2025/derived/engine_tables_2025.json`.

| Where | Constant | Value | Why a guess | Replace with |
|---|---|---|---|---|
| `config/phase1.py` | `MIN_CELL_N` | 30 | Minimum observations before a joint advancement cell is used instead of its fallback (pooled over outs, then independent per-runner marginals). A statistical threshold, not a baseball rate. | A proper shrinkage estimator across cells |
| `config/phase1.py` | `run_rule_margin`, `run_rule_after_inning` | 10, 7 | Taken from the *text* of `game_structure.run_rule` ("commonly 10 runs after 7 innings", conf C). Conferences differ; whether a given game is under the rule is drawn from the empirical share of 10-run games that ended early (`run_rule_freq.p_ended_early_given_margin_10plus_wmt`). | Per-conference rule table in Phase 7 |
| `config/phase1.py` | `extra_innings_placed_runner` | False | `game_structure.extra_innings_tiebreaker` says the runner-on-second rule is conference-optional and not universal; plain extra innings are used. Affects extra-inning length, not frequency. | Per-conference rule table in Phase 7 |
| `engine/game.py` | runner-collision rule | trailing runner stops one base short, or is out if that base is also taken | Only reachable through the independent per-runner marginal fallback (sparse cells); the joint tables never produce collisions. The run reports how often it fired. | Larger sample so no cell is sparse |
| `engine/game.py` | one base-running event per plate appearance | — | Steal attempts, wild pitches, passed balls, pickoffs and balks are drawn at most once before each PA at the empirical per-PA rate for the state. Real innings occasionally have two such events before one PA; the per-PA rate already counts them, so totals match but a few events land on the next PA. | Sequential event draws with a per-event hazard |
