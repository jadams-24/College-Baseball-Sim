# Phase 0 — The Yardstick

`benchmarks.json` is the definition of "realistic" for this project. Nothing in the engine is tuned by eye; every sim run prints a realism report against this file. If a number in the engine can't be traced here, it is a guess and gets flagged.

## What's in the file and where it came from

| Block | Source | Confidence |
|---|---|---|
| `league_totals_2025` (BA/OBP/SLG/K%/R/G/HR/G/SB/G/SH/G) | FanGraphs, "The Ridiculous Firewagon Offenses of College Baseball" (Feb 2026) — per-conference 2025 table sourced from Baseball-Reference; means computed in `derive.py` | B |
| `league_totals_2025.bb_pct` | WMT box totals, team-weighted and matchup-reweighted (see walk-rate note below) | B |
| `half_inning_2025` | WMT play-by-play, 38,106 half-innings, matchup-reweighted; Phase 1 gate | A (owner's label; 28% sample) |
| `league_totals_2025` (HBP%, SF, SB success, SB attempts, ERA, fielding, errors, PA/G, K/9) | WMT stats API box totals, 2,259 D1-vs-D1 games of 2025 (28% of the season), reweighted by tier x opponent-tier cell to the full-season matchup mix (`data/ncaa_2025/pbp/`) | B |
| `league_totals_by_tier_2025` | Same FanGraphs table, grouped | B |
| `pa_outcome_table_league_avg` | WMT play-by-play, 178,073 PA in 2,232 games, matchup-reweighted; reproduces BA .282 / OBP .381 / SLG .442 / HR 1.05 per game | B |
| `pitch_level_2023_2025` | SABR-Tooth Tigers (Trackman, 4.56M D1 pitches); rfrey22 count study (2013-19); pitches per PA and first-pitch strike from WMT play-by-play pitch sequences | A / B / C |
| `historical_trend` | NCAA official "Division I Baseball Statistics Trends 1970-2018" PDF; HR/G 2022-25 from Baseball America / FanGraphs | A |
| `pitching_distribution_2025` | FanGraphs (882 pitchers ≥ 50 IP) | A |
| `batting_distribution_2025` | NCAA.com record book; leaderboard spreads are placeholders | A / D |
| `game_structure` | Wikipedia season pages, NCAA; `run_distribution_per_team_game` from data.ncaa.com scoreboard JSON, all 8,079 final 2025 D1 games; extra-innings and run-rule frequency from WMT schedules (2,273 games with innings) combined with scoreboard margins | A / B / C |
| `base_running_2025` | WMT play-by-play: runner destinations by batter result and starting base, steal attempt and success rates, WP/PB and pickoffs per game | B |
| `league_totals_2025_team_weighted_wmt` | Same WMT box totals, raw and matchup-reweighted; a cross-check of the conf B conference means, not a replacement | B |
| `roster_rules_2025_26` | College Sports Commission, NCAA transfer-window PDF, Baseball Collegian, Baseball America | A |

## Things the 2025 numbers tell you that MLB numbers won't

These are the reasons prior builds calibrated to MLB feel wrong. Bake them into the outcome model, not the ratings:

- **Walks are ~11.4% of PA** (MLB ~8.4%). Every conference walks more than the majors.
- **Strikeouts are ~19.3%** (MLB ~22%). Lower than MLB despite the offense.
- **HBP is ~3% of PA**, more than double MLB. It matters for OBP.
- **BABIP is ~.334** vs MLB ~.290 — wider talent spread in pitching and defense.
- **Runs per team-game is 6.75**, more than two runs above MLB. Only 12 of 303 teams had a sub-4.00 ERA; nobody was under 3.00.
- **Errors ~1 per team-game**, fielding pct ~.970 (MLB ~.985). Errors are a real run source, not noise.
- **Stolen bases ~1.3 per game**, sac bunts ~0.43 — both several times MLB rates.
- **Conference spread is large**: SD of R/G across conferences is 0.5; the SEC slugs .489, the Patriot League .390. A fictional league should reproduce this spread across its tiers, not a single average.
- **The era matters**: 2011 BBCOR bats dropped R/G from 6.98 to 5.58 in one year; 2015 flat seams brought it back. Keep an "era preset" in config so the same engine can be validated against 2014 (dead) and 2025 (hot).

## Gaps to fill in the Phase 1 data pull (before Phase 1 gate)

These are the `conf: C` and `conf: D` entries. Pull from `stats.ncaa.org` (team + individual pages, all D1) and NCAA play-by-play via `baseballr::ncaa_*` or the `collegebaseball` Python package:

1. **Team-weighted league totals** — recompute BA/OBP/SLG/BB%/K% weighted by PA, not by conference. *Partly done:* `league_totals_2025_team_weighted_wmt` gives the WMT-sample values (matchup-reweighted BA .282, OBP .381, SLG .442, BB% .106, K% .194); the conf B values stand until the full stats.ncaa.org table arrives.
2. **HBP%, SF, SH, SB-ATT, errors, PO/A** from the full 300-team table (currently ACC-derived). *Done (conf B)* from WMT box totals; see the status section below.
3. **Run distribution per team-game** — histogram P(0 runs) through P(15+). *Done (conf A)* from the full-season scoreboard.
4. **Extra-innings frequency and run-rule frequency** from game logs. *Done (conf B).*
5. **Batted-ball out split** (GB/FB/LD/PU) — *Done (conf B)* from play text of 67,182 batter outs in play.
6. **Runner-advancement tables** from PBP (P(runner on 1st scores on double), etc.). *Done (conf B)*: `base_running_2025` and `data/ncaa_2025/derived/runner_advancement_2025.json`.
7. **Qualified-batter and qualified-pitcher distributions** — percentiles of BA, OBP, ISO, K%, BB%, ERA, K/9. Fit beta distributions for Phase 2 player generation.
8. **Pitches per PA** and count-state outcome tables from Trackman or PBP — Phase 5. *Pitches per PA done (conf B)*; pitch sequences are in the PA table for the count-state work.

### Phase 1 pull status (2026-10-01)

**Pulled.**

- Every 2025 D1 scoreboard day from data.ncaa.com (8,595 unique games; `scripts/pull_scoreboard.py`). Source of the conf A run histogram and of the true tier-by-tier matchup mix used for reweighting.
- WMT stats API (`api.wmt.games`): schedules with box lines for all 307 D1 teams (2,259 D1-vs-D1 games with both box totals, 28% of the season) and structured play-by-play for 2,232 games / 178,073 PA (`scripts/wmt_schedules.py`, `scripts/wmt_pull.py`, `scripts/wmt_parse.py`). 54 tier-stratified programs (13 P4, 26 mid, 15 low) plus every other WMT-covered D1 game. Parsed plays reconcile with box totals exactly on H, BB, HBP and K.
- 13 Sidearm season pages as a second-source cross-check of team totals (`data/ncaa_2025/sidearm/`).

**How the sample is used.** WMT covers its client schools' games only, so it is P4-heavy (59% of PA) and mid/low programs appear mostly against P4 opponents. Every WMT-derived rate is reweighted by batting tier x opponent tier to the full-season matchup mix from the scoreboard. The reweighting reproduces known values: R/G 6.64 vs 6.78 (scoreboard, D1-vs-D1), P4 R/G 7.23 vs 7.23, BA .282 vs .280, K% .194 vs .193, HR/G 1.05 vs 1.05. It under-shoots in the low tier (6.23 vs 6.59 R/G) because the low-vs-low cell has 68 team-games. Hence conf B, not A.

**Changed in `benchmarks.json`** (old -> new; full table in the PR and `data/ncaa_2025/derived/benchmark_changes.json`): HBP% .029 -> .0334; SF/G .42 -> .368; SB success .79 -> .76; ERA 6.0 -> 6.08; fielding pct .970 -> .9694; errors/G 1.05 -> 1.099; PA/G 38.5 -> 40.31; K/9 8.7 -> 8.17; new SB attempts/G 1.436; the whole PA outcome table (K .1938, BB .1055, HBP .0338, 1B .1602, 2B .0468, 3B .0047, HR .026, SF .009, SH .0094, in-play outs .3693, reached on error or fielder's choice .0413, now explicit); in-play out split GB/FB/LD/PU .456/.356/.069/.119; pitches per PA 3.9 (conf D) -> 3.857; first-pitch strike 58.5% from PBP (Trackman 57.4%); extra-innings frequency .06 (conf D) -> .0546; run-rule frequency (new) .152 = P(margin >= 10, scoreboard .195) x P(ended before the 9th | margin >= 10, WMT .78); new `base_running_2025` block (e.g. runner on 1st on a single: to 2nd 69%, to 3rd 28%, scores 1%; runner on 2nd scores on a single 60%; runner on 1st scores on a double 42%; steal attempt per PA with a runner on 1st or 2nd 6.7%, success 78.8%; WP+PB 2.59 per game). No conf A or B value changed.

**Phase 1 engine build (2026-10-01).** Building the state machine showed that three outcome classes depend on the base-out state in ways a single marginal table cannot carry: a sacrifice fly needs a runner on third with fewer than two outs, a sacrifice bunt and a fielder's choice need runners on. `pa_outcome_table_league_avg` therefore now lists `ROE` (.0141) and `FC` (.0272) separately instead of `ROE_FC` (.0413, same total, same source), and `_derived.state_dependence` records the conditional rates. The engine draws the in-play class (IP_OUT + SF + SH + FC) from the table and subtypes it by state from `data/ncaa_2025/derived/engine_tables_2025.json`; drawing FC at a flat rate had put three times too many reached-on-error plays in bases-empty states and errors per game 60% high. The empirical joint runner-advancement and pre-PA base-running tables the engine samples from are built by `scripts/build_engine_tables.py` from the same play-by-play.

**Walk rate resolved (2026-10-01).** `league_totals_2025.bb_pct` changes from .1137 (FanGraphs unweighted conference mean, conf B) to .1059 (WMT box totals, team-weighted and matchup-reweighted, conf B). The two sources agree conference by conference (SEC .121 / .121, ACC .116 / .121, Big Ten .114 / .117, Big 12 .114 / .113, Mountain West .095 / .095); the league gap is weighting. P4 conferences walk the most (.117 vs .103 mid, .099 low) and are a fifth of D1 teams, so the equal-weight conference mean sits .008 above the team-weighted league. The 13 Sidearm full-season team lines (5 P4, 4 mid, 4 low; 1,396 team-games) give .1108 for both sides combined, between the two as their mix implies. HBP/PA (.0334) and K/PA (.1937 vs FanGraphs .1927) agree across sources and stay. The all-D1 stats.ncaa.org table remains the way to make these conf A; WMT holds 28% of the season.

**Phase 1 gate revised (2026-10-01).** The per-game run histogram, extra-innings frequency and run-rule frequency move to the Phase 2 gate: a league-average engine with identical teams has runs-per-team-game SD 3.78 against the real 4.65 (4.34 after removing team-level strength), so its histogram tails cannot match without player and team variance. The Phase 1 gate adds `half_inning_2025`: runs per half-inning P(0)..P(4), P(5+), big-inning frequency (3+ runs) and PA per half-inning from the WMT play-by-play (38,106 half-innings, matchup-reweighted, tolerances 3 SE at the effective sample size of 9,954). Labeled conf A at the project owner's direction; the basis is the 28% WMT sample.

**Things the PBP says that the Phase 0 aggregates could not:** BB% in the WMT sample is .106 against the FanGraphs conference-mean .114 and SB/G 1.10 against 1.29; the FanGraphs figures are unweighted conference means, so part of the gap is weighting, part may be sample. Both are recorded in `league_totals_2025_team_weighted_wmt` for the Phase 1 realism report to flag. PA per team-game is 40.3, well above the 38.5 back-solved in Phase 0.

**Still open.** stats.ncaa.org team and individual tables (Akamai challenge; to be supplied separately), hence the conf B league line stays as is and the qualified-player percentiles stay conf D. Sidearm sites (202 of 252 screened) are behind Incapsula and unusable for bulk pulls from this environment.

### Phase 2 inputs and gate (2026-10-01)

**Player talent (`player_talent_2025`, conf B).** Player-season lines come from the WMT play-by-play (names normalized within team: the home and away scorers spell players differently). For K, BB, HBP and HR per PA, BABIP and extra-base share of hits, each player's rate minus its batting-tier x pitching-tier cell expectation has observed variance = true variance + binomial noise; the noise (mean q(1-q)/n) is subtracted (method of moments). Team means of the 50 full-season teams give var(team) + var(individual)/k_eff, which splits team from individual variance. Groups: regular and bench batters; weekend starters, midweek starters and relievers. Correlations use the same residuals with the multinomial sampling covariance subtracted. Tier effects are an additive logit fit to the nine tier cells. Earned runs per pitcher come from the pitcher of record on every scoring play (`runs_charged_2025.csv.gz`; 25,695 earned against the box score's 25,713).

**Bias flags.** Full-season teams in the WMT sample are 36 P4, 13 mid and 1 low, against a D1 mix of 21% / 50% / 29%. Team-level variances and individual spreads therefore rest mostly on P4 rosters. The Phase 2 gate run shows this matters: see below. Midweek-starter estimates rest on 25 pitchers. Pitcher BABIP has no individual true variance once team is removed; it is modeled at team level only.

**Gate targets.** `team_strength_2025` (conf A): team R/G and RA/G spread from every 2025 D1-vs-D1 scoreboard final. `qualified_players_2025` (conf B): percentiles from WMT full-season teams plus the Sidearm pages (61 teams: 39 P4, 17 mid, 5 low), reweighted to the D1 tier mix, tolerances from a team-cluster bootstrap. Qualification follows the NCAA rule (2.0 PA per team game and 75% of team games; 1 IP per team game), replacing the conf D placeholder's "1 PA per team game". `leaderboards_2025` (conf A) uses the FanGraphs full-population counts already in `pitching_distribution_2025` and the team extremes in `batting_distribution_2025`; individual BA and HR leaders have no full-population source here (the ncaa.com and d1baseball.com leader pages could not be fetched) and are informational. `game_structure.run_rule_freq` gains a tolerance of 3 SE of its product estimator (.0155); it had none.

**Intercepts.** The six league intercepts (one per rate) are solved by `scripts/solve_phase2_location.py` so simulated PA-weighted league rates equal the outcome table. They pin means only; runs, spreads and player distributions are free.

**Phase 2 gate result (20 seasons): FAIL, explained.** League totals hold (R/G 6.81, BA .284, SLG .443, half-inning distribution passes); OBP .3813 passes against the FanGraphs unweighted conference mean .385 by .0013, and the team-weighted box value is .3805, the same weighting issue the walk rate had. Qualified-player percentiles all pass. Failures trace to three model gaps: (1) team variance is tier-specific and has a conference component, while the model uses one P4-dominated team SD and no conference effect (scoreboard noise-corrected team SD of R/G: P4 .49, mid 1.10, low .92; RA/G .97, 1.23, 1.69; conferences carry 13-26% of within-tier RA variance); the sim gives R/G .74/.60/.50 and RA/G .59/.74/1.03. Runs per team-game SD is 4.14 against 4.68, 10-run margins 13.5% against 19.5%, so the run histogram tails, run-rule frequency and team ERA tails fall short. (2) The additive logit tier model over-credits P4 batting against weaker tiers (P4 vs low 10.7 R/G against a real 9.8), so P4 R/G is 7.67 against 7.21. (3) A fixed three-man weekend rotation gives 1,055 pitchers with 50+ IP against 882; real teams spread weekend starts (the top three make 79%). The decision on fixes is the project owner's.


### Phase 2 revision after the PR #4 review (2026-10-01)

**Owner decisions implemented.** (1) Per-tier team spreads plus a conference effect from the full scoreboard. (2) One talent scale: no tier term in any matchup; tiers and conferences are distributions of team strength. (3) Rotation churn through the Decider. (4) Earned runs by inning reconstruction. (5) Home advantage from the matchup-controlled decomposition. (6) OBP noted as the known weighting issue.

**Team strength (`team_talent_2025`, conf A for tier means, team covariances and the home effect; conf B for conference covariances and hosting).** Quasi-Poisson fit of runs per team-game on every 2025 D1-vs-D1 final (7,938 games, 306 teams): log E[runs of i vs j] = a + o_i − d_j ± h/2. Each team's (o, d) estimation covariance comes from the fit (dispersion 2.62), and is subtracted by method of moments. Within tier: pooled within-conference covariance minus noise gives the team covariance; the spread of conference means minus (team + noise)/n gives the conference covariance. True team SDs (o, d), in log runs: P4 .076/.149, mid .155/.177, low .147/.201. Conference SDs: P4 .050/.087 (4 conferences), mid .037/.106, low .145/.185. Tier means: P4 +.28/+.33, mid +.01/+.00, low −.22/−.25. Matchup-controlled home effect h = .0305 (SE .011), against a raw home/away runs ratio of .131: better teams host more. A nonconference hosting logistic gives P4 hosting low +.92, mid hosting low +.64, P4 vs mid 0, and slope 1.21 per log run of strength gap (disattenuated, reliability .84).

**Engine mapping.** `phase2_run_scale_2025.json`: log runs per half-inning are linear in a logit offset along the P4-minus-low tier contrast (quadratic terms .01 and −.03 over ±0.6), so one unit of o (d) becomes a fixed offset vector on batters' (pitchers') rates. Equal teams give a batting-last home effect of −.059. The scoreboard fits runs per game, which include run-rule and walk-off truncation, so `phase2_game_scale_2025.json` stretches the directions (k_o 1.135, k_d 1.103) until the same fit on simulated seasons recovers each team's (o, d) with slope 1. The home edge (.095) is set so the simulated matchup-controlled h equals .0305. The individual players' share of team variance (sum of squared usage shares × run value of individual variance) is removed from the team draw. What remains of the play-by-play team covariance after projecting out run value is kept as style.

