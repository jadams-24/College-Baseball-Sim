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
