# Phase 4 realism report: 20–80 ratings

20 simulated seasons, seeds 20251000–20251019, players generated from ratings. Generated 2026-10-03.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **FAIL**

Phase 1 and Phase 2 gate rows on the same run: **FAIL** (reports/phase2.md).

## Round trip, forward: true rates → 20 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 10 folds of 2 seasons. Tolerance is 4.09 SE across folds (Student t, 9 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2303 | +0.0010 ± 0.0027 | +0.08 | pass | 0.991 ± 0.022 | pass | 0.998 ± 0.021 | pass |
| gap | XBH share of hits | 2153 | +0.0009 ± 0.0062 | +0.04 | pass | 1.006 ± 0.033 | pass | 1.007 ± 0.024 | pass |
| power | HR/PA | 2452 | +0.0012 ± 0.0048 | +0.02 | pass | 1.001 ± 0.012 | pass | 1.011 ± 0.042 | pass |
| eye | BB/PA | 2452 | -0.0008 ± 0.0032 | -0.03 | pass | 0.999 ± 0.016 | pass | 0.998 ± 0.029 | pass |
| avoid_k | K/PA | 2452 | +0.0007 ± 0.0028 | +0.02 | pass | 1.001 ± 0.005 | pass | 1.023 ± 0.032 | pass |
| stuff | K/BF | 1814 | -0.0008 ± 0.0036 | -0.02 | pass | 1.002 ± 0.008 | pass | 0.997 ± 0.028 | pass |
| control | BB/BF | 1814 | -0.0010 ± 0.0040 | -0.03 | pass | 1.000 ± 0.017 | pass | 1.003 ± 0.018 | pass |
| movement | HR/BF | 1814 | -0.0015 ± 0.0038 | -0.05 | pass | 0.998 ± 0.026 | pass | 0.981 ± 0.022 | pass |
| stamina | pull hazard (log leash) | 4222 | -0.0010 ± 0.0019 | — | pass | 1.002 ± 0.003 | pass | 0.998 ± 0.018 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0014 / 1.010 / 0.987 | -0.0005 / 0.975 † / 1.008 | +0.0040 / 0.972 / 0.996 |
| gap | plate appearances | +0.0017 / 1.003 / 1.000 | +0.0026 / 1.012 / 1.009 | -0.0009 / 1.008 / 1.010 |
| power | plate appearances | -0.0002 / 0.999 / 0.995 | +0.0007 / 1.008 / 1.014 | +0.0020 / 0.995 / 1.016 |
| eye | plate appearances | -0.0020 / 1.001 / 0.976 | -0.0033 / 0.992 / 0.987 | +0.0018 / 1.002 / 1.020 |
| avoid_k | plate appearances | +0.0037 / 0.999 / 1.027 | +0.0004 / 0.997 / 1.019 | -0.0014 / 1.004 / 1.022 |
| stuff | batters faced | -0.0007 / 0.999 / 0.993 | -0.0032 / 1.008 / 1.000 | +0.0008 / 0.998 / 0.997 |
| control | batters faced | +0.0001 / 1.008 / 1.014 | +0.0047 / 0.997 / 0.997 | -0.0063 / 0.992 / 1.001 |
| movement | batters faced | -0.0035 / 0.981 / 0.974 | +0.0016 / 1.011 / 0.989 | -0.0026 / 1.002 / 0.978 |
| stamina | appearances | -0.0130 † / 0.999 / 1.010 | -0.0074 † / 1.001 / 0.994 | +0.0079 † / 1.001 / 0.995 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.946 | 1.039 |
| gap | 0.978 | 1.029 |
| power | 0.925 | 1.232 |
| eye | 1.012 | 1.066 |
| avoid_k | 0.975 | 1.164 |
| stuff | 0.999 | 1.213 |
| control | 1.000 | 1.055 |
| movement | 1.004 | 1.130 |

## True rating distributions (mean of 20 seasons)

Everyday players: regulars for batting ratings, weekend starters for pitching ratings. A P4 everyday player should average above 50 and a low-tier one below.

| Rating | D1 weighted mean | D1 weighted SD | P4 everyday | Mid everyday | Low everyday | Status |
|---|---|---|---|---|---|---|
| contact | 49.6 | 9.8 | 57.7 | 51.3 | 46.1 | pass |
| gap | 49.6 | 9.8 | 55.6 | 50.7 | 46.4 | pass |
| power | 49.5 | 9.7 | 57.1 | 49.5 | 44.1 | pass |
| eye | 49.9 | 9.9 | 54.9 | 49.9 | 45.9 | pass |
| avoid_k | 49.7 | 10.0 | 56.2 | 51.0 | 46.5 | pass |
| stuff | 50.1 | 9.8 | 58.9 | 51.2 | 45.2 | pass |
| control | 50.8 | 9.7 | 58.5 | 53.4 | 49.6 | pass |
| movement | 50.2 | 9.4 | 52.4 | 49.1 | 46.8 | pass |
| stamina | 51.7 | 10.0 | 50.0 | 49.9 | 50.0 | — |

