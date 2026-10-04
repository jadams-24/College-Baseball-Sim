# Phase 4 realism report: 20–80 ratings

40 simulated seasons, seeds 20251000–20251039, players generated from ratings. Generated 2026-10-04.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **FAIL**

Phase 1 and Phase 2 gate rows on the same run: **FAIL** (reports/phase2.md).

## Round trip, forward: true rates → 40 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 20 folds of 2 seasons. Tolerance is 3.45 SE across folds (Student t, 19 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2316 | +0.0012 ± 0.0021 | +0.10 | pass | 0.977 ± 0.013 | FAIL | 1.001 ± 0.014 | pass |
| gap | XBH share of hits | 2162 | +0.0014 ± 0.0039 | +0.05 | pass | 1.002 ± 0.014 | pass | 1.007 ± 0.017 | pass |
| power | HR/PA | 2462 | +0.0003 ± 0.0042 | +0.00 | pass | 0.997 ± 0.009 | pass | 1.002 ± 0.012 | pass |
| eye | BB/PA | 2462 | -0.0002 ± 0.0025 | -0.01 | pass | 0.997 ± 0.009 | pass | 0.998 ± 0.016 | pass |
| avoid_k | K/PA | 2462 | +0.0001 ± 0.0024 | +0.00 | pass | 1.002 ± 0.005 | pass | 0.994 ± 0.014 | pass |
| stuff | K/BF | 1838 | -0.0013 ± 0.0025 | -0.03 | pass | 1.000 ± 0.005 | pass | 0.988 ± 0.013 | pass |
| control | BB/BF | 1838 | -0.0016 ± 0.0025 | -0.04 | pass | 1.002 ± 0.008 | pass | 0.996 ± 0.013 | pass |
| movement | HR/BF | 1838 | -0.0019 ± 0.0053 | -0.06 | pass | 1.008 ± 0.015 | pass | 0.996 ± 0.014 | pass |
| stamina | pull hazard (log leash) | 4227 | +0.0012 ± 0.0021 | — | pass | 1.001 ± 0.005 | pass | 0.997 ± 0.014 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0011 / 0.979 / 0.997 | -0.0001 / 0.958 † / 1.002 | +0.0040 † / 0.974 † / 1.003 |
| gap | plate appearances | -0.0015 / 1.010 / 0.993 | +0.0030 / 1.004 / 1.018 | +0.0020 / 0.994 / 1.009 |
| power | plate appearances | -0.0016 / 1.000 / 1.027 | +0.0012 / 0.993 / 1.002 | +0.0005 / 0.997 / 0.990 |
| eye | plate appearances | -0.0025 / 0.993 / 0.984 | -0.0009 / 0.997 / 0.997 | +0.0019 / 0.998 / 1.007 |
| avoid_k | plate appearances | +0.0012 / 1.003 / 0.999 | +0.0001 / 1.002 / 0.994 | -0.0007 / 1.000 / 0.989 |
| stuff | batters faced | -0.0021 / 1.001 / 0.986 | -0.0019 / 0.996 / 0.998 | -0.0004 / 1.002 / 0.983 |
| control | batters faced | +0.0025 / 1.005 / 0.999 | +0.0014 / 0.998 / 0.990 | -0.0065 † / 0.998 / 0.998 |
| movement | batters faced | +0.0019 / 1.006 / 0.996 | +0.0044 / 1.008 / 1.009 | -0.0084 † / 1.006 / 0.987 |
| stamina | appearances | -0.0061 † / 1.003 / 1.008 | -0.0063 † / 1.002 / 0.988 | +0.0105 † / 0.997 / 0.999 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.936 | 1.042 |
| gap | 0.978 | 1.028 |
| power | 0.924 | 1.199 |
| eye | 1.007 | 1.062 |
| avoid_k | 0.977 | 1.125 |
| stuff | 1.001 | 1.183 |
| control | 1.002 | 1.049 |
| movement | 1.011 | 1.137 |

## True rating distributions (mean of 40 seasons)

Everyday players: regulars for batting ratings, weekend starters for pitching ratings. A P4 everyday player should average above 50 and a low-tier one below.

| Rating | D1 weighted mean | D1 weighted SD | P4 everyday | Mid everyday | Low everyday | Status |
|---|---|---|---|---|---|---|
| contact | 49.5 | 9.8 | 57.6 | 51.3 | 46.1 | pass |
| gap | 49.6 | 9.8 | 55.7 | 50.7 | 46.6 | pass |
| power | 49.5 | 9.7 | 57.1 | 49.5 | 44.1 | pass |
| eye | 49.9 | 9.9 | 54.8 | 49.8 | 45.9 | pass |
| avoid_k | 49.7 | 10.0 | 56.4 | 51.0 | 46.5 | pass |
| stuff | 50.3 | 9.7 | 58.8 | 51.2 | 45.6 | pass |
| control | 50.8 | 9.6 | 58.4 | 53.4 | 49.8 | pass |
| movement | 50.2 | 9.4 | 52.4 | 49.1 | 46.9 | pass |
| stamina | 51.7 | 10.0 | 49.9 | 49.9 | 50.0 | — |

