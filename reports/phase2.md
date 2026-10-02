# Phase 2 realism report

Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), 20 simulated 56-game seasons, a new league per season, seeds 20251000–20251019. Generated 2026-10-02.
Tolerances combine the benchmark's (3 SE of the real statistic) with 3 SE of the simulated mean at 20 seasons. Leaderboard rows pass if the real value lies inside the 95% Student-t prediction interval of the simulated seasons. Rows marked Phase 6 were moved to the Phase 6 gate (CLAUDE.md, deferred rows) and are reported, not gated.

## Gate: **FAIL**

## Phase 1 league totals (must be unchanged)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.7005 | 6.7500 | ±0.1700 | B | yes | pass |
| Batting average | 0.2816 | 0.2800 | ±0.0053 | B | yes | pass |
| On-base pct | 0.3793 | 0.3805 | ±0.0053 | B | yes | pass |
| Slugging pct | 0.4404 | 0.4400 | ±0.0103 | B | yes | pass |
| HR per team-game | 1.0495 | 1.0500 | ±0.0520 | B |  | pass |
| BB per PA | 0.1049 | 0.1059 | ±0.0051 | B |  | pass |
| K per PA | 0.1950 | 0.1927 | ±0.0057 | B |  | pass |
| HBP per PA | 0.0339 | 0.0334 | ±0.0040 | B |  | pass |
| Errors per team-game | 1.1005 | 1.0990 | ±0.1513 | B |  | pass |
| PA per team-game | 40.4856 | 40.3100 | ±1.0034 | B |  | pass |
| ERA | 6.1474 | 6.0800 | ±0.3081 | B |  | pass |
| Big-inning frequency (3+ runs) | 0.1041 | 0.1031 | ±0.0093 | A | yes | pass |
| PA per half-inning | 4.678 | 4.694 | ±0.055 | A | yes | pass |

Runs per half-inning: pass. Sim 0.6382, 0.1661, 0.0916, 0.0497, 0.0263, 0.0281 vs 0.6397, 0.1625, 0.0947, 0.0491, 0.0258, 0.0282.

## Game structure

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Extra-innings frequency | 0.0616 | 0.0546 | ±0.0152 | B | yes | pass |
| Run-rule frequency | 0.1282 | 0.1524 | ±0.0166 | B | Phase 6 | FAIL |
| Games decided by 10+ runs | 0.1710 | 0.1952 | — | A |  | n/a |
| Runs per team-game SD | 4.442 | 4.676 | — | A |  | n/a |
| Home win pct | 0.5923 | 0.5836 | ±0.0340 | A | yes | pass |
| Home run differential per game | 1.010 | 0.888 | ±0.520 | A | yes | pass |

### Runs per team-game histogram (±0.01 per bin and TVD ≤ 0.04, each combined with the sim's SE; 15+ bin in Phase 6): TVD 0.0274 (limit 0.0402) → **pass**

| Runs | Sim | Benchmark | Diff | Tol | Status |
|---|---|---|---|---|---|
| 0 | 0.0350 | 0.0400 | -0.0050 | ±0.0101 | pass |
| 1 | 0.0592 | 0.0606 | -0.0014 | ±0.0102 | pass |
| 2 | 0.0773 | 0.0770 | +0.0003 | ±0.0101 | pass |
| 3 | 0.0903 | 0.0916 | -0.0013 | ±0.0101 | pass |
| 4 | 0.0959 | 0.0971 | -0.0012 | ±0.0102 | pass |
| 5 | 0.0962 | 0.0916 | +0.0046 | ±0.0102 | pass |
| 6 | 0.0914 | 0.0876 | +0.0038 | ±0.0101 | pass |
| 7 | 0.0820 | 0.0767 | +0.0053 | ±0.0101 | pass |
| 8 | 0.0727 | 0.0647 | +0.0080 | ±0.0101 | pass |
| 9 | 0.0607 | 0.0579 | +0.0028 | ±0.0101 | pass |
| 10 | 0.0535 | 0.0508 | +0.0027 | ±0.0101 | pass |
| 11 | 0.0454 | 0.0454 | -0.0000 | ±0.0101 | pass |
| 12 | 0.0360 | 0.0362 | -0.0002 | ±0.0101 | pass |
| 13 | 0.0280 | 0.0302 | -0.0022 | ±0.0101 | pass |
| 14 | 0.0211 | 0.0260 | -0.0049 | ±0.0101 | pass |
| 15+ | 0.0553 | 0.0664 | -0.0111 | ±0.0106 | FAIL (Phase 6) |

