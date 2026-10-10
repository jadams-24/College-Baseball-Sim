# Phase 2 realism report

Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), 40 simulated 56-game seasons, a new league per season, seeds 20251000–20251039. Generated 2026-10-10.
Tolerances combine the benchmark's (3 SE of the real statistic) with 3 SE of the simulated mean at 40 seasons. Leaderboard rows pass if the real value lies inside the 95% Student-t prediction interval of the simulated seasons. Rows marked Phase 6 were moved to the Phase 6 gate (CLAUDE.md, deferred rows) and are reported, not gated.

## Gate: **PASS**

## Phase 1 league totals (must be unchanged)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.7057 | 6.7500 | ±0.1654 | B | yes | pass |
| Batting average | 0.2821 | 0.2800 | ±0.0052 | B | yes | pass |
| On-base pct | 0.3810 | 0.3805 | ±0.0053 | B | yes | pass |
| Slugging pct | 0.4418 | 0.4400 | ±0.0102 | B | yes | pass |
| HR per team-game | 1.0637 | 1.0500 | ±0.0512 | B |  | pass |
| BB per PA | 0.1063 | 0.1059 | ±0.0051 | B |  | pass |
| K per PA | 0.1934 | 0.1927 | ±0.0053 | B |  | pass |
| HBP per PA | 0.0343 | 0.0334 | ±0.0040 | B | yes | pass |
| Errors per team-game | 1.1078 | 1.0990 | ±0.1506 | B |  | pass |
| PA per team-game | 40.7759 | 40.3100 | ±1.0027 | B |  | pass |
| ERA | 6.1236 | 6.0800 | ±0.3068 | B |  | pass |
| Big-inning frequency (3+ runs) | 0.1035 | 0.1031 | ±0.0092 | A | yes | pass |
| PA per half-inning | 4.698 | 4.694 | ±0.054 | A | yes | pass |

Runs per half-inning: pass. Sim 0.6373, 0.1672, 0.0919, 0.0497, 0.0263, 0.0276 vs 0.6397, 0.1625, 0.0947, 0.0491, 0.0258, 0.0282.

## Game structure

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Extra-innings frequency | 0.0640 | 0.0546 | ±0.0151 | B | yes | pass |
| Run-rule frequency | 0.1184 | 0.1412 | ±0.0122 | A | Phase 6 | FAIL |
| Games decided by 10+ runs | 0.1594 | 0.1952 | — | A |  | n/a |
| Runs per team-game SD | 4.396 | 4.676 | — | A |  | n/a |
| Home win pct | 0.5862 | 0.5836 | ±0.0339 | A | yes | pass |
| Home run differential per game | 0.907 | 0.888 | ±0.517 | A | yes | pass |

### Runs per team-game histogram (±0.01 per bin and TVD ≤ 0.04, each combined with the sim's SE; 15+ bin in Phase 6): TVD 0.0349 (limit 0.0401) → **pass**

| Runs | Sim | Benchmark | Diff | Tol | Status |
|---|---|---|---|---|---|
| 0 | 0.0331 | 0.0400 | -0.0069 | ±0.0101 | pass |
| 1 | 0.0571 | 0.0606 | -0.0035 | ±0.0101 | pass |
| 2 | 0.0770 | 0.0770 | -0.0000 | ±0.0101 | pass |
| 3 | 0.0893 | 0.0916 | -0.0023 | ±0.0101 | pass |
| 4 | 0.0967 | 0.0971 | -0.0004 | ±0.0101 | pass |
| 5 | 0.0971 | 0.0916 | +0.0055 | ±0.0101 | pass |
| 6 | 0.0935 | 0.0876 | +0.0059 | ±0.0101 | pass |
| 7 | 0.0844 | 0.0767 | +0.0077 | ±0.0101 | pass |
| 8 | 0.0738 | 0.0647 | +0.0091 | ±0.0100 | pass |
| 9 | 0.0618 | 0.0579 | +0.0039 | ±0.0100 | pass |
| 10 | 0.0538 | 0.0508 | +0.0030 | ±0.0100 | pass |
| 11 | 0.0443 | 0.0454 | -0.0011 | ±0.0100 | pass |
| 12 | 0.0354 | 0.0362 | -0.0008 | ±0.0100 | pass |
| 13 | 0.0275 | 0.0302 | -0.0027 | ±0.0100 | pass |
| 14 | 0.0208 | 0.0260 | -0.0052 | ±0.0100 | pass |
| 15+ | 0.0545 | 0.0664 | -0.0119 | ±0.0104 | FAIL (Phase 6) |

