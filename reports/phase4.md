# Phase 4 realism report: 20–80 ratings

20 simulated seasons, seeds 20251000–20251019, players generated from ratings. Generated 2026-10-03.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **FAIL**

Phase 1 and Phase 2 gate rows on the same run: **FAIL** (reports/phase2.md).

## Round trip, forward: true rates → 20 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 10 folds of 2 seasons. Tolerance is 4.09 SE across folds (Student t, 9 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2314 | +0.0021 ± 0.0036 | +0.16 | pass | 0.990 ± 0.024 | pass | 0.995 ± 0.030 | pass |
| gap | XBH share of hits | 2155 | -0.0042 ± 0.0048 | -0.17 | pass | 0.995 ± 0.018 | pass | 0.990 ± 0.026 | pass |
| power | HR/PA | 2461 | +0.0021 ± 0.0053 | +0.03 | pass | 1.000 ± 0.011 | pass | 0.998 ± 0.030 | pass |
| eye | BB/PA | 2461 | +0.0006 ± 0.0036 | +0.02 | pass | 1.001 ± 0.020 | pass | 0.989 ± 0.039 | pass |
| avoid_k | K/PA | 2461 | -0.0003 ± 0.0045 | -0.01 | pass | 0.997 ± 0.010 | pass | 0.999 ± 0.030 | pass |
| stuff | K/BF | 1832 | -0.0018 ± 0.0042 | -0.04 | pass | 1.001 ± 0.009 | pass | 1.006 ± 0.045 | pass |
| control | BB/BF | 1832 | +0.0004 ± 0.0036 | +0.01 | pass | 0.999 ± 0.018 | pass | 1.018 ± 0.026 | pass |
| movement | HR/BF | 1832 | +0.0010 ± 0.0085 | +0.03 | pass | 1.004 ± 0.030 | pass | 1.011 ± 0.048 | pass |
| stamina | pull hazard (log leash) | 4215 | +0.0021 ± 0.0044 | — | pass | 1.001 ± 0.007 | pass | 0.996 ± 0.020 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0034 / 0.974 / 0.988 | +0.0007 / 0.983 / 0.999 | +0.0071 † / 0.979 / 0.996 |
| gap | plate appearances | -0.0047 / 1.015 / 0.992 | -0.0030 / 0.993 / 0.992 | -0.0050 / 0.985 / 0.987 |
| power | plate appearances | +0.0020 / 0.998 / 0.996 | -0.0024 / 0.999 / 0.975 | +0.0052 / 1.000 / 1.015 |
| eye | plate appearances | -0.0003 / 1.005 / 0.999 | +0.0003 / 0.994 / 0.991 | +0.0015 / 1.002 / 0.982 |
| avoid_k | plate appearances | -0.0005 / 1.004 / 1.009 | +0.0007 / 0.994 / 1.022 | -0.0010 / 0.993 / 0.972 |
| stuff | batters faced | -0.0024 / 0.996 / 1.007 | -0.0017 / 1.001 / 1.007 | -0.0015 / 1.003 / 1.004 |
| control | batters faced | -0.0019 / 0.999 / 1.005 | +0.0041 / 0.996 / 1.035 | -0.0012 / 1.002 / 1.014 |
| movement | batters faced | +0.0007 / 1.016 / 0.998 | +0.0051 / 0.999 / 1.010 | -0.0019 / 0.995 / 1.018 |
| stamina | appearances | -0.0099 † / 1.006 / 0.998 | -0.0029 / 1.000 / 0.998 | +0.0111 † / 0.997 / 0.994 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.953 | 1.035 |
| gap | 0.971 | 1.014 |
| power | 0.924 | 1.202 |
| eye | 1.010 | 1.056 |
| avoid_k | 0.970 | 1.140 |
| stuff | 0.997 | 1.226 |
| control | 0.998 | 1.069 |
| movement | 1.006 | 1.159 |

## True rating distributions (mean of 20 seasons)

Everyday players: regulars for batting ratings, weekend starters for pitching ratings. A P4 everyday player should average above 50 and a low-tier one below.

| Rating | D1 weighted mean | D1 weighted SD | P4 everyday | Mid everyday | Low everyday | Status |
|---|---|---|---|---|---|---|
| contact | 49.6 | 9.9 | 57.9 | 51.3 | 46.0 | pass |
| gap | 49.6 | 9.9 | 55.8 | 50.7 | 46.4 | pass |
| power | 49.6 | 9.8 | 57.4 | 49.5 | 44.0 | pass |
| eye | 49.9 | 9.9 | 55.1 | 49.9 | 45.8 | pass |
| avoid_k | 49.7 | 10.0 | 56.4 | 51.0 | 46.4 | pass |
| stuff | 50.3 | 9.6 | 58.6 | 51.3 | 45.7 | pass |
| control | 50.9 | 9.6 | 58.3 | 53.4 | 49.9 | pass |
| movement | 50.2 | 9.4 | 52.2 | 49.2 | 47.0 | pass |
| stamina | 51.7 | 10.0 | 50.0 | 49.9 | 50.0 | — |

