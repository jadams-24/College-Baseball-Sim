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
  - Unearned runs checked and ruled out (owner request 2026-10-05). Real: NCAA.com team ERA page, top 50 by ERA, R and ER allowed (`data/ncaa_leaders/raw_team/s211_*`). Sim: the same top-50-by-ERA selection, 8 seasons:

    | Top 50 by ERA | Real 2024 / 2025 / 2026 | Sim |
    |---|---|---|
    | Earned share of runs allowed | .869 / .866 / .867 | .900 ± .002 |
    | Unearned runs per game | .67 / .65 / .65 | .46 ± .01 |
    | Runs allowed per game | 5.05 / 4.80 / 4.81 | 4.61 ± .04 |

    Overall the earned share matches (.880 sim against .882). The sim's best teams allow too few unearned runs, not too many: with the real top-50 earned share the count under 4.00 would rise from 12.4 to 17.9 on these seasons. What is low is their total runs allowed. Real top teams' season totals include conference tournaments and the NCAA tournament (5–10 games against strong opponents), which the sim does not play before Phase 7. Re-checked once Phase 7's postseason is in.
  - Separate finding, not the cause of this row: the best teams' unearned runs (.46 against .65 per game). In the sim errors fall with team run prevention (`fielding6.team_error.slope_d`), so selecting the best staffs selects fewer errors; real top-ERA teams have a lower earned share than average (.867 against .882). Reported with the watch item.
- **Top starters' innings: watch item, re-checked in Phase 7.** The 2nd pitcher's IP (60.71 against 65.25 ± 4.46) and pitchers with 50+ IP (785 against 821 ± 32). The shortfall is in weekend starts (#2: 46.3 against 50.3) and relief (6.9 against 9.3). Phase 7's conference tournaments and postseason change how rotations are used, so the rows are re-checked there.
- **Closing a watch item** needs a 40-season run from now on (owner decision 2026-10-04).

**Result (40 seasons, seeds 20251000–20251039): every gated Phase 1, 2, 4, 5 and 6 row passes.**
- Phase 4 Contact slope .994 ± .014 (was .977 with the untilted expectation; every other number is identical, since the fix changes no draw).
- PA per team-game 40.66 against 40.31 ± 1.00. Team RA/G SD 1.680 against 1.596 ± .203. P4 batting vs low pitching 9.58 against 9.82 ± 1.11. The tier-mean recovery rows are all within 3 SE.
- Team-leader bands: best team BA .338 (.337–.359), best team ERA 2.98 (3.06–3.78, pad .13), most team HR per game 2.51 (2.40–2.67).
- Watch items, reported and not gated:
  - "offense extremes compressed": run rule .121 against .152 ± .016; 15+ bin .054 against .066 ± .010; OBP p10 .3257 against .3366 ± .0107; team R/G SD (all) 1.015 against 1.162 ± .143.
  - "top starters' innings": 2nd pitcher's IP 60.72 against 65.25 ± 4.46; pitchers with 50+ IP 785 against 821 ± 32.
  - "teams under 4.00 ERA": 15.5 against 6–12 ± 2.2.
- CI's own 40-season run of the fixed engine (commit 9627c38) passed every gated row; only the agreement check failed there, against the stale committed reports this run replaces.

### Phase 7: season and world (2026-10-05, owner decisions after the Phase 6 merge)

**Sources and confidence grades.**

| Data | Source | Grade |
|---|---|---|
| Scoreboard feed 2015-2019, 2021-2025 | data.ncaa.com casablanca scoreboard (`data/ncaa_<season>/scoreboard`) | B: 2015-2016 leave many results empty; 2017-2018 lack conference names; 2025 conference tournament games are mostly `TBA` placeholders |
| Brackets 2015-2025 (no 2020) | English Wikipedia tournament pages (`data/ncaa_brackets`) | B: secondary source; 2015-2018 regional hosts inferred (the 1 seeds); every season validated (64 teams, 16 regionals, winners consistent through the CWS); spot-checked against the known 2025 field |
| Bracketing principles | NCAA 2024-25 and 2025-26 prechampionship manuals (official PDFs) | A |
| Conference tournament formats 2025 | Wikipedia per conference, NEC and Big East confirmed on official pages (`data/conf_tournaments`) | B |
| 2025 and 2026 results with sites, canceled games | WarrenNolan team schedules (`data/ncaa_2025/warrennolan`, `data/ncaa_2026/warrennolan`) | B: every 2026 D1 record matches the NCAA's published one; about 106 team-games carry a different site label (conference tournaments at a member's park, alternate-site home series) |
| Pre-selection RPI 2026 | https://www.ncaa.com/rankings/baseball/d1/rpi, "Through Games May. 24 2026" (the page froze before selection) | A |

Not reachable: web.archive.org (egress policy), d1baseball.com and most Sidearm conference sites (bot protection). Not used.

**RPI.** `engine.rpi` implements the NCAA formula (0.25 WP + 0.50 OWP + 0.25 OOWP, Division I games only, WP weighted 0.7 for a home win and 1.3 for a road win, 1.3 for a home loss and 0.7 for a road loss, neutral 1.0; OWP leaves out the games against the team). On the 2026 results through May 24 its ranks agree with the NCAA's published pre-selection ranks at Spearman .99994 (206 of 308 exact, 303 within 3, 54 of the top 64 exact). Without the site weighting the agreement drops to .9930 (20 exact), so the weighting is in the published RPI. The remaining gaps are 7 tie games (left out) and the site labels above.

**Cancellations, not shorter schedules** (owner decision). WarrenNolan lists canceled games: 2.72% of regular-season team-games in 2025-2026 (by month 3.3% Feb, 2.2% Mar, 2.4% Apr, 3.7% May). Each scheduled sim game is canceled at its month's rate and never made up. Real teams schedule 53.7 games (32% and 30% of teams schedule the maximum 56), so they play 52.3; the sim schedules 56 and plays 54.4. The rest of the gap is scheduling, which is not modeled; games per team is reported, not gated. Season totals in the Phase 2 and 6 rows that are 56-game equivalents are now scaled per team by 56 / games played, as the benchmarks scale real teams.

