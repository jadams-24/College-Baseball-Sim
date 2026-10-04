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
- **Phase 2 — Player variance.** Fictional players sampled from empirical distributions (true-talent shapes fitted by deconvolution, Gaussian copula on the real correlations) with realistic correlations; teams on one talent scale (tiers and conferences are distributions of team strength). *Gate:* league totals unchanged; the per-game run histogram (bins 0–14 and total variation); extra-innings frequency; home win pct and home run differential; the tier-vs-tier scoring matrix; team R/G and RA/G spread overall and by tier; qualified-player percentiles; full-population leaderboard extremes; national team leaders (best team BA and ERA, most team HR per game, teams under 4.00 ERA, within the 2024–2026 range; changed from single-season values on 2026-10-04); national individual leaders (HR leader and 30+ HR hitters at a 56-game equivalent, BA leader, top-5 HR per game, within the 2023–2026 range; the 48-HR record a hard ceiling). Gate tolerances combine the benchmark's sampling error with the sim's at the number of seasons run. (Run-rule frequency, the 15+ runs bin, the 50+ IP count, qualified K/9 p50/p90 and the P4-batting-vs-low-pitching cell moved to Phase 6 on 2026-10-01: see the deferred rows there.)
- **Phase 4 — 20–80 ratings layer.** Ratings map to rates, nothing more: Contact, Gap, Power, Eye, Avoid K (batters); Stuff, Control, Movement, Stamina (pitchers); Speed reserved for Phase 6. Ratings sit on percentiles of each rate's D1 distribution, all of D1 on one scale: 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles (10 points per true-talent SD for a Gaussian rate; changed from a linear map on 2026-10-02 when HR talent got its fitted shape). *Gate:* forward round trip, ratings → true rates → 20 seasons: per rated rate, each qualifying player-season's opponent-adjusted observed rate regressed on his true rate (logit scale): slope 1, intercept 0 and dispersion 1 (residual variance equal to the predicted binomial variance against the opponents faced), within sampling error, also reported by workload tercile; P4 everyday players above 50, low-tier below; every Phase 1 and Phase 2 gate row unchanged. (Changed from the reverse direction on 2026-10-01: the empirical-Bayes estimator of ratings from stats stays as an informational section, the future scouting estimator for Phase 9.)
- **Phase 3 — Handedness and platoon splits** (moved after Phase 4 on 2026-10-01: no handedness source is reachable from the cloud; it starts once `data/ncaa_2025/rosters/` holds bats/throws from `tools/fetch_rosters.py`). Batters and pitchers get a throwing/batting hand (switch hitters included) at real rates; matchup rates shift by real platoon splits on top of the Phase 2 odds-ratio interaction (built in Phase 2). *Gate:* league totals unchanged; same-hand vs opposite-hand splits (league and qualified-player spread) and handedness shares match real data.
- **Phase 5 — Pitch-by-pitch.** Built only on what the play-by-play has: ball, called strike, swinging strike, foul, in play, HBP by count (no pitch type, velocity or location). *Gate:* pitches per PA and their distribution; count reach; BA, K% and BB% after each count; first-pitch strike rate; foul rate with two strikes; pitches (mean, p10/p50/p90) and innings per start, weekend and midweek; every PA-level rate unchanged from Phases 3 and 4; all Phase 1, 2 and 4 rows on the same run.
- **Phase 6 — Fielding, parks, fatigue, bullpen, manager AI.** Done 2026-10-04 (everything that does not need handedness; the bullpen Decider keeps a hook for lefty specialists once Phase 3 lands). *Gate:* errors, steals, earned share, pitcher usage at a 56-game equivalent, the deferred rows below, tier-mean recovery of offense and run prevention, and every Phase 1, 2, 4 and 5 row on the same run. No generic per-game noise term: rows close only through the mechanisms that cause them. Mechanisms and data: PHASE0_NOTES, Phase 6.

  Deferred rows (moved from the Phase 2 and 5 gates on 2026-10-01), 20-season report of 2026-10-04:

  | Row | Sim | Target | Status and cause |
  |---|---|---|---|
  | Run-rule frequency | .121 | .152 ± .017 | Watch item "offense extremes compressed" (below) |
  | Runs per team-game, 15+ bin | .053 | .066 ± .011 | Same watch item |
  | Pitchers with 50+ IP (56-game equivalent) | 789 | 821 ± 42 | Pass: rest days, carried fatigue, availability, swingman relief and Thursday openers |
  | Qualified K/9 p50 / p90 | 8.32 / 11.33 | 7.88 ± .93 / 10.56 ± 1.31 | Pass |
  | Midweek starter pitch count p10 (Mon–Wed) | 21.6 | 23.0 ± 2.9 | Pass: a Mon–Wed pull table and the midweek starter's staff role |
  | P4 batting vs low pitching (R/G) | 9.55 | 9.82 ± 1.22 | Pass: the "mismatch interaction" was nonconference scheduling matched by strength within tier, now in the schedule (`scripts/build_phase6_schedule.py`); no gap interaction was needed |

  Earlier watch items, rechecked at this gate:
  - Elite run prevention: best team ERA 3.08 (2024–2026 range 3.06–3.78), 50+ IP pitchers with ERA under 2.00 4.7 (real 5), teams under 4.00 13.6 (6 / 12 / 12). Closed by the schedule matching.
  - Reliever workloads: closed. Most appearances 34.7 (real 37–39 in up to 72 games), 50th-most-used pitcher 28.1 (28–29), the IP leader is never a reliever.
  - Strikeout leader 138 (real 169–191): innings, not rate. Top pitchers' IP 71/61/51 against 75/65/53, inside tolerance; real leaders' teams play 57–72 games.
  - Qualified ERA #2 / #5: 1.76 / 2.11 against 1.97–2.01 / 2.07–2.16. Informational.

  **Watch item "offense extremes compressed"** (owner decision 2026-10-04), reported and not gated: the run rule and the 15+ bin (Phase 6 report) and qualified OBP p10 (.3249 against .3366 ± .0108, Phase 2 report).
  - Runs vary less from game to game around team strength: scoreboard dispersion 2.2 against 2.6, and within-game residual correlation .048 against .073.
  - That narrows game margins, the run tail and season team stats. Fit noise in team offense is .081 against .098.
  - Checked and ruled out: schedule strength faced by the top offenses, the park netting, the team draw, and the full game-to-game list in PHASE0_NOTES.
  - OBP p10 is a level shift (sim qualified OBP about .01 low across P4 and mid), not explained yet.
  - Candidates need data not in the repository: wind and park orientation, umpires.
- **Phase 7 — Season/world.** Schedule, conferences, RPI, tournaments. Next after Phase 6 unless `data/ncaa_2025/rosters/` has landed, in which case Phase 3 goes first.
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