**New gate rows.** `tier_matrix_2025` (conf A): runs per team-game by batting tier × pitching tier, tolerance 3 two-way cluster-robust SE. `home_2025` (conf A): home win pct .5836 ± .0337, home run differential .888 ± .513.

**Usage.** Weekend starters come from real three-game patterns of the team's k-th most frequent weekend starter (547 series on full-season teams; top three make 79% of starts). The pull hazard for weekend starters is tabulated by rotation rank (aces average 4.91 IP per start, spot starters about 3.3). The intercept solve now averages 12 seasons per iteration: league rates vary from season to season with the conference draws (K% SD about .003), and the old two-season solve left K% at .1974.

**Gate result (20 seasons): FAIL on five rows, explained; nothing tuned.** Pass: every tier-matrix cell, every team-strength row, home win pct (.598) and home run differential (1.14), the half-inning distribution, extra innings, ERA (6.20), earned share (.8824 against .8824), all leaderboard rows except 50+ IP, and every qualified percentile except K/9 p50 and p90. Fail:
- OBP .3796 against .385 ± .005: the FanGraphs unweighted conference mean. The sim reproduces the team-weighted outcome table (box value .3805), the same weighting issue as the walk rate. Noted, not changed.
- Run-rule frequency .128 against .152, and the 15+ runs bin .052 against .066: games are too predictable given the teams. Fitting the same decomposition to simulated seasons gives dispersion 2.17 against 2.62 real. About a quarter of the missing game-level variance is shared by both teams in a game (residual correlation .073 real against .032 sim: park and weather, Phase 6). The rest is one team's day (blowout substitutions, bullpen availability, lineup changes; Phase 6 manager AI and fatigue).
- K/9 p50 8.64 and p90 11.78 against 7.66 and 10.54, and pitchers with 50+ IP 769 against 882: too few innings go to a team's top pitchers (67, 58, 50 IP against 77, 67, 54). Real top-three pitchers throw 10–15 IP a season in starts outside Fri–Sun series (Thursday openers, conference tournaments) and the third-busiest throws 19 of his 54 IP in relief. In the sim, weekend starters only start and the series is always Fri–Sun. So 1.7 pitchers per team qualify against 2.3, and the qualified group is K-heavy aces.
- Near-edge row: P4 batting vs low pitching is 10.83 against 9.82 ± 1.04. It passes over 20 seasons and fails in the 4-season CI run. The real data carry a mismatch interaction the one-scale model lacks: in P4–low games both sides score 7–11% below what the log-linear team strengths predict (P4 9.82 against 10.50 fitted; low 3.63 against 4.07). The engine's run rule covers part of it. The rest needs a mechanism, such as reserves in mismatches or blowouts, before any table is considered.


