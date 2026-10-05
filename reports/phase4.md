# Phase 4 realism report: 20–80 ratings

40 simulated seasons, seeds 20251000–20251039, players generated from ratings. Generated 2026-10-05.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **FAIL**

Phase 1 and Phase 2 gate rows on the same run: **FAIL** (reports/phase2.md).

## Round trip, forward: true rates → 40 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 20 folds of 2 seasons. Tolerance is 3.45 SE across folds (Student t, 19 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2156 | +0.0007 ± 0.0019 | +0.05 | pass | 1.001 ± 0.020 | pass | 0.998 ± 0.017 | pass |
| gap | XBH share of hits | 1989 | +0.0002 ± 0.0032 | +0.01 | pass | 1.005 ± 0.014 | pass | 0.999 ± 0.016 | pass |
| power | HR/PA | 2329 | +0.0017 ± 0.0055 | +0.03 | pass | 0.998 ± 0.011 | pass | 1.007 ± 0.023 | pass |
| eye | BB/PA | 2329 | -0.0003 ± 0.0026 | -0.01 | pass | 1.000 ± 0.009 | pass | 0.994 ± 0.018 | pass |
| avoid_k | K/PA | 2329 | +0.0001 ± 0.0030 | +0.00 | pass | 1.000 ± 0.007 | pass | 0.998 ± 0.018 | pass |
| stuff | K/BF | 1621 | -0.0010 ± 0.0036 | -0.02 | pass | 0.998 ± 0.005 | pass | 1.000 ± 0.019 | pass |
| control | BB/BF | 1621 | -0.0008 ± 0.0026 | -0.02 | pass | 1.002 ± 0.009 | pass | 1.006 ± 0.020 | pass |
| movement | HR/BF | 1621 | -0.0018 ± 0.0064 | -0.06 | pass | 1.005 ± 0.013 | pass | 0.993 ± 0.021 | pass |
| stamina | pull hazard (log leash) | 4073 | +0.0008 ± 0.0025 | — | pass | 1.000 ± 0.004 | pass | 0.993 ± 0.011 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0012 / 0.990 / 1.003 | -0.0014 / 1.005 / 1.003 | +0.0039 † / 0.993 / 0.990 |
| gap | plate appearances | +0.0007 / 1.015 / 1.001 | +0.0015 / 0.995 / 1.003 | -0.0013 / 1.009 / 0.993 |
| power | plate appearances | -0.0025 / 0.998 / 1.006 | +0.0014 / 1.000 / 1.009 | +0.0039 / 0.993 / 1.007 |
| eye | plate appearances | -0.0009 / 0.995 / 0.985 | -0.0011 / 1.002 / 0.991 | +0.0008 / 1.002 / 1.002 |
| avoid_k | plate appearances | +0.0010 / 1.003 / 1.008 | +0.0004 / 1.002 / 0.989 | -0.0007 / 0.993 / 0.999 |
| stuff | batters faced | -0.0019 / 0.999 / 0.991 | -0.0007 / 0.997 / 1.026 | -0.0007 / 0.998 / 0.986 |
| control | batters faced | +0.0026 / 1.004 / 0.982 | +0.0023 / 0.996 / 1.024 | -0.0055 † / 0.999 / 1.005 |
| movement | batters faced | -0.0024 / 1.000 / 0.989 | +0.0063 / 1.004 / 0.998 | -0.0074 / 1.008 / 0.991 |
| stamina | appearances | -0.0061 † / 1.003 / 1.011 | -0.0057 † / 1.001 / 0.995 | +0.0086 † / 0.997 / 0.985 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.944 | 1.039 |
| gap | 0.979 | 1.021 |
| power | 0.923 | 1.204 |
| eye | 1.009 | 1.059 |
| avoid_k | 0.974 | 1.125 |
| stuff | 0.998 | 1.194 |
| control | 1.002 | 1.059 |
| movement | 1.009 | 1.133 |

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
| control | 50.9 | 9.6 | 58.4 | 53.4 | 49.8 | pass |
| movement | 50.2 | 9.4 | 52.4 | 49.1 | 46.9 | pass |
| stamina | 51.7 | 10.0 | 49.9 | 49.9 | 50.0 | — |

## Example player cards (first simulated season)

