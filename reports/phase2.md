# Phase 2 realism report

Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), 40 simulated 56-game seasons, a new league per season, seeds 20251000–20251039. Generated 2026-10-09.
Tolerances combine the benchmark's (3 SE of the real statistic) with 3 SE of the simulated mean at 40 seasons. Leaderboard rows pass if the real value lies inside the 95% Student-t prediction interval of the simulated seasons. Rows marked Phase 6 were moved to the Phase 6 gate (CLAUDE.md, deferred rows) and are reported, not gated.

## Gate: **PASS**

## Phase 1 league totals (must be unchanged)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.6523 | 6.7500 | ±0.1651 | B | yes | pass |
| Batting average | 0.2815 | 0.2800 | ±0.0051 | B | yes | pass |
| On-base pct | 0.3794 | 0.3805 | ±0.0053 | B | yes | pass |
| Slugging pct | 0.4405 | 0.4400 | ±0.0102 | B | yes | pass |
| HR per team-game | 1.0568 | 1.0500 | ±0.0512 | B |  | pass |
| BB per PA | 0.1050 | 0.1059 | ±0.0051 | B |  | pass |
| K per PA | 0.1947 | 0.1927 | ±0.0053 | B |  | pass |
| HBP per PA | 0.0340 | 0.0334 | ±0.0040 | B |  | pass |
| Errors per team-game | 1.1071 | 1.0990 | ±0.1507 | B |  | pass |
| PA per team-game | 40.7265 | 40.3100 | ±1.0028 | B |  | pass |
| ERA | 6.0645 | 6.0800 | ±0.3066 | B |  | pass |
| Big-inning frequency (3+ runs) | 0.1024 | 0.1031 | ±0.0092 | A | yes | pass |
| PA per half-inning | 4.686 | 4.694 | ±0.054 | A | yes | pass |

Runs per half-inning: pass. Sim 0.6393, 0.1671, 0.0913, 0.0494, 0.0259, 0.0271 vs 0.6397, 0.1625, 0.0947, 0.0491, 0.0258, 0.0282.

## Game structure

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Extra-innings frequency | 0.0666 | 0.0546 | ±0.0151 | B | yes | pass |
| Run-rule frequency | 0.1170 | 0.1412 | ±0.0122 | A | Phase 6 | FAIL |
| Games decided by 10+ runs | 0.1579 | 0.1952 | — | A |  | n/a |
| Runs per team-game SD | 4.372 | 4.676 | — | A |  | n/a |
| Home win pct | 0.5872 | 0.5836 | ±0.0339 | A | yes | pass |
| Home run differential per game | 0.898 | 0.888 | ±0.517 | A | yes | pass |

### Runs per team-game histogram (±0.01 per bin and TVD ≤ 0.04, each combined with the sim's SE; 15+ bin in Phase 6): TVD 0.0347 (limit 0.0401) → **pass**

| Runs | Sim | Benchmark | Diff | Tol | Status |
|---|---|---|---|---|---|
| 0 | 0.0332 | 0.0400 | -0.0068 | ±0.0101 | pass |
| 1 | 0.0582 | 0.0606 | -0.0024 | ±0.0101 | pass |
| 2 | 0.0775 | 0.0770 | +0.0005 | ±0.0101 | pass |
| 3 | 0.0909 | 0.0916 | -0.0007 | ±0.0101 | pass |
| 4 | 0.0981 | 0.0971 | +0.0010 | ±0.0101 | pass |
| 5 | 0.0986 | 0.0916 | +0.0070 | ±0.0101 | pass |
| 6 | 0.0936 | 0.0876 | +0.0060 | ±0.0101 | pass |
| 7 | 0.0830 | 0.0767 | +0.0063 | ±0.0101 | pass |
| 8 | 0.0730 | 0.0647 | +0.0083 | ±0.0101 | pass |
| 9 | 0.0610 | 0.0579 | +0.0031 | ±0.0100 | pass |
| 10 | 0.0533 | 0.0508 | +0.0025 | ±0.0101 | pass |
| 11 | 0.0443 | 0.0454 | -0.0011 | ±0.0101 | pass |
| 12 | 0.0351 | 0.0362 | -0.0011 | ±0.0101 | pass |
| 13 | 0.0268 | 0.0302 | -0.0034 | ±0.0100 | pass |
| 14 | 0.0202 | 0.0260 | -0.0058 | ±0.0100 | pass |
| 15+ | 0.0531 | 0.0664 | -0.0133 | ±0.0103 | FAIL (Phase 6) |

