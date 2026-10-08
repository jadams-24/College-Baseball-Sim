# Phase 5 realism report: pitch-by-pitch

40 simulated seasons, seeds 20251000–20251039 (the Phase 4 report's league and seeds). Generated 2026-10-08.
Each plate appearance's outcome comes from the unchanged Phase 4 matchup model. Its pitch sequence comes from a count-state pitch chain conditioned on that outcome (engine/pitch.py), so PA-level rates cannot move. Pitch events by count, batted-ball results by count of contact and every benchmark below come from the 2025 WMT play-by-play pitch sequences, reweighted to the D1 tier mix. Tolerances combine 3 SE of the benchmark (bootstrap over games) with 3 SE of the simulated mean at the number of seasons run. The starter's pull hazard now reads these simulated pitch counts.

## Gate: **PASS**

Phase 1 and Phase 2 gate rows on the same run: **pass** (reports/phase2.md). Phase 4 forward ratings test on the same run: **pass** (reports/phase4.md).

## What the play-by-play supports

Every action of the 2,264 WMT games was checked. Per plate appearance the data has a pitch sequence over B (ball), K (called strike), S (swinging strike), F (foul), P (in play) and H (hit by pitch), plus the final count, the pitch count and a strikeout-looking flag. **There is no pitch type, velocity or location**, so the model has none: no zone, no pitch mix, no velocity. Control vs Eye moves balls and Stuff vs Avoid K moves swinging strikes at every count; zone rate and chase rate cannot be told apart in this data. Cleaning: a P before the last pitch changes neither balls nor strikes but is in the official pitch count; it is kept as a neutral pitch (2598 in the sample). 682 HBPs coded with a final P are read as H. Intentional walks (431 with catcher's interference) are left out (mostly automatic, no pitches), as are 5056 PAs with no sequence and 646 that break the count rules: 171592 of 178073 PAs are used. The engine's walks include the intentional ones (Phase 2 folds IBB into BB), so about 0.2% of simulated PAs get a full four-ball sequence that the data would not count.

## Pitches

| Metric | Sim | Data | Tol | Status |
|---|---|---|---|---|
| Pitches per PA | 3.798 | 3.805 | ±0.033 | pass |
| PAs with 1 pitch | 0.1326 | 0.1311 | ±0.0048 | pass |
| PAs with 2 pitches | 0.1508 | 0.1507 | ±0.0061 | pass |
| PAs with 3 pitches | 0.1728 | 0.1720 | ±0.0055 | pass |
| PAs with 4 pitches | 0.1828 | 0.1827 | ±0.0055 | pass |
| PAs with 5 pitches | 0.1681 | 0.1721 | ±0.0052 | pass |
| PAs with 6 pitches | 0.1171 | 0.1159 | ±0.0052 | pass |
| PAs with 7 pitches | 0.0487 | 0.0477 | ±0.0032 | pass |
| PAs with 8 pitches | 0.0179 | 0.0177 | ±0.0019 | pass |
| PAs with 9 pitches | 0.0062 | 0.0069 | ±0.0015 | pass |
| PAs with 10+ pitches | 0.0030 | 0.0030 | ±0.0007 | pass |
| First-pitch strike rate (first pitch not a ball or HBP) | 0.5828 | 0.5820 | ±0.0069 | pass |
| Foul rate with two strikes (fouls / pitches) | 0.2080 | 0.2078 | ±0.0056 | pass |

## How often each count is reached (share of PAs)

| Metric | Sim | Data | Tol | Status |
|---|---|---|---|---|
| Reach 0-1 | 0.4578 | 0.4580 | ±0.0075 | pass |
| Reach 0-2 | 0.1882 | 0.1881 | ±0.0069 | pass |
| Reach 1-0 | 0.4088 | 0.4097 | ±0.0070 | pass |
| Reach 1-1 | 0.3763 | 0.3766 | ±0.0073 | pass |
| Reach 1-2 | 0.2627 | 0.2629 | ±0.0063 | pass |
| Reach 2-0 | 0.1504 | 0.1516 | ±0.0049 | pass |
| Reach 2-1 | 0.2114 | 0.2125 | ±0.0056 | pass |
| Reach 2-2 | 0.2190 | 0.2192 | ±0.0064 | pass |
| Reach 3-0 | 0.0529 | 0.0536 | ±0.0030 | pass |
| Reach 3-1 | 0.1017 | 0.1031 | ±0.0047 | pass |
| Reach 3-2 | 0.1358 | 0.1366 | ±0.0055 | pass |

## Outcome of the PAs that pass through each count

BA is hits per at-bat, K% and BB% per PA, among the PAs that reach the count at any point.

| Metric | Sim | Data | Tol | Status |
|---|---|---|---|---|
| BA after 0-0 | 0.2817 | 0.2821 | ±0.0080 | pass |
| K% after 0-0 | 0.1948 | 0.1957 | ±0.0085 | pass |
| BB% after 0-0 | 0.1029 | 0.1045 | ±0.0051 | pass |
| BA after 0-1 | 0.2447 | 0.2449 | ±0.0106 | pass |
| K% after 0-1 | 0.2840 | 0.2845 | ±0.0119 | pass |
| BB% after 0-1 | 0.0626 | 0.0627 | ±0.0055 | pass |
| BA after 0-2 | 0.1818 | 0.1837 | ±0.0147 | pass |
| K% after 0-2 | 0.4468 | 0.4458 | ±0.0165 | pass |
| BB% after 0-2 | 0.0385 | 0.0397 | ±0.0075 | pass |
| BA after 1-0 | 0.2963 | 0.2967 | ±0.0122 | pass |
| K% after 1-0 | 0.1585 | 0.1590 | ±0.0111 | pass |
| BB% after 1-0 | 0.1815 | 0.1845 | ±0.0096 | pass |
| BA after 1-1 | 0.2584 | 0.2565 | ±0.0116 | pass |
| K% after 1-1 | 0.2479 | 0.2495 | ±0.0109 | pass |
| BB% after 1-1 | 0.1150 | 0.1159 | ±0.0082 | pass |
| BA after 1-2 | 0.1939 | 0.1945 | ±0.0129 | pass |
| K% after 1-2 | 0.4155 | 0.4153 | ±0.0147 | pass |
| BB% after 1-2 | 0.0707 | 0.0698 | ±0.0078 | pass |
| BA after 2-0 | 0.3129 | 0.3151 | ±0.0255 | pass |
| K% after 2-0 | 0.1162 | 0.1151 | ±0.0151 | pass |
| BB% after 2-0 | 0.3480 | 0.3510 | ±0.0168 | pass |
| BA after 2-1 | 0.2740 | 0.2714 | ±0.0192 | pass |
| K% after 2-1 | 0.1928 | 0.1929 | ±0.0138 | pass |
| BB% after 2-1 | 0.2299 | 0.2363 | ±0.0133 | pass |
| BA after 2-2 | 0.2049 | 0.2051 | ±0.0140 | pass |
| K% after 2-2 | 0.3542 | 0.3537 | ±0.0145 | pass |
| BB% after 2-2 | 0.1474 | 0.1480 | ±0.0108 | pass |
| BA after 3-0 | 0.3014 | 0.3152 | ±0.0565 | pass |
| K% after 3-0 | 0.0650 | 0.0635 | ±0.0174 | pass |
| BB% after 3-0 | 0.6742 | 0.6673 | ±0.0316 | pass |
| BA after 3-1 | 0.2967 | 0.2937 | ±0.0325 | pass |
| K% after 3-1 | 0.1118 | 0.1129 | ±0.0183 | pass |
| BB% after 3-1 | 0.4931 | 0.4963 | ±0.0262 | pass |
| BA after 3-2 | 0.2232 | 0.2225 | ±0.0191 | pass |
| K% after 3-2 | 0.2528 | 0.2526 | ±0.0185 | pass |
| BB% after 3-2 | 0.3565 | 0.3584 | ±0.0187 | pass |

## Starts

Pitches are the starter's pitches on completed plate appearances; innings are the outs on the starter's plate appearances / 3 (as in the data). Midweek p10 is a Phase 6 row (CLAUDE.md deferred rows): the pull hazards ignore tier, and low-tier staffs leave midweek starters in longer. The pull hazard (Phase 2 usage tables, Stamina leash from Phase 4) now reads the simulated pitch counts.

| Metric | Sim | Data | Tol | Status |
|---|---|---|---|---|
| Pitches per start, weekend | 77.1 | 78.0 | ±3.0 | pass |
| Pitches per start, weekend, p10 | 44.7 | 46.0 | ±6.5 | pass |
| Pitches per start, weekend, p50 | 79.8 | 81.0 | ±2.8 | pass |
| Pitches per start, weekend, p90 | 104.4 | 103.0 | ±1.8 | pass |
| Innings per start, weekend | 4.365 | 4.433 | ±0.238 | pass |
| Pitches per start, midweek | 49.7 | 53.8 | ±5.5 | pass |
| Pitches per start, midweek, p10 | 21.6 | 23.0 | ±2.9 | pass (Phase 6) |
| Pitches per start, midweek, p50 | 46.0 | 47.0 | ±4.8 | pass |
| Pitches per start, midweek, p90 | 83.1 | 80.0 | ±6.5 | pass |
| Innings per start, midweek | 2.732 | 3.021 | ±0.374 | pass |

## PA-level outcomes unchanged from Phase 4

League rates of this run against the merged Phase 4 run (reports/phase4_baseline.json), tolerance 3 SE of the difference.

| Metric | Phase 5 | Phase 4 | Tol | Status |
|---|---|---|---|---|
| Runs per team-game | 6.6448 | 6.7423 | ±0.0878 | differs (moved on purpose in PR B: decisions; gated against data in reports/phase2.md) |
| Batting average | 0.2817 | 0.2819 | ±0.0018 | pass |
| On-base pct | 0.3795 | 0.3802 | ±0.0022 | pass |
| Slugging pct | 0.4406 | 0.4424 | ±0.0025 | pass |
| HR per team-game | 1.0570 | 1.0684 | ±0.0182 | pass |
| BB per PA | 0.1049 | 0.1059 | ±0.0014 | pass |
| K per PA | 0.1944 | 0.1949 | ±0.0029 | pass |
| HBP per PA | 0.0340 | 0.0337 | ±0.0005 | pass |
| PA per team-game | 40.6958 | 40.5317 | ±0.1122 | differs (moved on purpose in Phase 6: fielding or base running; gated against data in reports/phase6.md) |
| Errors per team-game | 1.1044 | 1.0820 | ±0.0165 | differs (moved on purpose in Phase 6: fielding or base running; gated against data in reports/phase6.md) |
| ERA | 6.0650 | 6.2210 | ±0.0846 | differs (moved on purpose in PR B: decisions; gated against data in reports/phase6.md) |
| Earned share of runs | 0.8770 | 0.8830 | ±0.0018 | differs (moved on purpose in Phase 6: fielding or base running; gated against data in reports/phase6.md) |

## Informational

- Correction Jacobian (rows d logit P(K), P(BB), P(HBP) at the league chain; columns the average batter-pitcher K direction, BB direction and the HBP event): [[1.024, -0.068, -0.053], [-0.026, 1.339, -0.051], [0.125, 0.117, 1.007]]. League chain without conditioning: K 0.1923, BB 0.1105, HBP 0.0318, in play 0.6653; PA model at league average: K 0.1802, BB 0.1080, HBP 0.0280, in play 0.6838.
- Response of the chain's K and BB logits to one unit of each measured player direction (1, 0 for a K direction and 0, 1 for a BB direction if the event-level directions add up to the rate they were measured on): batter_K [0.97, 0.0]; batter_BB [-0.02, 1.33]; pitcher_K [1.08, -0.05]; pitcher_BB [-0.11, 1.34].
- Pitchers with 50+ IP (Phase 6 deferred row, currently passing): 806.6 (real 882; Phase 4 run 870.6).

### Player pitch profiles (informational)

Qualified players (150+ PA or BF): mean and SD across players of each per-pitch event rate, and its correlation with the player's K% and BB%. The data columns are the raw 2025 sample (P4-heavy, one season, the same sampling noise as a simulated season).

| Side | Event | Mean sim / data | SD sim / data | Corr with K% sim / data | Corr with BB% sim / data |
|---|---|---|---|---|---|
| pitcher | ball | 0.371 / 0.367 | 0.0365 / 0.0305 | -0.44 / -0.23 | +0.88 / +0.84 |
| pitcher | called strike | 0.180 / 0.182 | 0.0162 / 0.0203 | +0.43 / +0.21 | -0.34 / -0.04 |
| pitcher | swinging strike | 0.099 / 0.113 | 0.0259 / 0.0272 | +0.89 / +0.77 | -0.28 / -0.18 |
| pitcher | foul | 0.159 / 0.160 | 0.0176 / 0.0208 | +0.41 / +0.08 | -0.50 / -0.35 |
| pitcher | in play | 0.182 / 0.171 | 0.0270 / 0.0249 | -0.73 / -0.77 | -0.44 / -0.53 |
| batter | ball | 0.378 / 0.385 | 0.0295 / 0.0301 | -0.18 / -0.04 | +0.87 / +0.88 |
| batter | called strike | 0.181 / 0.173 | 0.0219 / 0.0314 | -0.21 / -0.10 | +0.32 / +0.25 |
| batter | swinging strike | 0.094 / 0.099 | 0.0334 / 0.0322 | +0.83 / +0.78 | -0.23 / -0.18 |
| batter | foul | 0.157 / 0.158 | 0.0183 / 0.0234 | +0.16 / +0.01 | -0.50 / -0.42 |
| batter | in play | 0.181 / 0.176 | 0.0268 / 0.0279 | -0.76 / -0.73 | -0.57 / -0.63 |