## Tier vs tier scoring (runs per team-game; scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| p4 batting vs p4 pitching | 5.966 | 6.364 | ±0.519 | A | yes | pass |
| p4 batting vs mid pitching | 8.425 | 8.614 | ±0.646 | A | yes | pass |
| p4 batting vs low pitching | 10.565 | 9.820 | ±1.121 | A | Phase 6 | pass |
| mid batting vs p4 pitching | 4.543 | 4.762 | ±0.556 | A | yes | pass |
| mid batting vs mid pitching | 6.622 | 6.724 | ±0.458 | A | yes | pass |
| mid batting vs low pitching | 8.833 | 8.457 | ±0.920 | A | yes | pass |
| low batting vs p4 pitching | 3.247 | 3.629 | ±0.653 | A | yes | pass |
| low batting vs mid pitching | 5.201 | 5.880 | ±0.676 | A | yes | FAIL |
| low batting vs low pitching | 7.202 | 7.046 | ±0.724 | A | yes | pass |

## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Team R/G mean (all) | 6.700 | 6.747 | ±0.214 | A | yes | pass |
| Team R/G SD across teams (all) | 1.127 | 1.162 | ±0.143 | A | yes | pass |
| Team RA/G mean (all) | 6.702 | 6.841 | ±0.285 | A | yes | pass |
| Team RA/G SD across teams (all) | 1.842 | 1.596 | ±0.212 | A | yes | FAIL |
| Team R/G mean (p4) | 7.063 | 7.207 | ±0.325 | A | yes | pass |
| Team R/G SD across teams (p4) | 0.923 | 0.793 | ±0.217 | A | yes | pass |
| Team RA/G mean (p4) | 5.324 | 5.767 | ±0.442 | A | yes | FAIL |
| Team RA/G SD across teams (p4) | 1.135 | 1.112 | ±0.307 | A | yes | pass |
| Team R/G mean (mid) | 6.638 | 6.668 | ±0.321 | A | yes | pass |
| Team R/G SD across teams (mid) | 1.103 | 1.255 | ±0.218 | A | yes | pass |
| Team RA/G mean (mid) | 6.666 | 6.871 | ±0.351 | A | yes | pass |
| Team RA/G SD across teams (mid) | 1.547 | 1.377 | ±0.255 | A | yes | pass |
| Team R/G mean (low) | 6.548 | 6.553 | ±0.386 | A | yes | pass |
| Team R/G SD across teams (low) | 1.219 | 1.141 | ±0.272 | A | yes | pass |
| Team RA/G mean (low) | 7.743 | 7.560 | ±0.633 | A | yes | pass |
| Team RA/G SD across teams (low) | 2.000 | 1.819 | ±0.436 | A | yes | pass |

## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)

