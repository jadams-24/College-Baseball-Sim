# Phase 0 — The Yardstick

`benchmarks.json` is the definition of "realistic" for this project. Nothing in the engine is tuned by eye; every sim run prints a realism report against this file. If a number in the engine can't be traced here, it is a guess and gets flagged.

## What's in the file and where it came from

| Block | Source | Confidence |
|---|---|---|
| `league_totals_2025` (BA/OBP/SLG/BB%/K%/R/G/HR/G/SB/G/SH/G) | FanGraphs, "The Ridiculous Firewagon Offenses of College Baseball" (Feb 2026) — per-conference 2025 table sourced from Baseball-Reference; means computed in `derive.py` | B |
| `league_totals_2025` (HBP%, SF, SB success, ERA, fielding, errors, PA/G, K/9) | Derived from ACC 2025 team stat lines (theacc.com) and NCAA trend table | C — replace in Phase 1 |
| `league_totals_by_tier_2025` | Same FanGraphs table, grouped | B |
| `pa_outcome_table_league_avg` | Back-solved from the aggregates above so BA/OBP/SLG/HR-per-game all reconcile | C — re-fit from PBP |
| `pitch_level_2023_2025` | SABR-Tooth Tigers (Trackman, 4.56M D1 pitches); rfrey22 count study (2013-19) | A / C |
| `historical_trend` | NCAA official "Division I Baseball Statistics Trends 1970-2018" PDF; HR/G 2022-25 from Baseball America / FanGraphs | A |
| `pitching_distribution_2025` | FanGraphs (882 pitchers ≥ 50 IP) | A |
| `batting_distribution_2025` | NCAA.com record book; leaderboard spreads are placeholders | A / D |
| `game_structure` | Wikipedia season pages, NCAA; `run_distribution_per_team_game` from data.ncaa.com scoreboard JSON, all 8,079 final 2025 D1 games (`data/ncaa_2025/`) | A / C |
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

1. **Team-weighted league totals** — recompute BA/OBP/SLG/BB%/K% weighted by PA, not by conference.
2. **HBP%, SF, SH, SB-ATT, errors, PO/A** from the full 300-team table (currently ACC-derived).
3. **Run distribution per team-game** — histogram P(0 runs) through P(15+). Required for the Phase 1 gate; no sim is realistic if it gets the shape wrong even with the mean right.
4. **Extra-innings frequency and run-rule frequency** from game logs.
5. **Batted-ball out split** (GB/FB/LD/PU) — placeholder now; needed before fielding in Phase 6.
6. **Runner-advancement tables** from PBP (P(runner on 1st scores on double), etc.). Phase 1's base-out state machine depends on these.
7. **Qualified-batter and qualified-pitcher distributions** — percentiles of BA, OBP, ISO, K%, BB%, ERA, K/9. Fit beta distributions for Phase 2 player generation.
8. **Pitches per PA** and count-state outcome tables from Trackman or PBP — Phase 5.

### Phase 1 pull status (2026-09-30)

**Pulled.** Every 2025 D1 scoreboard day from data.ncaa.com (`scripts/pull_scoreboard.py`, 8,595 unique games, raw JSON committed under `data/ncaa_2025/scoreboard/`). From it, `scripts/build_run_histogram.py` computes the runs-per-team-game histogram over 16,068 D1 team-games and writes it into `game_structure.run_distribution_per_team_game` (gap 3 above; now conf A). The same data gives two cross-checks that were not used to change any conf B value:

- Mean runs per D1 team-game is 6.81 against the conf B value of 6.75 ± 0.15 (FanGraphs conference means).
- Runs per game by conference agrees with the FanGraphs table to within about 0.1 for the large conferences (ACC 7.33 vs 7.35, SEC 7.37 vs 7.32, Big 12 7.12 vs 7.14, Big Ten 7.11 vs 7.10). Full list in `data/ncaa_2025/run_distribution_2025.json`.
- 19.5% of games end with a margin of 10 or more, an upper bound on run-rule frequency (gap 4); the scoreboard feed does not record innings played, so extra-innings frequency stays conf D.

**Not pulled.** Team batting, pitching and fielding tables, individual qualified-player tables and play-by-play (gaps 1, 2, 4, 5, 6, 7). stats.ncaa.org serves the team list but puts every team, stats and contest page behind Akamai Bot Manager's JavaScript challenge, and completing that challenge from this environment was stopped by the session's safety policy; data.ncaa.com serves no per-game box score or play-by-play JSON for 2025; www.ncaa.com and sdataprod.ncaa.com are denied by the network policy. `data/README.md` lists every host tried. All conf C entries in `league_totals_2025`, the conf C outcome table, and the conf D placeholders other than the histogram are unchanged.

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