**Conference tournaments.** All 29 published 2025 formats are implemented from building blocks (single and double elimination with byes, play-ins, pools of three, best-of-three series, two four-team brackets). Each reproduces its published game range and qualifier count. The formats inferred from the 2025 game sequences (WarrenNolan event labels; the feed's tournament games are placeholders) agree with the published ones: teams 29/29, games 29/29, champion = automatic bid 28/29 (ASUN: weather ended the final, Stetson got the bid by conference policy, as published). Elimination patterns agree (one loss in single elimination, two in double elimination, mixed with play-ins and pools). Seeds come from conference win%; the site from the published 2025 site: neutral, the top seed's park (Horizon, Ivy), the higher seed's campus (Patriot, Southland brackets), or a predetermined member's park, drawn at random in the fictional league (GUESS, GUESSES.md).

**Selection and seeding** (`scripts/build_phase7_selection.py`, few predictors, every season with complete results: 2017-2019, 2021-2025). Logistic regressions with a season intercept; in the engine the open slots go to the largest score + logistic noise, the same model.
- At-large among non-automatic teams: RPI z-score 11.2 ± 1.0, P4 1.28 ± .35 (likelihood ratio 13.7 keeps it). In-sample, the model's top picks match 90% of the real at-large teams.
- National seeds among the field: RPI z-score 9.8 ± 1.2; P4 adds nothing (LR 1.3). 82% in-sample agreement.
- Grade B: RPI recomputed without neutral-site flags (the feed has none) and, in 2025, without most conference tournament results.
- Measurement-error correction (owner decision 2026-10-05). The sim selects on the exact RPI, the fit used the feed's, and error in a predictor flattens a logistic slope. The feed's 2025 RPI z differs from the exact one (WarrenNolan games with sites and conference tournaments; 307 of 307 teams matched) by SD .0927 (correlation .9957); neutral flags alone account for .030 (2025) and .028 (2026). Under the probit approximation, observed slope² = true² / (1 + true² σ² / (π²/3)): at-large coefficients × 1.221 (RPI z 13.71, P4 1.56), national seeds × 1.156 (RPI z 11.36). The 2025 error is applied to every fitted season (GUESS: only 2025 can be measured).
- Check: the same models refitted on the exact RPI of 2025-2026 (70 at-large bids, 32 national seeds) give RPI z 18.6 ± 4.4 and P4 2.64 ± 1.00 (at-large) and RPI z 14.5 ± 3.8 (national seeds). Rule (owner): a corrected coefficient within one SE of the refit is validated. National seeds: 0.83 SE, **validated**. At-large: 1.10 and 1.07 SE, **not validated**, stays a GUESS (GUESSES.md). The refit lies above even the corrected slopes; with two seasons it cannot separate a steeper committee in 2025-2026 from sampling (single-season feed slopes in 2017-2025 range 7.7-17.0). The engine uses the corrected coefficients.

**Bracket and postseason.** National seed k hosts regional k; the other 48 teams fill the 2, 3 and 4 lines in the order of the seed score and are placed at random with no two conference mates in one regional (the published principle; the sim has no geography). Super regionals pair 1-16 ... 8-9 at the better national seed's park; the CWS is two four-team double-elimination brackets and a best-of-three final at a neutral site. Neutral-site games have no home edge and a league-average park. Tournament starters come from a conditional logit on role and rest fitted on 205 starts from May 20, 2025 (wk1 +5.0, wk2 +4.4, wk3 +3.4 against deep relievers; 4-5 days' rest about -1.5 against 6+).

**Benchmarks** (benchmarks.json `season_world_2015_2026`, built by `scripts/build_phase7_*.py`, `scripts/write_phase7_benchmarks.py`):
- Seeds (160 regionals, 10 seasons): hosts win their regional .625 ± .038; top-8 national seeds reaching Omaha 4.10 ± .33 of 8; national seeds among the CWS teams (2018 on) 5.43; CWS slots P4 73, mid 6, low 1 of 80; champion P4 in 9 of 10.
- Field: at-large P4 26.0, mid 7.1, low 0.4 per season; 10.6 conferences with more than one bid; worst RPI rank given an at-large bid 56.9 (47-80), best rank left out 30.2 (24-34).
- Postseason: the host at its park wins .734 of regional games and .601 of super regional games; in regional games without the host the better seed wins .630.
- Conference tournaments: a regular-season (co-)champion takes the automatic bid in .425 (181 tournaments, 2019 and 2021-2025).
- Standings (D1 games before conference tournament week, 2017-2019 and 2022-2025): win% SD P4 .121, mid .136, low .147; best record .821-.917.