## Tier vs tier scoring (runs per team-game; scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| p4 batting vs p4 pitching | 6.016 | 6.364 | ±0.502 | A | yes | pass |
| p4 batting vs mid pitching | 8.394 | 8.614 | ±0.634 | A | yes | pass |
| p4 batting vs low pitching | 9.518 | 9.820 | ±1.103 | A | Phase 6 | pass |
| mid batting vs p4 pitching | 4.466 | 4.762 | ±0.542 | A | yes | pass |
| mid batting vs mid pitching | 6.608 | 6.724 | ±0.459 | A | yes | pass |
| mid batting vs low pitching | 8.059 | 8.457 | ±0.831 | A | yes | pass |
| low batting vs p4 pitching | 3.617 | 3.629 | ±0.638 | A | yes | pass |
| low batting vs mid pitching | 5.646 | 5.880 | ±0.635 | A | yes | pass |
| low batting vs low pitching | 7.150 | 7.046 | ±0.710 | A | yes | pass |

## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Team R/G mean (all) | 6.653 | 6.747 | ±0.211 | A | yes | pass |
| Team R/G SD across teams (all) | 1.018 | 1.162 | ±0.142 | A | watch item: offense extremes compressed | FAIL |
| Team RA/G mean (all) | 6.653 | 6.841 | ±0.283 | A | yes | pass |
| Team RA/G SD across teams (all) | 1.701 | 1.596 | ±0.204 | A | yes | pass |
| Team R/G mean (p4) | 6.956 | 7.207 | ±0.305 | A | yes | pass |
| Team R/G SD across teams (p4) | 0.801 | 0.793 | ±0.215 | A | yes | pass |
| Team RA/G mean (p4) | 5.391 | 5.767 | ±0.430 | A | yes | pass |
| Team RA/G SD across teams (p4) | 1.091 | 1.112 | ±0.302 | A | yes | pass |
| Team R/G mean (mid) | 6.534 | 6.668 | ±0.315 | A | yes | pass |
| Team R/G SD across teams (mid) | 1.057 | 1.255 | ±0.218 | A | yes | pass |
| Team RA/G mean (mid) | 6.696 | 6.871 | ±0.352 | A | yes | pass |
| Team RA/G SD across teams (mid) | 1.477 | 1.377 | ±0.244 | A | yes | pass |
| Team R/G mean (low) | 6.638 | 6.553 | ±0.376 | A | yes | pass |
| Team R/G SD across teams (low) | 1.029 | 1.141 | ±0.261 | A | yes | pass |
| Team RA/G mean (low) | 7.476 | 7.560 | ±0.609 | A | yes | pass |
| Team RA/G SD across teams (low) | 1.822 | 1.819 | ±0.423 | A | yes | pass |

## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)

Qualified per team: batters sim 7.52 vs data 7.56; pitchers sim 2.08 vs data 2.27.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| BA p10 | 0.2323 | 0.2385 | ±0.0135 | B | yes | pass |
| BA p50 | 0.2884 | 0.2959 | ±0.0149 | B | yes | pass |
| BA p90 | 0.3453 | 0.3533 | ±0.0170 | B | yes | pass |
| OBP p10 | 0.3232 | 0.3366 | ±0.0108 | B | watch item: offense extremes compressed | FAIL |
| OBP p50 | 0.3832 | 0.3889 | ±0.0135 | B | yes | pass |
| OBP p90 | 0.4451 | 0.4487 | ±0.0129 | B | yes | pass |
| ISO p10 | 0.0797 | 0.0755 | ±0.0188 | B | yes | pass |
| ISO p50 | 0.1582 | 0.1667 | ±0.0198 | B | yes | pass |
| ISO p90 | 0.2623 | 0.2775 | ±0.0407 | B | yes | pass |
| K_pct p10 | 0.1166 | 0.1075 | ±0.0249 | B | yes | pass |
| K_pct p50 | 0.1823 | 0.1829 | ±0.0139 | B | yes | pass |
| K_pct p90 | 0.2660 | 0.2689 | ±0.0410 | B | yes | pass |
| BB_pct p10 | 0.0620 | 0.0668 | ±0.0106 | B | yes | pass |
| BB_pct p50 | 0.1009 | 0.1058 | ±0.0136 | B | yes | pass |
| BB_pct p90 | 0.1512 | 0.1584 | ±0.0159 | B | yes | pass |
| ERA p10 | 3.19 | 3.41 | ±0.619 | B | yes | pass |
| ERA p50 | 5.10 | 5.12 | ±0.665 | B | yes | pass |
| ERA p90 | 7.57 | 7.64 | ±1.275 | B | yes | pass |
| K9 p10 | 5.74 | 5.72 | ±0.671 | B | yes | pass |
| K9 p50 | 8.39 | 7.88 | ±0.922 | B | Phase 6 | pass |
| K9 p90 | 11.47 | 10.56 | ±1.303 | B | Phase 6 | pass |

