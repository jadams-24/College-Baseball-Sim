# Phase 5 realism report: pitch-by-pitch

20 simulated seasons, seeds 20251000–20251019 (the Phase 4 report's league and seeds). Generated 2026-10-03.
Each plate appearance's outcome comes from the unchanged Phase 4 matchup model. Its pitch sequence comes from a count-state pitch chain conditioned on that outcome (engine/pitch.py), so PA-level rates cannot move. Pitch events by count, batted-ball results by count of contact and every benchmark below come from the 2025 WMT play-by-play pitch sequences, reweighted to the D1 tier mix. Tolerances combine 3 SE of the benchmark (bootstrap over games) with 3 SE of the simulated mean at the number of seasons run. The starter's pull hazard now reads these simulated pitch counts.

## Gate: **FAIL**

Phase 1 and Phase 2 gate rows on the same run: **FAIL** (reports/phase2.md). Phase 4 forward ratings test on the same run: **FAIL** (reports/phase4.md).

## What the play-by-play supports

Every action of the 2,264 WMT games was checked. Per plate appearance the data has a pitch sequence over B (ball), K (called strike), S (swinging strike), F (foul), P (in play) and H (hit by pitch), plus the final count, the pitch count and a strikeout-looking flag. **There is no pitch type, velocity or location**, so the model has none: no zone, no pitch mix, no velocity. Control vs Eye moves balls and Stuff vs Avoid K moves swinging strikes at every count; zone rate and chase rate cannot be told apart in this data. Cleaning: a P before the last pitch changes neither balls nor strikes but is in the official pitch count; it is kept as a neutral pitch (2598 in the sample). 682 HBPs coded with a final P are read as H. Intentional walks (431 with catcher's interference) are left out (mostly automatic, no pitches), as are 5056 PAs with no sequence and 646 that break the count rules: 171592 of 178073 PAs are used. The engine's walks include the intentional ones (Phase 2 folds IBB into BB), so about 0.2% of simulated PAs get a full four-ball sequence that the data would not count.

## Pitches

| Metric | Sim | Data | Tol | Status |
|---|---|---|---|---|
| Pitches per PA | 3.815 | 3.805 | ±0.033 | pass |
| PAs with 1 pitch | 0.1304 | 0.1311 | ±0.0049 | pass |
| PAs with 2 pitches | 0.1502 | 0.1507 | ±0.0061 | pass |
| PAs with 3 pitches | 0.1712 | 0.1720 | ±0.0055 | pass |
| PAs with 4 pitches | 0.1829 | 0.1827 | ±0.0055 | pass |
| PAs with 5 pitches | 0.1700 | 0.1721 | ±0.0052 | pass |
| PAs with 6 pitches | 0.1191 | 0.1159 | ±0.0052 | pass |
| PAs with 7 pitches | 0.0491 | 0.0477 | ±0.0033 | pass |
| PAs with 8 pitches | 0.0181 | 0.0177 | ±0.0019 | pass |
| PAs with 9 pitches | 0.0062 | 0.0069 | ±0.0015 | pass |
| PAs with 10+ pitches | 0.0030 | 0.0030 | ±0.0007 | pass |
| First-pitch strike rate (first pitch not a ball or HBP) | 0.5800 | 0.5820 | ±0.0071 | pass |
| Foul rate with two strikes (fouls / pitches) | 0.2066 | 0.2078 | ±0.0056 | pass |

## How often each count is reached (share of PAs)

| Metric | Sim | Data | Tol | Status |
|---|---|---|---|---|
| Reach 0-1 | 0.4570 | 0.4580 | ±0.0077 | pass |
| Reach 0-2 | 0.1865 | 0.1881 | ±0.0070 | pass |
| Reach 1-0 | 0.4117 | 0.4097 | ±0.0071 | pass |
| Reach 1-1 | 0.3791 | 0.3766 | ±0.0073 | pass |
| Reach 1-2 | 0.2638 | 0.2629 | ±0.0065 | pass |
| Reach 2-0 | 0.1521 | 0.1516 | ±0.0051 | pass |
| Reach 2-1 | 0.2143 | 0.2125 | ±0.0056 | pass |
| Reach 2-2 | 0.2216 | 0.2192 | ±0.0064 | pass |
| Reach 3-0 | 0.0536 | 0.0536 | ±0.0030 | pass |
| Reach 3-1 | 0.1039 | 0.1031 | ±0.0047 | pass |
| Reach 3-2 | 0.1385 | 0.1366 | ±0.0055 | pass |

## Outcome of the PAs that pass through each count

BA is hits per at-bat, K% and BB% per PA, among the PAs that reach the count at any point.

| Metric | Sim | Data | Tol | Status |
|---|---|---|---|---|
| BA after 0-0 | 0.2822 | 0.2821 | ±0.0081 | pass |
| K% after 0-0 | 0.1946 | 0.1957 | ±0.0087 | pass |
| BB% after 0-0 | 0.1052 | 0.1045 | ±0.0052 | pass |
| BA after 0-1 | 0.2457 | 0.2449 | ±0.0107 | pass |
| K% after 0-1 | 0.2828 | 0.2845 | ±0.0120 | pass |
| BB% after 0-1 | 0.0644 | 0.0627 | ±0.0055 | pass |
| BA after 0-2 | 0.1829 | 0.1837 | ±0.0147 | pass |
| K% after 0-2 | 0.4455 | 0.4458 | ±0.0167 | pass |
| BB% after 0-2 | 0.0397 | 0.0397 | ±0.0075 | pass |
| BA after 1-0 | 0.2974 | 0.2967 | ±0.0123 | pass |
| K% after 1-0 | 0.1587 | 0.1590 | ±0.0112 | pass |
| BB% after 1-0 | 0.1840 | 0.1845 | ±0.0097 | pass |
| BA after 1-1 | 0.2591 | 0.2565 | ±0.0117 | pass |
| K% after 1-1 | 0.2476 | 0.2495 | ±0.0110 | pass |
| BB% after 1-1 | 0.1173 | 0.1159 | ±0.0082 | pass |
| BA after 1-2 | 0.1948 | 0.1945 | ±0.0130 | pass |
| K% after 1-2 | 0.4145 | 0.4153 | ±0.0148 | pass |
| BB% after 1-2 | 0.0722 | 0.0698 | ±0.0078 | pass |
| BA after 2-0 | 0.3150 | 0.3151 | ±0.0255 | pass |
| K% after 2-0 | 0.1163 | 0.1151 | ±0.0152 | pass |
| BB% after 2-0 | 0.3506 | 0.3510 | ±0.0169 | pass |
| BA after 2-1 | 0.2756 | 0.2714 | ±0.0192 | pass |
| K% after 2-1 | 0.1924 | 0.1929 | ±0.0139 | pass |
| BB% after 2-1 | 0.2331 | 0.2363 | ±0.0134 | pass |
| BA after 2-2 | 0.2052 | 0.2051 | ±0.0141 | pass |
| K% after 2-2 | 0.3545 | 0.3537 | ±0.0146 | pass |
| BB% after 2-2 | 0.1495 | 0.1480 | ±0.0108 | pass |
| BA after 3-0 | 0.3033 | 0.3152 | ±0.0566 | pass |
| K% after 3-0 | 0.0648 | 0.0635 | ±0.0174 | pass |
| BB% after 3-0 | 0.6751 | 0.6673 | ±0.0317 | pass |
| BA after 3-1 | 0.2993 | 0.2937 | ±0.0325 | pass |
| K% after 3-1 | 0.1112 | 0.1129 | ±0.0183 | pass |
| BB% after 3-1 | 0.4951 | 0.4963 | ±0.0263 | pass |
| BA after 3-2 | 0.2234 | 0.2225 | ±0.0192 | pass |
| K% after 3-2 | 0.2532 | 0.2526 | ±0.0185 | pass |
| BB% after 3-2 | 0.3586 | 0.3584 | ±0.0188 | pass |

## Starts

Pitches are the starter's pitches on completed plate appearances; innings are the outs on the starter's plate appearances / 3 (as in the data). Midweek p10 is a Phase 6 row (CLAUDE.md deferred rows): the pull hazards ignore tier, and low-tier staffs leave midweek starters in longer. The pull hazard (Phase 2 usage tables, Stamina leash from Phase 4) now reads the simulated pitch counts.

| Metric | Sim | Data | Tol | Status |
|---|---|---|---|---|
| Pitches per start, weekend | 77.2 | 78.0 | ±3.0 | pass |
| Pitches per start, weekend, p10 | 44.5 | 46.0 | ±6.5 | pass |
| Pitches per start, weekend, p50 | 80.0 | 81.0 | ±2.8 | pass |
| Pitches per start, weekend, p90 | 104.6 | 103.0 | ±1.9 | pass |
| Innings per start, weekend | 4.343 | 4.433 | ±0.239 | pass |
| Pitches per start, midweek | 49.6 | 53.8 | ±5.5 | pass |
| Pitches per start, midweek, p10 | 21.4 | 23.0 | ±2.9 | pass (Phase 6) |
| Pitches per start, midweek, p50 | 46.0 | 47.0 | ±4.8 | pass |
| Pitches per start, midweek, p90 | 83.0 | 80.0 | ±6.5 | pass |
| Innings per start, midweek | 2.709 | 3.021 | ±0.374 | pass |

## PA-level outcomes unchanged from Phase 4

League rates of this run against the merged Phase 4 run (reports/phase4_baseline.json), tolerance 3 SE of the difference.

| Metric | Phase 5 | Phase 4 | Tol | Status |
|---|---|---|---|---|
| Runs per team-game | 6.7378 | 6.7423 | ±0.1088 | pass |
| Batting average | 0.2822 | 0.2819 | ±0.0022 | pass |
| On-base pct | 0.3802 | 0.3802 | ±0.0028 | pass |
| Slugging pct | 0.4419 | 0.4424 | ±0.0027 | pass |
| HR per team-game | 1.0561 | 1.0684 | ±0.0203 | pass |
| BB per PA | 0.1052 | 0.1059 | ±0.0017 | pass |
| K per PA | 0.1946 | 0.1949 | ±0.0034 | pass |
| HBP per PA | 0.0340 | 0.0337 | ±0.0006 | pass |
| PA per team-game | 40.5128 | 40.5317 | ±0.1266 | pass |
| Errors per team-game | 1.1034 | 1.0820 | ±0.0225 | pass (Phase 6 fielding; gated against data in reports/phase6.md) |
| ERA | 6.1822 | 6.2210 | ±0.1031 | pass |
| Earned share of runs | 0.8782 | 0.8830 | ±0.0024 | differs (Phase 6 fielding; gated against data in reports/phase6.md) |

## Informational

- Correction Jacobian (rows d logit P(K), P(BB), P(HBP) at the league chain; columns the average batter-pitcher K direction, BB direction and the HBP event): [[1.029, -0.038, -0.053], [-0.013, 1.364, -0.051], [0.134, 0.13, 1.006]]. League chain without conditioning: K 0.1877, BB 0.0994, HBP 0.0317, in play 0.6812; PA model at league average: K 0.1808, BB 0.1073, HBP 0.0277, in play 0.6842.
- Response of the chain's K and BB logits to one unit of each measured player direction (1, 0 for a K direction and 0, 1 for a BB direction if the event-level directions add up to the rate they were measured on): batter_K [0.97, 0.01]; batter_BB [0.01, 1.36]; pitcher_K [1.09, -0.04]; pitcher_BB [-0.08, 1.37].
- Pitchers with 50+ IP (Phase 6 deferred row, currently passing): 780.0 (real 882; Phase 4 run 870.6).

### Player pitch profiles (informational)

Qualified players (150+ PA or BF): mean and SD across players of each per-pitch event rate, and its correlation with the player's K% and BB%. The data columns are the raw 2025 sample (P4-heavy, one season, the same sampling noise as a simulated season).

| Side | Event | Mean sim / data | SD sim / data | Corr with K% sim / data | Corr with BB% sim / data |
|---|---|---|---|---|---|
| pitcher | ball | 0.374 / 0.367 | 0.0378 / 0.0305 | -0.46 / -0.23 | +0.89 / +0.84 |
| pitcher | called strike | 0.181 / 0.182 | 0.0159 / 0.0203 | +0.44 / +0.21 | -0.35 / -0.04 |
| pitcher | swinging strike | 0.098 / 0.113 | 0.0267 / 0.0272 | +0.90 / +0.77 | -0.31 / -0.18 |
| pitcher | foul | 0.157 / 0.160 | 0.0178 / 0.0208 | +0.43 / +0.08 | -0.52 / -0.35 |
| pitcher | in play | 0.180 / 0.171 | 0.0270 / 0.0249 | -0.72 / -0.77 | -0.43 / -0.53 |
| batter | ball | 0.381 / 0.385 | 0.0293 / 0.0301 | -0.19 / -0.04 | +0.88 / +0.88 |
| batter | called strike | 0.182 / 0.173 | 0.0218 / 0.0314 | -0.25 / -0.10 | +0.35 / +0.25 |
| batter | swinging strike | 0.093 / 0.099 | 0.0339 / 0.0322 | +0.84 / +0.78 | -0.25 / -0.18 |
| batter | foul | 0.156 / 0.158 | 0.0182 / 0.0234 | +0.18 / +0.01 | -0.52 / -0.42 |
| batter | in play | 0.180 / 0.176 | 0.0265 / 0.0279 | -0.75 / -0.73 | -0.57 / -0.63 |

