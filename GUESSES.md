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
| `config/phase2.py` | `P_FIRST_TEAM_HOSTS` | 0.5 | Home site of nonconference series and midweek games is a coin flip; no home-field effect is modeled (real home win pct .588 is reported as a diagnostic). | Home-field model in Phase 6 |
| `config/phase2.py` | `MIN_HAZARD_N` | 30 | Batters faced needed before a pull-hazard cell is used instead of its coarser backoff. Statistical threshold. | Smoothed hazard model |
| `engine/manager.py` | pull beyond observed range | pull at 120+ pitches | Only reached when no hazard cell has data (pitch counts past the sample's maximum). | — |
| `engine/manager.py` | batting order | talent order (expected OBP + SLG, best first) | Manager behavior; affects how PA are spread across the nine starters. | Manager AI in Phase 6 |
| `engine/league.py` | rotation and bullpen ranks | ordered by K − BB − HR logit offsets | Best pitcher gets Friday and the most relief work. Real teams churn: the top three make 79% of weekend starts and teams use 6.5 weekend starters. | Rotation changes / fatigue in Phase 6 |
| `engine/league.py` | fixed roster roles | no injuries, demotions or role changes | Every weekend start goes to the same three pitchers, so too many pitchers reach 50 IP (see reports/phase2.md). | Phase 6 |
| `engine/league.py` | team-effect correlation | same matrix as individual correlation | Team batting (pitching) effects across rates are drawn with the individual correlation matrix; 50 full-season teams are too few to estimate a separate one. | All-D1 team tables |
| `engine/game2.py` | earned runs | unearned if the runner reached on an error or scored on a play with an error or passed ball | Approximates the scoring rule, which also reconstructs the inning without errors. Gives 90.9% earned against the data's 88.2%. | Inning reconstruction |
| `engine/game2.py` | no in-game substitutions | — | Starters bat all game; no pinch hitters or defensive changes, so fewer batters reach the 75%-of-games qualification line (6.6 vs 7.6 per team). | Manager AI in Phase 6 |
| `scripts/build_phase2_benchmarks.py` | `FULL_SEASON_GAMES`, `MIN_TEAM_GAMES`, `MIN_TRIALS` | 40, 25, 30 | Sample-selection thresholds for the variance estimates. Statistical choices. | — |

