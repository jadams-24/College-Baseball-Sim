# Phase 4 realism report: 20–80 ratings

20 simulated seasons, seeds 20251000–20251019, players generated from ratings. Generated 2026-10-02.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **PASS**

Phase 1 and Phase 2 gate rows on the same run: **pass** (reports/phase2.md).

## Round trip, forward: true rates → 20 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 10 folds of 2 seasons. Tolerance is 4.09 SE across folds (Student t, 9 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2315 | +0.0004 ± 0.0031 | +0.03 | pass | 1.007 ± 0.026 | pass | 1.002 ± 0.022 | pass |
| gap | XBH share of hits | 2156 | +0.0007 ± 0.0082 | +0.03 | pass | 0.999 ± 0.007 | pass | 1.003 ± 0.027 | pass |
| power | HR/PA | 2450 | -0.0010 ± 0.0075 | -0.01 | pass | 1.004 ± 0.014 | pass | 1.008 ± 0.032 | pass |
| eye | BB/PA | 2450 | +0.0010 ± 0.0041 | +0.03 | pass | 1.002 ± 0.016 | pass | 1.001 ± 0.027 | pass |
| avoid_k | K/PA | 2450 | -0.0000 ± 0.0023 | -0.00 | pass | 1.000 ± 0.008 | pass | 1.000 ± 0.032 | pass |
| stuff | K/BF | 2258 | -0.0002 ± 0.0041 | -0.01 | pass | 1.001 ± 0.008 | pass | 0.992 ± 0.015 | pass |
| control | BB/BF | 2258 | +0.0020 ± 0.0045 | +0.05 | pass | 1.002 ± 0.011 | pass | 1.012 ± 0.022 | pass |
| movement | HR/BF | 2258 | -0.0062 ± 0.0072 | -0.20 | pass | 0.993 ± 0.020 | pass | 0.995 ± 0.034 | pass |
| stamina | pull hazard (log leash) | 3878 | +0.0001 ± 0.0026 | — | pass | 1.001 ± 0.009 | pass | 0.994 ± 0.033 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0029 / 1.019 / 1.004 | -0.0030 / 0.993 / 0.994 | +0.0056 † / 0.979 / 1.007 |
| gap | plate appearances | +0.0038 / 1.005 / 1.007 | -0.0024 / 0.984 / 0.995 | +0.0012 / 1.009 / 1.007 |
| power | plate appearances | -0.0045 / 1.008 / 0.990 | +0.0005 / 1.004 / 1.015 | -0.0007 / 1.001 / 1.010 |
| eye | plate appearances | +0.0018 / 0.990 / 0.988 | -0.0023 / 1.002 / 0.994 | +0.0032 / 1.010 / 1.014 |
| avoid_k | plate appearances | +0.0022 / 1.002 / 0.993 | -0.0021 / 1.001 / 0.998 | +0.0003 / 0.996 / 1.007 |
| stuff | batters faced | +0.0008 / 1.006 / 1.008 | +0.0007 / 0.997 / 0.994 | -0.0015 / 1.001 / 0.983 |
| control | batters faced | +0.0022 / 0.990 / 1.016 | +0.0045 / 1.000 / 1.011 | -0.0002 / 1.009 / 1.010 |
| movement | batters faced | -0.0026 / 0.986 / 0.989 | -0.0074 / 1.006 / 0.992 | -0.0073 / 0.986 / 1.001 |
| stamina | appearances | -0.0019 / 0.997 / 1.008 | -0.0009 / 1.002 / 0.990 | +0.0014 / 1.001 / 0.991 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 1.000 | 1.010 |
| gap | 0.998 | 1.013 |
| power | 1.002 | 1.028 |
| eye | 1.015 | 1.028 |
| avoid_k | 0.993 | 1.028 |
| stuff | 0.993 | 1.043 |
| control | 1.001 | 1.029 |
| movement | 0.998 | 1.008 |

## True rating distributions (mean of 20 seasons)

Everyday players: regulars for batting ratings, weekend starters for pitching ratings. A P4 everyday player should average above 50 and a low-tier one below.

| Rating | D1 weighted mean | D1 weighted SD | P4 everyday | Mid everyday | Low everyday | Status |
|---|---|---|---|---|---|---|
| contact | 50.1 | 9.9 | 57.3 | 51.4 | 46.2 | pass |
| gap | 50.1 | 9.9 | 55.7 | 50.8 | 46.6 | pass |
| power | 50.2 | 10.0 | 57.2 | 49.7 | 44.4 | pass |
| eye | 50.2 | 9.9 | 54.8 | 50.0 | 46.0 | pass |
| avoid_k | 50.2 | 10.0 | 56.4 | 51.1 | 46.8 | pass |
| stuff | 49.8 | 10.0 | 59.8 | 51.1 | 44.5 | pass |
| control | 49.9 | 10.1 | 59.3 | 53.5 | 49.1 | pass |
| movement | 50.0 | 10.0 | 53.0 | 49.4 | 46.1 | pass |
| stamina | 52.0 | 10.0 | 50.4 | 49.9 | 50.2 | — |

