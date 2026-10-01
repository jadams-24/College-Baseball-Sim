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
- **Phase 1 — League-average PA engine.** One outcome table, base-out state machine with real runner-advancement tables, no players. *Gate:* 10,000 games; R/G, BA, OBP, SLG, the runs-per-half-inning distribution, big-inning frequency and PA per half-inning within tolerance. (The per-game run histogram was moved to Phase 2 on 2026-10-01: identical teams cannot reproduce its tails.)
- **Phase 2 — Player variance.** Fictional players sampled from empirical distributions with realistic correlations; teams on one talent scale (tiers and conferences are distributions of team strength). *Gate:* league totals unchanged; the per-game run histogram (bins 0–14 and total variation); extra-innings frequency; home win pct and home run differential; the tier-vs-tier scoring matrix; team R/G and RA/G spread overall and by tier; qualified-player percentiles; full-population leaderboard extremes. Gate tolerances combine the benchmark's sampling error with the sim's at the number of seasons run. (Run-rule frequency, the 15+ runs bin, the 50+ IP count, qualified K/9 p50/p90 and the P4-batting-vs-low-pitching cell moved to Phase 6 on 2026-10-01: see the deferred rows there.)
- **Phase 4 — 20–80 ratings layer.** Ratings map to rates, nothing more: Contact, Gap, Power, Eye, Avoid K (batters); Stuff, Control, Movement, Stamina (pitchers); Speed reserved for Phase 6. 50 is the D1 average and 10 points one true-talent SD, all of D1 on one scale. *Gate:* round-trip ratings → 20 seasons → ratings estimated from the season stats with the same noise removal: per rating, calibration slope 1, bias 0 and residual SD equal to the estimator's predicted SD, within sampling error; P4 everyday players above 50, low-tier below; every Phase 1 and Phase 2 gate row unchanged.
- **Phase 3 — Handedness and platoon splits** (moved after Phase 4 on 2026-10-01: no handedness source is reachable from the cloud; it starts once `data/ncaa_2025/rosters/` holds bats/throws from `tools/fetch_rosters.py`). Batters and pitchers get a throwing/batting hand (switch hitters included) at real rates; matchup rates shift by real platoon splits on top of the Phase 2 odds-ratio interaction (built in Phase 2). *Gate:* league totals unchanged; same-hand vs opposite-hand splits (league and qualified-player spread) and handedness shares match real data.
- **Phase 5 — Pitch-by-pitch.** *Gate:* pitches/PA and count distributions match; PA-level totals unchanged from Phases 3 and 4.
- **Phase 6 — Fielding, parks, fatigue, bullpen, manager AI.** *Gate:* error, SB, pitcher-usage benchmarks, and the deferred rows below. No generic per-game noise term: these rows close only through the mechanisms that cause them.

  Deferred rows (moved from the Phase 2 gate on 2026-10-01; current values from the 20-season Phase 2 report):

  | Row | Current | Target | Diagnosed cause |
  |---|---|---|---|
  | Run-rule frequency | .129 | .152 ± .017 | Too little game-to-game variance given the teams: dispersion of runs around the team-strength fit 2.17 sim vs 2.62 real. About a quarter is shared by both teams in a game (residual correlation .032 sim vs .073 real: parks, weather); the rest is one team's game (bullpen availability, lineup changes, blowout substitutions). |
  | Runs per team-game, 15+ bin | .053 | .066 ± .010 | Same as the run-rule row. |
  | Pitchers with 50+ IP | 769 | 882 ± 31 | Too few innings reach a team's top pitchers (67/58/50 vs 77/67/54 IP). Real top three get 9.8/6.0/5.5 IP from starts outside Fri–Sun series and 4.3/9.4/19.4 IP in relief; the sim's starters only start and every series is Fri–Sun. Needs swingman relief and Thursday openers, with rest days and fatigue. Inputs: `usage_2025.pitcher_ip_split_by_team_rank`, `pitcher_starts_by_team_rank`, `weekend_series_rank_patterns`. |
  | Qualified K/9 p50 / p90 | 8.67 / 11.77 | 7.66 ± .78 / 10.54 ± 1.19 | Same cause: 1.7 qualified pitchers per team vs 2.3, all aces, and staffs are ordered by K − BB − HR. |
  | P4 batting vs low pitching (R/G) | 10.88 | 9.82 ± 1.21 | Mismatch interaction: in real P4–low games both sides score 7–11% below what team strengths predict (P4 9.82 vs 10.50 fitted; low 3.63 vs 4.07). The run rule covers part; the rest needs reserves in mismatches and blowouts (manager AI). |

  Watch item, recheck at the Phase 6 gate. The Phase 2 sim has slightly too much elite run prevention at the very top. All four rows pass, but they lean the same way (20-season report, 2026-10-01):

  | Row | Sim | Real |
  |---|---|---|
  | Best team ERA | 2.93 | 3.20 |
  | 50+ IP pitchers with ERA < 2.00 | 8.7 | 5 |
  | 50+ IP pitchers with ERA < 3.00 | 62.8 | 57 |
  | Teams with ERA < 4.00 | 16.6 | 12 |

  Diagnosed so far: a convex game-level response to run prevention (fixed by the one-scale quadratic map; it cut the lean). What remains is the single best team: recovered rating .80 sim vs .71 real; top 5% now matches. Candidate causes are a Gaussian tail in the team draw, and the missing game-to-game variance (deferred rows above), which would add noise to the best teams' season ERAs.
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
