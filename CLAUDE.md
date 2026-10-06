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
- **Phase 2 — Player variance.** Fictional players sampled from empirical distributions (true-talent shapes fitted by deconvolution, Gaussian copula on the real correlations) with realistic correlations; teams on one talent scale (tiers and conferences are distributions of team strength). *Gate:* league totals unchanged; the per-game run histogram (bins 0–14 and total variation); extra-innings frequency; home win pct and home run differential; the tier-vs-tier scoring matrix; team R/G and RA/G spread overall and by tier; qualified-player percentiles; full-population leaderboard extremes; national team leaders (best team BA and ERA, most team HR per game, within the 2024–2026 range; changed from single-season values on 2026-10-04; teams under 4.00 ERA became a watch item the same day, see Phase 6; on full seasons, postseason included, as the NCAA.com team pages count them, from 2026-10-05 once Phase 7 plays the postseason); national individual leaders (HR leader and 30+ HR hitters at a 56-game equivalent, BA leader, top-5 HR per game, within the 2023–2026 range; the 48-HR record a hard ceiling). Gate tolerances combine the benchmark's sampling error with the sim's at the number of seasons run (40 seasons for every gate from 2026-10-04 on; 20 before). (Run-rule frequency, the 15+ runs bin, the 50+ IP count, qualified K/9 p50/p90 and the P4-batting-vs-low-pitching cell moved to Phase 6 on 2026-10-01: see the deferred rows there.)
- **Phase 4 — 20–80 ratings layer.** Ratings map to rates, nothing more: Contact, Gap, Power, Eye, Avoid K (batters); Stuff, Control, Movement, Stamina (pitchers); Speed reserved for Phase 6. Ratings sit on percentiles of each rate's D1 distribution, all of D1 on one scale: 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles (10 points per true-talent SD for a Gaussian rate; changed from a linear map on 2026-10-02 when HR talent got its fitted shape). *Gate:* forward round trip, ratings → true rates → 20 seasons: per rated rate, each qualifying player-season's opponent-adjusted observed rate regressed on his true rate (logit scale): slope 1, intercept 0 and dispersion 1 (residual variance equal to the predicted binomial variance against the opponents faced), within sampling error, also reported by workload tercile; P4 everyday players above 50, low-tier below; every Phase 1 and Phase 2 gate row unchanged. (Changed from the reverse direction on 2026-10-01: the empirical-Bayes estimator of ratings from stats stays as an informational section, the future scouting estimator for Phase 9.)
- **Phase 3 — Handedness and platoon splits** (moved after Phase 4 on 2026-10-01: no handedness source is reachable from the cloud; it starts once `data/ncaa_2025/rosters/` holds bats/throws from `tools/fetch_rosters.py`). Batters and pitchers get a throwing/batting hand (switch hitters included) at real rates; matchup rates shift by real platoon splits on top of the Phase 2 odds-ratio interaction (built in Phase 2). *Gate:* league totals unchanged; same-hand vs opposite-hand splits (league and qualified-player spread) and handedness shares match real data.
- **Phase 5 — Pitch-by-pitch.** Built only on what the play-by-play has: ball, called strike, swinging strike, foul, in play, HBP by count (no pitch type, velocity or location). *Gate:* pitches per PA and their distribution; count reach; BA, K% and BB% after each count; first-pitch strike rate; foul rate with two strikes; pitches (mean, p10/p50/p90) and innings per start, weekend and midweek; every PA-level rate unchanged from Phases 3 and 4; all Phase 1, 2 and 4 rows on the same run.
- **Phase 6 — Fielding, parks, fatigue, bullpen, manager AI.** Done 2026-10-04 (everything that does not need handedness; the bullpen Decider keeps a hook for lefty specialists once Phase 3 lands). *Gate:* errors, steals, earned share, pitcher usage at a 56-game equivalent, the deferred rows below, tier-mean recovery of offense and run prevention, and every Phase 1, 2, 4 and 5 row on the same run. No generic per-game noise term: rows close only through the mechanisms that cause them. Mechanisms and data: PHASE0_NOTES, Phase 6.

  Deferred rows (moved from the Phase 2 and 5 gates on 2026-10-01), 40-season report of 2026-10-04:

  | Row | Sim | Target | Status and cause |
  |---|---|---|---|
  | Run-rule frequency | .121 | .152 ± .016 | Watch item "offense extremes compressed" (below) |
  | Runs per team-game, 15+ bin | .054 | .066 ± .010 | Same watch item |
  | Pitchers with 50+ IP (56-game equivalent) | 785 | 821 ± 32 | Watch item "top starters' innings" (below) |
  | Qualified K/9 p50 / p90 | 8.33 / 11.39 | 7.88 ± .92 / 10.56 ± 1.30 | Pass |
  | Midweek starter pitch count p10 (Mon–Wed) | 21.6 | 23.0 ± 2.9 | Pass: a Mon–Wed pull table and the midweek starter's staff role |
  | P4 batting vs low pitching (R/G) | 9.58 | 9.82 ± 1.11 | Pass: the "mismatch interaction" was nonconference scheduling matched by strength within tier, now in the schedule (`scripts/build_phase6_schedule.py`); no gap interaction was needed |

  The Phase 4 Contact slope fell to .976–.991 once Phase 6 fielding was on. The forward test's expectation now includes the defense faced (the fielding team's reached-on-error odds move outs to errors and back); at 40 seasons the slope is .994 ± .014. Ablations: PHASE0_NOTES, Phase 6.

  PA per team-game is gated against real data in the Phase 6 report (40.31 ± 1.0), not against the Phase 4 run: the per-opportunity base running (2026-10-04) has fewer caught-stealing and pickoff outs, so more plate appearances. Errors and earned share are gated the same way, because Phase 6 fielding moves them.

  A watch item is marked closed only when a 40-season run confirms it (owner decision 2026-10-04).

  Earlier watch items, rechecked on the 40-season run:
  - Elite run prevention: best team ERA 2.98 (2024–2026 range 3.06–3.78, passes on its pad of .13), 50+ IP pitchers with ERA under 2.00 5.1 (real 5). Closed. Teams under 4.00 ERA stays open as its own watch item (below).
  - Reliever workloads: closed. Most appearances 34.6 (real 37–39 in up to 72 games), 50th-most-used pitcher 28.2 (28–29), the IP leader is a reliever in 0 of 40 seasons.
  - Strikeout leader 138 (real 169–191): innings, not rate. Real leaders' teams play 57–72 games. Top pitchers' IP: see "top starters' innings".
  - Qualified ERA #2 / #5: 1.75 / 2.04 against 1.97–2.01 / 2.07–2.16. Informational.

  **Watch item "top starters' innings"** (owner decision 2026-10-04), reported and not gated, re-checked in Phase 7 once conference tournaments and the postseason change rotation usage: the 2nd pitcher's IP (60.7 against 65.3 ± 4.5) and pitchers with 50+ IP (785 against 821 ± 32). The #2 pitcher is short in Fri–Sun starts (46.3 against 50.3) and relief (6.9 against 9.3); the #1 and #3 rows pass (71.5 / 50.8 against 75.4 / 53.3).

  **Watch item "teams under 4.00 ERA"** (owner decision 2026-10-04), reported and not gated: 15.5 against the 2024–2026 band 6–12 ± 2.2. The drawn run-prevention tail reproduces the scoreboard fit's (top-25 order statistics within ±.7 SD of the model, top-12 mean .612 against .623), so the cause is downstream of the team draw. The unearned-run check (2026-10-05) is a lead, not a dismissal (owner): the sim's top-50-by-ERA teams have fewer unearned runs than real (.46 against .65 per game) and a higher earned share (.901 against .866). Phase 7 re-check, 40 seasons, full seasons (postseason included, same definition as NCAA.com): 13.8 teams (regular season 15.8). Pitching against fielding (NCAA.com 2025, every team): the correlation across teams of ERA with errors per game is .727 in the sim against .655 real; the 50 best teams by ERA make .757 errors per game against .912 real (all teams 1.088 against 1.150). The engine's error-on-run-prevention slope is confirmed on all of D1 (−.685 against −.720), so it is not a one-line cause. Open.

  **Watch item "offense extremes compressed"** (owner decision 2026-10-04; seven rows from 2026-10-05), reported and not gated: the run rule and the 15+ bin (Phase 6 report); qualified OBP p10 and team R/G SD across teams (all) (Phase 2 report); the P4-vs-mid nonconference margin SD, the postseason upset rate and the RPI of the team ranked 64 (Phase 7 report). It is the next task after the Phase 7 merge, before any new phase: a written diagnosis plan first, for owner approval.
  - Runs vary less from game to game around team strength: scoreboard dispersion 2.2 against 2.6, and within-game residual correlation .046 against .073 (40 seasons).
  - That narrows game margins, the run tail and season team stats. Fit noise in team offense is .081 against .098.
  - Checked and ruled out: schedule strength faced by the top offenses, the park netting, the team draw, and the full game-to-game list in PHASE0_NOTES.
  - OBP p10 is a level shift (sim qualified OBP about .01 low across P4 and mid), not explained yet.
  - Candidates need data not in the repository: wind and park orientation, umpires.
