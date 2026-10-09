# Bullpen deployment: variance fix #1 (option A)

Owner decision 2026-10-09: model the demotion first (the AI's relief choice reacts to each reliever's recent results), gate it, re-measure the mop-up and all-entries gaps with the same estimator, and add a fixed quality-by-margin term only for a significant remainder.

## What was built

1. **Recent form** (`scripts/build_bullpen_form.py`): the relief choice's conditional logit refitted on the 2025 play-by-play (9192 relief choices, 50 full-season staffs) with, per leverage (late and close / other / blowout), the runs allowed in the reliever's last outing (capped at 5), the mean over the three before it, and a no-outing-yet term. The form terms are scaled by 1.6909 so the engine's within-pitcher slopes match the real P4 ones (`scripts/solve_bullpen_form.py`): fitted on real staffs, observed form also carries quality, which the engine's roles already sort by.
2. **Quality by margin** (only after step 1; the remainder was significant): utility + γ × badness z (within staff, K − BB − HR talent) × clip((|margin| − 4)/4, 0, 1), γ = 0.7465 solved in the engine against the real P4 relief-entry quality at a margin of 8+. One-sided: a first, two-sided version (weight −1 at a tie) concentrated close games on each staff's best reliever (busiest pitcher 27.0 appearances against 24.49 ± 1.22); the one-sided term gives 24.28 and every usage row passes.

## Gate rows (P4 staffs; reports/phase6.md, 40 seasons)

| Row | Real P4 | ± (3 SE) |
|---|---|---|
| Next entry a blowout, per run allowed last outing | +0.0109 | 0.0123 |
| Next entry margin, per run | +0.068 | 0.106 |
| Workload third low: runs per BF against staff | +0.0147 | 0.0246 |
| Workload third mid: runs per BF against staff | +0.0067 | 0.0155 |
| Workload third high: runs per BF against staff | -0.0164 | 0.0136 |
| Relief-entry quality, margin 0-1 | -0.0057 | 0.0043 |
| Relief-entry quality, margin 2-3 | -0.0037 | 0.0051 |
| Relief-entry quality, margin 4 | -0.0034 | 0.0069 |
| Relief-entry quality, margin 5-7 | +0.0034 | 0.0054 |
| Relief-entry quality, margin 8+ | +0.0127 | 0.0100 |

## What each part closes (8 instrumented seasons each, seeds 980001-980008; round 2's estimators)

Missing dispersion before: real 2.6185 minus engine 2.214 = 0.404.

| Engine | Dispersion φ | Within-game residual corr. | Relief quality Δφ, all entries (corr. with rest of game) | P4 real minus engine: margin 5+ / all entries |
|---|---|---|---|---|
| Before (round 3) | +2.214 ± 0.011 | +0.044 ± 0.003 | -0.215 ± 0.004 (-0.196) | +0.126 ± 0.024 / +0.208 ± 0.033 |
| + recent form | +2.210 ± 0.013 | +0.046 ± 0.005 | -0.208 ± 0.003 (-0.189) | +0.117 ± 0.024 / +0.204 ± 0.030 |
| + quality by margin (one-sided, final) | +2.236 ± 0.011 | +0.055 ± 0.004 | -0.185 ± 0.003 (-0.161) | +0.110 ± 0.024 / +0.205 ± 0.032 |

- Recent form: Δφ -0.005 ± 0.017 (-1% of the missing): nothing. Real usage reacts to results and the engine now does too (gated), but which reliever happens to be in a slump barely moves game-to-game variance.
- Quality by margin: Δφ +0.027 ± 0.017 (+7% of the missing; 1.6 SE). Real 0.073 within-game residual correlation; the engine moves from .044 to .055. (The two-sided version gave +0.039, 10%, but failed the busiest-pitcher row.)
- Still open: the engine's relief-quality component stays far more anti-correlated with the rest of the game than real (all entries, real −.03). Real minus engine on P4 staffs is still about +.11 (margin 5+) and +.20 (all entries); the entry-quality rows themselves now match, so what remains is not who enters at which margin. Candidates for the next round: how quickly relievers are pulled after runs (the pull hazard by runs is pooled), and the starter's pull timing in games already lopsided.