**Benchmarks on the current conference map** (owner decision 2026-10-05, after the first 40-season run failed nine rows).
- The failing rows (P4 mean RPI and the RPI at ranks 1/16/32/64, at-large bids by tier, conferences with more than one bid, P4 win% spread) all measured P4 strength against benchmarks averaged over 2015-2025. The sim builds the 2025 conference map. Under that map the real 2025 season matches the sim: P4 against mid-tier nonconference win% .757 (sim .757), at-large P4/mid 31/4 (sim 30.2/4.2), multi-bid conferences 8 (sim 7.5). Earlier seasons differ because of realignment (a 12-team Pac-12, smaller P4 conferences, 31 automatic bids before 2025's 29), and mapping them onto 2025 tiers counts some former conference games as P4-mid nonconference games (P4 win% in those games .678, .688, .709, .757 in 2022-2025).
- These rows are now benchmarked on 2025-2026, the two seasons played under the current map (`scripts/build_phase7_current.py`, benchmarks.json `season_world_2015_2026.current`), from the WarrenNolan results (neutral-site flags, complete conference tournaments) and the published brackets (the 2026 bracket added, validated). 2025 and 2026 are reported separately and together. **The sim's inputs were fitted to 2025 data, so 2026 is the independent check.**
- Tolerance: 3 × the combined SE of the sim mean and of a two-season real mean, the latter from the season-to-season SD estimated on the 2022-2025 swings of the same rows (successive-difference SD; GUESS, GUESSES.md).
- Seed rates and home field stay on 2015-2025 (owner decision). The multi-season blocks stay in benchmarks.json for reference.

**P4 against mid-tier, 2025 alone** (nonconference regular-season games, WarrenNolan): P4 win% .762 (2026 .756), run margin 4.00 (3.93), margin SD 5.99 (5.95); sim .757, 3.64, 5.66 (8 seasons). Win% matches; the margin spread is about 5% tight, the watch item "offense extremes compressed". With the real spread (normal margin model, win probability Phi(Phi^-1(p) x SD ratio)) the better seed's win% in regional games without the host and the host's win% would each fall by about one point per game; the report prints the numbers from the run.

**Scheduled games** (owner decision 2026-10-05). Each team draws the number of regular-season games it schedules from the 2025-2026 distribution (mean 53.7; 26.7% schedule exactly 56, 31% at least 56; 10th percentile 50). Real teams below 56 lose midweek games (Thu-Sun games stay near 42 from 51 scheduled up; Mon-Wed games fall from 13.4 at 56 to about 10 at 50-52), so the sim drops midweek games until both teams reach their targets (GUESS for which games go). Targets above 56 (4.2%, exempt trips) are capped at 56; below 42 (1.8%) at 42. Cancellations (2.72%) apply on top. Games played per team is gated: 52.25 real (52.36 in 2025, 52.14 in 2026).

**Teams under 4.00 ERA: definitions.** The NCAA.com team ERA page counts every game of a season, conference tournaments and the NCAA tournament included (its 2025 data year shows Northeastern 60 games, Coastal Carolina 69 through the CWS final), so the 6-12 range is full seasons. The sim's count uses the same definition: regular season plus its postseason (it has no non-Division I games). The unearned-run check's numbers are in the Phase 7 report (sim) against: earned share .882 overall (WMT play-by-play, 2025), .869 / .866 / .867 for the 50 lowest-ERA teams in 2024 / 2025 / 2026, unearned runs .67 / .65 / .65 per game for them.

**Team leaders on full seasons** (owner decision 2026-10-05). The Phase 2 team-leader rows (best team ERA and BA, most team HR per game, teams under 4.00 ERA) now read the sim's regular season plus its postseason, as the NCAA.com team pages count real seasons. The rest of the Phase 2 report stays on the regular season.

**Pitching against fielding** (owner request 2026-10-05, the lead from the unearned-run check). Real 2025, every Division I team (NCAA.com team pages 211 and 212, all pages, 299 teams, full seasons; `scripts/build_phase7_era_fielding.py`, benchmarks.json `season_world_2015_2026.era_fielding`, conf B: full seasons include non-Division I games). Correlation across teams of ERA with errors per game .655 (with fielding percentage −.680); of runs allowed per game with errors per game .721. Errors per game 1.150 for all teams, .866 for the 50 best by runs allowed per game, .912 for the 50 best by ERA; earned share (mean of team ER/R) .870 for all, .866 for the 50 best by ERA. The engine draws a team's error log-odds as slope × run prevention d + noise (slope −.720, 133 box-score teams, Phase 6). Refitted on the 298 NCAA.com teams matched to the 2025 scoreboard fit, the slope is −.685, residual true SD .127 (engine total .136), so the slope is not the cause. Sim (40 seasons, full seasons): correlation of ERA with errors per game .727, of runs allowed per game with errors per game .801; errors per game 1.088 for all teams, .730 for the 50 best by runs allowed, .757 for the 50 best by ERA; earned share .883 for all, .901 for the 50 best by ERA. The owner's reading holds: the sim's best run-prevention teams field better than real ones (17% fewer errors per game for the 50 best by ERA, against 5% fewer for all teams), and their earned share is higher. Part of it follows from the same elite run-prevention tail (more teams under 4.00 ERA; errors follow total run prevention at the fitted slope, so more extreme teams make fewer errors). Not fixed in this PR (owner: report it unless it is a one-line cause).

**40-season run, 2026-10-05.** Every gate passes (Phases 2, 4, 5, 6 and 7). Team leaders on full seasons: best team ERA 3.056 (band 3.06–3.78, pad .122), best team BA .338, most team HR per game 2.462; teams under 4.00 ERA 13.8 (watch item). Worst RPI rank given an at-large bid 56.9 against 50.0 ± 8.9 (60.0 before the measurement-error correction). RPI of the team ranked 64 .5487 against .5433 (reported, watch item).

### Engine restructure (PR A, 2026-10-06, owner approval of the in-game management plan)

**Why.** The engine drew each plate appearance's outcome first and then a pitch sequence to match. That is right for statistics, but nothing can happen between pitches: no steal on 2-0, no pitchout. One manager object answered for both teams and drew from the game's random stream, so a game could not change hands or be saved and resumed reproducibly. PR A changes the engine's structure only. No decision changes yet; that is PR B.

**Forward play, exact.** With the matchup's outcome probabilities m (the reached-on-error tilt for the fielding team included) and the pitch chain's absorption probabilities h_o(c), the chain transformed by H(c) = sum_o w_o h_o(c), w_o = m(o) / h_o(0-0), is played one pitch at a time (`engine/pitch.py` `forward`). Its law of (outcome, sequence) is exactly the outcome-first method's: the sequence given the outcome is the conditioned chain (the Doob h-transform), and the outcome law is m. Check (`scripts/check_forward_chain.py`, `reports/forward_chain_check.md`):
- 10,000 matchups from a generated league, 5,000,000 plate appearances by each method.
- The forward chain's exact outcome law equals the matchup's to 4.4e-16.
- Two-sample tests: PA outcome p .48, count the PA ended at .11, pitches per PA .16, pitch events by count .70, outcome x pitches .18, counts reached (Bonferroni over 12) .81.
- Matchup by matchup against the exact law: p .58 (old), .90 (new).
- Pitches per PA 3.8620 against 3.8623.

**Session, controllers, streams.**
- `GameSession` plays a game in phases, with a pause point before every pitch: `run(stop)`, `sim_ahead` (next pitch, plate appearance, half inning, inning, three innings, end of game, with the AI managing a side meanwhile) and `save` / `load` (pickle; complete with the engine, or light with a live engine reattached).
- Each team has its own controller (`engine/control.py`): the batting side for pinch hitters, pinch runners, steals and bunts; the fielding side for relievers, defensive changes, intentional walks and pitching changes.
- The engine's draws come from a Philox stream positioned per plate appearance. Each team's AI draws from its own stream positioned by (decision kind, plate appearance, call number), and is positioned only if the decision draws (`engine/rng.py`).
- Tests (`tests/test_session_determinism.py`, 200 games each):
  - pause at a random pitch, save, discard, restore and resume: identical pitch-by-pitch log; three games resumed in a fresh process from a complete save;
  - a scripted human giving the AI's answers takes over random teams at random pitches, with sim-ahead stops: identical log;
  - the same fixed policy given as a human controller and as an AI manager: identical log;
  - a pause before a 2-0 pitch with a runner on first and second open, restored. The called steal there is PR B.

**40-season run (2026-10-06).** Phases 2, 4, 5 and 6 pass; Phase 7 failed one row, the RPI of the team ranked 32, 0.5734 against 0.5692 ± 0.0039 (the old engine's run: 0.5723, passing by .0004). Across all 234 gated rows the new run agrees with the old engine's (mean shift −0.04 SE, none beyond 3 SE, largest 2.4), so the restructure moved nothing systematically. Owner decision 2026-10-07: rank 32 joins rank 64 in the watch item "offense extremes compressed" (the same cause: the middle of the RPI table runs high because records spread too little from game to game). The Phase 7 report was rebuilt from the run's saved aggregates (`scripts/run_phase5.py --from-reports`, which reproduces the reports exactly but for the date).

**Run-rule benchmark (owner decision 2026-10-07).** At the start of the variance-fix stage, after PR B, the benchmark becomes the direct count from all games (about .141–.144; real-data sizes above) and the engine's early-ending rate is refitted from all games, not the play-by-play subsample, together, so engine and benchmark change once.

**Cost.** One season takes 220 s against 152 s single-threaded: each matchup's chain needs its full absorption matrix (one 12 x 12 solve), and decisions go through the controllers. Changing the streams changed every seed's results; all reports were regenerated on the 40-season run below.

### "Offense extremes compressed": real-data sizes (2026-10-06, owner: sizes only, no fixes)
Measured on committed data, no simulation (`scripts/diag_sizes.py`, `reports/diagnosis_sizes.md`):
- **Non-D1 games.**
  - 90 of the 8,079 scoreboard games, not the ~141 estimated: 51 New Orleans D1 games are dropped by a name mismatch ("LSU New Orleans" in `teams_2025.csv`). Not changed.
  - Removing the 90: run rule .1524 → .1509 (5% of the gap), 15+ bin .0664 → .0650 (11%), OBP p10 .3366 → .3354 (10%). Team R/G SD is already D1-vs-D1.
- **Run-rule benchmark definition.** P(ended early | margin 10+) is .785 in WMT's games and .724 in the rest (difference .061 ± .024). A direct count on WarrenNolan's innings gives .141–.144, against the product estimator's .152. The engine's "rule in effect" probability uses the WMT figure (.7805). For owner decision.
- **Fielding independent of pitching (candidate 10): not supported.**
  - Corrected for noise in d and game noise shared with d, the real error residual SD is .113 ± .011 (slope −.762 ± .040). The engine's is .136 (slope −.720), already as independent as the data or more.
  - The true real ERA–errors correlation is .80 ± .04 (observed .655). The sim's lower game noise can explain at most a quarter of its tighter observed correlation.
  - Unearned share: .134 for the real 50 best by ERA, about .099 in the sim.
- **Starter day-to-day form (candidate 11):** −8% ± 14% of the missing variance (95% upper bound 19%).
- **Error clustering (candidate 12):** 2+ error half-innings are 1.63 times the binomial expectation; 2.9% ± 2.4% of the missing variance (upper bound 8%).
- Running total for candidates 11 + 12: −5% (upper bound 23%).
- Indication only: in WMT, team-game dispersion splits 2.40 within half-innings and .42 between them. The sim's 2.22 total is below the real within-half part alone, so the missing variance likely sits between innings.

### Decisions that change outcomes (PR B, 2026-10-07, owner approval 2026-10-06/07)

**Steals before each pitch.** The batting side is asked before every pitch when the lead runner can steal (runner on first with second open, else on second with third open). The AI answers with the play-by-play's attempt rate for that pitch: a per-pitch hazard by count, outs, base, score and inning (`scripts/build_prb_steals.py`, `data/ncaa_2025/derived/prb_steals.json`, `reports/prb_steals.md`), plus the runner's speed, the pitcher's hold and the tier cell. A steal resolves on a ball or a strike (on a foul the runner goes back, on a ball in play he was running and the advancement tables apply). Success: by count, outs and base, plus speed, the catcher's arm and the tier cell. Every runner's destination and any error come from the play-by-play's steal plays in that base-out state, split into plays with no runner out and plays with one, so double steals move the trailing runner as in the data.
- **The data.** The feed writes a steal as its own line between two results, stamped with the pitch count at the end of the plate appearance. The pitch of a mid-PA steal is never recorded. **Correction:** the "41 games with exact-count steals" reported on 2026-10-06 were steals written into the previous batter's line, not live stamps; no game records the pitch. The model is fitted by EM on the pitch path (which ball or strike is unknown), with the 389 steals written into a plate appearance's own line on its last pitch entering with their position known. Inning-ending caught stealing leaves no plate appearance: the two-out attempt and success levels are set to the direct counts (attempt factor 1.256, success .799).
- **Validation (replaces the held-out exact-count check, which the data cannot support).** Fitted on 80% of games, the model predicts in the other 20% the share of eligible plate appearances with an attempt by length and final count, and the last-pitch attempts by count. Totals agree (932 predicted, 969 observed), but by length p < 1e-9 and by final count p < 1e-5: real attempts concentrate in long plate appearances and full counts more than a per-pitch hazard on the path before the attempt can produce. A pitch-number term does not fix it: its coefficients are not identified next to the count terms (±3 logits), and the final-count χ² stays at 51.8 against 49.9. Candidate causes, not yet measured: a steal changes the rest of its plate appearance (with a runner in scoring position the pitch mix shifts: 3.61 pitches per PA with a runner on first only against 3.72 on second only); batters take pitches while a runner who means to go is on; and the real sample's selection (plate appearances in which a wild pitch, passed ball, pickoff or balk came first are left out, and those are more often long plate appearances, while the sim draws those events before the plate appearance). The last-pitch steals, whose count is exact, agree by count (p .03).
- **Box-score scoring.** Steal attempts per team-game count every runner who tries (a double steal is two), as box scores do. A runner picked off while breaking is charged a caught stealing in the box score; the play-by-play files him as a pickoff (131 of 532 pickoff outs, `prb_inputs.json` `pickoff_scoring`). The sim scores the same share of its pickoff outs as caught stealing (scoring only, no change in play). That is why box success (.760) is below the play-by-play's (.785).
- **Success offset centring.** The fitted success rate is the attempting runners', and a runner's attempt and success propensities share one speed factor, so the success offset is centred on attempt-weighted runners (`engine/game2.py` `_centre_success`). Centring on all runners gave .799 against the play-by-play's .785.

**Bunts and intentional walks.** The AI calls a bunt or an intentional walk at the start of a plate appearance with the play-by-play's rate by base state, outs, score, inning and lineup slot (`scripts/build_prb_decisions.py`, `data/ncaa_2025/derived/prb_inputs.json`). A called bunt plays the completed bunts' pitches before two strikes, then swings away (GUESS). A bunt in play takes its result and every runner's destination from the bunt table by outs and bases (sacrifice, bunt single, out, fielder's choice, error). The AI's call rate is the data's bunt rate divided by the chance a called bunt ends in a bunt in play. An intentional walk is awarded without pitches (NCAA 8-2-b). A batter who swings away plays his season law with his lineup slot's average shares of called bunts and intentional walks taken out, m_sw = (m − b̄·law_bunt − ī·e_BB) / (1 − b̄ − ī) (`prb_inputs.json` `by_slot`; law_bunt pooled over the states bunts happen in), so over a season his totals are m again while each state keeps its own mix, as in the data. A human who swings away faces the same m_sw: human and AI odds are equal. A first version subtracted each state's own b and i. Where the AI walks a batter more often than his season walk rate, the subtraction clipped at zero and added walks: the 40-season run had intentional walks .101, the Phase 4 Eye intercept off by +.0022 and runs per team-game .085 lower. **Timing.** The pinch hitter, the intentional walk and the bunt are decided as the plate appearance begins, in the state the data's models were fitted on (the base state before any wild pitch, passed ball or steal during the plate appearance). Asked after the engine's base-running draws, the state had more runners on second (8.9% of plate appearances against 7.4%), and intentional walks came out 13% high. **Pitch chain.** The Phase 5 base chain is solved on simulated seasons so their pitch events by count equal the data's (`scripts/solve_phase5_chain.py`). With called bunts playing their own pitches, it was re-solved on this engine. The chain fitted without bunts gave 13.7% one-pitch plate appearances against 13.1%. A bunt is the feed's bunt flag or a sacrifice hit written without the word ("grounded out to p, SAC"): 10% of sacrifice hits carry no flag, so bunts are .720 per team-game, not .681. Sacrifice hits come only from called bunts.

**Bunt situations.** The AI's bunt rate is fitted on outs x occupied-bases cells plus score, inning and slot, not on bases and outs as separate main effects. What a team bunts for depends on both together. The main-effects fit put 16% of bunts with nobody on and nobody out against 10.4% in the data, and 0.8% with runners on first and third and one out against 5.1%. Bunt hits came out .217 per team-game against .191.

**The Phase 4 forward test with decisions.** A plate appearance's expected K, BB, HR, BABIP and extra-base share are those of the law it played: the swing-away law, a called bunt's law (called as the plate appearance began), or a walk for an intentional walk. This follows the same principle as "the forward test's expectation includes the defense faced" (Phase 6). Bunt outcomes do not depend on the batter, and the swing-away law is not his season law. Measured against the matchup law, the second 40-season run failed three rows: Contact BABIP intercept +.0032 (tolerance ±.0023), Control BB intercept −.0060 (±.0029), Stuff K slope 1.006 (±.005).

**Plate appearances cut off by a caught stealing (Phase 4 test).** A caught stealing for the third out during a plate appearance ends it unrecorded; the batter leads off next inning. Steals are tried more at two strikes, so the cut-off plate appearances are more often ones headed for a strikeout, and the completed ones are selected: Avoid K intercept −.0024 ± .0022 against −.0009 in the PR A run, of which −.0009 is this (3,000-game check: .25% of plate appearances cut off; their ex-ante K .193, K probability at the count reached .250). The forward test's expectation is made exact: each cut-off plate appearance adds its ex-ante K, BB and HR minus their probabilities at the count it was cut off at (the forward chain's outcome law at that count averages to the ex-ante law). Bookkeeping only; play unchanged (identical game logs).

