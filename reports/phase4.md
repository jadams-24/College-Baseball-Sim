# Phase 4 realism report: 20–80 ratings

40 simulated seasons, seeds 20251000–20251039, players generated from ratings. Generated 2026-10-06.
Ratings re-express the true rates the engine uses, on percentiles of each rate's D1 distribution (PA- or BF-weighted, all of D1 on one scale): 50 is the D1 median, 60/70/80 the 84.1st/97.7th/99.87th percentiles; for a Gaussian rate this is 10 points per true-talent SD. Batters: Contact (BABIP), Gap (extra-base share of hits), Power (HR/PA), Eye (BB/PA), Avoid K (K/PA). Pitchers: Stuff (K/BF), Control (BB/BF), Movement (HR/BF), Stamina (individual leash on the pull hazard). Speed is reserved for Phase 6: the engine has no speed-linked rate yet.

## Gate: **PASS**

Phase 1 and Phase 2 gate rows on the same run: **pass** (reports/phase2.md).

## Round trip, forward: true rates → 40 seasons → observed rates

For each rated rate, every qualifying player-season's opponent-adjusted observed rate is regressed on the player's true rate, on the logit scale. The opponent-adjusted observed offset is o = z + (x − E) / V. Here z is the true offset, and x the count. E and V are the sums of p and of p(1 − p) over the player's own trials, at his true rates against the opponents he actually faced (recorded by the engine). The regression is weighted by V. The intercept is the average of o − z at the group's own mean talent; the table shows it in logit units and in rating points. Dispersion is Σ(x − E)² / ΣV: 1 when the noise around the true rate is exactly the binomial noise of those trials. Stamina: each pull decision's probability is 1 − (1 − h)^θ, with the manager's own baseline hazard h and log θ = a + b·(true log leash), fitted by maximum likelihood. Its dispersion is the same ratio on pull counts. Qualifying: config.phase4.MIN_TRIALS (150 PA or BF, 100 balls in play for Contact, 35 hits for Gap, 8 appearances for Stamina). Statistics are means over 20 folds of 2 seasons. Tolerance is 3.45 SE across folds (Student t, 19 df, the coverage of 3 SE).

| Rating | Rate | Player-seasons per season | Intercept (logit) | Intercept (rating pts) | Status | Slope | Status | Dispersion | Status |
|---|---|---|---|---|---|---|---|---|---|
| contact | BABIP | 2148 | -0.0002 ± 0.0026 | -0.01 | pass | 0.999 ± 0.016 | pass | 0.998 ± 0.013 | pass |
| gap | XBH share of hits | 1988 | -0.0004 ± 0.0036 | -0.02 | pass | 0.992 ± 0.014 | pass | 0.992 ± 0.016 | pass |
| power | HR/PA | 2324 | -0.0018 ± 0.0042 | -0.03 | pass | 1.000 ± 0.009 | pass | 0.996 ± 0.015 | pass |
| eye | BB/PA | 2324 | -0.0001 ± 0.0021 | -0.00 | pass | 1.003 ± 0.009 | pass | 1.000 ± 0.012 | pass |
| avoid_k | K/PA | 2324 | -0.0009 ± 0.0024 | -0.02 | pass | 0.999 ± 0.005 | pass | 1.000 ± 0.016 | pass |
| stuff | K/BF | 1619 | -0.0018 ± 0.0029 | -0.04 | pass | 1.000 ± 0.004 | pass | 1.005 ± 0.018 | pass |
| control | BB/BF | 1619 | +0.0001 ± 0.0026 | +0.00 | pass | 0.995 ± 0.009 | pass | 0.993 ± 0.021 | pass |
| movement | HR/BF | 1619 | -0.0026 ± 0.0060 | -0.08 | pass | 1.002 ± 0.022 | pass | 1.003 ± 0.018 | pass |
| stamina | pull hazard (log leash) | 4072 | -0.0001 ± 0.0023 | — | pass | 1.000 ± 0.004 | pass | 0.998 ± 0.011 | pass |

### By workload tercile (informational)

Qualifying player-seasons split into thirds by workload. Each cell: intercept (logit) / slope / dispersion; † marks a value outside the same tolerance. The manager orders players by true talent only. Lineup rank, rotation slot and bullpen rank are set once per season from the true offsets (engine/league.py: batting order by expected OBP + SLG against a league-average pitcher; pitchers by K − BB − HR). Start shares, reliever choice and weekend rotation patterns follow that order (engine/manager.py), and no in-season statistic feeds any choice. So a player's workload depends on his true talent, not his results, and a forward regression on true talent is not biased by it. The one outcome-dependent usage rule is the in-game pull hazard (outing pitch count and runs), so a pitcher's batters faced carry part of his outings' luck; Stamina is therefore split by appearances, since its batters faced are partly the pulls themselves. Plate appearances also follow results within a season, though not through the manager: a hitter whose balls in play fall for hits keeps innings going, his team bats more and he comes up more often. The heaviest third is therefore slightly selected on good luck, most for Contact, the rate that most moves lineup turnover.