## Example player cards (first simulated season)

| Player | Team (tier) | Role | Ratings | Season |
|---|---|---|---|---|
| Best P4 hitter (OPS, qualified): D. Clan | Traijeax Owls (p4) | regular | Contact 66, Gap 64, Power 68, Eye 45, Avoid K 58, Speed 32 | 51 G, 246 PA, 0.408/0.473/0.808, 21 HR, 10.2% BB, 19.5% K |
| Median mid-major regular: TH. Hedeans | Meashur Lynx (mid) | regular | Contact 55, Gap 48, Power 48, Eye 41, Avoid K 48, Speed 57 | 48 G, 189 PA, 0.307/0.376/0.452, 4 HR, 8.5% BB, 14.3% K |
| Median low-tier regular: S. Rur | Hean Hawks (low) | regular | Contact 42, Gap 37, Power 26, Eye 45, Avoid K 62, Speed 59 | 46 G, 188 PA, 0.321/0.414/0.404, 0 HR, 12.8% BB, 6.9% K |
| Home-run leader: CL. Rail | Zet Lynx (mid) | regular | Contact 58, Gap 59, Power 63, Eye 47, Avoid K 51, Speed 58 | 54 G, 267 PA, 0.339/0.432/0.763, 25 HR, 11.6% BB, 13.9% K |
| Highest true Contact, qualified: H. Weawood | Briberg Comets (p4) | regular | Contact 80, Gap 56, Power 74, Eye 60, Avoid K 58, Speed 64 | 56 G, 273 PA, 0.343/0.421/0.589, 15 HR, 12.1% BB, 19.0% K |
| Bench player with most PA: Z. Clis | Claiford Cardinals (mid) | bench | Contact 39, Gap 44, Power 47, Eye 39, Avoid K 43, Speed 53 | 42 G, 143 PA, 0.227/0.294/0.297, 2 HR, 7.7% BB, 26.6% K |
| Best P4 weekend starter (ERA, qualified): W. Stobraley | Kamut Clippers (p4) | sp_weekend | Stuff 80, Control 58, Movement 64, Stamina 62 | 15 G, 13 GS, 76.1 IP, 1.41 ERA, 16.0 K/9, 1.8 BB/9, 0.4 HR/9 |
| Median mid-major weekend starter: C. Cuford | Tryshelt Hornets (mid) | sp_weekend | Stuff 46, Control 58, Movement 59, Stamina 51 | 16 G, 13 GS, 70.2 IP, 5.48 ERA, 5.3 K/9, 3.9 BB/9, 1.1 HR/9 |
| Low-tier reliever with most innings: TH. Kaiberg | Rurel Quakers (low) | rp | Stuff 55, Control 57, Movement 51, Stamina 60 | 23 G, 0 GS, 65.1 IP, 4.13 ERA, 8.4 K/9, 2.8 BB/9, 0.1 HR/9 |
| Starter with the highest true Stamina: ST. Theatem | Zytheawell Miners (low) | sp_weekend | Stuff 54, Control 70, Movement 46, Stamina 79 | 13 G, 11 GS, 78.0 IP, 3.23 ERA, 9.0 K/9, 2.7 BB/9, 0.7 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2302 | 1.048 ± 0.050 | 0.07 ± 0.10 | 7.22 / 7.02 | 1.030 ± 0.021 | 0.37 |
| gap | 2153 | 1.029 ± 0.049 | -0.48 ± 0.18 | 7.78 / 7.57 | 1.028 ± 0.037 | 0.39 |
| power | 2452 | 1.047 ± 0.023 | 0.12 ± 0.11 | 6.23 / 5.27 | 1.181 ± 0.022 | 0.59 |
| eye | 2452 | 0.961 ± 0.035 | 0.13 ± 0.07 | 5.84 / 5.85 | 1.000 ± 0.016 | 0.66 |
| avoid_k | 2452 | 0.994 ± 0.009 | 0.02 ± 0.03 | 4.59 / 4.35 | 1.055 ± 0.010 | 0.78 |
| stuff | 1814 | 0.975 ± 0.015 | 0.28 ± 0.08 | 3.97 / 3.69 | 1.078 ± 0.031 | 0.86 |
| control | 1814 | 0.974 ± 0.017 | 0.44 ± 0.10 | 4.95 / 4.87 | 1.016 ± 0.023 | 0.72 |
| movement | 1814 | 0.789 ± 0.043 | 0.90 ± 0.07 | 7.89 / 8.42 | 0.937 ± 0.017 | 0.45 |
| stamina | 4221 | 0.998 ± 0.005 | -0.03 ± 0.07 | 4.59 / 4.61 | 0.997 ± 0.009 | 0.79 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