**Calls with no data (GUESSES.md):** pitchout, hit-and-run, intentional ball and mound visit. Only a human makes them; the AI never does, so no gated row moves. The NCAA limits apply (`data/ncaa_rules/`, 2025-26 rules book): three free coach trips a game (one more in extra innings), a second trip to the same pitcher in an inning removes him, no second trip while the same batter is up (9-4); an intentional walk without pitches (8-2-b); a walk after a pitching change at 2-0, 2-1, 3-0, 3-1 or 3-2 is the previous pitcher's (10-22-b); a foul bunt with two strikes is a strikeout (10-23).

**Data-based or guess:**
- Data: steal attempt and success by count and game state, double-steal destinations, pickoff scoring, bunt and intentional-walk rates by game state, bunt outcomes and destinations, the pitcher's hold on attempts (SD .470 logit).
- Guess: two-strike bunts, the bunting batter's pitch mix (completed bunts only), the hold's effect on success (not detectable, SD 0), pitchout, hit-and-run, mound visits, no straight steal of home.

**Gate decisions (owner, 2026-10-07).**
- Steals by pitch path are gated on the sample free of selection. That sample is every plate appearance that began with a lead runner able to steal and has a ball or strike, whatever base running came first. An attempt is any steal or caught stealing during it, and success is that of the first. It is computed the same way on the play-by-play (`scripts/build_prb_decisions.py` `selection_free()`) and on the simulated plate appearances.
- The first-event sample stays as a diagnostic. It leaves out the plate appearances in which a wild pitch, passed ball, pickoff or balk came first, which are more often long ones; the engine draws those events before the pitches, so the sim has no such selection. On the play-by-play the selection raises the attempt rate at 7 pitches from .170 to .193.
- Steal attempts per team-game and the success rate stay gated.
- In the Phase 5 "PA-level outcomes unchanged from Phase 4" block, runs per team-game and ERA are moved on purpose by the decisions (sacrifice bunts, intentional walks, steals) with every rate unchanged. They are gated against real data instead, as Phase 6 did for PA per team-game, errors and earned share: runs per team-game in the Phase 2 report and ERA in the Phase 6 report (`league_totals_2025.era`, 6.08 ± .30).