**OBP benchmark replaced (2026-10-01, project owner decision on PR #4).** `league_totals_2025.obp` changes from .385 (FanGraphs mean of conference values, conf B, no source recorded) to .3805: the team-weighted, matchup-reweighted WMT box value (2,259 D1-vs-D1 games), the same method and source as `bb_pct`. It stays conf B with tolerance .005. The .385 weights every conference equally, so it over-weights the P4 conferences, which reach base most (in-sample OBP P4 .392, mid .365, low .335). This is the same error the walk rate had. Built by `scripts/build_pbp_benchmarks.py` (`obp_resolution`); the change is appended to `data/ncaa_2025/derived/benchmark_changes.json`.

**Phase 2 gate revised (2026-10-01, project owner decisions on PR #4).** Five rows move to the Phase 6 gate because their causes are built there (CLAUDE.md, Phase 6 deferred rows): run-rule frequency and the 15+ runs bin (game-to-game variance: parks and weather, bullpen availability, lineup changes, blowout substitutions); the 50+ IP count and qualified K/9 p50/p90 (swingman relief and Thursday openers, which need rest days and fatigue); and P4 batting vs low pitching (reserves in mismatches). No per-game noise term is added, because it would double-count once parks and bullpens exist. The data behind the diagnoses are kept as Phase 6 inputs: `usage_2025.pitcher_ip_split_by_team_rank`, `pitcher_starts_by_team_rank` and `team_talent_2025.residual_corr_within_game` (.073 real; .032 sim). Gate tolerances now combine the benchmark's tolerance with 3 SE of the simulated mean at the number of seasons run, sqrt(tol² + (3 se_sim)²), for every gate row. Leaderboard rows use the 95% Student-t prediction interval of the simulated seasons, with n − 1 degrees of freedom. Result: the 20-season report passes. The 4-season CI run fails best team ERA: its four seasons give 2.65–2.77 against the real 3.20, while over 20 seasons the mean is 2.86 with SD .23, so the real value sits about 1.5 SD up. The ERA-extreme rows all lean the same way (pitchers under 2.00 ERA 9.8 against 5, teams under 4.00 17.6 against 12) but pass over 20 seasons. Left for the project owner.


**Elite run-prevention lean diagnosed (2026-10-01, project owner decision on PR #4).** `scripts/diag_phase2_defense_tail.py` fits the scoreboard decomposition to simulated seasons and compares recovered team ratings with the real fit. Tier means were right (P4 run prevention .328 sim vs .334 real), so the single stretch k_d was not inflating tier means. The engine's per-game response to a team's rating was convex instead: the slope of recovered on true run prevention was 1.10 ± .02 within P4, 1.02 within mid and 0.99 within low (offense 1.07/1.04/0.96). The run rule truncates lopsided games, which compresses bad defenses, while good defenses play close, low-scoring games with nothing truncated. The pooled linear stretch therefore over-amplified the top of P4. The fix keeps one scale: one map per side for every team, engine units = k x + q x², solved like the offense scale so that the fit on simulated seasons recovers each team's rating with slope 1 and no curvature (`phase2_game_scale_2025.json`: offense k 1.137, q −.068; run prevention k 1.105, q −.087; home edge .107).

Results:
- Top 5% of recovered run prevention now matches: .594 sim vs .597 real, and .710 vs .694 within P4. Within-P4 SD is .200 vs .193.
- Best team ERA moves from 2.86 to 2.93 (real 3.20), pitchers under 2.00 ERA from 9.8 to 8.7 (5), teams under 4.00 from 17.6 to 16.6 (12).
- What remains is the single best team (recovered .80 vs .71; one real season is one draw). It is a named watch item in CLAUDE.md, to recheck at the Phase 6 gate.

CI now runs the report's own 20 seasons and seeds, and checks that the committed report's gate verdicts equal its own.

### Phase 4: 20-80 ratings (2026-10-01)

**Phase order.** Phase 3 (handedness) moved after Phase 4 by project owner decision: no handedness source is reachable from the cloud (the WMT API has no bats/throws; school roster sites refuse this container). `tools/fetch_rosters.py` is run by the owner locally; Phase 3 starts once `data/ncaa_2025/rosters/` exists.

**Scale (`ratings_scale_2025`, conf B).** rating = 50 + 10 sign (z − mean) / sd for one true rate per rating: Contact BABIP, Gap XBH share of hits, Power HR/PA, Eye BB/PA, Avoid K K/PA; Stuff K/BF, Control BB/BF, Movement HR/BF. mean and sd are the PA- (BF-) weighted mean and true SD of z over all of D1, from the Phase 2 noise-removed distributions as the generator draws them (8 calibration seasons, seeds 940001–940008). Batter HBP and pitcher HBP, BABIP and XBH allowed are carried unrated. Speed is reserved: no engine rate depends on a runner's speed yet.

**Stamina (`stamina_2025`, conf B).** Individual leash on the Phase 2 pull hazard, h' = 1 − (1 − h)^θ, log θ ~ N(μ, σ²) per role, fitted by empirical Bayes with the exact discrete-time likelihood on the 2025 play-by-play: starters σ .54 (271 pitchers with 5+ starts), relievers σ .62 (847). Method-of-moments check: .52 and .51. With leash variance, pitchers with 50+ IP rise from 769 to 872 (deferred row; real 882).

**Round trip, first version: reverse direction (engine/report4.py, now the informational scouting estimator).** Players are generated as ratings and simulated for 20 seasons. Ratings are estimated back from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. The estimator is empirical Bayes on a grid with an opponent-mixture binomial likelihood and a normal prior per role × tier, run in 10 folds of 2 seasons. Gate: slope 1, bias 0 and SD ratio 1 within the Student-t tolerance across folds, on players with at least half a regular's workload.

**First gate result (20 seasons, reverse direction): FAIL on seven rows, explained.** Every Phase 1 and Phase 2 row passes on the same run. Tier distributions pass for every rating (P4 everyday players above 50, low below). Stamina, Contact, Gap and Eye recover fully. Failing rows: bias for Stuff (+.08 ± .04), Control (+.17 ± .05), Movement (+.33 ± .07), Power (−.13 ± .12) and Avoid K (+.03 ± .03); slope for Control (.991 ± .008) and Movement (.962 ± .028).

**Cause: playing time depends on talent, and the estimator's prior does not know it.** The manager starts, bats high and works its best players most: start shares and batting order by talent, rotation and bullpen ranks by K − BB − HR. Within a role group, true rating and workload correlate +.10 to +.28 for pitchers and +.50 for regulars' Power. A prior per role × tier shrinks a team's busiest players toward too low a mean and its least-used players toward too high a one. Within a role, bias rises with workload: Movement for weekend starters is −1.2 / +.2 / +1.3 by workload tercile, and Power for regulars −2.9 / −.7 / +1.6. Weighted by trials over all players, the bias is .00 for every rating, so the engine and the anchor are right. The gate keeps the busier half of players, which gives the positive pitcher biases, largest where shrinkage is strongest (Movement, reliability .39).

**Fixes tried (4 seasons, not committed).**
1. Prior mean linear in log trials: pitcher biases go to Stuff +.03, Control .00, Movement +.03. Power gets worse (bias −.39, SD ratio 1.07), because its relation with workload is convex.
2. A prior per workload rank on the team (role × tier × rank): biases go to about zero. But Power's SD ratio is 1.06–1.13 and Movement's slope .89–.94, and pooling four seasons does not fix either (1.09, .94). Given a rank, one rating is not normally distributed. The rank is the team's order on a combination of ratings (OBP + SLG for hitters, K − BB − HR for pitchers), so a team's top hitter is a mixture of power hitters and on-base hitters, and a normal prior per rank misstates the spread.

**Gate changed to the forward direction (2026-10-01, project owner decision on PR #5).** The reverse direction (ratings estimated from stats) tests an estimator, and its prior has to model how managers hand out playing time. The forward direction tests what Phase 4 claims: ratings map to rates, and the engine turns those rates into stats with nothing but sampling noise. For each rated rate, each qualifying player-season's opponent-adjusted observed rate is regressed on his true rate on the logit scale. The gate asks for slope 1, intercept 0 and dispersion 1 within sampling error, and the result is also reported by workload tercile.

- The engine records, per player and rate, the sum of p and of p(1 − p) over his own trials at his true rates against the opponents he actually faced (E, V). The observed offset is z + (x − E)/V.
- The box-score version (opponents adjusted from the team-by-team fit only) runs 1–7% over dispersion 1. A box score shows which team a player faced, not which pitcher, so it is reported as informational.
- The manager orders players by true talent only: lineup, rotation and bullpen order are set once per season from the true offsets, and no in-season statistic feeds any choice. Workload therefore does not select on results, and the forward regression on true talent is not biased by it.
- The in-game pull hazard (outing pitches and runs) is the one outcome-dependent usage rule. Stamina's terciles are split by appearances, because its batters faced are partly the pulls themselves.
- The empirical-Bayes estimator stays in the report as informational: the future scouting estimator for Phase 9, with the workload-selection diagnosis above.
- Pitchers with 50+ IP (870.5 vs 882) now passes. It stays in the Phase 6 deferred table, marked currently passing, because swingman relief may still move it.

### Phase 5: pitch-by-pitch (2026-10-01)

**What the data supports.** Every action of the 2,264 WMT games was audited. Each plate appearance has a pitch sequence over B (ball), K (called strike), S (swinging strike), F (foul), P (in play) and H (hit by pitch), the final count, the pitch count and a strikeout-looking flag. There is no pitch type, velocity or location, so the model has none. Zone and chase cannot be separated: Control and Eye move balls and takes, Stuff and Avoid K move whiffs against contact.

**Cleaning** (`scripts/build_phase5_benchmarks.py`). A P before the last pitch changes neither balls nor strikes but is in the official pitch count; 2,598 such pitches are kept as neutral pitches (N). 682 HBPs coded with a final P are read as H. Intentional walks and catcher's interference (431) are excluded, as are 5,056 PAs with no sequence and 646 that break the count rules. 171,592 of 178,073 PAs are used, reweighted to the D1 tier mix, with standard errors from a bootstrap over games.

**Benchmarks** (`pitch_level_2025`, conf B, new block, no existing value changed). These cover pitches per PA and their distribution, count reach, BA / K% / BB% of PAs passing through each count, first-pitch strike rate, foul rate with two strikes, and pitches (mean, p10, p50, p90) and innings per start, weekend and midweek. The Phase 0 Trackman first-pitch strike rate (.574, `pitch_level_2023_2025`) is kept but not gated. It counts differently from the play-by-play the engine is built on (.582 here, first pitch not a ball or HBP).

**Model** (`engine/pitch.py`). The PA outcome is drawn first from the unchanged Phase 4 matchup model, so PA totals cannot move. The pitch sequence is then drawn from a count-state chain conditioned exactly on that outcome (Doob h-transform).
- Player effects follow directions measured in the data. A split-half regression gives each side's per-pitch event rates (ball, called strike, whiff, foul, in play) on true K% and BB%, with binomial noise removed by the cross-half covariance. For example, a patient batter takes more: more balls and called strikes, fewer whiffs, fouls and balls in play.
- A small correction along the average directions makes each matchup's chain reproduce its own K, BB and HBP rates, so the conditioning only shapes the batted-ball side.
- The league base chain is solved (`scripts/solve_phase5_chain.py`) so the simulated league's per-count event shares equal the data's (max gap .002). The pooled data shares already average over players, and tilting them again had left pitches per PA at 3.76 against 3.81.
- Ball-in-play results by count come from the data's shares at the count of contact.
- The pull hazard now reads the simulated pitch counts.

**Gate result (20 seasons): FAIL on one row, explained; not changed.** Every other Phase 5 row passes:
- pitches per PA 3.815 vs 3.805;
- every count-reach and outcome-by-count row;
- first-pitch strike rate .580 vs .582;
- two-strike foul rate .207 vs .208;
- weekend pitches and innings per start;
- midweek mean, p50, p90 and innings.

Every PA-level rate is unchanged from Phase 4, every Phase 1 and Phase 2 row passes, and so does the Phase 4 forward ratings test. 50+ IP is 879.4 (real 882). The failing row is midweek starter pitch count p10, 22.0 against 27.0 ± 3.7:
- The benchmark is reweighted by batting-tier × pitching-tier cell. Low-vs-low gets 19.6% of the weight from only 15 midweek starts, the shortest of which is 28 pitches, so that cell's 10th percentile is not identified.
- A bootstrap of 15 starts with a minimum of 28 never produces a shorter one, so the row's standard error is understated.
- Every well-populated cell has p10 21.5–25 (mid-vs-mid 23.0 on 184 starts, P4-vs-mid 23.5 on 276); P4-vs-P4 is 31 (252 starts). The raw sample is 24.
- The engine's pull hazards are tier-blind (pooled over the raw sample), so the sim (22) sits near the raw value. Low-tier staffs leaving midweek starters in longer is tier-dependent manager behaviour.

Left for the project owner (PR description).

**Gate revised and passed (2026-10-01, project owner decisions on PR #7).** Two changes were made.
- Midweek starter p10 moved to the Phase 6 deferred table. Pull decisions ignore tier, and low-tier managers leave midweek starters in longer.
- Sparse tier cells in reweighted percentile benchmarks are now pooled (below).

On the report's 20 seasons every gated Phase 5 row passes, every PA-level rate is unchanged from Phase 4, every Phase 1 and Phase 2 row passes, and the Phase 4 forward ratings test passes. Midweek p10 is reported at 22.0 against the pooled 26.0 ± 3.9. Two deferred rows now pass because their benchmarks moved: qualified K/9 p50 (8.58 vs 7.88 ± .93) and p90 (11.69 vs 10.56 ± 1.32). They stay deferred, because their cause (an ace-heavy qualified group) is unchanged.

### Sparse-cell pooling for tier-reweighted percentiles (2026-10-01, project owner decision on PR #7)

**Rule** (`scripts/lib/pooling.py`, floor `config.benchmarks.MIN_CELL_N_PERCENTILE` = 50). In a tier-reweighted percentile benchmark, a tier cell (a tier, or a batting-tier × pitching-tier pair) with fewer than 50 observations is pooled with its nearest cell before reweighting.
- The merge repeats until every group has 50: the smallest group merges with its smallest neighbour, a neighbour being one tier step away on one side (p4 – mid – low). Sparse cells therefore pool with each other first.
- A pooled group keeps the sum of its cells' weights.
- The pooling is fixed from the full sample and held fixed in every bootstrap replicate.
- Why 50: with 50 observations a p10 has about 5 values below it, so the quantile is bracketed by data. A 15-start cell whose minimum is above the pooled p10 cannot estimate its own tail, and its bootstrap never draws below that minimum, which understates the SE.

**Rows it applies to.** Every tier-reweighted percentile in the repo:
- the qualified-player percentiles (BA, OBP, ISO, K%, BB%, ERA, K/9 at p10–p90; 35 rows);
- the starter pitch-count percentiles (p10, p50, p90, weekend and midweek; 6 rows).

Every other reweighted benchmark is a mean or a share.

**Results.** Recomputed without pooling, every row equals its old value exactly, so the changes come from the rule alone. Changes are logged in `benchmark_changes_phase2.json` and `benchmark_changes_phase5.json`.
- **Qualified players.** The low tier has fewer than 50 qualified players on both sides, so it pools with mid (batters 165, pitchers 56).
  - BA p10–p90 .237 / .258 / .295 / .324 / .351 → .239 / .265 / .296 / .325 / .353.
  - OBP: largest move p75 .418 → .420.
  - ISO: p50 .163 → .167, p75 .213 → .219.
  - K%: no move above .002.
  - BB%: p25 .082 → .080, p50 .108 → .106, p90 .154 → .158.
  - ERA: p25 4.16 → 4.22, p50 5.09 → 5.12, p90 7.69 → 7.64.
  - K/9: p10 5.82 → 5.72, p25 6.83 → 6.74, p50 7.66 → 7.88, p75 9.55 → 9.70.
  - Every move is within the row's tolerance; tolerances changed slightly because the bootstrap now uses the pooled weights.
- **Starter pitch counts.**
  - Weekend: low-vs-low, mid-vs-low and low-vs-mid pool (125 starts). p10 46 → 47, p50 82, p90 104 → 103.
  - Midweek: the same three cells pool (15 + 17 + 18 = 50 starts). p10 27 → 26, p50 54 → 52, p90 94.
- **Midweek starter p10** is still a Phase 6 row (owner decision). The pooled value (26) is closer to the sim (22) but not within tolerance. The tier behaviour behind it is real: low-tier staffs leave midweek starters in longer. It belongs with manager AI.

### True-talent shapes, percentile ratings and the individual-leader gate (2026-10-02, project owner decision after the leaders audit, PR #8)

**Problem.** The national-leaders audit (`reports/leaders_audit.md`) found the HR tail too long: the sim's HR leader averaged 43.4 (35–75) and 8.3 hitters a season reached 30 HR. Real seasons had 26–37 and 0–5. The cause was the talent draw, not season length. Batter HR talent was Gaussian on the logit scale: method-of-moments mean and SD, with the SD converted from the probability scale by the delta method.

**Shapes by deconvolution** (`scripts/build_talent_shapes.py`, `data/ncaa_2025/derived/talent_shapes_2025.json`, `reports/talent_shapes.md`).
- Data: the method-of-moments player-season lines, role groups, tier expectations and qualifying cut, with each team's effect removed by empirical-Bayes shrinkage.
- Fits per side and rate: the individual distribution in units of the group's method-of-moments SD, by marginal likelihood (binomial integrated over the distribution). Three fits: Gaussian; sinh-arcsinh (Jones & Pewsey 2009: skew eps, tail weight delta); and NPMLE (Kiefer–Wolfowitz, the nonparametric bound).
- A shape is used when the likelihood-ratio statistic against the Gaussian exceeds 13.82 (chi-square, 2 df, p < .001; strict because 11 shapes are tested).
- Result: only **batter HR/PA** qualifies (LRT 27.7). Its shape has eps −1.66 and delta 1.07: a long left tail (hitters with almost no power sit far down on the logit scale) and a short right tail. Standardized quantiles: q.99 +1.21 and q.999 +1.31, against the Gaussian's +2.33 and +3.09.
- The NPMLE is only 1.0 log-likelihood unit above the sinh-arcsinh fit and puts no mass above +0.85 SD units.
- Batter K is borderline (LRT 11.9, a shorter high-K tail) and stays Gaussian. Every other rate has LRT ≤ 4.7.
- Pitcher BABIP has no individual spread to shape (SD 0 for starters).

**HR uses the full fitted distribution.**
- For a skewed rate, the method of moments' location (logit of the mean rate) and its delta-method SD are biased. HR therefore takes the fitted location (−.42) and scale (1.28) in method-of-moments SD units, as well as the shape.
- The other rates keep their method-of-moments mean and SD, so their draws are unchanged bit for bit.
- The team draw's removal of the individual share (config.phase2._team_draws) uses the fitted SD.

**Draw** (`engine/league.py`).
- Gaussian copula: the correlated normal draw on the play-by-play correlations is unchanged. Each component's normal score is mapped through its rate's fitted quantile table, so rank correlations are kept exactly.
- The league location was re-solved because the new shape has a lower mean rate. The HR intercept moved from −.311 to −.163; the other five moved within solve noise. Simulated league rates equal the table to 4 decimals.
- Regular batters' true HR/PA against an average pitcher, before the re-solve: p99 .073 → .054, maximum .142 → .069.

**20-80 scale on percentiles** (`engine/ratings.py`, `scripts/build_phase4_scale.py`, `ratings_scale_2025`).
- rating = 50 + 10 · sign · Φ⁻¹(F(z)), with F the PA- (BF-) weighted D1 distribution of true z. 50 is the D1 median; 60, 70 and 80 are the 84.1st, 97.7th and 99.87th percentiles, the meaning these ratings had under the Gaussian.
- F is a quantile table at normal scores ±4.25 (step .05) from 200 generated leagues, weighted by each roster slot's mean PA/BF in 8 simulated seasons. Between points the map is linear both ways, so it inverts exactly; beyond the table it continues the end segments.
- Rates still Gaussian map as before within table noise (Eye at 80: z +.904, against +.908 linear).
- Power at 80 is z +1.364, against +1.940 on the old linear map.
- The scouting estimator (informational) reads its estimates through the same map.

**Individual-leader gate** (`individual_leaders_2023_2026`, conf A, new block; `scripts/write_leader_benchmarks.py`).
- Sources: NCAA.com national leader pages (top 50) for 2024–2026, and the record book for 2023 (Caglianone 33 HR in 71 G, Wilken 31 in 66, Wetherholt .449).
- Counting stats use a 56-game equivalent: each player's HR × 56 / his games, because real leaders' teams played 57–72 games with the postseason.
- The pages give games but not plate appearances, so the top-5 row is HR per game played on both sides.
- Bands (lowest to highest real season): HR leader 25.5–34.5; 30+ HR hitters 0–3; BA leader .433–.455; top-5 HR per game .410–.539.
- A row passes if the 20-season sim mean lies in the band, widened by 3 SE of the sim mean. The single-season record (48, Incaviglia 1985) is a hard ceiling on every simulated player-season.
- The conf D placeholders `leaderboards_2025.individual_ba_top` and `individual_hr_top` are removed, superseded by this block (logged in `benchmark_changes_leaders.json`).

**Result (20 seasons, seeds 20251000–20251019): every Phase 1, 2, 4 and 5 gate row passes, and no row changed status.**
- HR leader: 43.4 → 29.7 (26–35).
- Hitters with 30+ HR: 8.3 → 0.95.
- Top-5 HR per game: .499.
- Most HR in any of the 20 seasons: 35.
- BA leader: .442.

Rows that moved but still pass:
- Qualified ISO p50 .1625 → .1669 (benchmark .1667) and p25 .1184 → .1207.
- Most team HR per game 2.80 → 2.68 (real 2.672).
- Pitchers with 50+ IP 879 → 870 (deferred row).
- Power forward test: slope 1.004, dispersion 1.008.
- League rates within .001 of their old values.

### Phase 6: fielding, parks, fatigue, bullpen and manager AI (2026-10-02 to 2026-10-04, project owner request after PR #10)

Everything that does not need handedness. Inputs come from the committed 2025 WMT play-by-play: new event tables (`scripts/build_phase6_events.py`) and `data/ncaa_2025/derived/phase6_inputs_2025.json`. No new fetch. Every mechanism can be switched off on its own (`config.phase6.FEATURES`) for ablation.

**Calendar and bullpen** (`scripts/build_phase6_usage.py`).
- Each team-week follows a real weekly pattern: a midweek game on Mon/Tue/Wed and a three-game series starting Thu or Fri (patterns and shares from the 50 full-season teams).
- Staffs have 18 pitchers (the data median; `N_RELIEVERS` 8 → 13).
- Relief choice and the midweek starter use conditional logits fitted on the 2025 entries. Alternatives are every unused pitcher on the staff. Terms:
  - role × leverage (late and close, blowout, other);
  - rest cells (days since the last outing, split by that outing's pitches);
  - back to back.
- A pitcher's rest and fatigue carry across games (`Manager.record_game`).
- A between-innings pitching change takes effect only when the side next takes the field. Before, the replacement was credited with an appearance even when the game ended first, which inflated pitchers per team-game (4.55 against 4.30 real).

**Leash** (`scripts/build_phase6_pull.py`).
- The pull hazard gets a proportional-hazards multiplier: log θ = tier (relievers and midweek starters) + season week (starters) + the midweek starter's staff role class (weekend arm −.46, reliever +.28). It is fitted by maximum likelihood on the engine's split: Thu–Sun series games against Mon–Wed midweek games.
- Midweek starts use a pull table rebuilt on Mon–Wed starts only. The Phase 2 table pools Thursday series openers, whose aces carry long leashes into the 70–100 pitch cells.
- Each pitcher's Stamina deviation is scaled to the midweek leash spread (.31, by empirical Bayes on 29 pitchers with 5+ midweek starts, against Phase 4's .54 for all starts).
- Weekend starters get no tier term. The per-decision fit gives mid- and low-tier weekend starters θ .78, but realized pitch counts by tier are flat in the data (p90 101 / 103 / 101), and with the term the engine's mid and low tiers overshoot (108 / 107).

**Substitutions** (`scripts/build_phase6_subs.py`).
- Hazards by inning × margin with tier multipliers: pinch hitters per plate appearance, pinch runners per batter reaching base, defensive or blowout substitutions per half-inning in the field.
- The lineup spot replaced follows its real share.
- Who comes in: entries per game not started, by start rank (flat at about .33 for ranks 1–10, falling to .14 for the deepest).
- A pinch runner must be faster than the runner.
- Rosters carry 17 position players (the data median; `N_BENCH` 5 → 8).
- Playing time follows hitting at ρ = .47 among regulars: the within-team correlation of start share with OBP (.49) and OPS (.45), disattenuated for sampling noise. Start ranks are ordered by ρ × hitting value plus noise, and the batting order stays by hitting value.
- Starts are persistent by rank: P(start | started the team's last game) against P(start | sat it). The lag-one difference is .33–.45 for ranks 4–14.
- Before these changes, substitutes crowded onto resting regulars and 9.0 batters per team qualified.
- Qualification counts games with a plate appearance, as the benchmark does (`scripts/build_phase2_gate.py`). The sim had counted every appearance, including pinch runners and defensive substitutes without one, which Phase 6 added. That let marginal regulars pass the 75% games line, and OBP p10 fell to .321.

**Parks** (`scripts/build_phase2_teams.py`, `scripts/build_phase6_parks.py`).
- The scoreboard fit gains a park term. Park SD by tier (noise removed): P4 .111, mid .095, low .167 log runs.
- The rate mix (K, BB, HBP, HR, BABIP, XBH) comes from home/road box-score park factors of 50 full-season teams.
- The engine draws each team's (o, d) as totals from the fit without parks; those are what the scoreboard sees and were validated in Phase 2. It then draws a park run level from the tier and nets the park out of the totals by the team's scheduled exposure (`scripts/solve_phase6_park_exposure.py`):
  - A team's no-park total absorbs its home park and the parks it visits, in proportions set by the fit on this schedule design. On simulated seasons, where net ratings and every park are known, the no-park fit's recovered minus drawn ratings are regressed on the team's home park and the mean park of its road games: o absorbs .567 of the home park and .367 of the road parks, d −.398 and −.268 (SE ≤ .065; seeds 940001–4).
  - The engine nets o_net = o − .567·p_home − .367·E[p_road] and d_net = d + .398·p_home + .268·E[p_road]. E[p_road] is the schedule's expectation: conference road games at the mean of the conference mates' drawn parks, nonconference road games at the tier means of the opponents in the schedule mix.
  - The earlier ±park/2 netting assumed a team's total holds its home park only. It left visited parks in the net ratings, which shifted tier means: low-tier teams' expected road parks average .07 log runs above P4 teams' (−.053, −.007 and +.016 by tier on generated schedules).
- Two earlier versions failed on simulated seasons fitted the same way:
  - Drawing net ratings and parks independently, from the park fit's own decomposition, overstated P4 team R/G spread (1.03 against .79). The park fit's noise removal misses part of the sampling covariance between a team's o and its park, which inflates the "true" o spread (P4 .106 against .072 implied by the no-park fit).
  - Drawing the park conditional on (o, d), at the "true" correlation of about −.4, double-counted. On simulated seasons fitted the same way, independent parks already reproduce the real recovered o–park and d–park correlations (−.4 to −.6 and about 0); that correlation is sampling noise, and conditioning on it overshoots.
- An asymmetric version (offense net of the park, run prevention independent of it) put half the park variance into season RA/G spreads (1.81 against 1.60 overall) and was dropped. The recovered correlations are reported as diagnostics only.

**Run prevention split into pitching and fielding** (`scripts/solve_phase6_fielding_scale.py`).
- The scoreboard's run prevention d already includes fielding, but the Phase 6 error model ties each team's error log-odds to d (slope −.72) on top of a pitching staff that carried all of d.
- Because the two parts are correlated, the double count added linearly to RA/G spread: about .13 runs, 1.86 against 1.73 with fielding off.
- The staff now gets g(d) + φ·e, where e is the team's expected error log-odds (team term plus its regular fielders). Total run prevention stays g(d).
- φ is the engine's run response, .1035 log runs per unit of e, measured by shifting every team's errors ±.5 on calibration seeds. The play-by-play gives .127: 0.80 runs per error play by state-matched run expectancy (reached-on-error against a batted-ball out .905; an error on any other play against the same result without one .597), times 1.07 errors per unit.
- The engine applies error odds only to reached-on-error and advancement errors, hence the smaller response.
- Fielding's share of run-prevention variance is small, about 1% D1-wide and 4% within P4, but it is correlated with pitching quality.

**Fielding and speed** (`scripts/build_phase6_fielding.py`).
- Errors per chance by position, with true SDs by the method of moments, plus a team error term tied to run prevention.
- Outfield arms (extra bases allowed) and catcher arms (steal success against).
- One speed factor loads attempt, success and extra bases.
- Steal attempt and success by offense tier × defense tier cell. Attempts rise in mismatches: P4 running on mid or low defenses .117–.132 per opportunity, against .081 for P4 on P4 and .087 for mid on mid. Main effects spread that onto every game and overshot attempts (1.53 against 1.44).
- Range is not identifiable from the play-by-play: the scorer's hit location is where the ball was fielded, not where it was hit. It is not modelled.

**Benchmark changes** (logged in `benchmark_changes_phase6.json`).
- `league_totals_2025.sb_per_team_game`: 1.29 → 1.098. The old value was the FanGraphs unweighted mean of conference tables (Phase 0). The new value is the WMT box totals reweighted to the full-season matchup mix, the source of the attempt and success rows it is the product of. Full-season Sidearm team totals agree (1.047 on 13 teams).
- `leaderboards_2025.pitchers_50ip` gains `value_56g` = 821: the raw 882 × .931 ± .034, the ratio of 56-game-equivalent to raw 50+ IP counts on the WMT full-season teams (real teams play 57–72 games with the postseason). It is the same normalization as the individual-leader rows.
- `pitch_level_2025` starts: midweek is now Mon–Wed (Thursday series openers are weekend starts).
- New `usage_phase6_2025`: usage rows at a 56-game equivalent, batters per team-game and earned-run share.
- Errors per team-game and earned share leave the Phase 5 "unchanged from Phase 4" rows, because Phase 6 fielding moves them on purpose. They are gated against real data instead.

**Run rule and the 15+ runs bin: part of the "offense extremes compressed" watch item (below), not closed** (owner decision, 2026-10-03: no noise term).
- Runs vary less from game to game around team strength in the sim than in reality. Scoreboard dispersion is about 2.2 against 2.6 real (without parks), and within-game residual correlation .05 against .073.
- The missing variance is about two-thirds one team's game, which drives margins and so the run rule, and one-third shared by both teams, which feeds the 15+ bin. Tested and ruled out, each against the play-by-play or the scoreboard:
  - Shortened games: scheduled 7-inning doubleheader games and weather-shortened games are 1.2% of games.
  - In-season drift in team strength: a team's scoreboard residuals are not positively autocorrelated across its games at lags 1–20 (all about −.02, the fitting bias).
  - Pitcher day form: starters' per-start dispersion is 1.02 for walks and 1.01 for hits on balls in play, both at the sim's level. Strikeouts run 1.37 against 1.12, but that is worth under 1% of run variance.
  - Defensive days: team errors per game are only mildly overdispersed (1.11).
  - Seasonal run environment (temperature proxy): week effects have true variance .0008 in log runs, about 7% of the shared gap.
  - Team-strength tails: sim and real RA/G and R/G quantiles agree.
  - Persistence within a game: runs in innings 1–3 and 4–6 correlate .068 real against .041 sim, a gap of 1.7 SE.
  - Mechanisms that are in and help: parks (residual correlation .032 → .05), bullpen rest and fatigue, lineup persistence and blowout substitutions.
- Remaining candidates need data not in the repository:
  - Wind relative to each park's orientation. NOAA hourly weather is reachable and allowed by its robots.txt; park orientations are not available.
  - Umpire strike zones and field conditions.

**Mismatch interaction investigated; the cause was the schedule** (`scripts/build_phase6_schedule.py`; project owner request: build the mismatch interaction from data on the continuous strength gap, not tier labels; then rescoped to remove an invented underdog penalty, no offsetting term).
- The 20-season run after the park-exposure netting failed four rows that pointed the same way: low batting vs mid pitching (5.20 against 5.88), team RA/G spread (1.88 against 1.60), and the low and mid offense recovery rows. Watch items P4 RA/G mean and qualified OBP p10, and the elite run-prevention lean, leaned the same way.
- Gap curve. Runs per team-game were fitted on the two teams' scoreboard ratings plus a term in the squared strength gap g (o + d of the batting team minus the fielding team's), separately for the favored (g > 0) and underdog side, on the real scoreboard and on simulated seasons measured the same way.
  - Fitted jointly with the ratings, real games show a favored-side shortfall only (−.088 ± .019 per g², about 9% at g = 1; underdog +.022 ± .026), while the sim showed an underdog penalty (−.109 ± .019). The joint fit is poorly identified, though: adding the terms widens the real fitted strength spread by 18% and the sim's by 1%, and the two g² terms trade off against that spread.
  - Two-step (ratings from the additive fit, then the g² terms on its residuals): favored −.036 ± .011 real against −.035 ± .003 sim; underdog −.044 ± .020 real against −.084 ± .007 sim (1.9 SE; −.063 ± .010 with every Phase 6 mechanism off).
  - The real favored-side shortfall is late: innings lost to the run rule and the skipped bottom ninth (−.23 per g²) and fewer runs per late inning batted (−.10 ± .03); innings 1–6 carry −.037 ± .013. The sim already loses more late innings than real (−.31), so the run rule and blowout substitutions cover it.
- PA level (owner request: find the layer). The same g² terms in a logit for each rate (K, BB, HBP, HR per PA; hits per ball in play; extra-base hits per hit; reached on error), and runs given the PA outcomes against a BaseRuns yardstick, on (batting team, pitching team, home) cells:
  - Real: mismatches walk more on both sides (+.12 ± .03 favored, +.09 ± .03 underdog); underdogs strike out more (+.11 ± .03); favored sides hit fewer extra-base hits (−.11 ± .04). Runs given the PA outcomes are flat in g (+.002 ± .012 favored, −.011 ± .021 underdog), so nothing enters at the compounding layer.
  - Sim: the same signs at smaller size (BB +.03 both sides, K +.02 underdog) and runs given the outcomes flat as well (−.014 ± .003, +.003 ± .005). The odds-ratio combination and run compounding do not penalize weak offenses beyond the data; runs per game against the additive prediction agree (underdog −.086 ± .043 real, −.091 ± .011 sim, on these cells).
- Parks (owner hypothesis: park rate shifts produce runs that depend on hitter quality). Tested on the scoreboard with the park fit: the interaction of the fitted park with the matchup (o_bat − d_pit) is +.004 ± .018 per season in the sim and +.058 ± .077 real. Rejected; the park model is unchanged.
- The cause: the tier cells' fitted predictions, not their residuals. In low batting vs mid pitching the residual is 1.008 real against .981 sim, but the additive prediction is 5.83 real against 5.36 sim, because the mean strength gap in those games is −.34 real and −.46 sim with the same tier means. Real nonconference schedules are matched by strength within tier. On the 2025 regular season (games before May 26; the NCAA tournament adds selection of its own and the sim has no postseason), the teams in each nonconference pairing sit this far from their tier's mean strength (log runs, fit without parks):

  | Team's tier → opponent's tier | Real (SE) | Sim before | Sim after |
  |---|---|---|---|
  | low → mid | +.088 (.014) | +.018 | +.063 |
  | low → P4 | +.154 (.024) | +.007 | +.153 |
  | mid → low | −.060 (.011) | −.009 | −.053 |
  | mid → P4 | +.027 (.012) | −.004 | +.016 |
  | P4 → low | −.005 (.020) | +.009 | −.029 |
  | P4 → mid | +.016 (.009) | −.007 | +.018 |

  Opponents' deviations covary too (.0175 in cross-tier games, .0010 of it the fit's own noise covariance). For low teams most of the selection is the conference (+.133 of the +.154 against P4): strong low conferences play up. The same estimator on simulated seasons returned about zero before the change, so it is not a fitting artifact.
  - Model: each week's tier pairs are drawn from the real mix as before; the teams of each tier then fill their cross-tier slots with weight exp(β[tier|opponent tier] × deviation), same-tier slots take the rest, and opponents are matched by rank on z + σ N(0, 1) (z in tier SD units). Six β and σ are solved on generated schedules against the six means and the covariance (β low|mid .88, low|P4 1.35, mid|low −.65, mid|P4 .23, P4|low .19, P4|mid .65; σ 1.86).
  - Same-tier pairings are not matched and come out weaker than real (low vs low −.12 against −.04): the weakest low teams play part of their real schedule outside D1, which the D1-only scoreboard omits; the sim plays 56 D1 games.
  - The gap curve after the change (4 seasons, two-step): favored −.041 ± .007 sim against −.036 ± .011 real; underdog −.084 ± .012 against −.044 ± .020, a difference of −.040 ± .023 (1.7 SE). By gap bin the favored side matches within 1% beyond g = .75; the underdog side runs 4–8% low beyond |g| = .75, within 1–1.5 SE per bin. Not significant, so no gap interaction is added (owner rule). It stays a named watch item, with the joint-fit caveat above: the joint fit puts the difference at −.12 ± .03 because it trades the g² terms against the strength spread differently on real and simulated seasons.

**Team-leader rows rebuilt from three seasons** (owner decision 2026-10-04; `scripts/parse_ncaa_leaders.py`, `scripts/write_leader_benchmarks.py`, logged in `benchmark_changes_leaders.json`).
- After the schedule change, best team BA failed: .339 against .356 ± .013. Its tolerance is a prediction interval from the sim's own seasons, which tightened from ±.026.
- The four single-season team-leader rows (best team BA, best team ERA, most team HR per game, teams with ERA under 4.00) are now gated like the individual leaders. The band runs from the lowest to the highest real season, widened by 3 SE of the sim mean. Source: NCAA.com team pages 210, 211 and 323, top 50, for 2024–2026 (`data/ncaa_leaders/raw_team/`). The year mapping is checked against the 2025 scoreboard: the /2024/ table's games match each listed team's 2025 games (Coastal Carolina 69, Georgia 60, Northeastern 60).
- These are rates and counts of teams, so none is normalized to 56 games. Real seasons include the postseason and non-D1 games.

  | Row | 2024 | 2025 | 2026 |
  |---|---|---|---|
  | Best team BA | .359 Austin Peay | .337 New Mexico | .356 Georgia Tech |
  | Best team ERA | 3.78 Hawaii | 3.06 Northeastern | 3.22 Oregon St. |
  | Most team HR per game | 2.607 Austin Peay | 2.400 Georgia | 2.672 Georgia |
  | Teams with ERA under 4.00 | 6 | 12 | 12 |

- Three Phase 0 entries were wrong and are corrected. Best team BA (.356, Georgia Tech) and most team HR (Georgia, 179 HR in 67 games) were the 2026 season's values. Best team ERA (3.20, Coastal Carolina) was 2025's second-best; Northeastern's 3.06 was first.

**Offense extremes compressed: named watch item** (owner decision 2026-10-04: diagnose time-boxed; if no structural cause, one watch item). Covers qualified OBP p10, the run rule and the 15+ runs bin.
- Season and game extremes run narrower than real. In the final run: OBP p10 .3249 against .3366; run rule .121 against .152; 15+ bin .053 against .066. Team R/G SD across teams is 1.032 against 1.162, passing.
- Checked and ruled out:
  - Schedule. The strongest offenses face the same pitching as in reality: within-tier correlation of offense with opponents' run prevention .425 sim against .434 real; top-10 offenses' opponents .235 against .241. Matching on total strength already reproduces this.
  - Selection on offense and on run prevention separately. Real low teams that play P4 teams are +.073 in offense and +.081 in run prevention, against the sim's +.055 and +.098. That is within noise, so no separate weights.
  - Park netting. Recovered offense regressed on drawn total offense and the home park gives slopes .93 low, .97 mid and .81 P4, and home-park coefficients −.12, +.02 and +.05.
  - Team draw. Low-tier total offense SD averages .188 over 12 generated leagues (SD .025) against .199 configured, short because only 10 low conferences are drawn. The real season's realization is .207, inside that spread.
- The cause that remains: fit noise in team offense is .081 sim against .098 real, because runs vary less from game to game around team strength (scoreboard dispersion 2.2 against 2.6). Season team stats, single-game margins and the run distribution's tail all carry that variance. It is the cause already named for the run rule and the 15+ bin. Everything tested for it is listed above; no noise term is added.
- OBP p10 does not fit that cause cleanly, so it is listed with its own evidence. The sim's qualified OBP sits about .01 low across the distribution in P4 and mid: a level shift, not a narrower tail. League OBP matches (.380 against .3805).
  - The benchmark audit found no fault: unpooled p10 .3363 against pooled .3366; the sample teams are representative (the low-tier sample teams are weaker, 5.85 against 6.55 R/G).
  - Ablations that did not move it: ρ = 1, a 14-man bench, Gaussian HR talent.
  - Counting qualification by games with a plate appearance, as the benchmark does, fixed a .321 → .324 drop.
  - Unexplained so far; it misses its tolerance by .0009.

**Pre-PA base running per opportunity** (`scripts/build_engine_tables.py`; found when CI checked the Phase 1 engine against the new SB benchmark).
- The feed records a plate appearance at its base state after any events during it. After a steal from first, the next PA reads runner on second in 1,720 of 1,941 cases.
- The Phase 1 table divided events in each state by the PAs recorded there. That left out the PAs in which a runner left the state, and inflated every pre-PA event rate in those states: Phase 1 steal attempts ran 15% high (1.22 SB per team-game against the sample's 1.06; the old 1.29 benchmark hid it).
- Rates are now per base-running opportunity: every state a half-inning passes through between plate appearances (the state before each event, and the state the PA is recorded in). Both engines draw again after an event until none occurs.
- Phase 1 now gives 1.048 SB, .269 CS and success .796 per team-game, against the sample's 1.059 / .277 / .793. R/G, BA, OBP, SLG and the half-inning rows are unchanged within their tolerances. Every later phase was recalibrated on the new table.

**Gate changes after the base-running fix** (owner decision 2026-10-04).
- **PA per team-game.** It is gated against real data in the Phase 6 report (`league_totals_2025.pa_per_team_game`, 40.31 ± 1.0). The Phase 5 "unchanged from Phase 4" row compared it with the run frozen at the Phase 4 merge (40.53 ± .12). The per-opportunity base running moves it on purpose: fewer caught-stealing and pickoff outs, so more plate appearances (40.67 in the 20-season run). Errors and earned share were handled the same way, because Phase 6 fielding moves them.
- **40 seasons for every gate**, this phase and later (`scripts/run_phase2.REPORT_SEASONS`).
  - The fix changes the random-number sequence, so the 20-season run redrew every season. Rows at their tolerance edge moved by noise-sized amounts:
    - team R/G SD 1.032 → 1.009 (1.5 SE);
    - Contact slope .990 → .976 (1.7 SE);
    - IP of a team's 2nd pitcher 60.79 → 60.71 (0.4 SE);
    - the 50+ IP prediction interval narrowed as the sample season SD fell from 19.5 to 15.8.
  - None of these points to a systematic shift.
- **Determinism is per machine, not across machines.**
  - CI's run of the same 20 seeds disagreed with the committed report on six edge rows: Contact slope, PA per team-game, IP rank 2 and 50+ IP passed on CI and failed locally; mid-tier R/G SD failed on CI and passed locally; team R/G SD (all) failed in both.
  - Locally a season hashes identically under three `PYTHONHASHSEED`s, and package versions match the pins. CPU-dependent floating point in the linear algebra and vector math changes the draws, and the seasons diverge.
  - CI now checks two things: its own 40-season run passes every gate, and each gated row's value agrees with the committed report within `CI_AGREEMENT_Z` = 4.5 combined standard errors (`tests/agreement.py`; the report JSON records each gated row's value and SE). It no longer compares verdicts.
  - Making the simulation deterministic across machines is a watch item to close before Phase 12 (shared leagues and saves).
- **Team R/G SD (all)** joins the "offense extremes compressed" watch item. It fails on both machines (1.009 against 1.162 ± .145), and it is the same narrowing of season team stats the watch item describes.

**Contact slope, teams under 4.00 ERA, top starters' innings** (owner decision 2026-10-04, after the first 40-season run failed four rows).
- **Phase 4 Contact slope: fixed.** It ran .976–.991 in every run since Phase 6 (.99–1.007 before), and .977 ± .013 at 40 seasons.
  - Ablations, 20 seasons each (seeds 20251000–20251019; each switch redraws the seasons, so levels differ by noise of SE ≈ .005–.007). The slope is shown two ways: with the engine's recorded expectation, and with the expectation recomputed under the fielding team's reached-on-error tilt:

    | Run | Recorded | With the defense's tilt |
    |---|---|---|
    | All mechanisms on | .976 | .993 |
    | Fielding off | .991 | .991 (no tilt) |
    | Parks off | .992 | 1.007 |
    | Substitutions off | .988 | 1.005 |
    | Speed off | .985 | 1.002 |
    | Schedule matching off | .981 | .995 |

  - Cause: Phase 6 fielding tilts each in-play out toward reached on error by the fielding team's error odds (`_roe_tilt`). Contact is BABIP without reached on error, so a batter's hit share among hits and outs depends on the defense he faces: an error-prone defense leaves fewer outs. The engine recorded the untilted expectation. Strong hitters face P4 defenses, which make fewer errors, so they read as underperforming (residual per unit variance −.0046 for P4 batters, +.0073 low; −.0012 and +.0018 with the tilt).
  - The tilt term is −.014 to −.017 in every run with fielding on and zero with it off. With it, the slope averages 1.000 over the five fielding-on runs. Parks, substitutions, speed and schedule matching add nothing beyond noise.
  - Fix: the engine records the BABIP expectation against the defense actually faced, exact under the tilt (`engine.game2._babip_vs`), as it already did for the opposing pitcher and park. The fielding model is unchanged: reached-on-error does replace outs in real box scores, and the ratings test adjusts for the defense the way it adjusts for the pitcher. No draw changes, so no other row moves.
- **Teams with ERA under 4.00: watch item "teams under 4.00 ERA".** 15.5 at 40 seasons against the 2024–2026 band 6–12 ± 2.1.
  - The cheap check: the engine's team draw (tier mean, conference and team effects on the real conference structure) plus the scoreboard fit's own estimation noise, 4,000 replications, against the fitted run prevention of the 2025 scoreboard (fit without parks, the totals the engine draws).
  - The tail matches. Ranks 1, 2, 3, 5, 10, 12, 15, 20 and 25 of fitted run prevention sit at −.67 to +.66 SD of the model's: real .713 / .694 / .688 / .657 / .550 / .525 / .486 / .459 / .446, model medians .766 / .705 / .668 / .618 / .545 / .525 / .497 / .460 / .429. The top-12 mean is .623 real against .612 ± .050. Teams above .5: 12 real, 14.5 model (90% range 7–23).
  - So the draw is not the cause. The count is set downstream of the draw (how run prevention converts to earned runs per nine for the best staffs), and it is reported, not gated.
- **Top starters' innings: watch item, re-checked in Phase 7.** The 2nd pitcher's IP (60.71 against 65.25 ± 4.46) and pitchers with 50+ IP (785 against 821 ± 32). The shortfall is in weekend starts (#2: 46.3 against 50.3) and relief (6.9 against 9.3). Phase 7's conference tournaments and postseason change how rotations are used, so the rows are re-checked there.
- **Closing a watch item** needs a 40-season run from now on (owner decision 2026-10-04).

**Result (20 seasons, seeds 20251000–20251019): every gated Phase 1, 2, 4, 5 and 6 row passes.**
- The rows that had failed now pass. Team RA/G SD is 1.636 against 1.596 ± .220. Low batting vs mid pitching is 5.59 against 5.88 ± .66. The tier-mean recovery rows are all within 3 SE.
- P4 batting vs low pitching is 9.55 against 9.82 ± 1.22. P4 RA/G mean is 5.54 against 5.77 ± .45 and is gated again.
- The new team-leader rows sit inside their 2024–2026 bands: best team BA .339, best team ERA 3.08, most team HR per game 2.53, teams under 4.00 ERA 13.6 (band 6–12 plus a pad of 2.8).
- Watch item "offense extremes compressed", reported and not gated: run rule .121 against .152 ± .017; 15+ bin .053 against .066 ± .011; OBP p10 .3249 against .3366 ± .0108.

## Bibliography

- Jones, M. C. and Pewsey, A. (2009). Sinh-arcsinh distributions. *Biometrika* 96(4), 761–780.
- Kiefer, J. and Wolfowitz, J. (1956). Consistency of the maximum likelihood estimator in the presence of infinitely many incidental parameters. *Annals of Mathematical Statistics* 27(4), 887–906.
- FanGraphs, Michael Baumann, "The Ridiculous Firewagon Offenses of College Baseball," Feb 13, 2026 — https://blogs.fangraphs.com/the-ridiculous-firewagon-offenses-of-college-baseball/
- NCAA, "Division I Baseball Statistics Trends (1970-2018)" — http://fs.ncaa.org/Docs/stats/baseball_RB/reports/TrendsYBY.pdf
- Baseball America, "The NCAA Division I Home Run Record Has Been Broken, Again" (2024) — https://www.baseballamerica.com/stories/the-ncaa-division-i-home-run-record-has-been-broken-again/
- ACC 2025 overall statistics — https://theacc.com/stats.aspx?path=baseball&year=2025
- SABR-Tooth Tigers (Medium), "When does throwing a strike matter the most in college baseball?" — https://medium.com/sabr-tooth-tigers/when-does-throwing-a-strike-matter-the-most-in-college-baseball-a8023d61a531
- rfrey22 (Medium), "More About Counts in D1 Baseball" — https://rfrey22.medium.com/more-about-counts-in-d1-baseball-9ac3ec4c86c2
- College Sports Commission, Roster Limits — https://www.collegesportscommission.org/roster-limits/
- NCAA Division I Notification of Transfer Windows (2025-26) — http://fs.ncaa.org/Docs/eligibility_center/Transfer/DIUG_Windows.pdf
- The Baseball Collegian, "NCAA Baseball Revenue Sharing" — https://baseballcollegian.com/blog/ncaa-baseball-revenue-sharing-who-offers-full-scholarships/
- NCAA.com, single-season HR leaders (updated May 2026) — https://www.ncaa.com/news/baseball/article/2025-06-22/di-college-baseballs-single-season-home-run-leaders
- Wikipedia, 2025 and 2026 NCAA Division I baseball seasons
- NCAA.com scoreboard JSON feed (data.ncaa.com/casablanca), 2025 D1 baseball, fetched 2026-09-30 — https://data.ncaa.com/casablanca/scoreboard/baseball/d1/2025/05/17/scoreboard.json (one file per day)
- WMT Live Stats API (api.wmt.games), 2025 D1 baseball schedules, box totals and play-by-play actions, fetched 2026-09-30 to 2026-10-01 — https://api.wmt.games/api/statistics/teams/{ncaa_team_id}/games and https://api.wmt.games/api/statistics/games/{game_id}?with[]=actions
- Sidearm Sports team stats pages, 2025 season totals for 13 programs, fetched 2026-09-30 — e.g. https://rolltide.com/sports/baseball/stats/2025
