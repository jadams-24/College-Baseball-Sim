# Phase 4 realism report: 20–80 ratings

40 simulated seasons, seeds 20251000–20251039, players generated from ratings. Generated 2026-10-09.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **FAIL**

Phase 1 and Phase 2 gate rows on the same run: **pass** (reports/phase2.md).

## Round trip, forward: true rates → 40 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 20 folds of 2 seasons. Tolerance is 3.45 SE across folds (Student t, 19 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2152 | -0.0001 ± 0.0027 | -0.01 | pass | 1.003 ± 0.015 | pass | 0.989 ± 0.021 | pass |
| gap | XBH share of hits | 1994 | +0.0022 ± 0.0042 | +0.09 | pass | 0.993 ± 0.015 | pass | 1.010 ± 0.018 | pass |
| power | HR/PA | 2329 | +0.0008 ± 0.0038 | +0.01 | pass | 1.001 ± 0.010 | pass | 0.996 ± 0.022 | pass |
| eye | BB/PA | 2329 | +0.0003 ± 0.0025 | +0.01 | pass | 1.002 ± 0.009 | pass | 0.996 ± 0.020 | pass |
| avoid_k | K/PA | 2329 | -0.0001 ± 0.0020 | -0.00 | pass | 1.001 ± 0.006 | pass | 0.992 ± 0.018 | pass |
| stuff | K/BF | 1642 | +0.0007 ± 0.0019 | +0.02 | pass | 0.999 ± 0.005 | pass | 0.998 ± 0.022 | pass |
| control | BB/BF | 1642 | -0.0003 ± 0.0034 | -0.01 | pass | 0.998 ± 0.009 | pass | 0.983 ± 0.022 | pass |
| movement | HR/BF | 1642 | -0.0076 ± 0.0044 | -0.24 | FAIL | 0.994 ± 0.020 | pass | 0.990 ± 0.019 | pass |
| stamina | pull hazard (log leash) | 4121 | +0.0035 ± 0.0031 | — | FAIL | 0.998 ± 0.004 | pass | 0.993 ± 0.010 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0013 / 1.008 / 0.990 | -0.0007 / 0.988 / 0.989 | +0.0013 / 1.005 / 0.988 |
| gap | plate appearances | +0.0002 / 0.983 / 1.003 | +0.0014 / 0.988 / 1.018 | +0.0042 / 0.999 / 1.009 |
| power | plate appearances | +0.0018 / 1.001 / 0.999 | -0.0035 / 0.999 / 0.996 | +0.0032 / 1.001 / 0.994 |
| eye | plate appearances | +0.0007 / 1.001 / 1.003 | -0.0004 / 1.004 / 1.003 | +0.0008 / 1.001 / 0.986 |
| avoid_k | plate appearances | +0.0017 / 1.004 / 0.999 | +0.0001 / 0.999 / 1.001 | -0.0016 / 1.000 / 0.979 |
| stuff | batters faced | +0.0010 / 0.997 / 0.996 | -0.0001 / 1.003 / 0.994 | +0.0011 / 0.997 / 1.002 |
| control | batters faced | -0.0014 / 0.996 / 0.987 | +0.0055 / 0.994 / 0.987 | -0.0043 / 0.998 / 0.978 |
| movement | batters faced | -0.0155 † / 0.995 / 0.978 | -0.0034 / 0.994 / 0.992 | -0.0063 / 0.994 / 0.995 |
| stamina | appearances | -0.0143 † / 1.003 / 1.003 | -0.0060 † / 0.998 / 0.980 † | +0.0154 † / 0.992 † / 0.998 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.938 | 1.033 |
| gap | 0.969 | 1.033 |
| power | 0.922 | 1.196 |
| eye | 1.030 | 1.275 |
| avoid_k | 0.983 | 1.181 |
| stuff | 1.006 | 1.256 |
| control | 1.000 | 1.033 |
| movement | 1.002 | 1.139 |

## True rating distributions (mean of 40 seasons)

Everyday players: regulars for batting ratings, weekend starters for pitching ratings. A P4 everyday player should average above 50 and a low-tier one below.

| Rating | D1 weighted mean | D1 weighted SD | P4 everyday | Mid everyday | Low everyday | Status |
|---|---|---|---|---|---|---|
| contact | 49.6 | 9.7 | 57.4 | 51.3 | 46.3 | pass |
| gap | 49.6 | 9.8 | 55.6 | 50.7 | 46.8 | pass |
| power | 49.5 | 9.6 | 56.9 | 49.5 | 44.3 | pass |
| eye | 49.9 | 9.8 | 54.7 | 49.9 | 46.0 | pass |
| avoid_k | 49.8 | 9.9 | 56.2 | 51.0 | 46.7 | pass |
| stuff | 50.4 | 9.8 | 58.9 | 51.2 | 45.5 | pass |
| control | 51.0 | 9.7 | 58.5 | 53.4 | 49.8 | pass |
| movement | 50.3 | 9.4 | 52.4 | 49.1 | 46.9 | pass |
| stamina | 51.5 | 9.9 | 49.9 | 49.9 | 50.0 | — |