**Where the runs went (owner request 2026-10-07: decompose the drop before merging).**
- The 40-season run has 6.64 runs per team-game against the frozen Phase 4 baseline's 6.74. Of that gap, −.027 was already in PR A (6.715).
- Decomposition: seven variants on the same 8 seasons (seeds 20251000–07; same leagues and schedules), paired differences in runs per team-game:
  - PR A code against PR B code with decisions off (pinch hitter, intentional walk and bunt asked at the start of the plate appearance): −.0005 ± .0018.
  - The Phase 5 chain re-solved on the PR B engine: +.025 ± .014.
  - Steals decided before each pitch: −.058 ± .012 before the fix below, −.028 ± .015 after.
  - Called bunts: −.042 ± .009.
  - Intentional walks: −.015 ± .007.
  - Interaction: +.014 ± .019.
  - Total from PR A: −.047 ± .014.
- **A bug, fixed.** In the data, an opportunity that held a steal was followed by another, where a wild pitch, passed ball, pickoff or balk could come next. With steals moved to the pitches, a steal drawn from the pre-PA table ended the draws, and those later events were lost: wild pitches .782 per team-game against .823, other events 4–5% low, and fewer runs on singles and sacrifice flies. Now the steal draw is skipped and the draws go on, which restores those events (wild pitches .837).
- **The rest is legitimate.**
  - Steals: the per-pitch steals' own run value is lower (by the sim's run expectancy, +.018 per team-game against +.038 for the table's). The attempts are spread over counts and outs as the play-by-play has them, while the table drew them all before the first pitch.
  - Bunts: a sacrifice trades an out for a base, at the data's rate in the data's situations.
  - Intentional walks: called where they lower the run expectancy.
  - Every rate is unchanged (Phase 5 block), and bunts, sacrifice hits, bunt hits, intentional walks, steals and success match the play-by-play (Phase 6 report).