## Tier vs tier scoring (runs per team-game; scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| p4 batting vs p4 pitching | 6.057 | 6.364 | ±0.503 | A | yes | pass |
| p4 batting vs mid pitching | 8.446 | 8.614 | ±0.637 | A | yes | pass |
| p4 batting vs low pitching | 9.596 | 9.820 | ±1.104 | A | Phase 6 | pass |
| mid batting vs p4 pitching | 4.519 | 4.762 | ±0.545 | A | yes | pass |
| mid batting vs mid pitching | 6.672 | 6.724 | ±0.460 | A | yes | pass |
| mid batting vs low pitching | 8.138 | 8.457 | ±0.833 | A | yes | pass |
| low batting vs p4 pitching | 3.620 | 3.629 | ±0.639 | A | yes | pass |
| low batting vs mid pitching | 5.667 | 5.880 | ±0.632 | A | yes | pass |
| low batting vs low pitching | 7.196 | 7.046 | ±0.709 | A | yes | pass |

## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Team R/G mean (all) | 6.706 | 6.747 | ±0.211 | A | yes | pass |
| Team R/G SD across teams (all) | 1.029 | 1.162 | ±0.142 | A | watch item: offense extremes compressed | pass |
| Team RA/G mean (all) | 6.706 | 6.841 | ±0.283 | A | yes | pass |
| Team RA/G SD across teams (all) | 1.712 | 1.596 | ±0.205 | A | yes | pass |
| Team R/G mean (p4) | 7.003 | 7.207 | ±0.306 | A | yes | pass |
| Team R/G SD across teams (p4) | 0.794 | 0.793 | ±0.215 | A | yes | pass |
| Team RA/G mean (p4) | 5.432 | 5.767 | ±0.431 | A | yes | pass |
| Team RA/G SD across teams (p4) | 1.094 | 1.112 | ±0.301 | A | yes | pass |
| Team R/G mean (mid) | 6.598 | 6.668 | ±0.316 | A | yes | pass |
| Team R/G SD across teams (mid) | 1.078 | 1.255 | ±0.219 | A | yes | pass |
| Team RA/G mean (mid) | 6.754 | 6.871 | ±0.353 | A | yes | pass |
| Team RA/G SD across teams (mid) | 1.484 | 1.377 | ±0.244 | A | yes | pass |
| Team R/G mean (low) | 6.677 | 6.553 | ±0.375 | A | yes | pass |
| Team R/G SD across teams (low) | 1.034 | 1.141 | ±0.262 | A | yes | pass |
| Team RA/G mean (low) | 7.531 | 7.560 | ±0.607 | A | yes | pass |
| Team RA/G SD across teams (low) | 1.838 | 1.819 | ±0.424 | A | yes | pass |

## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)

Qualified per team: batters sim 7.52 vs data 7.56; pitchers sim 1.99 vs data 2.27.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| BA p10 | 0.2329 | 0.2385 | ±0.0135 | B | yes | pass |
| BA p50 | 0.2893 | 0.2959 | ±0.0149 | B | yes | pass |
| BA p90 | 0.3458 | 0.3533 | ±0.0170 | B | yes | pass |
| OBP p10 | 0.3247 | 0.3366 | ±0.0108 | B | watch item: offense extremes compressed | FAIL |
| OBP p50 | 0.3850 | 0.3889 | ±0.0135 | B | yes | pass |
| OBP p90 | 0.4467 | 0.4487 | ±0.0130 | B | yes | pass |
| ISO p10 | 0.0803 | 0.0755 | ±0.0188 | B | yes | pass |
| ISO p50 | 0.1592 | 0.1667 | ±0.0198 | B | yes | pass |
| ISO p90 | 0.2633 | 0.2775 | ±0.0407 | B | yes | pass |
| K_pct p10 | 0.1157 | 0.1075 | ±0.0249 | B | yes | pass |
| K_pct p50 | 0.1810 | 0.1829 | ±0.0139 | B | yes | pass |
| K_pct p90 | 0.2642 | 0.2689 | ±0.0410 | B | yes | pass |
| BB_pct p10 | 0.0627 | 0.0668 | ±0.0106 | B | yes | pass |
| BB_pct p50 | 0.1020 | 0.1058 | ±0.0136 | B | yes | pass |
| BB_pct p90 | 0.1525 | 0.1584 | ±0.0160 | B | yes | pass |
| ERA p10 | 3.24 | 3.41 | ±0.619 | B | yes | pass |
| ERA p50 | 5.13 | 5.12 | ±0.666 | B | yes | pass |
| ERA p90 | 7.64 | 7.64 | ±1.275 | B | yes | pass |
| K9 p10 | 5.70 | 5.72 | ±0.671 | B | yes | pass |
| K9 p50 | 8.35 | 7.88 | ±0.922 | B | Phase 6 | pass |
| K9 p90 | 11.42 | 10.56 | ±1.303 | B | Phase 6 | pass |