## Example player cards (first simulated season)

| Player | Team (tier) | Role | Ratings | Season |
|---|---|---|---|---|
| Best P4 hitter (OPS, qualified): D. Stealt | Thajyx Kestrels (p4) | regular | Contact 62, Gap 68, Power 68, Eye 70, Avoid K 54, Speed 55 | 56 G, 268 PA, 0.387/0.494/0.863, 26 HR, 17.5% BB, 14.6% K |
| Median mid-major regular: CL. Feawor | Thaix Bluejays (mid) | regular | Contact 48, Gap 62, Power 54, Eye 65, Avoid K 46, Speed 51 | 42 G, 177 PA, 0.264/0.383/0.438, 5 HR, 15.8% BB, 21.5% K |
| Median low-tier regular: D. Hean | Koford Miners (low) | regular | Contact 49, Gap 54, Power 49, Eye 53, Avoid K 42, Speed 49 | 44 G, 189 PA, 0.306/0.390/0.431, 3 HR, 9.5% BB, 18.5% K |
| Home-run leader: S. Gyr | Stoukouberg Coyotes (p4) | regular | Contact 64, Gap 64, Power 70, Eye 55, Avoid K 49, Speed 32 | 56 G, 267 PA, 0.351/0.404/0.753, 26 HR, 7.1% BB, 23.6% K |
| Highest true Contact, qualified: H. Weawood | Briberg Comets (p4) | regular | Contact 80, Gap 56, Power 74, Eye 60, Avoid K 58, Speed 64 | 56 G, 274 PA, 0.352/0.435/0.678, 20 HR, 12.4% BB, 18.2% K |
| Bench player with most PA: V. Noult | Neagear Cardinals (mid) | bench | Contact 39, Gap 48, Power 47, Eye 51, Avoid K 51, Speed 41 | 41 G, 138 PA, 0.252/0.397/0.411, 4 HR, 13.0% BB, 16.7% K |
| Best P4 weekend starter (ERA, qualified): P. Reans | Nythaberg Bluejays (p4) | sp_weekend | Stuff 80, Control 59, Movement 55, Stamina 60 | 14 G, 13 GS, 79.0 IP, 1.37 ERA, 16.3 K/9, 2.4 BB/9, 0.5 HR/9 |
| Median mid-major weekend starter: F. Zigrult | Nivoul Raptors (mid) | sp_weekend | Stuff 50, Control 52, Movement 53, Stamina 50 | 15 G, 13 GS, 71.1 IP, 5.05 ERA, 6.8 K/9, 4.9 BB/9, 1.3 HR/9 |
| Low-tier reliever with most innings: W. Gut | Niceason Ironmen (low) | rp | Stuff 54, Control 63, Movement 52, Stamina 69 | 19 G, 2 GS, 68.1 IP, 5.27 ERA, 7.0 K/9, 2.8 BB/9, 0.7 HR/9 |
| Starter with the highest true Stamina: ST. Theatem | Zytheawell Miners (low) | sp_weekend | Stuff 54, Control 70, Movement 46, Stamina 79 | 11 G, 9 GS, 56.0 IP, 5.46 ERA, 8.5 K/9, 2.1 BB/9, 1.0 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2316 | 1.056 ± 0.041 | 0.03 ± 0.07 | 7.26 / 6.98 | 1.040 ± 0.021 | 0.36 |
| gap | 2162 | 1.031 ± 0.038 | -0.41 ± 0.09 | 7.78 / 7.57 | 1.028 ± 0.020 | 0.39 |
| power | 2462 | 1.058 ± 0.023 | 0.15 ± 0.07 | 6.21 / 5.25 | 1.183 ± 0.016 | 0.59 |
| eye | 2462 | 0.962 ± 0.012 | 0.13 ± 0.04 | 5.85 / 5.83 | 1.004 ± 0.010 | 0.65 |
| avoid_k | 2462 | 1.002 ± 0.007 | 0.02 ± 0.02 | 4.53 / 4.34 | 1.043 ± 0.008 | 0.78 |
| stuff | 1838 | 0.976 ± 0.008 | 0.30 ± 0.04 | 3.93 / 3.68 | 1.066 ± 0.016 | 0.86 |
| control | 1838 | 0.967 ± 0.009 | 0.45 ± 0.04 | 4.95 / 4.87 | 1.016 ± 0.006 | 0.72 |
| movement | 1838 | 0.787 ± 0.018 | 0.87 ± 0.09 | 7.86 / 8.48 | 0.927 ± 0.014 | 0.46 |
| stamina | 4226 | 1.000 ± 0.006 | 0.02 ± 0.04 | 4.59 / 4.59 | 0.999 ± 0.008 | 0.79 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