- Script: `scripts/decompose_decisions.py` (one season per variant, via `config.decisions.FEATURES`).

**The steal-path tails (owner request 2026-10-07: test "runner goes on the full-count pitch with two outs").**
- On the selection-free sample, the sim has too many attempts in short plate appearances and too few in long ones and at final count 3-2.
- The hypothesis: real runners go on the 3-2 pitch with two outs. Test: the steals written into the plate appearance's own line (on its last pitch, count known), by outs.
- A two-out strikeout ends the inning and is not scored as a steal, and ball four forces a runner on first, so two-out last-pitch steals are almost absent (11 at 3-2, against 134 with one out and 70 with none).
- Attempts per plate appearance ending 3-2, by outs at its start, real against sim (3,000 games):
  - 0 outs: .145 against .126; on the last pitch .028 against .010.
  - 1 out: .171 against .150; on the last pitch .037 against .012.
  - 2 outs: .134 against .109; on the last pitch .003 against .003.
- So the two-out gap is earlier in the plate appearance, not on the payoff pitch: the hypothesis does not explain it. With fewer than two outs, the 3-2 gap is the runner going on the payoff pitch (strike-'em-out, throw-'em-out). The steal model has outs and count effects but no count x outs interaction, so it makes about a third of those.
- Tried and withdrawn (owner agreed 2026-10-08): a 3-2 x outs term in the attempt model, fitted from the last-pitch steals whose count is known. It fits at +2.53 logits but changes no gated row (3,000 games each: attempts at 7 pitches .123 both ways, real .170; at 3-2 .128 both ways, real .150); it only moves attempts from earlier 3-2 pitches onto the last one.
- Owner decision 2026-10-08: the watch item "steal timing within the plate appearance" takes every attempt-by-length row (2 to 8+ pitches), the final-count 3-2 row and the 7-pitch success row. These stay gated: attempts per eligible plate appearance, success, the other final-count rows, the other success-by-length rows, attempts per team-game, bunts, sacrifices, bunt hits and intentional walks.
- Candidate for the variance stage (owner, 2026-10-08; no work now): plate-appearance length by base state. Real plate appearances with runners on, above all in scoring position, may run longer than with the bases empty, while the sim's pitch chain does not depend on the base state. To test from the play-by-play: pitches per plate appearance and the final-count mix by base state, real against sim. If real, it could explain the steal timing and also the watch item "top starters' innings".

**Benchmarks (2026-10-07).**
- `league_totals_2025.sb_attempts_per_team_game` gets a tolerance, 0.131: the stolen-base row's relative tolerance (0.1 / 1.098) on the same box-score sample. It was reported, not gated, before.
- New block `decisions_2025`, from the 2025 play-by-play (4,464 team-games), tolerance 3 SE:
  - bunts, sacrifice hits, bunt hits and intentional walks per team-game;
  - steal attempts and success per eligible plate appearance, by length (2 to 8+ pitches) and by final count, on the sample free of selection (`steal_paths`); the first-event sample is kept as `steal_paths_first_event` (diagnostic).

### Phase 3: handedness and platoon splits (2026-10-08, plan approved by the owner with adjustments)

Plan: `plans/phase3_plan_2026-10-08.md`. Data: the roster aggregates (`data/ncaa_2025/roster_aggregates/`, 232 of 277 D1 teams, counts only, approved as representative without weighting) and the 2025 WMT play-by-play. Report: `reports/phase3.md`, on the same 40-season run as every other report.

