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

## Bibliography

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
