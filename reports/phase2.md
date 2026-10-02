# Phase 2 realism report

Fictional D1 league (307 teams, 30 conferences, real sizes and tiers), 20 simulated 56-game seasons, a new league per season, seeds 20251000–20251019. Generated 2026-10-02.
Tolerances combine the benchmark's (3 SE of the real statistic) with 3 SE of the simulated mean at 20 seasons. Leaderboard rows pass if the real value lies inside the 95% Student-t prediction interval of the simulated seasons. Rows marked Phase 6 were moved to the Phase 6 gate (CLAUDE.md, deferred rows) and are reported, not gated.

## Gate: **FAIL**

## Phase 1 league totals (must be unchanged)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Runs per team-game | 6.7494 | 6.7500 | ±0.1724 | B | yes | pass |
| Batting average | 0.2830 | 0.2800 | ±0.0053 | B | yes | pass |
| On-base pct | 0.3804 | 0.3805 | ±0.0053 | B | yes | pass |
| Slugging pct | 0.4423 | 0.4400 | ±0.0105 | B | yes | pass |
| HR per team-game | 1.0487 | 1.0500 | ±0.0526 | B |  | pass |
| BB per PA | 0.1050 | 0.1059 | ±0.0051 | B |  | pass |
| K per PA | 0.1938 | 0.1927 | ±0.0057 | B |  | pass |
| HBP per PA | 0.0338 | 0.0334 | ±0.0040 | B |  | pass |
| Errors per team-game | 1.1040 | 1.0990 | ±0.1513 | B |  | pass |
| PA per team-game | 40.5326 | 40.3100 | ±1.0038 | B |  | pass |
| ERA | 6.1947 | 6.0800 | ±0.3102 | B |  | pass |
| Big-inning frequency (3+ runs) | 0.1052 | 0.1031 | ±0.0093 | A | yes | pass |
| PA per half-inning | 4.685 | 4.694 | ±0.055 | A | yes | pass |

Runs per half-inning: pass. Sim 0.6366, 0.1660, 0.0922, 0.0501, 0.0266, 0.0285 vs 0.6397, 0.1625, 0.0947, 0.0491, 0.0258, 0.0282.

## Game structure

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Extra-innings frequency | 0.0617 | 0.0546 | ±0.0151 | B | yes | pass |
| Run-rule frequency | 0.1292 | 0.1524 | ±0.0165 | B | Phase 6 | FAIL |
| Games decided by 10+ runs | 0.1727 | 0.1952 | — | A |  | n/a |
| Runs per team-game SD | 4.442 | 4.676 | — | A |  | n/a |
| Home win pct | 0.5949 | 0.5836 | ±0.0342 | A | yes | pass |
| Home run differential per game | 1.121 | 0.888 | ±0.524 | A | yes | pass |

### Runs per team-game histogram (±0.01 per bin and TVD ≤ 0.04, each combined with the sim's SE; 15+ bin in Phase 6): TVD 0.0297 (limit 0.0401) → **pass**

| Runs | Sim | Benchmark | Diff | Tol | Status |
|---|---|---|---|---|---|
| 0 | 0.0342 | 0.0400 | -0.0058 | ±0.0101 | pass |
| 1 | 0.0582 | 0.0606 | -0.0024 | ±0.0102 | pass |
| 2 | 0.0763 | 0.0770 | -0.0007 | ±0.0102 | pass |
| 3 | 0.0891 | 0.0916 | -0.0025 | ±0.0102 | pass |
| 4 | 0.0949 | 0.0971 | -0.0022 | ±0.0101 | pass |
| 5 | 0.0952 | 0.0916 | +0.0036 | ±0.0102 | pass |
| 6 | 0.0911 | 0.0876 | +0.0035 | ±0.0101 | pass |
| 7 | 0.0824 | 0.0767 | +0.0057 | ±0.0101 | pass |
| 8 | 0.0734 | 0.0647 | +0.0087 | ±0.0101 | pass |
| 9 | 0.0617 | 0.0579 | +0.0038 | ±0.0101 | pass |
| 10 | 0.0541 | 0.0508 | +0.0033 | ±0.0101 | pass |
| 11 | 0.0461 | 0.0454 | +0.0007 | ±0.0101 | pass |
| 12 | 0.0366 | 0.0362 | +0.0004 | ±0.0101 | pass |
| 13 | 0.0288 | 0.0302 | -0.0014 | ±0.0101 | pass |
| 14 | 0.0218 | 0.0260 | -0.0042 | ±0.0100 | pass |
| 15+ | 0.0559 | 0.0664 | -0.0105 | ±0.0104 | FAIL (Phase 6) |