- **Phase 7 — Season/world.** Schedule length from the real distribution, cancellations, the 29 conference tournament formats, RPI, selection, the bracket, regionals, supers and the CWS. *Gate (40 seasons, PASS 2026-10-05):* RPI formula against the NCAA's published 2026 RPI; cancellations and games per team; win% spread by tier and the best record; RPI at ranks 1/16/32 and mean RPI by tier, at-large bids by tier, multi-bid conferences, worst at-large and best left-out RPI ranks (all on 2025–2026, the current conference map, with season-to-season variation in the tolerance); seed rates, CWS share by tier and postseason home field (2015–2025); conference tournaments won by the regular-season champion; the same-conference bracketing rule; every Phase 2, 4, 5 and 6 row on the same run. Selection: logistic on RPI z (+ P4 for at-large) with a measurement-error correction for the feed's RPI (national seeds validated against an exact-RPI refit; at-large a GUESS). Reported: RPI rank 64 (watch item "offense extremes compressed"), P4-vs-mid margins, the champion's tier. Details: PHASE0_NOTES, Phase 7.
- Phases 8–12 (roster rules, recruiting, development, program/facilities, UI) come later and are not to be started.

## Architecture constraints
- **The engine never makes a decision; it asks for one.** Every choice point (lineup, pitching change, steal, bunt, pinch hit, IBB) goes through a `Decider` interface. An AI manager answers it now; a human answers the same call later.
- **Deterministic given a seed, per machine.** Every game and season takes an RNG seed and reproduces exactly on the same machine. Across machines it does not: CPU-dependent floating point (linear algebra and vector math) changes the draws, so CI's run of the report seeds differs from the committed report. CI therefore checks that its own 40-season run passes every gate, and that each gated row's value agrees with the committed report within sampling error (`tests/agreement.py`, `config.phase2.CI_AGREEMENT_Z`), not verdict for verdict.
  - Watch item, to fix before Phase 12 (shared leagues and saves need it): make the simulation deterministic across machines.