| Rating | Workload | Light | Middle | Heavy |
|---|---|---|---|---|
| contact | plate appearances | -0.0025 / 1.009 / 1.006 | -0.0006 / 0.990 / 1.006 | +0.0019 / 0.986 / 0.986 |
| gap | plate appearances | -0.0029 / 0.982 / 0.998 | +0.0002 / 1.004 / 1.003 | +0.0008 / 0.983 / 0.980 † |
| power | plate appearances | -0.0008 / 1.001 / 0.982 | -0.0035 / 0.997 / 0.990 | -0.0011 / 1.003 / 1.008 |
| eye | plate appearances | -0.0015 / 1.003 / 0.998 | -0.0019 / 1.001 / 1.000 | +0.0022 / 1.003 / 1.000 |
| avoid_k | plate appearances | +0.0003 / 1.003 / 1.003 | -0.0008 / 0.993 / 1.006 | -0.0018 / 1.002 / 0.993 |
| stuff | batters faced | -0.0051 † / 0.996 / 1.007 | -0.0018 / 1.003 / 1.017 | -0.0001 / 1.000 / 0.996 |
| control | batters faced | +0.0041 / 0.994 / 0.992 | +0.0015 / 0.991 / 1.000 | -0.0036 † / 0.992 / 0.988 |
| movement | batters faced | -0.0052 / 0.992 / 1.004 | -0.0017 / 1.007 / 1.015 | -0.0018 / 1.008 / 0.993 |
| stamina | appearances | -0.0085 † / 1.000 / 1.010 | -0.0077 † / 1.002 / 0.998 | +0.0095 † / 0.996 / 0.994 |

Box-score version (informational): the same regression with opponents adjusted only from the league's team-by-team results. A box score shows which team a player faced, not which pitcher (or hitter): an ace or a midweek starter. That adds variance the team-level baseline cannot attribute, so its dispersion runs above 1.

| Rating | Slope | Dispersion |
|---|---|---|
| contact | 0.945 | 1.038 |
| gap | 0.968 | 1.017 |
| power | 0.927 | 1.188 |
| eye | 1.013 | 1.060 |
| avoid_k | 0.974 | 1.125 |
| stuff | 1.000 | 1.196 |
| control | 0.996 | 1.047 |
| movement | 1.006 | 1.153 |

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
| Best P4 hitter (OPS, qualified): J. Jusheson | Stoukouberg Coyotes (p4) | regular | Contact 62, Gap 64, Power 74, Eye 69, Avoid K 51, Speed 50 | 41 G, 195 PA, 0.381/0.490/0.863, 21 HR, 15.4% BB, 21.0% K |
| Median mid-major regular: V. Veatyton | Cit Cardinals (mid) | regular | Contact 41, Gap 69, Power 55, Eye 56, Avoid K 66, Speed 65 | 43 G, 197 PA, 0.278/0.387/0.438, 4 HR, 13.7% BB, 10.2% K |
| Median low-tier regular: Z. Geathir | Relt Ironmen (low) | regular | Contact 46, Gap 35, Power 40, Eye 58, Avoid K 50, Speed 56 | 49 G, 174 PA, 0.270/0.413/0.401, 4 HR, 12.6% BB, 19.5% K |
| Home-run leader: N. Troujeal | Shaberg Rams (mid) | regular | Contact 67, Gap 58, Power 79, Eye 48, Avoid K 56, Speed 51 | 52 G, 250 PA, 0.376/0.449/0.826, 27 HR, 10.0% BB, 16.4% K |
| Highest true Contact, qualified: H. Weawood | Briberg Comets (p4) | regular | Contact 80, Gap 56, Power 74, Eye 60, Avoid K 58, Speed 64 | 52 G, 253 PA, 0.372/0.450/0.619, 12 HR, 11.9% BB, 18.2% K |
| Bench player with most PA: Z. Woson | Wicot Gulls (p4) | bench | Contact 45, Gap 50, Power 49, Eye 69, Avoid K 56, Speed 53 | 40 G, 136 PA, 0.273/0.444/0.424, 2 HR, 18.4% BB, 18.4% K |
| Best P4 weekend starter (ERA, qualified): SH. Reamofield | Zacit Mustangs (p4) | sp_weekend | Stuff 64, Control 44, Movement 56, Stamina 61 | 13 G, 8 GS, 52.1 IP, 1.55 ERA, 11.5 K/9, 4.0 BB/9, 0.3 HR/9 |
| Median mid-major weekend starter: SH. Showell | Dousaton Bison (mid) | sp_weekend | Stuff 48, Control 56, Movement 54, Stamina 49 | 14 G, 14 GS, 72.1 IP, 5.35 ERA, 7.5 K/9, 3.4 BB/9, 1.1 HR/9 |
| Low-tier reliever with most innings: D. Saishun | Trix Rapids (low) | rp | Stuff 34, Control 42, Movement 60, Stamina 76 | 22 G, 0 GS, 69.2 IP, 11.76 ERA, 6.5 K/9, 5.4 BB/9, 1.3 HR/9 |
| Starter with the highest true Stamina: ST. Theatem | Zytheawell Miners (low) | sp_weekend | Stuff 54, Control 70, Movement 46, Stamina 79 | 14 G, 11 GS, 90.0 IP, 3.80 ERA, 9.7 K/9, 2.0 BB/9, 0.9 HR/9 |