## Tier vs tier scoring (runs per team-game; scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| p4 batting vs p4 pitching | 6.040 | 6.364 | ±0.527 | A | yes | pass |
| p4 batting vs mid pitching | 8.639 | 8.614 | ±0.644 | A | yes | pass |
| p4 batting vs low pitching | 10.654 | 9.820 | ±1.114 | A | Phase 6 | pass |
| mid batting vs p4 pitching | 4.614 | 4.762 | ±0.568 | A | yes | pass |
| mid batting vs mid pitching | 6.676 | 6.724 | ±0.459 | A | yes | pass |
| mid batting vs low pitching | 8.904 | 8.457 | ±0.893 | A | yes | pass |
| low batting vs p4 pitching | 3.229 | 3.629 | ±0.632 | A | yes | pass |
| low batting vs mid pitching | 5.235 | 5.880 | ±0.690 | A | yes | pass |
| low batting vs low pitching | 7.177 | 7.046 | ±0.708 | A | yes | pass |

## Team strength spread (scoreboard, all 2025 D1-vs-D1 finals)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Team R/G mean (all) | 6.749 | 6.747 | ±0.216 | A | yes | pass |
| Team R/G SD across teams (all) | 1.223 | 1.162 | ±0.147 | A | yes | pass |
| Team RA/G mean (all) | 6.751 | 6.841 | ±0.287 | A | yes | pass |
| Team RA/G SD across teams (all) | 1.708 | 1.596 | ±0.206 | A | yes | pass |
| Team R/G mean (p4) | 7.177 | 7.207 | ±0.327 | A | yes | pass |
| Team R/G SD across teams (p4) | 1.030 | 0.793 | ±0.221 | A | yes | FAIL |
| Team RA/G mean (p4) | 5.389 | 5.767 | ±0.453 | A | yes | pass |
| Team RA/G SD across teams (p4) | 1.068 | 1.112 | ±0.303 | A | yes | pass |
| Team R/G mean (mid) | 6.696 | 6.668 | ±0.321 | A | yes | pass |
| Team R/G SD across teams (mid) | 1.194 | 1.255 | ±0.220 | A | yes | pass |
| Team RA/G mean (mid) | 6.735 | 6.871 | ±0.353 | A | yes | pass |
| Team RA/G SD across teams (mid) | 1.404 | 1.377 | ±0.250 | A | yes | pass |
| Team R/G mean (low) | 6.536 | 6.553 | ±0.383 | A | yes | pass |
| Team R/G SD across teams (low) | 1.309 | 1.141 | ±0.271 | A | yes | pass |
| Team RA/G mean (low) | 7.746 | 7.560 | ±0.609 | A | yes | pass |
| Team RA/G SD across teams (low) | 1.835 | 1.819 | ±0.429 | A | yes | pass |

## Qualified players (NCAA qualification; WMT full-season + Sidearm, tier-reweighted)