## Leaderboards (full-population extremes)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Pitchers with 50+ IP | 823.7 (season range 784.0–860.0) | 821.1 (56-game eq. of 882) | ±38.1 | A | Phase 6 | pass |
| 50+ IP pitchers with ERA < 2.00 | 7.750 (season range 2.000–14.000) | 5 | ±6.217 | A | yes | pass |
| 50+ IP pitchers with ERA < 3.00 | 60.6 (season range 45.0–86.0) | 57 | ±19.7 | A | yes | pass |

## National team leaders (NCAA.com team pages, 2024–2026)

Rates and counts of teams on full seasons: real seasons include conference tournaments, the NCAA tournament and non-D1 games; the sim's its regular season plus its postseason when the Phase 7 world is on (the rest of this report is the regular season). A row passes if the simulated mean lies in the band from the lowest to the highest real season, widened by 3 SE of the simulated mean. Benchmark column: the band, then each season.

| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Teams with ERA < 4.00 | 16.8 (season range 7.0–26.0) | 6.0–12.0 (2024 6.0, 2025 12.0, 2026 12.0) | ±1.9 | A | watch item: teams under 4.00 ERA | FAIL |
| Best team ERA | 2.999 (season range 2.300–3.375) | 3.060–3.780 (2024 3.780, 2025 3.060, 2026 3.220) | ±0.117 | A | yes | pass |
| Best team BA | 0.337 (season range 0.323–0.360) | 0.337–0.359 (2024 0.359, 2025 0.337, 2026 0.356) | ±0.004 | A | yes | pass |
| Most team HR per game | 2.417 (season range 2.000–2.941) | 2.400–2.672 (2024 2.607, 2025 2.400, 2026 2.672) | ±0.122 | A | yes | pass |

## Individual leaders (NCAA.com national leaders 2024–2026, record book 2023)

Counting stats at a 56-game equivalent (each real player's HR × 56 / his games; real leaders' teams played 57–72 games, the sim plays 56); rates as they are. A row passes if the simulated mean lies in the band from the lowest to the highest real season, widened by 3 SE of the simulated mean. Benchmark column: the band, then each season.

| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| HR leader (56-game equivalent) | 28.5 (season range 23.7–37.7) | 25.5–34.5 (2023 26.3, 2024 34.5, 2025 25.5, 2026 33.4) | ±1.5 | A | yes | pass |
| Hitters with 30+ HR (56-game equivalent) | 0.45 (season range 0.00–3.00) | 0.00–3.00 (2024 3.00, 2025 0.00, 2026 2.00) | ±0.39 | A | yes | pass |
| BA leader (qualified) | 0.445 (season range 0.426–0.475) | 0.433–0.455 (2023 0.449, 2024 0.433, 2025 0.455, 2026 0.446) | ±0.006 | A | yes | pass |
| Top-5 HR hitters, HR per game | 0.466 (season range 0.394–0.560) | 0.410–0.539 (2024 0.539, 2025 0.410, 2026 0.528) | ±0.018 | A | yes | pass |
| Most HR by any player, all 40 seasons (hard ceiling) | 35 | ≤ 48 (D1 record) | — | A | yes | pass |

## Diagnostics

- Earned share of runs 0.8766 (data 0.8824); pitchers per team-game 4.34 (data 4.298)
- Weekend starts by a team's top three starters 0.808 (data 0.789); weekend starters per team 6.19 (data 6.48)
- Innings of a team's three busiest pitchers 69.8, 58.6, 48.5 (data, full-season teams averaging 57.2 games: 77.2, 66.7, 54.4)