**Hands are drawn per player, never by tier (owner rule).** Pitchers: P(throws L) = expit(a[role] + b[role] s), s the pitcher's true K-BB per batter faced against an average batter, standardized within role (weekend and midweek starters, relievers). Batters: throws L at the position group's roster share (C .003, 1B .32, IF .03, OF .27, UT/DH .06; left-handed throwers appear at catcher and the infield only at those near-zero rates, owner adjustment 4); bats L / R / S by a multinomial logit on position group and throws plus the batter's standardized true run value per PA. The hands come from their own random stream, drawn after every other, so no other draw moves.

**The fit goes through the noise of the observed talent bins** (`scripts/build_phase3_hands.py`). The aggregates bin matched players by quintiles of an observed index (pitchers: K-BB per BF, adjusted for the batters faced and for platoon, owner adjustment 1; batters: linear-weights run value per PA). A simulated population (four seasons of the engine with hands off) stands in for the real players: each simulated player's play-by-play workload is his season's times his tier's coverage (solved so the binned players' mean workload equals the table's), his observed index is his true one plus binomial noise, and he falls into the table's bins by its edges. Two things had to be emulated for the population to match the table:
- **Coverage.** The play-by-play covers P4 teams almost fully and low-tier teams little (coverage factors: P4 relievers 1.0, starters .75; mid .63 / .38; low .20 / .14).
- **The aggregator's opponent adjustment over-corrects for schedules.** It subtracts the opponents' raw mean, and that mean carries the pitchers the opponents faced, so a P4 pitcher's index is pulled down by the P4 pitching his opponents faced (−.028 K-BB on average; low tier +.024). Without the emulation the simulated P4 pitchers sat in the top bin 38% of the time against 25% real; with it, 25% against 25% (the spread over the bins matches by tier and role).

Fitted slopes per SD of true K-BB: starters +.20 ± .16, relievers −.23 ± .17 (neither different from zero). Batters: bats L against R +.28 ± .08 per SD of true run value (better hitters are more often left-handed), S against R +.20 ± .17. Intercepts are set so the D1 shares match: left-handers among pitchers who appeared, by role, the tiers weighted by their number of teams (.264 starters, .251 relievers; the raw play-by-play sample is P4-heavy).

**The tier gradient (check, owner adjustments 2 and 3).** Batters: the talent-conditional draw gives L shares by tier .369 / .322 / .290 (P4 / mid / low, at each tier's real mix of positions) against .372 / .317 / .291 real. The gradient comes out of where the talent is. Pitchers: it does not. The slopes are flat or negative, so the talent-only model gives relievers .22 / .25 / .28 against .31 / .25 / .20 real. The same fit with a tier term measures the effect of tier at equal talent: P4 +.48 ± .19 and low −.71 ± .48 log-odds against mid, P4 against low +1.19 ± .50. At a .25 base share that is .34 P4, .25 mid, .14 low. The run-value index as the talent measure (sensitivity check) gives the same conclusion: P4 against low +1.07 ± .56, relievers predicted .27 / .25 / .24. Whole rosters show part of it too: left-handers are .295 of P4 roster pitchers against .225 low; among pitchers who appeared, .31–.35 against .20. Per the owner's rule, no tier term was added. Failing rows become the watch item "left-handers by tier", and Phase 9 gets the requirement "recruiting values handedness beyond talent" with this measured size (see the 40-season run below for which rows).

**Platoon shifts** (`scripts/build_phase3_platoon.py`). Logit offsets on the batter's six rates by (side he hits from, pitcher's hand), a switch hitter on the side opposite the pitcher. They are fitted against `platoon_league.csv` by batting tier: per tier and rate, logit(real) − logit(sim) for the four pairs, less its mean over the pairs (a tier-level gap is not a platoon effect), averaged over tiers. The simulated cells already carry who faced whom (hands are drawn with talent; bullpens and pinch hitters choose by hand), so the gap is the platoon effect. The shifts are centred so each rate's league value does not move to first order. One iteration on seasons played with the shifts left gaps of at most .024 logit (SEs .03–.09). Largest effects: a left-handed batter against a left-hander −.49 logit on HR and +.07 on K; against a right-hander +.14 on BB and −.11 on K.

**Levels are not gated, splits are.** The hand-known plate appearances of a tier are not a sample of that tier: low-tier batters in the play-by-play face mostly P4 pitching (the schedules of the teams it covers), so their K% is .28. Tier-weighted levels carry their opponents, and the first trial failed nearly every level row for that reason. The gate rows are splits (rate against left-handers minus against right-handers) within each batting tier. Tiers are weighted by their hand-known plate appearances, since the engine's shift is one number for every tier. The levels are reported.

**The plate-appearance mix is reported, not gated (a change from the plan).** The plan gated the share of plate appearances with the platoon advantage. Its real tolerance can be computed only binomially on plate appearances, which is several times too small: a player's plate appearances all share his hand, and the aggregates have no clustering unit for them. The hands behind it are gated with conference-clustered intervals, and the AI's choices by hand are gated as odds ratios. Proposed fix: a by-conference platoon table in the next aggregator run.

**Usage by hand** (`scripts/build_phase3_usage.py`). Fitted from `relief_by_hand.csv` and `pinch_hit_by_hand.csv`:
- the pull hazard is multiplied by the real change rate for the hands of the pitcher and of the batter due up (a left-hander with a right-handed batter due up is pulled 1.2–1.4 times as often as average);
- the relief choice gets +g/2 for a pitcher of the due-up batter's hand and +f/2 for one of the replaced pitcher's hand (f < 0: teams change hands);
- the pinch-hit hazard is multiplied by the rate for the pitcher's hand and the bats due up;
- the bench pick gives a bench player with the platoon advantage exp(gamma) times the weight.

The data-only estimates ignore who is available in a bullpen or on a bench. So g, f, gamma and the pull multipliers' ratios were then solved in the engine (two steps on four seasons each) until the simulated statistics equal the real ones: left-hander entry difference .218 against .236, pinch hitters' advantage share .666 against .678, change-rate ratios 1.75 / 1.16 against 1.77 / 1.16. The final values: g .72 / .76 (innings 1-6 / 7+), f −.50 / −.48, gamma 1.36. One model serves every tier (GUESSES.md).

