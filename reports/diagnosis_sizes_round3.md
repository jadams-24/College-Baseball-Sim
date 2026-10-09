# Diagnosis sizes, round 3: the sim side on the final engine (variance stage)

2026-10-09. Owner (2026-10-08): "size times through the order, mop-up pitching, PA length by base state and platoon lineups (sizes only), with the running total". Scripts: `scripts/diag_round3_sim.py` (an instrumented play-by-play of 8 simulated seasons, seeds 980001+; the instrumentation draws nothing: an instrumented season equals the uninstrumented checkpoint on every metric) and `scripts/diag_round3.py` (round 2's estimators on the simulated play-by-play). JSON: `reports/diagnosis_sizes_round3.json`. Nothing was changed in the engine.

Round 2 sized each mechanism on real data only (an upper bound on what it could add). Round 3 measures the same quantity on the current engine, so **real minus engine** is what building the mechanism could add.

**The gap now.** Dispersion of runs per team-game around the scoreboard fit: engine 2.214 ± 0.011 (8 seasons; the 40-season Phase 6 report: 2.209) against real 2.6185; missing 0.404.

## Sized list and running total (dispersion units, Δφ; what a fix could add to the engine)

| Candidate | Real minus engine | SE | Share of the missing | Running total (share) | Notes |
|---|---|---|---|---|---|
| 11. Starter day-to-day form (5+ starts) | -0.032 | 0.055 | -8% | -0.032 ± 0.055 (-8%) | not measured (the engine has no start-level form: about 0) |
| 12. Errors clustering in half-innings | +0.012 | 0.010 | +3% | -0.020 ± 0.056 (-5%) | not measured (errors independent by play: about 0) |
| 3. Times through the order: the remaining penalty | -0.042 | 0.008 | -10% | -0.062 ± 0.056 (-15%) | the engine already has +0.008 / +0.014 / +0.011 runs per PA (2nd / 3rd / 4th+) against +0.032 / +0.053 / +0.078 |
| 4. Mop-up: relief entries at a margin of 5+ | +0.130 | 0.019 | +32% | +0.068 ± 0.059 (+17%) | engine -0.064 ± 0.003 against real +0.066 ± 0.019 |
| 5. Plate-appearance length by base state | +0.001 | 0.000 | +0% | +0.068 ± 0.059 (+17%) | pitches per PA with runners on minus empty, within result: real -0.036 ± 0.008, engine -0.019 ± 0.001 |
| 6. Platoon lineups | -0.000 | 0.000 | -0% | +0.068 ± 0.059 (+17%) | real lineups add +0.020 to the platoon-advantage share; +0.0041 runs per team-game |

- Sources that add variance (positive rows): +0.142, 35% of the missing. Times through the order would narrow it further, as round 2 found with the real hook.

## Bullpen deployment: the main lead

| Relief entries | Engine | Real | Real minus engine | Corr. with the rest of the team-game (engine / real) | Entering pitcher minus team relief mean, rv per PA (engine / real) |
|---|---|---|---|---|---|
| Margin 5+ | -0.064 ± 0.003 | +0.066 ± 0.019 | +0.130 ± 0.019 | -0.102 / +0.125 | +0.0035 / +0.0179 |
| Margin 7+ (the engine's blowout bin) | -0.028 ± 0.003 | +0.065 ± 0.017 | +0.093 ± 0.017 | -0.059 / +0.154 | +0.0078 / +0.0263 |
| All | -0.215 ± 0.004 | -0.029 ± 0.025 | +0.186 ± 0.025 | -0.196 / -0.013 | -0.0002 / — |

- Blowout relievers in the engine are only a little worse than their team's relief mean (+.004 at 5+, +.008 at 7+ runs per PA) against real +.018 and +.026: real teams hand blowouts to clearly worse arms, the engine's relief choice much less so.
- Across all relief entries the engine's quality component is strongly anti-correlated with the rest of the game (-0.20 against -0.01): its relief choice sorts the best relievers into close games and the worst out of them much more sharply than real teams do, which damps game-to-game variance. Real minus engine on all relief entries: +0.186 ± 0.025 (46% of the missing); the 5+ row above is part of it, not additional.
- P4-only comparison (2026-10-09, `scripts/diag_bullpen_p4.py`, `reports/diagnosis_bullpen_p4.json`): the gap holds on the 36 P4 staffs against the engine's P4 staffs (margin 5+: +.126 ± .024; all relief entries: +.208 ± .033).
- Mechanism check (2026-10-09, `scripts/diag_bullpen_feedback.py`): the reading above, that the engine sorts relievers too sharply, does not hold. Real staffs have no wider reliever talent spread than the engine's, yet real workload tracks observed quality twice as steeply (lowest workload third +.033, highest -.031 runs per PA against the staff mean; engine +.019 / -.013), and real relief usage reacts to results: per run of value allowed in an outing, the reliever's next entry is a blowout (7+) 1.8 points more often (P4, ± .5; engine 0 ± .2). Part of the real mop-up gap is therefore selection on noise (relievers who were hit elsewhere pitch the blowouts), which the leave-game-out estimator reads as quality. Fix design to the owner before building.

## Plate-appearance length by base state

- Real plate appearances with runners on are not longer: within the result they are -0.036 ± 0.008 pitches shorter (pickoff throws are not pitches). The engine's are -0.019 ± 0.001 shorter already (steals and pitchouts end some).
- The difference moves -0.16 pitches and -0.043 batters per start from the starter to the bullpen: Δφ +0.0006. Negligible; and it does not explain the steal-timing watch item (real attempts come later in the plate appearance).

## Platoon lineups

- Engine: the starting nine's left-handed share against right-handed minus left-handed starters, within team: +0.0025 ± 0.0004 (the lineup ignores the starter's hand: GUESSES.md). Platoon-advantage share of all plate appearances 0.462 ± 0.002 (real .480).
- Real (`data/ncaa_2025/roster_aggregates/lineup_by_starter_hand.csv`, roster run 37878486296, 169 teams with starters of both hands): the starting nine's left-handed share is +0.047 higher against right-handed starters (P4 +0.050, mid +0.044, low +0.024), and the right-handed share +0.048 higher against left-handers. Against a fixed lineup that adds +0.020 to the platoon-advantage share of the starting nine: engine .462 + .020 is about the real .480, so platoon lineups close that gap. The lineup's quality cost is nil (-0.0007 ± 0.0006 runs per starter PA, against left- minus right-handed starters).
- Size on the engine's team-games (8 seasons): the advantage is worth +0.0084 runs per PA (batter-demeaned), so the response adds +0.0041 runs per team-game, Δφ -0.0001 ± 0.0000 (correlation with the rest of the game -0.024): nothing for dispersion or margins. Worth building for the platoon-advantage share (Phase 3's reported row), not for the watch item.

## Phase 3's measured variance link (40 seasons, against PR B's run)

| Row | Real | PR B | Phase 3 | Change | Gap closed |
|---|---|---|---|---|---|
| P4 vs mid nonconference margin SD | 5.9702 | 5.6139 | 5.6890 | +0.0751 ± 0.0412 | 21% ± 12% |
| Regional upset rate (games without the host) | 0.3705 | 0.3425 | 0.3527 | +0.0102 ± 0.0159 | 37% ± 57% |
| Runs per team-game, 15+ bin | 0.0664 | 0.0509 | 0.0515 | +0.0006 ± 0.0012 | 4% ± 8% |
| Run-rule frequency | 0.1412 | 0.1164 | 0.1156 | -0.0008 ± 0.0020 | -3% ± 8% |
