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
- **Phase 2 — Player variance.** Fictional players sampled from empirical distributions (true-talent shapes fitted by deconvolution, Gaussian copula on the real correlations) with realistic correlations; teams on one talent scale (tiers and conferences are distributions of team strength). *Gate:* league totals unchanged; the per-game run histogram (bins 0–14 and total variation); extra-innings frequency; home win pct and home run differential; the tier-vs-tier scoring matrix; team R/G and RA/G spread overall and by tier; qualified-player percentiles; full-population leaderboard extremes; national individual leaders (HR leader and 30+ HR hitters at a 56-game equivalent, BA leader, top-5 HR per game, within the 2023–2026 range; the 48-HR record a hard ceiling). Gate tolerances combine the benchmark's sampling error with the sim's at the number of seasons run. (Run-rule frequency, the 15+ runs bin, the 50+ IP count, qualified K/9 p50/p90 and the P4-batting-vs-low-pitching cell moved to Phase 6 on 2026-10-01: see the deferred rows there.)
- **Phase 4 — 20–80 ratings layer.** Ratings map to rates, nothing more: Contact, Gap, Power, Eye, Avoid K (batters); Stuff, Control, Movement, Stamina (pitchers); Speed reserved for Phase 6. Ratings sit on percentiles of each rate's D1 distribution, all of D1 on one scale: 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles (10 points per true-talent SD for a Gaussian rate; changed from a linear map on 2026-10-02 when HR talent got its fitted shape). *Gate:* forward round trip, ratings → true rates → 20 seasons: per rated rate, each qualifying player-season's opponent-adjusted observed rate regressed on his true rate (logit scale): slope 1, intercept 0 and dispersion 1 (residual variance equal to the predicted binomial variance against the opponents faced), within sampling error, also reported by workload tercile; P4 everyday players above 50, low-tier below; every Phase 1 and Phase 2 gate row unchanged. (Changed from the reverse direction on 2026-10-01: the empirical-Bayes estimator of ratings from stats stays as an informational section, the future scouting estimator for Phase 9.)
- **Phase 3 — Handedness and platoon splits** (moved after Phase 4 on 2026-10-01: no handedness source is reachable from the cloud; it starts once `data/ncaa_2025/rosters/` holds bats/throws from `tools/fetch_rosters.py`). Batters and pitchers get a throwing/batting hand (switch hitters included) at real rates; matchup rates shift by real platoon splits on top of the Phase 2 odds-ratio interaction (built in Phase 2). *Gate:* league totals unchanged; same-hand vs opposite-hand splits (league and qualified-player spread) and handedness shares match real data.
- **Phase 5 — Pitch-by-pitch.** Built only on what the play-by-play has: ball, called strike, swinging strike, foul, in play, HBP by count (no pitch type, velocity or location). *Gate:* pitches per PA and their distribution; count reach; BA, K% and BB% after each count; first-pitch strike rate; foul rate with two strikes; pitches (mean, p10/p50/p90) and innings per start, weekend and midweek; every PA-level rate unchanged from Phases 3 and 4; all Phase 1, 2 and 4 rows on the same run.
- **Phase 6 — Fielding, parks, fatigue, bullpen, manager AI.** *Gate:* error, SB, pitcher-usage benchmarks, and the deferred rows below. No generic per-game noise term: these rows close only through the mechanisms that cause them.

  Deferred rows (moved from the Phase 2 gate on 2026-10-01; current values from the 20-season Phase 2 report):

  | Row | Current | Target | Diagnosed cause |
  |---|---|---|---|
  | Run-rule frequency | .129 | .152 ± .017 | Too little game-to-game variance given the teams: dispersion of runs around the team-strength fit 2.17 sim vs 2.62 real. About a quarter is shared by both teams in a game (residual correlation .032 sim vs .073 real: parks, weather); the rest is one team's game (bullpen availability, lineup changes, blowout substitutions). |
  | Runs per team-game, 15+ bin | .053 | .066 ± .010 | Same as the run-rule row. |
  | Pitchers with 50+ IP | 870.5 (currently passing: Phase 4 Stamina added leash variance; stays deferred, since swingman relief may still move it) | 882 ± 31 | Too few innings reach a team's top pitchers (67/58/50 vs 77/67/54 IP). Real top three get 9.8/6.0/5.5 IP from starts outside Fri–Sun series and 4.3/9.4/19.4 IP in relief; the sim's starters only start and every series is Fri–Sun. Needs swingman relief and Thursday openers, with rest days and fatigue. Inputs: `usage_2025.pitcher_ip_split_by_team_rank`, `pitcher_starts_by_team_rank`, `weekend_series_rank_patterns`. |
  | Qualified K/9 p50 / p90 | 8.58 / 11.69 (currently passing since the sparse-tier pooling of 2026-10-01 moved the benchmark; stays deferred, the cause below is unchanged) | 7.88 ± .93 / 10.56 ± 1.32 | Same cause: 1.7 qualified pitchers per team vs 2.3, all aces, and staffs are ordered by K − BB − HR. |
  | Midweek starter pitch count p10 (moved from the Phase 5 gate on 2026-10-01) | 22.0 | 26.0 ± 3.9 | Pull decisions ignore tier: the pull hazards are pooled over the P4-heavy raw sample, and low-tier managers leave midweek starters in longer. Needs tier-aware manager AI and bullpens. |
  | P4 batting vs low pitching (R/G) | 10.88 | 9.82 ± 1.21 | Mismatch interaction: in real P4–low games both sides score 7–11% below what team strengths predict (P4 9.82 vs 10.50 fitted; low 3.63 vs 4.07). The run rule covers part; the rest needs reserves in mismatches and blowouts (manager AI). |

  Watch item, recheck at the Phase 6 gate. The Phase 2 sim has slightly too much elite run prevention at the very top. All four rows pass, but they lean the same way (20-season report, 2026-10-01):

  | Row | Sim | Real |
  |---|---|---|
  | Best team ERA | 2.93 | 3.20 |
  | 50+ IP pitchers with ERA < 2.00 | 8.7 | 5 |
  | 50+ IP pitchers with ERA < 3.00 | 62.8 | 57 |
  | Teams with ERA < 4.00 | 16.6 | 12 |

  Diagnosed so far: a convex game-level response to run prevention (fixed by the one-scale quadratic map; it cut the lean). What remains is the single best team: recovered rating .80 sim vs .71 real; top 5% now matches. Candidate causes are a Gaussian tail in the team draw, and the missing game-to-game variance (deferred rows above), which would add noise to the best teams' season ERAs.

  Watch items from the national-leaders audit (2026-10-01, `reports/leaders_audit.md`). This is informational and not gated; nothing has been changed for it. Sim values are the mean (range) over the 20-season report run. Real values are NCAA.com leaders for 2024/2025/2026 (`data/ncaa_leaders/`), where 2025 is the calibration season. The batting-average leader matches (.438 sim vs .433/.455/.446) and is not listed.

  | Item | Sim | Real 2024 / 2025 / 2026 | Diagnosed cause |
  |---|---|---|---|
  | Reliever workloads | Max IP with ≤3 starts: 108.9 (97.3–141.0). Most appearances: 48 (47–50) in 56 games. The 50th-most-used pitcher has 40 appearances. Of the top 50 by appearances, 23.1 have 60+ IP. 127 relievers per season reach 60+ IP. The season's innings leader is a reliever in 19 of 20 seasons. | Most appearances 38 / 37 / 39 in up to 72 games. The 50th-most-used pitcher has 29 / 28 / 28 appearances. Of the top 50 by appearances, 6 / 5 / 12 have 60+ IP, with a maximum of 102.2 / 74.0 / 92.0 IP. The pages have no GS column, so "≤3 starts" cannot be checked directly. | Bullpens have no memory between games. `Manager.relief_pitcher` draws any reliever not yet used in *this* game by bullpen-rank share. It has no rest days, no carried fatigue and no availability check, so the rank-1 reliever gets about 16% of relief calls every day. A reliever's Stamina is drawn on his role's scale independently of the K − BB − HR staff ordering. A 70–87 Stamina reliever (leash multiplier θ ≈ .25) goes 2.0–2.7 IP per outing, and these workloads correlate with Stamina (r = .57 among relievers in one season). Real staffs would start such an arm or rest him. Same mechanism as the 50+ IP row: rest days, fatigue, swingman roles. |
  | Strikeout leader | 141.8 (122–167); #5 119.7 | 191 / 180 / 169 (2023: 209); #5 145 / 126 / 133 | Innings, not rate. The sim leader's K/9 is 14.7, against real leaders at 17.2 / 13.6 / 15.9. The sim leader throws 88 IP, the real ones 95–122, and 8 of 20 sim leaders are relievers. Top starters' innings are short (67/58/50 vs 77/67/54, the 50+ IP row) because long relievers absorb them (row above). Season length explains part: the sim plays 56 games with no postseason, while real leaders' teams played 57–72 (×62/56 gives about 157). |
  | ERA #2–#5 (qualified) | #2 1.55 (1.24–1.77); #5 1.91 (1.76–2.10); leader 1.33 matches | #2 2.01 / 1.97 / 1.98; #5 2.16 / 2.11 / 2.07 | Real #2 sits above the sim's whole range, so the leaning ERA-extremes item above extends past the single best team. Over-used long relievers make up part of the qualified low tail (row one): 1.9 of the sim's low five have ≤3 starts, and the ERA leader does in 7 of 20 seasons. Recheck once that row is fixed. |
  | HR leader; hitters with 30+ / 25+ HR | Fixed 2026-10-02 (Phase 2 generation, not Phase 6): HR leader 29.7 (26–35), 30+ HR hitters 0.95, now gate rows | 25.5–34.5 and 0–3 at a 56-game equivalent | Batter HR talent was Gaussian on the logit scale; deconvolution of the play-by-play gives a skewed shape with a short right tail (q.999 +1.31 SD vs +3.09), now drawn through a Gaussian copula (PHASE0_NOTES, true-talent shapes). |
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