- **In-game management and sim controls** (product requirement, owner decision 2026-10-06).
  - The user can manage a game pitch by pitch. Before any pitch they can call a steal, hit-and-run, bunt, pitchout, intentional ball or pitching change, or make a mound visit, pinch runner or defensive change. Example that must work: stealing on a 2-0 count.
  - The user can sim ahead at any moment: next at-bat, half inning, full inning, three innings or end of game. While simming, the AI manager makes the user's decisions, then hands control back at the stopping point.
  - Human and AI decisions resolve with the same outcome probabilities. The human gets no better or worse odds than the AI.
  - Steal success depends on count, runner speed, catcher arm and a pitcher hold/time-to-plate rating. There is no pitch-type model: the play-by-play has no pitch types, so one would be guesswork; fitting by count captures the real pitch mix in each count.
  - Pitch types are a possible future display layer that never changes outcomes, unless real pitch-type data becomes available. Pitch calling by the user is out of scope.
  - Steal attempts by the AI manager depend on game state (score, inning, outs, count), fitted from the play-by-play.
- **Engine is headless.** No UI code in the engine package. Reports are markdown/HTML written to `reports/`.
- **Data is committed.** Scraped NCAA tables and play-by-play go in `data/` and are committed, not re-fetched each session. Record the fetch date and source URL in `data/README.md`.

## Stack
- Python 3.11+, `numpy`, `pandas`, `pytest`. Add dependencies only when needed and pin them in `requirements.txt`.
- Tests in `tests/`. Each phase gate is a pytest test that loads `benchmarks.json` and fails outside tolerance. CI runs them on every push.

## Workflow
- Work on a branch, open a PR. The PR description includes the realism report for the current phase.
- Never edit `benchmarks.json` values without a new source and a note in `PHASE0_NOTES.md`.
- When a gate fails, report why before proposing a fix. Do not silently widen a tolerance.