Qualified per team: batters sim 7.95 vs data 7.56; pitchers sim 1.95 vs data 2.27.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| BA p10 | 0.2311 | 0.2385 | ±0.0136 | B | yes | pass |
| BA p50 | 0.2883 | 0.2959 | ±0.0149 | B | yes | pass |
| BA p90 | 0.3460 | 0.3533 | ±0.0170 | B | yes | pass |
| OBP p10 | 0.3221 | 0.3366 | ±0.0108 | B | yes | FAIL |
| OBP p50 | 0.3828 | 0.3889 | ±0.0135 | B | yes | pass |
| OBP p90 | 0.4447 | 0.4487 | ±0.0130 | B | yes | pass |
| ISO p10 | 0.0775 | 0.0755 | ±0.0188 | B | yes | pass |
| ISO p50 | 0.1568 | 0.1667 | ±0.0199 | B | yes | pass |
| ISO p90 | 0.2624 | 0.2775 | ±0.0407 | B | yes | pass |
| K_pct p10 | 0.1185 | 0.1075 | ±0.0250 | B | yes | pass |
| K_pct p50 | 0.1833 | 0.1829 | ±0.0140 | B | yes | pass |
| K_pct p90 | 0.2657 | 0.2689 | ±0.0411 | B | yes | pass |
| BB_pct p10 | 0.0634 | 0.0668 | ±0.0106 | B | yes | pass |
| BB_pct p50 | 0.1014 | 0.1058 | ±0.0136 | B | yes | pass |
| BB_pct p90 | 0.1486 | 0.1584 | ±0.0159 | B | yes | pass |
| ERA p10 | 3.21 | 3.41 | ±0.619 | B | yes | pass |
| ERA p50 | 5.09 | 5.12 | ±0.666 | B | yes | pass |
| ERA p90 | 7.67 | 7.64 | ±1.279 | B | yes | pass |
| K9 p10 | 5.72 | 5.72 | ±0.674 | B | yes | pass |
| K9 p50 | 8.36 | 7.88 | ±0.928 | B | Phase 6 | pass |
| K9 p90 | 11.35 | 10.56 | ±1.306 | B | Phase 6 | pass |

## Leaderboards (full-population extremes)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Pitchers with 50+ IP | 785.5 (season range 757.0–819.0) | 821.1 (56-game eq. of 882) | ±34.8 | A | Phase 6 | FAIL |
| 50+ IP pitchers with ERA < 2.00 | 6.750 (season range 2.000–13.000) | 5 | ±4.963 | A | yes | pass |
| 50+ IP pitchers with ERA < 3.00 | 54.6 (season range 41.0–70.0) | 57 | ±14.7 | A | yes | pass |
| Teams with ERA < 4.00 | 21.6 (season range 14.0–29.0) | 12 | ±9.7 | A | yes | pass |
| Best team ERA | 2.754 (season range 2.383–3.002) | 3.2 | ±0.420 | A | yes | FAIL |
| Best team BA | 0.349 (season range 0.334–0.389) | 0.356 | ±0.026 | A | yes | pass |
| Most team HR per game | 2.639 (season range 2.340–3.250) | 2.672 | ±0.512 | A | yes | pass |

## Individual leaders (NCAA.com national leaders 2024–2026, record book 2023)

Counting stats at a 56-game equivalent (each real player's HR × 56 / his games; real leaders' teams played 57–72 games, the sim plays 56); rates as they are. A row passes if the simulated mean lies in the band from the lowest to the highest real season, widened by 3 SE of the simulated mean. Benchmark column: the band, then each season.

| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| HR leader (56-game equivalent) | 29.8 (season range 25.0–35.0) | 25.5–34.5 (2023 26.3, 2024 34.5, 2025 25.5, 2026 33.4) | ±2.1 | A | yes | pass |
| Hitters with 30+ HR (56-game equivalent) | 0.90 (season range 0.00–3.00) | 0.00–3.00 (2024 3.00, 2025 0.00, 2026 2.00) | ±0.68 | A | yes | pass |
| BA leader (qualified) | 0.453 (season range 0.437–0.471) | 0.433–0.455 (2023 0.449, 2024 0.433, 2025 0.455, 2026 0.446) | ±0.007 | A | yes | pass |
| Top-5 HR hitters, HR per game | 0.488 (season range 0.437–0.568) | 0.410–0.539 (2024 0.539, 2025 0.410, 2026 0.528) | ±0.025 | A | yes | pass |
| Most HR by any player, all 20 seasons (hard ceiling) | 35 | ≤ 48 (D1 record) | — | A | yes | pass |

## Diagnostics

- Earned share of runs 0.8787 (data 0.8824); pitchers per team-game 4.34 (data 4.298)
- Weekend starts by a team's top three starters 0.807 (data 0.789); weekend starters per team 6.24 (data 6.48)
- Innings of a team's three busiest pitchers 71.7, 60.8, 50.7 (data, full-season teams averaging 57.2 games: 77.2, 66.7, 54.4)
