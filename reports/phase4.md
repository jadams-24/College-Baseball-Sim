# Phase 4 realism report: 20–80 ratings

40 simulated seasons, seeds 20251000–20251039, players generated from ratings. Generated 2026-10-08.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **PASS**

Phase 1 and Phase 2 gate rows on the same run: **pass** (reports/phase2.md).

## Round trip, forward: true rates → 40 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 20 folds of 2 seasons. Tolerance is 3.45 SE across folds (Student t, 19 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2152 | +0.0002 ± 0.0027 | +0.01 | pass | 1.000 ± 0.016 | pass | 0.991 ± 0.020 | pass |
| gap | XBH share of hits | 1991 | +0.0023 ± 0.0044 | +0.09 | pass | 1.002 ± 0.015 | pass | 1.000 ± 0.016 | pass |
| power | HR/PA | 2325 | -0.0006 ± 0.0042 | -0.01 | pass | 1.000 ± 0.009 | pass | 1.003 ± 0.019 | pass |
| eye | BB/PA | 2325 | +0.0005 ± 0.0027 | +0.02 | pass | 1.002 ± 0.010 | pass | 1.003 ± 0.015 | pass |
| avoid_k | K/PA | 2325 | -0.0005 ± 0.0018 | -0.01 | pass | 1.002 ± 0.005 | pass | 1.003 ± 0.018 | pass |
| stuff | K/BF | 1620 | -0.0018 ± 0.0019 | -0.04 | pass | 0.999 ± 0.006 | pass | 0.997 ± 0.019 | pass |
| control | BB/BF | 1620 | +0.0008 ± 0.0032 | +0.02 | pass | 0.998 ± 0.010 | pass | 0.994 ± 0.020 | pass |
| movement | HR/BF | 1620 | -0.0012 ± 0.0047 | -0.04 | pass | 0.994 ± 0.020 | pass | 1.002 ± 0.019 | pass |
| stamina | pull hazard (log leash) | 4077 | +0.0007 ± 0.0021 | — | pass | 1.000 ± 0.004 | pass | 1.001 ± 0.014 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0025 / 1.001 / 1.003 | -0.0009 / 0.996 / 0.991 | +0.0030 / 0.990 / 0.982 |
| gap | plate appearances | +0.0003 / 0.984 / 1.007 | +0.0007 / 1.006 / 0.995 | +0.0051 / 1.007 / 1.000 |
| power | plate appearances | -0.0019 / 1.002 / 1.000 | -0.0005 / 1.000 / 0.993 | -0.0001 / 0.997 / 1.012 |
| eye | plate appearances | -0.0014 / 1.000 / 1.003 | +0.0011 / 1.007 / 1.003 | +0.0014 / 1.000 / 1.002 |
| avoid_k | plate appearances | +0.0022 / 1.002 / 1.009 | -0.0013 / 1.000 / 1.011 | -0.0017 / 1.003 / 0.992 |
| stuff | batters faced | -0.0051 † / 0.999 / 0.987 | -0.0022 / 1.003 / 1.008 | +0.0002 / 0.996 / 0.994 |
| control | batters faced | +0.0039 / 0.996 / 1.004 | +0.0043 / 0.995 / 1.002 | -0.0038 / 0.996 / 0.982 |
| movement | batters faced | -0.0030 / 1.006 / 1.013 | +0.0039 / 0.980 / 1.004 | -0.0039 / 0.991 / 0.996 |
| stamina | appearances | -0.0078 † / 1.005 / 1.011 | -0.0057 † / 1.003 / 1.000 | +0.0093 † / 0.993 † / 0.997 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.936 | 1.036 |
| gap | 0.975 | 1.024 |
| power | 0.919 | 1.200 |
| eye | 1.029 | 1.284 |
| avoid_k | 0.984 | 1.193 |
| stuff | 1.009 | 1.255 |
| control | 1.003 | 1.046 |
| movement | 0.996 | 1.153 |

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
| stamina | 51.6 | 10.0 | 49.9 | 49.9 | 50.0 | — |

## Example player cards (first simulated season)