## Leaderboards (full-population extremes)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Pitchers with 50+ IP | 773.5 (season range 732.0–801.0) | 821.1 (56-game eq. of 882) | ±34.2 | A | Phase 6 | FAIL |
| 50+ IP pitchers with ERA < 2.00 | 6.350 (season range 3.000–12.000) | 5 | ±4.604 | A | yes | pass |
| 50+ IP pitchers with ERA < 3.00 | 51.8 (season range 33.0–78.0) | 57 | ±18.8 | A | yes | pass |

## National team leaders (NCAA.com team pages, 2024–2026)

Rates and counts of teams on full seasons: real seasons include conference tournaments, the NCAA tournament and non-D1 games; the sim's its regular season plus its postseason when the Phase 7 world is on (the rest of this report is the regular season). A row passes if the simulated mean lies in the band from the lowest to the highest real season, widened by 3 SE of the simulated mean. Benchmark column: the band, then each season.

| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Teams with ERA < 4.00 | 15.6 (season range 4.0–26.0) | 6.0–12.0 (2024 6.0, 2025 12.0, 2026 12.0) | ±2.3 | A | watch item: teams under 4.00 ERA | FAIL |
| Best team ERA | 3.027 (season range 2.105–3.434) | 3.060–3.780 (2024 3.780, 2025 3.060, 2026 3.220) | ±0.142 | A | yes | pass |
| Best team BA | 0.338 (season range 0.327–0.359) | 0.337–0.359 (2024 0.359, 2025 0.337, 2026 0.356) | ±0.004 | A | yes | pass |
| Most team HR per game | 2.414 (season range 1.984–3.194) | 2.400–2.672 (2024 2.607, 2025 2.400, 2026 2.672) | ±0.138 | A | yes | pass |

## Individual leaders (NCAA.com national leaders 2024–2026, record book 2023)

Counting stats at a 56-game equivalent (each real player's HR × 56 / his games; real leaders' teams played 57–72 games, the sim plays 56); rates as they are. A row passes if the simulated mean lies in the band from the lowest to the highest real season, widened by 3 SE of the simulated mean. Benchmark column: the band, then each season.

| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| HR leader (56-game equivalent) | 28.9 (season range 25.1–36.6) | 25.5–34.5 (2023 26.3, 2024 34.5, 2025 25.5, 2026 33.4) | ±1.4 | A | yes | pass |
| Hitters with 30+ HR (56-game equivalent) | 0.35 (season range 0.00–3.00) | 0.00–3.00 (2024 3.00, 2025 0.00, 2026 2.00) | ±0.31 | A | yes | pass |
| BA leader (qualified) | 0.447 (season range 0.420–0.520) | 0.433–0.455 (2023 0.449, 2024 0.433, 2025 0.455, 2026 0.446) | ±0.010 | A | yes | pass |
| Top-5 HR hitters, HR per game | 0.465 (season range 0.403–0.573) | 0.410–0.539 (2024 0.539, 2025 0.410, 2026 0.528) | ±0.017 | A | yes | pass |
| Most HR by any player, all 40 seasons (hard ceiling) | 35 | ≤ 48 (D1 record) | — | A | yes | pass |

## Diagnostics

- Earned share of runs 0.8772 (data 0.8824); pitchers per team-game 4.35 (data 4.298)
- Weekend starts by a team's top three starters 0.808 (data 0.789); weekend starters per team 6.19 (data 6.48)
- Innings of a team's three busiest pitchers 69.3, 58.1, 47.4 (data, full-season teams averaging 57.2 games: 77.2, 66.7, 54.4)