## Example player cards (first simulated season)

| Player | Team (tier) | Role | Ratings | Season |
|---|---|---|---|---|
| Best P4 hitter (OPS, qualified): G. Cleawell | Nythaberg Bluejays (p4) | regular | Contact 43, Gap 80, Power 77, Eye 65, Avoid K 63, Speed 53 | 56 G, 255 PA, 0.338/0.434/0.850, 27 HR, 13.3% BB, 12.9% K |
| Median mid-major regular: BR. Brair | Mim Comets (mid) | regular | Contact 44, Gap 45, Power 51, Eye 51, Avoid K 53, Speed 63 | 52 G, 217 PA, 0.271/0.381/0.442, 7 HR, 12.9% BB, 18.9% K |
| Median low-tier regular: L. Zyshison | Tryn Mustangs (low) | regular | Contact 52, Gap 54, Power 57, Eye 58, Avoid K 59, Speed 37 | 55 G, 267 PA, 0.251/0.368/0.447, 8 HR, 12.7% BB, 17.6% K |
| Home-run leader: N. Troujeal | Shaberg Rams (mid) | regular | Contact 67, Gap 58, Power 80, Eye 48, Avoid K 56, Speed 51 | 56 G, 285 PA, 0.411/0.472/0.859, 31 HR, 9.5% BB, 18.2% K |
| Highest true Contact, qualified: H. Weawood | Briberg Comets (p4) | regular | Contact 80, Gap 57, Power 74, Eye 60, Avoid K 59, Speed 64 | 56 G, 285 PA, 0.397/0.493/0.730, 19 HR, 15.4% BB, 21.4% K |
| Bench player with most PA: V. Noult | Neagear Cardinals (mid) | bench | Contact 39, Gap 48, Power 47, Eye 51, Avoid K 51, Speed 41 | 42 G, 144 PA, 0.186/0.317/0.246, 1 HR, 9.7% BB, 16.7% K |
| Best P4 weekend starter (ERA, qualified): F. Wefofield | Vywood Stags (p4) | sp_weekend | Stuff 73, Control 64, Movement 67, Stamina 48 | 14 G, 14 GS, 81.1 IP, 1.44 ERA, 12.6 K/9, 2.4 BB/9, 0.2 HR/9 |
| Median mid-major weekend starter: TR. Tusofield | Claiweafield Hornets (mid) | sp_weekend | Stuff 42, Control 44, Movement 54, Stamina 61 | 16 G, 14 GS, 72.0 IP, 5.38 ERA, 5.4 K/9, 4.0 BB/9, 1.4 HR/9 |
| Low-tier reliever with most innings: D. Saishun | Trix Rapids (low) | rp | Stuff 34, Control 42, Movement 59, Stamina 76 | 23 G, 0 GS, 62.0 IP, 9.87 ERA, 7.3 K/9, 5.7 BB/9, 1.2 HR/9 |
| Starter with the highest true Stamina: ST. Theatem | Zytheawell Miners (low) | sp_weekend | Stuff 54, Control 70, Movement 46, Stamina 79 | 14 G, 10 GS, 70.2 IP, 4.97 ERA, 10.2 K/9, 2.3 BB/9, 1.3 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2314 | 1.046 ± 0.051 | 0.03 ± 0.19 | 7.23 / 6.96 | 1.039 ± 0.043 | 0.38 |
| gap | 2155 | 1.062 ± 0.056 | -0.41 ± 0.08 | 7.79 / 7.49 | 1.040 ± 0.037 | 0.38 |
| power | 2461 | 1.060 ± 0.030 | 0.12 ± 0.13 | 6.23 / 5.26 | 1.184 ± 0.026 | 0.59 |
| eye | 2461 | 0.967 ± 0.022 | 0.12 ± 0.07 | 5.84 / 5.82 | 1.003 ± 0.024 | 0.66 |
| avoid_k | 2461 | 1.004 ± 0.009 | 0.01 ± 0.04 | 4.57 / 4.33 | 1.054 ± 0.017 | 0.78 |
| stuff | 1831 | 0.975 ± 0.014 | 0.31 ± 0.06 | 3.97 / 3.67 | 1.083 ± 0.022 | 0.85 |
| control | 1831 | 0.968 ± 0.015 | 0.46 ± 0.10 | 4.97 / 4.87 | 1.021 ± 0.016 | 0.72 |
| movement | 1831 | 0.787 ± 0.041 | 0.93 ± 0.11 | 7.89 / 8.41 | 0.938 ± 0.019 | 0.45 |
| stamina | 4215 | 1.002 ± 0.007 | 0.02 ± 0.08 | 4.59 / 4.59 | 0.999 ± 0.013 | 0.79 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