## Example player cards (first simulated season)

| Player | Team (tier) | Role | Ratings | Season |
|---|---|---|---|---|
| Best P4 hitter (OPS, qualified): D. Gon | Joufaiwood Miners (p4) | regular | Contact 63, Gap 64, Power 65, Eye 64, Avoid K 69, Speed — | 55 G, 266 PA, 0.389/0.515/0.808, 22 HR, 13.5% BB, 12.0% K |
| Median mid-major regular: SH. Braim | Faiberg Monarchs (mid) | regular | Contact 47, Gap 53, Power 52, Eye 38, Avoid K 48, Speed — | 52 G, 228 PA, 0.277/0.345/0.475, 7 HR, 6.1% BB, 20.6% K |
| Median low-tier regular: GR. Duton | Brouwood Coyotes (low) | regular | Contact 47, Gap 64, Power 56, Eye 38, Avoid K 41, Speed — | 55 G, 261 PA, 0.285/0.354/0.430, 5 HR, 6.1% BB, 18.8% K |
| Home-run leader: GR. Mour | Heanaison Bluejays (p4) | regular | Contact 67, Gap 80, Power 74, Eye 40, Avoid K 56, Speed — | 56 G, 287 PA, 0.378/0.434/0.815, 28 HR, 5.6% BB, 16.4% K |
| Highest true Contact, qualified: K. Zuns | Huthoux Cardinals (p4) | regular | Contact 80, Gap 57, Power 77, Eye 52, Avoid K 39, Speed — | 55 G, 273 PA, 0.304/0.353/0.577, 18 HR, 5.5% BB, 33.3% K |
| Bench player with most PA: R. Thilins | Staweafield Ospreys (low) | bench | Contact 41, Gap 44, Power 45, Eye 63, Avoid K 60, Speed — | 31 G, 143 PA, 0.255/0.426/0.377, 2 HR, 22.4% BB, 10.5% K |
| Best P4 weekend starter (ERA, qualified): L. Dewell | Cealex Ospreys (p4) | sp_weekend | Stuff 70, Control 72, Movement 46, Stamina 53 | 12 G, 12 GS, 71.1 IP, 2.27 ERA, 11.0 K/9, 1.6 BB/9, 0.6 HR/9 |
| Median mid-major weekend starter: H. Zeberg | Gakouton Monarchs (mid) | sp_weekend | Stuff 65, Control 61, Movement 36, Stamina 47 | 14 G, 14 GS, 71.0 IP, 4.94 ERA, 12.0 K/9, 1.6 BB/9, 1.8 HR/9 |
| Low-tier reliever with most innings: K. Claishuns | Keley Kestrels (low) | rp | Stuff 38, Control 43, Movement 37, Stamina 73 | 48 G, 1 GS, 109.2 IP, 12.39 ERA, 6.0 K/9, 5.8 BB/9, 1.4 HR/9 |
| Starter with the highest true Stamina: S. Zaisaiton | Kuton Sailors (low) | sp_weekend | Stuff 40, Control 44, Movement 37, Stamina 78 | 8 G, 8 GS, 45.0 IP, 5.60 ERA, 7.0 K/9, 3.4 BB/9, 0.8 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2314 | 1.004 ± 0.036 | 0.12 ± 0.12 | 7.14 / 7.05 | 1.013 ± 0.032 | 0.40 |
| gap | 2155 | 1.005 ± 0.038 | -0.22 ± 0.13 | 7.72 / 7.52 | 1.027 ± 0.024 | 0.41 |
| power | 2450 | 1.038 ± 0.016 | 0.42 ± 0.13 | 5.83 / 5.20 | 1.123 ± 0.031 | 0.64 |
| eye | 2450 | 0.978 ± 0.023 | 0.09 ± 0.07 | 5.74 / 5.78 | 0.993 ± 0.021 | 0.66 |
| avoid_k | 2450 | 1.009 ± 0.013 | 0.01 ± 0.02 | 4.32 / 4.30 | 1.007 ± 0.016 | 0.80 |
| stuff | 2257 | 1.004 ± 0.011 | 0.11 ± 0.09 | 3.76 / 3.71 | 1.013 ± 0.026 | 0.86 |
| control | 2257 | 0.988 ± 0.015 | 0.27 ± 0.06 | 4.94 / 4.90 | 1.009 ± 0.008 | 0.76 |
| movement | 2257 | 0.942 ± 0.035 | 0.35 ± 0.07 | 7.88 / 8.13 | 0.969 ± 0.022 | 0.39 |
| stamina | 3878 | 1.000 ± 0.011 | 0.00 ± 0.05 | 4.26 / 4.26 | 1.001 ± 0.014 | 0.82 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