Qualified per team: batters sim 7.95 vs data 7.56; pitchers sim 2.02 vs data 2.27.

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| BA p10 | 0.2321 | 0.2385 | ±0.0135 | B | yes | pass |
| BA p50 | 0.2897 | 0.2959 | ±0.0149 | B | yes | pass |
| BA p90 | 0.3477 | 0.3533 | ±0.0170 | B | yes | pass |
| OBP p10 | 0.3225 | 0.3366 | ±0.0108 | B | yes | FAIL |
| OBP p50 | 0.3845 | 0.3889 | ±0.0135 | B | yes | pass |
| OBP p90 | 0.4457 | 0.4487 | ±0.0130 | B | yes | pass |
| ISO p10 | 0.0782 | 0.0755 | ±0.0189 | B | yes | pass |
| ISO p50 | 0.1575 | 0.1667 | ±0.0199 | B | yes | pass |
| ISO p90 | 0.2651 | 0.2775 | ±0.0407 | B | yes | pass |
| K_pct p10 | 0.1186 | 0.1075 | ±0.0250 | B | yes | pass |
| K_pct p50 | 0.1832 | 0.1829 | ±0.0140 | B | yes | pass |
| K_pct p90 | 0.2664 | 0.2689 | ±0.0411 | B | yes | pass |
| BB_pct p10 | 0.0634 | 0.0668 | ±0.0106 | B | yes | pass |
| BB_pct p50 | 0.1012 | 0.1058 | ±0.0136 | B | yes | pass |
| BB_pct p90 | 0.1486 | 0.1584 | ±0.0159 | B | yes | pass |
| ERA p10 | 3.36 | 3.41 | ±0.623 | B | yes | pass |
| ERA p50 | 5.23 | 5.12 | ±0.668 | B | yes | pass |
| ERA p90 | 7.62 | 7.64 | ±1.276 | B | yes | pass |
| K9 p10 | 5.69 | 5.72 | ±0.671 | B | yes | pass |
| K9 p50 | 8.28 | 7.88 | ±0.928 | B | Phase 6 | pass |
| K9 p90 | 11.32 | 10.56 | ±1.313 | B | Phase 6 | pass |

## Leaderboards (full-population extremes)

| Metric | Sim | Benchmark | Tol | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| Pitchers with 50+ IP | 807.4 (season range 771.0–834.0) | 821.1 (56-game eq. of 882) | ±38.2 | A | Phase 6 | pass |
| 50+ IP pitchers with ERA < 2.00 | 6.000 (season range 2.000–13.000) | 5 | ±5.945 | A | yes | pass |
| 50+ IP pitchers with ERA < 3.00 | 44.5 (season range 30.0–70.0) | 57 | ±21.5 | A | yes | pass |
| Teams with ERA < 4.00 | 15.9 (season range 10.0–25.0) | 12 | ±9.6 | A | yes | pass |
| Best team ERA | 2.882 (season range 2.119–3.587) | 3.2 | ±0.686 | A | yes | pass |
| Best team BA | 0.354 (season range 0.332–0.379) | 0.356 | ±0.029 | A | yes | pass |
| Most team HR per game | 2.848 (season range 2.286–3.571) | 2.672 | ±0.797 | A | yes | pass |

## Individual leaders (NCAA.com national leaders 2024–2026, record book 2023)

Counting stats at a 56-game equivalent (each real player's HR × 56 / his games; real leaders' teams played 57–72 games, the sim plays 56); rates as they are. A row passes if the simulated mean lies in the band from the lowest to the highest real season, widened by 3 SE of the simulated mean. Benchmark column: the band, then each season.

| Metric | Sim | Real band (seasons) | Sim SE pad | Conf | Gate | Status |
|---|---|---|---|---|---|---|
| HR leader (56-game equivalent) | 30.9 (season range 26.0–36.0) | 25.5–34.5 (2023 26.3, 2024 34.5, 2025 25.5, 2026 33.4) | ±1.9 | A | yes | pass |
| Hitters with 30+ HR (56-game equivalent) | 1.30 (season range 0.00–4.00) | 0.00–3.00 (2024 3.00, 2025 0.00, 2026 2.00) | ±0.90 | A | yes | pass |
| BA leader (qualified) | 0.448 (season range 0.427–0.485) | 0.433–0.455 (2023 0.449, 2024 0.433, 2025 0.455, 2026 0.446) | ±0.011 | A | yes | pass |
| Top-5 HR hitters, HR per game | 0.501 (season range 0.439–0.576) | 0.410–0.539 (2024 0.539, 2025 0.410, 2026 0.528) | ±0.025 | A | yes | pass |
| Most HR by any player, all 20 seasons (hard ceiling) | 36 | ≤ 48 (D1 record) | — | A | yes | pass |

## Diagnostics

- Earned share of runs 0.8787 (data 0.8824); pitchers per team-game 4.26 (data 4.298)
- Weekend starts by a team's top three starters 0.807 (data 0.789); weekend starters per team 6.24 (data 6.48)
- Innings of a team's three busiest pitchers 72.4, 61.4, 51.3 (data, full-season teams averaging 57.2 games: 77.2, 66.7, 54.4)