| Player | Team (tier) | Role | Ratings | Season |
|---|---|---|---|---|
| Best P4 hitter (OPS, qualified): H. Weawood | Briberg Comets (p4) | regular | Contact 80, Gap 56, Power 74, Eye 60, Avoid K 58, Speed 64 | 52 G, 255 PA, 0.437/0.518/0.869, 25 HR, 14.9% BB, 18.0% K |
| Median mid-major regular: J. Pizul | Shaford Pioneers (mid) | regular | Contact 53, Gap 55, Power 58, Eye 54, Avoid K 45, Speed 45 | 48 G, 219 PA, 0.259/0.363/0.454, 9 HR, 11.9% BB, 26.0% K |
| Median low-tier regular: H. Lacing | Stax Falcons (low) | regular | Contact 40, Gap 64, Power 56, Eye 51, Avoid K 30, Speed 57 | 41 G, 128 PA, 0.241/0.359/0.444, 5 HR, 12.5% BB, 24.2% K |
| Home-run leader: G. Vealey | Saiberg Lynx (mid) | regular | Contact 60, Gap 75, Power 70, Eye 55, Avoid K 50, Speed 72 | 54 G, 256 PA, 0.446/0.551/0.960, 30 HR, 14.1% BB, 10.9% K |
| Highest true Contact, qualified: H. Weawood | Briberg Comets (p4) | regular | Contact 80, Gap 56, Power 74, Eye 60, Avoid K 58, Speed 64 | 52 G, 255 PA, 0.437/0.518/0.869, 25 HR, 14.9% BB, 18.0% K |
| Bench player with most PA: ST. Pason | Seatriley Clippers (p4) | bench | Contact 47, Gap 48, Power 54, Eye 60, Avoid K 50, Speed 26 | 37 G, 133 PA, 0.220/0.388/0.320, 3 HR, 15.8% BB, 21.8% K |
| Best P4 weekend starter (ERA, qualified): TR. Lealt | Jestyr Mariners (p4) | sp_weekend | Stuff 59, Control 63, Movement 61, Stamina 34 | 14 G, 11 GS, 56.0 IP, 1.61 ERA, 8.4 K/9, 1.8 BB/9, 0.3 HR/9 |
| Median mid-major weekend starter: V. Sougewell | Shouck Sentinels (mid) | sp_weekend | Stuff 51, Control 55, Movement 47, Stamina 40 | 13 G, 13 GS, 57.1 IP, 5.18 ERA, 7.7 K/9, 3.0 BB/9, 0.9 HR/9 |
| Low-tier reliever with most innings: W. Goberg | Vogeawood Falcons (low) | rp | Stuff 50, Control 34, Movement 66, Stamina 75 | 19 G, 1 GS, 66.0 IP, 5.05 ERA, 10.5 K/9, 7.1 BB/9, 0.7 HR/9 |
| Starter with the highest true Stamina: ST. Theatem | Zytheawell Miners (low) | sp_weekend | Stuff 54, Control 70, Movement 46, Stamina 79 | 13 G, 11 GS, 85.1 IP, 3.80 ERA, 8.6 K/9, 2.1 BB/9, 0.8 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2152 | 1.070 ± 0.045 | 0.17 ± 0.08 | 7.28 / 6.92 | 1.052 ± 0.024 | 0.35 |
| gap | 1991 | 1.034 ± 0.035 | -0.41 ± 0.08 | 7.83 / 7.59 | 1.033 ± 0.018 | 0.38 |
| power | 2324 | 1.055 ± 0.020 | 0.30 ± 0.06 | 6.29 / 5.33 | 1.181 ± 0.017 | 0.58 |
| eye | 2324 | 0.848 ± 0.009 | 0.15 ± 0.03 | 6.32 / 6.11 | 1.034 ± 0.009 | 0.69 |
| avoid_k | 2324 | 0.974 ± 0.008 | 0.00 ± 0.02 | 4.70 / 4.43 | 1.059 ± 0.010 | 0.79 |
| stuff | 1620 | 0.959 ± 0.010 | 0.30 ± 0.03 | 4.00 / 3.69 | 1.084 ± 0.016 | 0.87 |
| control | 1620 | 0.964 ± 0.010 | 0.37 ± 0.06 | 5.03 / 4.87 | 1.033 ± 0.014 | 0.71 |
| movement | 1620 | 0.769 ± 0.023 | 1.01 ± 0.09 | 7.89 / 8.44 | 0.934 ± 0.013 | 0.44 |
| stamina | 4076 | 1.001 ± 0.006 | 0.02 ± 0.04 | 4.68 / 4.67 | 1.001 ± 0.008 | 0.78 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