## Future scouting estimator (Phase 9, informational; not gated)

Recruiting (Phase 9) will show coaches noisy ratings, estimated from what they can see. This is the candidate estimator. It is empirical Bayes from box-score information only: counting stats, each player's opponents (team, home or away) and the league's team-by-team results. It uses an opponent-mixture binomial likelihood and a normal prior per role × tier, fitted by marginal maximum likelihood, in the same folds (engine/eb.py, engine/report4.py). Slope regresses the true rating on the estimate; bias is true − estimated; the SD ratio is the residual SD over the posterior SD the estimator predicts.

| Rating | Players per season | Slope | Bias | Resid SD / predicted | SD ratio | Reliability |
|---|---|---|---|---|---|---|
| contact | 2147 | 1.043 ± 0.035 | 0.13 ± 0.11 | 7.25 / 6.99 | 1.037 ± 0.021 | 0.36 |
| gap | 1988 | 1.055 ± 0.045 | -0.46 ± 0.09 | 7.85 / 7.49 | 1.048 ± 0.023 | 0.37 |
| power | 2323 | 1.049 ± 0.013 | 0.24 ± 0.06 | 6.24 / 5.32 | 1.173 ± 0.014 | 0.59 |
| eye | 2323 | 0.956 ± 0.013 | 0.17 ± 0.04 | 5.92 / 5.93 | 0.998 ± 0.007 | 0.65 |
| avoid_k | 2323 | 1.000 ± 0.007 | 0.02 ± 0.03 | 4.61 / 4.41 | 1.044 ± 0.010 | 0.77 |
| stuff | 1619 | 0.974 ± 0.007 | 0.30 ± 0.04 | 3.95 / 3.68 | 1.074 ± 0.016 | 0.86 |
| control | 1619 | 0.977 ± 0.012 | 0.44 ± 0.05 | 4.97 / 4.87 | 1.022 ± 0.015 | 0.71 |
| movement | 1619 | 0.763 ± 0.018 | 0.98 ± 0.11 | 7.87 / 8.44 | 0.932 ± 0.020 | 0.45 |
| stamina | 4072 | 0.999 ± 0.008 | 0.00 ± 0.05 | 4.67 / 4.66 | 1.001 ± 0.006 | 0.78 |

Workload selection: the estimator's prior ignores that playing time depends on talent. Managers start, bat high and work their best players most, so within a role group true rating and workload correlate (+.10 to +.28 for pitchers, +.50 for regulars' Power). A prior per role × tier pulls a team's busiest players toward too low a mean and its least-used toward too high a one. On players with at least half a regular's workload, the pitcher ratings are estimated slightly low: a third of a point for Movement, where shrinkage is strongest (reliability .39). Within a role, bias rises with workload (Movement for weekend starters −1.2 / +.2 / +1.3 by workload tercile; Power for regulars −2.9 / −.7 / +1.6). Weighted by trials over all players it is .00. Two variants were tried (PHASE0_NOTES.md, Phase 4): a prior mean linear in log trials (fixes the pitchers, but Power's relation is convex) and a prior per workload rank on the team (fixes the means, but given a rank one rating is not normal, so the spread is misstated). For Phase 9 that bias may be the right behaviour: coaches see stats and playing time, not true talent. Revisit it there.