**Individual platoon spread.** League-level shifts only (GUESSES.md: individual spread zero). The sim's spread is reported against `platoon_spread.csv`.

**First 40-season run (commit ad6ae50, reports in cc3aa85) and the centring fix.** Phase 2 and Phase 4 passed. The two reliever tier rows failed, as predicted (they became the watch item). Four other rows failed:
- HR per team-game 1.042 against the Phase 4 run's 1.068 ± .018 (PR B 1.057), and SLG with it;
- distinct batters per team-game 10.505 (limit 10.499; PR B 10.481);
- low-tier offense, recovered minus drawn, −.009 ± .006.

Cause, measured on four seasons of the same seeds:
- With the platoon shifts on and the first usage model, league HR per PA was .02592 against .02581 off.
- After the usage solve (stronger bullpen matching), same-hand plate appearances rose (lefty batter against lefty pitcher .094 → .101), and HR per PA fell to .02558. The shifts had been centred, to first order, on the earlier mix.
- The pinch-hit and late pull multipliers, normalized on the real opportunity mix, averaged 1.021 / 1.023 and 1.022 on the engine's.

The fix applies the design ("centred on the league mix"; "multipliers average 1 over the mix") to the final engine's mix:
- the multipliers are rescaled to average 1 on the engine's opportunity mix (`build_phase3_usage.py --normalize`);
- each rate's four shifts get the constant that keeps the league rate exactly (`build_phase3_platoon.py --recentre`): HR +.0137 logit, BB +.0046, HBP +.0046, the rest under .002.

No tolerance moved.

**Second run and the strength-map re-solve (owner decision 2026-10-08).**
- With the re-centred shifts, the 40-season run passed every row but one: low-tier offense, recovered minus drawn, −.0075 ± .0025 (3.07 SE).
- That row had drifted across PRs since the map was last solved on 2026-10-04: −.0038 (Phase 6), −.0058 (Phase 7), −.0070 (PR B), −.0075 (Phase 3; Phase 3's own share −.0005 ± .0034).
- The strength map and home edge were re-solved on the current engine (`solve_phase2_game_scale.py --warm`: 2 iterations of 8 seasons, then 1 of 16 when the drift check read run-prevention curvature at z −2.01). Targets were unchanged.
- The final drift check passes every row (`reports/drift_check.md`).

**Final 40-season run (2026-10-08): every Phase 2–7 gate passes.**
- Low-tier offense recovery +.001.
- HR per team-game 1.060 (Phase 4 run 1.068 ± .018).
- Runs per team-game 6.67.
- The reliever tier rows stay in the watch item:
  - P4 .229 against .306;
  - low .279 against .197.
- **Variance link against PR B:**

| Row | Real | PR B | Phase 3 | Change | Gap closed |
|---|---|---|---|---|---|
| P4-vs-mid margin SD | 5.97 | 5.61 | 5.69 | +.077 ± .041 | 22% ± 12% |
| Regional upset rate | .371 | .343 | .365 | +.023 ± .016 | 81% ± 57% (not significant) |
| 15+ bin | .066 | .051 | .052 | +.001 | 4% |
| Run rule | .152 | .116 | .116 | 0 | 0% |

- **Platoon-advantage share** .464 against .480 (reported); the advantage above random pairing is .008 against .022.

**Process (owner decisions 2026-10-08).**
- Resumable runs are keyed on a hash of what the seasons read (engine, config, scripts, derived inputs, benchmarks.json), not the git commit. A documentation commit keeps finished seasons; any change to code or inputs starts fresh.
- The roster workflow commits its aggregates to its own branch and opens a pull request, so no pull request's head lacks CI.
- The next aggregator run adds `platoon_league.csv` scopes by the batting and the pitching conference. These give conference-clustered intervals for the plate-appearance mix, so the platoon-advantage share can be gated.

### Variance stage, item 1: the run-rule benchmark and the early-ending rate (2026-10-08, owner decision 2026-10-07)

**Benchmark changed** (`game_structure.run_rule_freq`; `scripts/build_run_rule.py`; old block in `data/ncaa_2025/derived/benchmark_changes_variance.json`):
- Old: .1524 ± .0155 (conf B), a product estimator: the scoreboard's share of 10-run margins (.1952, all 8,079 games) × the WMT sample's share of those that ended early (.7805).
- New: **.1412 ± .0114 (conf A)**, the direct count: the share of the 8,418 D1-vs-D1 finals of 2025 that ended before the 9th with a final margin of 10 or more, from WarrenNolan's schedule pages (innings recorded for every final, blank = 9). Tolerance 3 binomial SE. Scheduled 7-inning games that reach a 10-run margin are counted, as before.
- Check of the innings field: on the 2,240 games WarrenNolan and the WMT schedules share, the innings agree in 99.9% and the early/full call in 100%.
- Why the old value was high: the WMT games end early more often given a 10-run margin (.785 against .724 in the rest, round 1 sizes); all games give .7403 ± .0109 (1,606 games with a 10-run margin).
- 2026 as a check (not pooled; the engine is calibrated to 2025): .1351 ± .0037; P(ended early | margin 10+) .7729 ± .0109.

**Engine refitted** (`data/ncaa_2025/derived/run_rule_in_effect_2025.json`, `config/phase1.py`): the probability that a game is under the rule, which the engine draws per game, was the WMT conditional itself (.7805). It is now solved so the share of simulated games with a final margin of 10 or more that end early matches all games' .7403: one proportional step from the Phase 3 40-season run (sim .7422 at .7805) gives **.7785 ± .0116**. The 40-season run that follows confirms it: .7409 ± .0019.

**Result, 40 seasons (2026-10-08):** every Phase 2-7 gate passes. Run-rule frequency .1156 ± .0014 against .1412 ± .0122: still outside, and still the watch item "offense extremes compressed" (the share of 10-run margins, .1560 against .1908, is the gap; the early-ending rate now matches). The gap fell from .037 (against .1524) to .026. Drift check after the refit: every row within 2 SE (`reports/drift_check.md`).

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