## Example player cards (first simulated season)

| Player | Team (tier) | Role | Ratings | Season |
|---|---|---|---|---|
| Best P4 hitter (OPS, qualified): ST. Pewell | Nythaberg Bluejays (p4) | regular | Contact 63, Gap 80, Power 77, Eye 54, Avoid K 65, Speed 53 | 51 G, 255 PA, 0.377/0.451/0.809, 23 HR, 11.8% BB, 13.7% K |
| Median mid-major regular: J. Thas | Ceford Ospreys (mid) | regular | Contact 54, Gap 56, Power 59, Eye 63, Avoid K 45, Speed 59 | 48 G, 209 PA, 0.228/0.411/0.411, 7 HR, 16.3% BB, 23.4% K |
| Median low-tier regular: C. Clourd | Nawell Thunder (low) | regular | Contact 41, Gap 48, Power 43, Eye 33, Avoid K 50, Speed 47 | 33 G, 109 PA, 0.275/0.380/0.440, 4 HR, 12.8% BB, 10.1% K |
| Home-run leader: G. Vealey | Saiberg Lynx (mid) | regular | Contact 60, Gap 75, Power 70, Eye 55, Avoid K 50, Speed 72 | 54 G, 258 PA, 0.440/0.523/0.977, 31 HR, 12.0% BB, 14.0% K |
| Highest true Contact, qualified: H. Weawood | Briberg Comets (p4) | regular | Contact 80, Gap 56, Power 73, Eye 60, Avoid K 58, Speed 64 | 52 G, 253 PA, 0.364/0.462/0.775, 22 HR, 15.0% BB, 19.8% K |
| Bench player with most PA: TR. Wydeam | Brygreack Comets (p4) | bench | Contact 46, Gap 48, Power 55, Eye 41, Avoid K 51, Speed 65 | 39 G, 135 PA, 0.228/0.459/0.315, 2 HR, 6.7% BB, 28.9% K |
| Best P4 weekend starter (ERA, qualified): N. Stouvuwell | Nythaberg Bluejays (p4) | sp_weekend | Stuff 62, Control 66, Movement 51, Stamina 47 | 13 G, 10 GS, 62.1 IP, 1.59 ERA, 9.7 K/9, 1.2 BB/9, 0.4 HR/9 |
| Median mid-major weekend starter: Z. Wing | Fouziberg Bobcats (mid) | sp_weekend | Stuff 50, Control 55, Movement 57, Stamina 55 | 17 G, 14 GS, 82.1 IP, 5.36 ERA, 6.8 K/9, 3.6 BB/9, 0.7 HR/9 |
| Low-tier reliever with most innings: N. Teton | Zusyt Lancers (low) | rp | Stuff 38, Control 46, Movement 46, Stamina 62 | 32 G, 1 GS, 66.2 IP, 4.72 ERA, 6.1 K/9, 4.2 BB/9, 0.7 HR/9 |
| Starter with the highest true Stamina: ST. Theatem | Zytheawell Miners (low) | sp_weekend | Stuff 54, Control 70, Movement 46, Stamina 79 | 15 G, 11 GS, 84.2 IP, 6.06 ERA, 10.0 K/9, 2.9 BB/9, 1.3 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2152 | 1.074 ± 0.046 | 0.18 ± 0.07 | 7.23 / 6.89 | 1.051 ± 0.025 | 0.34 |
| gap | 1993 | 1.030 ± 0.036 | -0.44 ± 0.07 | 7.84 / 7.55 | 1.039 ± 0.019 | 0.37 |
| power | 2328 | 1.055 ± 0.016 | 0.32 ± 0.04 | 6.24 / 5.29 | 1.179 ± 0.015 | 0.58 |
| eye | 2328 | 0.849 ± 0.011 | 0.17 ± 0.03 | 6.29 / 6.09 | 1.032 ± 0.009 | 0.69 |
| avoid_k | 2328 | 0.977 ± 0.008 | 0.01 ± 0.03 | 4.67 / 4.43 | 1.055 ± 0.010 | 0.78 |
| stuff | 1641 | 0.964 ± 0.009 | 0.32 ± 0.05 | 4.01 / 3.69 | 1.086 ± 0.014 | 0.86 |
| control | 1641 | 0.968 ± 0.008 | 0.43 ± 0.06 | 5.04 / 4.90 | 1.029 ± 0.016 | 0.71 |
| movement | 1641 | 0.781 ± 0.019 | 1.03 ± 0.12 | 7.89 / 8.38 | 0.942 ± 0.020 | 0.44 |
| stamina | 4121 | 1.003 ± 0.006 | 0.01 ± 0.06 | 4.69 / 4.70 | 0.998 ± 0.007 | 0.78 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