| Player | Team (tier) | Role | Ratings | Season |
|---|---|---|---|---|
| Best P4 hitter (OPS, qualified): N. Zousaiwell | Wason Lynx (p4) | regular | Contact 47, Gap 77, Power 66, Eye 57, Avoid K 43, Speed 62 | 50 G, 224 PA, 0.339/0.460/0.811, 21 HR, 12.1% BB, 21.4% K |
| Median mid-major regular: S. Nuveaford | Caigoufield Kestrels (mid) | regular | Contact 52, Gap 49, Power 58, Eye 32, Avoid K 58, Speed 54 | 50 G, 230 PA, 0.273/0.361/0.464, 9 HR, 4.8% BB, 14.8% K |
| Median low-tier regular: T. Sokans | Stuzux Sailors (low) | regular | Contact 55, Gap 38, Power 51, Eye 43, Avoid K 36, Speed 24 | 51 G, 234 PA, 0.280/0.372/0.455, 8 HR, 9.8% BB, 17.9% K |
| Home-run leader: S. Gyr | Stoukouberg Coyotes (p4) | regular | Contact 64, Gap 64, Power 70, Eye 55, Avoid K 49, Speed 32 | 51 G, 247 PA, 0.376/0.415/0.823, 27 HR, 6.1% BB, 28.3% K |
| Highest true Contact, qualified: H. Weawood | Briberg Comets (p4) | regular | Contact 80, Gap 56, Power 74, Eye 60, Avoid K 58, Speed 64 | 52 G, 257 PA, 0.356/0.439/0.671, 17 HR, 12.8% BB, 19.5% K |
| Bench player with most PA: F. Train | Wouton Cardinals (mid) | bench | Contact 35, Gap 41, Power 41, Eye 26, Avoid K 42, Speed 68 | 36 G, 129 PA, 0.306/0.380/0.389, 1 HR, 7.0% BB, 18.6% K |
| Best P4 weekend starter (ERA, qualified): P. Reans | Nythaberg Bluejays (p4) | sp_weekend | Stuff 80, Control 59, Movement 55, Stamina 60 | 13 G, 12 GS, 70.2 IP, 1.40 ERA, 16.8 K/9, 2.8 BB/9, 0.4 HR/9 |
| Median mid-major weekend starter: V. Vung | Steason Mustangs (mid) | sp_weekend | Stuff 56, Control 60, Movement 51, Stamina 38 | 14 G, 14 GS, 57.0 IP, 5.21 ERA, 7.9 K/9, 3.0 BB/9, 1.1 HR/9 |
| Low-tier reliever with most innings: Z. Grus | Louton Kestrels (low) | rp | Stuff 45, Control 47, Movement 60, Stamina 57 | 30 G, 1 GS, 62.2 IP, 3.30 ERA, 9.3 K/9, 3.4 BB/9, 0.1 HR/9 |
| Starter with the highest true Stamina: ST. Theatem | Zytheawell Miners (low) | sp_weekend | Stuff 54, Control 70, Movement 46, Stamina 79 | 10 G, 9 GS, 57.0 IP, 6.00 ERA, 7.9 K/9, 2.2 BB/9, 1.6 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2155 | 1.054 ± 0.050 | 0.13 ± 0.08 | 7.27 / 7.01 | 1.038 ± 0.030 | 0.36 |
| gap | 1989 | 1.043 ± 0.034 | -0.45 ± 0.07 | 7.81 / 7.55 | 1.034 ± 0.022 | 0.38 |
| power | 2329 | 1.046 ± 0.026 | 0.26 ± 0.08 | 6.26 / 5.32 | 1.176 ± 0.016 | 0.59 |
| eye | 2329 | 0.962 ± 0.011 | 0.16 ± 0.04 | 5.92 / 5.92 | 1.000 ± 0.011 | 0.65 |
| avoid_k | 2329 | 1.002 ± 0.009 | 0.03 ± 0.02 | 4.60 / 4.41 | 1.044 ± 0.011 | 0.77 |
| stuff | 1620 | 0.977 ± 0.006 | 0.30 ± 0.04 | 3.94 / 3.68 | 1.071 ± 0.017 | 0.86 |
| control | 1620 | 0.968 ± 0.011 | 0.46 ± 0.04 | 4.97 / 4.88 | 1.018 ± 0.008 | 0.72 |
| movement | 1620 | 0.780 ± 0.021 | 0.92 ± 0.09 | 7.78 / 8.37 | 0.929 ± 0.013 | 0.44 |
| stamina | 4073 | 1.002 ± 0.006 | 0.01 ± 0.06 | 4.66 / 4.66 | 0.999 ± 0.008 | 0.78 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

