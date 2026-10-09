# Diagnosis sizes: "offense extremes compressed" (real data only)

2026-10-06. Measurement only, no fixes (owner: "Report sizes only; no fixes yet"). Script: `scripts/diag_sizes.py`; machine-readable output: `reports/diagnosis_sizes.json`. Context: `plans/combined_report_2026-10-06.md`, section 1 (step 1 and candidates 10, 11, 12). Sim values are copied from the 40-season reports of 2026-10-05 (`reports/phase2.md`, `phase6.md`, `phase7.md`); nothing was simulated. SEs are bootstrap (400 reps over teams or starters, 200 over games) or binomial where stated.

## Summary

Benchmark definitions (item 1), in row units:

| Row | Benchmark now | Recomputed | SE | Sim | Share of the sim gap closed |
|---|---|---|---|---|---|
| Run-rule frequency, product estimator, D1-vs-D1 only | 0.1524 | 0.1509 | 0.0051 | 0.1201 | 5% |
| Run-rule frequency, direct count, WarrenNolan D1-vs-D1 finals matched to the scoreboard | 0.1524 | 0.1440 | 0.0040 | 0.1201 | 26% (see caveat: the engine reads the same conditional) |
| Runs per team-game, 15+ bin, D1-vs-D1 only | 0.0664 | 0.0650 | 0.0020 | 0.0533 | 11% |
| Qualified OBP p10, play-by-play without non-D1 games | 0.3366 | 0.3354 | 0.0035 | 0.3242 | 10% |
| Team R/G SD (all) | 1.162 | 1.158 (New Orleans restored) | 0.047 | 1.032 | already D1-vs-D1; 3% |

Game-level variance (items 3 and 4), on the dispersion scale: real 2.6185 against sim 2.224, missing 0.3945 (about 2.68 runs² per team-game, or 0.058 in log runs).

| Candidate | Real size (Δφ) | SE | Share of the missing .3945 | Running total | 95% upper bound of the share |
|---|---|---|---|---|---|
| 11. Starter day-to-day form (starters with 5+ starts) | -0.032 | 0.055 | -8% | -8% | 19% |
| 12. Errors clustering in half-innings | +0.012 | 0.010 | +3% | -5% | 8% |
| Total of 11 and 12 | -0.020 | 0.056 | -5% | | 23% |

These are real-data sizes of each mechanism, so they are upper bounds on what each could add to the sim: the sim's own values of the same measures are not measured here (they come later, on the new engine). Neither candidate is detectably different from zero.

Round 2 (2026-10-07, `scripts/diag_tto_mopup.py`): candidates 3 (times through the order) and 4 (mop-up pitching) and the updated running total are in the section "Round 2" at the end.

Round 3 (2026-10-09, `scripts/diag_round3.py`): the same estimators on the final engine's own play-by-play, so real minus engine is what a fix could add; plate-appearance length by base state and platoon lineups added. `reports/diagnosis_sizes_round3.md`.

Context from item 3: in the real play-by-play, the covariance between different half-innings of one team-game is worth 0.42 ± 0.05 dispersion units. Two of the starter's innings covary about as much as one of his innings and a bullpen inning of the same game, so it is a game-level part (G = 0.078 ± 0.021 in log variance), not starter-specific. Its sim counterpart is the first thing to measure on the new engine.

Candidate 10 (fielding independent of pitching), in its own units:

| Measure | Real | SE | Engine or sim |
|---|---|---|---|
| ERA vs errors per game, observed correlation (NCAA.com, 299 teams) | 0.655 | 0.043 | sim 0.727 |
| Same, true (noise-removed) correlation | 0.801 | 0.044 | not measured |
| Same, the real true correlation observed with the sim's run noise (counterfactual) | 0.661 to 0.673 | | sim 0.727 |
| Team error log-odds left after run prevention d, true SD (all corrections) | 0.113 | 0.011 | engine 0.136 |
| Slope of error log-odds on d (all corrections) | -0.762 | 0.040 | engine -0.720 |
| Unearned share of runs, 50 best teams by ERA / all teams | 0.134 / 0.130 | 0.004 / 0.002 | sim 0.099 / 0.117 (1 − earned shares .901 / .883, means of team shares) |

Of the .072 gap in the ERA-errors correlation, noise attenuation can account for 0.006 to 0.018 (8% to 25%). The real independent fielding variance is not larger than the engine's; it is somewhat smaller.

## 1. Non-D1 opponents

### (a) How many scoreboard games involve a non-D1 opponent

- Method: a side is D1 if its scoreboard name is one of the 307 teams in `data/ncaa_2025/pbp/teams_2025.csv`, with New Orleans added (that file names it "LSU New Orleans"; the scoreboard calls it "New Orleans"). This is the same split as the conference-tag rule in `scripts/build_run_histogram.py`: the two agree on every one of the 16,158 sides.
- Result: **90 of 8,079 games** involve a non-D1 opponent (84 with the non-D1 team listed away, 6 home), 1.1%. D1-vs-D1: 7,989.
- The plan's "about 141" was 141 games: the 90 above plus 51 D1-vs-D1 games of New Orleans, which the team-strength fit drops because of the name mismatch (`scripts/build_phase2_teams.py` `load()` and `build_phase2_gate.py` `team_strength()` filter on the names in teams_2025.csv). That is why `team_strength_2025` has 306 teams and 7,938 games. Reported, not changed.
- WarrenNolan cross-check: 78 of the 90 games are on the D1 team's WarrenNolan page on the same date, and WarrenNolan flags the opponent non-D1 in all 78. The other 12 are not on WarrenNolan (it omits some non-D1 games, as `data/README.md` notes for 2026). WarrenNolan has 86 final games against non-D1 opponents; none of its non-D1 opponents is a 2025 D1 team.
- Those games are lopsided: margin of 10+ in 0.478 of them (all games .195), the D1 side scores 12.21 runs on average, 15+ in 0.322 of them, and wins 0.900.

### (b) Run-rule frequency and the 15+ bin on D1-vs-D1 games

- Run rule, the benchmark's product estimator P(margin ≥ 10, scoreboard) × P(ended before the 9th | margin ≥ 10, WMT), SE by the delta method as in `scripts/write_phase2_benchmarks.py`:
  - as committed (reproduced): 0.1952 × 0.7805 = **0.1523** ± 0.0051 (8,079 scoreboard games; 451 WMT 10-run games of 2,273);
  - D1-vs-D1 only (both factors; the WMT factor also loses 15 games: 14 against non-D1 teams and one 2024 game in the 2025 file): 0.1920 × 0.7857 = **0.1509** ± 0.0051. Closes 4.6% of the gap to the sim (.1524 − .1201 = .0323).
- A direct count is possible on a sample almost four times larger: WarrenNolan records innings for every final (blank = 9). On the 2,248 games it shares with the WMT schedules, its innings equal WMT's in every game. Direct D1-vs-D1 run-rule rate (game ended before the 9th with a margin of 10+, scheduled 7-inning games included as in the benchmark):
  - all 8,418 WarrenNolan D1-vs-D1 finals: **0.1412** ± 0.0038 (P(margin ≥ 10) 0.1908, P(ended early | margin ≥ 10) 0.7403 on 1,606 games);
  - the 7,890 of them matched to the scoreboard's D1-vs-D1 finals: **0.1440** ± 0.0040;
  - the 716 conference-tournament games (WarrenNolan event label; most are placeholders without scores in the scoreboard): 0.0782.
- Why the direct count is lower: P(ended early | margin ≥ 10) is 0.785 on the 441 WarrenNolan 10-run games that are in the WMT schedules and 0.724 on the other 1,165 (difference 0.061 ± 0.024, about 2.6 SE). It is higher in the WMT games in every tier pair with more than a handful of WMT games, so it is not only tier mix:

  | Tier pair | WarrenNolan n | P(early) | WMT n | P(early) |
  |---|---|---|---|---|
  | low–low | 319 | 0.734 | 4 | 0.250 |
  | low–mid | 223 | 0.771 | 19 | 0.895 |
  | low–p4 | 100 | 0.740 | 70 | 0.771 |
  | mid–mid | 544 | 0.728 | 69 | 0.754 |
  | mid–p4 | 232 | 0.746 | 145 | 0.807 |
  | p4–p4 | 188 | 0.745 | 141 | 0.787 |

  WMT holds every game of its client programs, so the WMT factor describes those programs' games (their conferences' and opponents' run-rule agreements), not D1 as a whole. The data cannot say which agreements differ; candidate 1 (run rules by conference) is the place to look.
- **Caveat that limits what a benchmark change buys:** the engine plays the rule with probability `p_run_rule_in_effect` = the same WMT conditional (0.7805; `config/phase1.py` reads it from this benchmark entry). If the benchmark's conditional moves to WarrenNolan's .740, the engine's input moves with it and the sim's run-rule rate falls in proportion. What is left is the margin distribution: P(final margin ≥ 10) is 0.1920 real (D1-vs-D1) against about 0.154 implied for the sim (.1201 / .7805; approximate, since the sim's rule acts after the 7th). Non-D1 games close 8% of that margin gap.
- 15+ runs bin, P(15+) per D1 team-game, game-cluster SE: committed 0.0664 ± 0.0020 (16,068 team-games, reproduced exactly); D1-vs-D1 **0.0650** ± 0.0020 (15,978 team-games). Closes 11% of the gap (.0664 − .0533). The 90 D1 sides against non-D1 opponents score 15+ at 0.322.

### (c) Qualified OBP p10

- How it is built (`scripts/build_phase2_gate.py` `qualified()`): qualified batters (2.0 PA per team game, 75% of team games) on the WMT teams with 40+ parsed games, plus 11 Sidearm full-season pages, each tier weighted by its share of D1 teams, tiers under 50 qualified players pooled with the nearest; tolerance 3 SE from a team-cluster bootstrap. The WMT part counts every parsed game, including games against non-D1 opponents.
- Non-D1 games in the parsed play-by-play: 7 (Hawaii 4: Chaminade twice, Hawaii Hilo, Hawaii Pacific; Iowa 2: Loras, Augustana; Nevada 1: Simpson). Removed from the games, plate appearances, base-running events and charged runs, and from the team-game counts used by the qualification rule.
- Result (same code, same bootstrap seed; the committed value reproduces exactly): **0.3366 → 0.3354** (3 SE 0.0104); unpooled 0.3363 → 0.3358; 461 qualified batters either way. Closes 10% of the gap to the sim (0.3242).
- Not removable: the 11 Sidearm pages are season totals. By the scoreboard, those teams played 5 non-D1 games in all (Troy 2, Missouri State, Cal Poly, SFA 1 each).

### (d) Team R/G SD

- Confirmed D1-vs-D1 only: `team_strength()` in `scripts/build_phase2_gate.py` keeps a team-game only when both teams are in teams_2025.csv. Reproduced: 1.1615 (benchmark 1.162, 306 teams). Non-D1 games cannot move this row.
- The name mismatch drops New Orleans (51 D1 games, 6.86 R/G). With it restored: 1.1581 on 307 teams. SE of the SD about .047 (1.162 / √(2 × 305)).

## 2. Fielding independent of pitching (candidate 10)

### (a) Reliability of team ERA and errors per game, and the true correlation

- **Split halves, WMT box lines.** 50 teams with 30+ D1-vs-D1 box-score games (57.8 on average; these are WMT's full-season programs, mostly P4). Games in date order, odd against even. Reliability of the full season by Spearman-Brown; true correlation from cross-half correlations (ERA of one half with errors of the other), which removes the within-game link between errors and runs:

  | | Half-season reliability | Full-season reliability | Observed corr with E/G | True corr with E/G |
  |---|---|---|---|---|
  | ERA | 0.766 ± 0.054 | 0.867 ± 0.035 | 0.579 ± 0.105 | 0.709 ± 0.121 |
  | Runs allowed per game | 0.805 ± 0.049 | 0.892 ± 0.031 | 0.673 ± 0.089 | 0.767 ± 0.097 |
  | Errors per game | 0.635 ± 0.094 | 0.777 ± 0.077 | | |

- **All of D1 (NCAA.com 2025 pages, 299 teams).** Split halves are not available there, so the noise variance of each team's season statistic is computed from its own games, runs and errors with per-game dispersions measured within team on the WMT box lines (108 teams, 3,784 team-games): earned runs φ = 3.04, runs allowed φ = 2.79, errors φ = 1.12 (variance / mean per game); within-game correlation of errors with earned runs 0.096, with runs allowed 0.273. Noise variance, noise covariance and true variance follow; true correlation = (observed covariance − noise covariance) / √(true variances).

  | | Reliability of the stat | Reliability of E/G | Observed corr | True corr |
  |---|---|---|---|---|
  | ERA | 0.851 ± 0.015 | 0.740 ± 0.025 | 0.655 ± 0.043 | 0.801 ± 0.044 |
  | Runs allowed per game | 0.862 ± 0.014 | 0.740 | 0.721 ± 0.036 | 0.839 ± 0.037 |

  Check of the noise model on the 50 split-half teams: it gives reliabilities 0.833 (ERA) and 0.697 (E/G) against split-half 0.867 and 0.777, and a true correlation of 0.732 against 0.709. They agree within SE. SEs on the NCAA.com rows are a bootstrap over teams with the noise parameters fixed.
- The NCAA.com observed .655 reproduces. Its true correlation is about 0.80; the 50 WMT teams' 0.71 is lower because they cover a narrower range of team quality.
- **How much of the sim's .727 can be noise attenuation.** The sim's game-to-game run variance is lower (dispersion 2.224 against 2.6185). Holding the real true spreads and true correlation fixed and shrinking the run noise of ERA by 2.224 / 2.6185 gives an observed correlation of 0.661; shrinking the error noise by the same ratio as well gives 0.673. That is 0.006 to 0.018 of the .072 gap. For runs allowed per game: 0.725 to 0.736 against real .721 and sim .801. So at most about a quarter of the gap is the sim's lower noise. The rest has to be a tighter true relation in the sim, or wider true team spreads (the sim has more elite run-prevention teams). The sim's own split-half reliabilities would settle which; they are not measured here.

### (b) True variance of the team error rate left after run prevention

- Model as in `scripts/build_phase6_fielding.py` `team_error()`: y = logit(E / (PO + A + E)) − logit(league rate), weighted by chances, on d from the scoreboard fit with parks. Run on the NCAA.com pages (every team, full seasons), with three corrections applied in turn:

  | Step | Slope on d | Residual true SD |
  |---|---|---|
  | Binomial noise only (the PHASE0_NOTES refit; reproduces −.685 / .127) | -0.685 ± 0.033 | 0.127 ± 0.010 |
  | + errors overdispersed against binomial-by-chances (φ = 1.090, WMT within team) | same | 0.121 ± 0.011 |
  | + noise in d (fit covariance, mean noise variance 0.0127 against true variance of d 0.0696) | -0.809 ± 0.041 | 0.087 ± 0.016 |
  | + noise shared by errors and d in the same games (an error adds runs allowed; covariance -0.0033) | **-0.762** ± 0.040 | **0.113** ± 0.011 |

- Independent check, WMT box lines split by game (game id parity): each half's error rate against d refitted on the scoreboard without that half's games, so no game noise is shared; true variance of y from the covariance of the two halves. 68 teams with 8+ games per half: slope -0.844 ± 0.202, residual true variance 0.0128 ± 0.0108 (SD 0.113). Consistent with the NCAA.com estimate (0.0127 ± 0.0025) but much less precise.
- Against the engine (fielders .119, team .066, total residual .136, slope −.720): the real residual is **0.113 ± 0.011**, variance 0.0127 against the engine's 0.0185, about 2 SE smaller. The true correlation of d with the error log-odds is -0.872 ± 0.027 real against -0.820 implied by the engine's parameters. So the engine already gives fielding at least as much independence from run prevention as the data shows. Candidate 10 as stated (fielding too tied to pitching in the engine) is not supported by the error model's parameters.

### Unearned runs, low-ERA teams against the rest (NCAA.com 2025, full seasons)

| Group | Teams | Unearned share of runs (Σ(R − ER) / ΣR) | SE | Errors per game | Unearned runs per error |
|---|---|---|---|---|---|
| 50 best by ERA | 50 | 0.134 | 0.004 | 0.912 | 0.708 |
| ERA under 4.00 | 12 | 0.135 | 0.009 | 0.819 | 0.677 |
| the other 249 | 249 | 0.130 | 0.002 | 1.198 | 0.779 |
| all | 299 | 0.130 | 0.002 | 1.150 | 0.769 |
| ERA quintile 1 | 60 | 0.131 | 0.004 | 0.912 | 0.705 |
| ERA quintile 2 | 60 | 0.137 | 0.004 | 1.066 | 0.758 |
| ERA quintile 3 | 59 | 0.129 | 0.004 | 1.108 | 0.777 |
| ERA quintile 4 | 60 | 0.128 | 0.004 | 1.235 | 0.775 |
| ERA quintile 5 | 60 | 0.127 | 0.004 | 1.428 | 0.814 |

Real low-ERA teams make fewer errors (0.91 against 1.20 per game) and fewer unearned runs per error (0.71 against 0.78), but they also allow fewer runs in all, so their unearned share (0.134) is the same as the other teams' (0.130). The sim's 50 best by ERA have an unearned share of about .099 (earned share .901). The partial correlation of ERA with errors per game at equal runs allowed per game is -0.515 (real): at fixed total run prevention, teams with more errors have lower ERA, which is the same partition the engine uses (pitching takes the remainder). The engine's partition can be compared on this row once the sim side is measured.

## 3. Starter day-to-day form (candidate 11)

### Method

- Unit: a half-inning, from the WMT play-by-play (37,970 half-innings, 2,224 games; runs from plate appearances plus base-running events equal the box score in every game). A half-inning belongs to the starter if he faced its first batter; all its runs count, including those after he left.
- Expectation e_i: the scoreboard fit without parks (the fit whose dispersion is 2.6185) gives each team-game's expected runs; it is spread over innings by the league's share of runs by inning number, and scaled so the sample's expected and observed totals agree. Residual r_i = runs − e_i.
- A shared multiplicative effect of log-variance σ² on a group of half-innings gives cov(r_i, r_j) = e_i e_j σ² for any two of them. Each component is estimated as Σ r_i r_j / Σ e_i e_j over one type of pair, all pairs within one batting team:
  - A: two half-innings of the same start (talent P + form F + the game's shared part G);
  - B: the same starter's half-innings in two different games (P);
  - C: a starter half-inning and a relief half-inning of the same game (G, plus the covariance of the starter's and the bullpen's deviations from team d);
  - Cb: the same starter's half-innings in one game with relief half-innings in another of his starts (that covariance alone);
  - F = (A − B) − (C − Cb). G is the batting team's day, park and weather, umpire and the fielding team's day together.
- Bootstrap over starters (400). Conversion to the dispersion scale: a start-level effect adds F × (Σ e over the starter's half-innings)² to the team-game's variance, so Δφ = F × mean((Σ e_S)² / E_team-game).

### Results

| | Starters with 5+ starts | 10+ starts |
|---|---|---|
| Starters / starts | 281 / 2,694 | 123 / 1,677 |
| A within start | +0.0701 ± 0.0155 | +0.0821 ± 0.0171 |
| B = P, same starter other games | +0.0073 ± 0.0062 | +0.0108 ± 0.0071 |
| C same game, starter × relief | +0.0715 ± 0.0198 | +0.0677 ± 0.0233 |
| Cb | -0.0060 ± 0.0051 | -0.0025 ± 0.0055 |
| G = C − Cb, game's shared part | +0.0775 ± 0.0210 | +0.0702 ± 0.0249 |
| **F, start-level form** | -0.0146 ± 0.0253 | +0.0011 ± 0.0276 |
| Δφ from F | -0.032 ± 0.055 | +0.003 ± 0.065 |
| Share of the missing .3945 | -8% ± 14% | +1% ± 17% |

- Form is not detectable: F is -0.015 ± 0.025 (5+ starts) and +0.001 ± 0.028 (10+). Almost all of the covariance inside a start (A) is also present between the starter's innings and the bullpen's innings of the same game (C): it belongs to the game, not to the starter. The 95% upper bound on form's share of the missing variance is about 19% (5+ starts) or 33% (10+).
- Innings 1–3 against 4–6 (starts in which the starter began innings 1, 2 and 3 and at least one of 4–6; correlation of residual sums): same start 0.060 ± 0.018 (n 2,985); his next start's 4–6 0.016 ± 0.022 (talent); relief innings 7–9 of the same game 0.029 ± 0.019 (game). Beyond talent and the game, about +0.015, within its SE (about .035).
- Dispersions (runs around the fit, no pitcher term unless stated): half-innings 2.31; half-innings begun by the starter 2.19; per start (sum of his half-innings, 4.33 on average) 3.38; per start with a pitcher term (each starter's season ratio, 5+ starts, 2,694 starts) 3.13. The rise from half-inning to start is the cross-inning covariance (P, G, F); the decomposition above assigns it to G.
- Caveats: a starter is pulled after bad innings, so bad days contribute fewer within-start pairs, which biases F (and A) down. The pairing C uses relief innings, which are later in the game; if game conditions change during a game, G from C is smaller than the G inside a start and F is biased up. The WMT sample is 59% P4.

### Where the real cross-inning covariance sits (context for the sim side)

Exact split of the team-game dispersion in the WMT sample (4,448 team-games, runs around the same expectation): total 2.81 ± 0.08 (above the scoreboard's 2.62: different sample, P4-heavy); inside half-innings 2.40 ± 0.05; between half-innings of the same team-game 0.42 ± 0.05, of which starter × starter 0.13, starter × relief 0.20, relief × relief 0.09. The sim's total 2.224 is below this sample's within-half-inning part alone (the bases differ: the WMT total is 2.81 against the scoreboard's 2.62, so this is an indication, not a comparison). Measuring the same split on the sim (the runs-per-half-inning distribution already passes its Phase 1 gate) would show whether the missing .39 sits between half-innings, i.e. in the game's shared part G, which no single-pitcher or single-play mechanism supplies.

## 4. Errors clustering into big innings (candidate 12)

- Data: 38,071 half-innings with at least one chance, 2,232 games, 4,509 errors on 4,472 plays (fielder credits from `fielding_2025.csv.gz`; they equal the box-score errors in 99.96% of team-games). Unearned runs from `runs_charged_2025.csv.gz`.
- Expectations: Poisson with the fielding team's errors per half-inning; binomial with the half-inning's chances (PO + A + E) and the team's errors per chance. The binomial already gives long innings more errors, including the chances an error itself creates.

| Errors in the half-inning | 0 | 1 | 2 | 3+ |
|---|---|---|---|---|
| Observed | 0.8927 | 0.0972 | 0.0091 | 0.0009 |
| Poisson, team rate | 0.8892 | 0.1035 | 0.0069 | 0.0004 |
| Binomial by chances | 0.8879 | 0.1059 | 0.0059 | 0.0002 |
| Mean runs | 0.634 | 1.728 | 2.810 | 4.257 |
| P(3+ runs) | 0.079 | 0.270 | 0.490 | 0.743 |
| Half-innings | 33,987 | 3,702 | 347 | 35 |

- Share of half-innings with 2+ errors: observed 0.0100 ± 0.0005, Poisson 0.0073, binomial 0.0061 ± 0.0001; ratio observed / binomial **1.63 ± 0.08**. Counting error plays instead of errors (two errors on one play count once): 0.0092 against 0.0060, so double-error plays are a small part of it.
- P(3+ run half-inning | at least one error) 0.293 ± 0.007; P(3+ | no error) 0.079 ± 0.001.
- Unearned runs per error 0.759 ± 0.016 (NCAA.com, all D1: .769); by errors in the half-inning: 1: 0.706, 2: 0.738, 3+: 0.850.
- Errors per team-game: variance around the binomial-by-chances expectation 0.984 against binomial 0.977 (mean 1.010).
- **Variance contribution.** Runs per half-inning mixed over the observed error-count distribution have variance 1.8922; over the binomial distribution 1.8833 (means equal to 4 decimals). Times 8.53 half-innings per team-game: 0.075 runs² per team-game; over 6.51 runs per team-game: **Δφ = 0.0116 ± 0.0097**, 2.9% of the missing .3945 (against Poisson: 0.0084). It credits every run difference between multi-error and single-error half-innings to the clustering (multi-error half-innings are also long ones), so it is an upper bound.

## Not measured here

- Every sim-side counterpart: split-half reliabilities, the error residual as the sim realizes it, F and G, the error-count distribution per half-inning, and the within/between half-inning split of the sim's dispersion. They need sim play-by-play, which waits for the new engine (no season was simulated here).
- Step 0 (offense / pitching / shared split by weekend and conference) and candidates 1, 3, 4, 5, 7 were not part of this task.
- Sidearm season totals cannot be split by opponent (item 1c).

<!-- round2: scripts/diag_tto_mopup.py -->
## Round 2: times through the order (candidate 3) and mop-up pitching (candidate 4)

2026-10-07. Owner: "size times through the order and mop-up pitching in blowouts next, from real data only... Keep the running total of explained variance. Sizes only, no fixes." Script: `scripts/diag_tto_mopup.py` (run after `scripts/diag_sizes.py`); its numbers are under `item5_tto`, `item6_mopup` and `running_total` in `reports/diagnosis_sizes.json`. Data: the WMT play-by-play (2,232 games, 178,073 plate appearances), round 1's half-inning table and expectation. Nothing was simulated. SEs: cluster-robust by pitcher for regressions, bootstrap (400 reps) over games or teams otherwise, as stated.

### Running total of explained variance (real-data sizes)

Common scale (round 1): missing dispersion 2.6185 − 2.224 = 0.3945. A component t_g of a team-game's runs (centred) is worth Δφ = mean((r_g² − (r_g − t_g)²) / μ_g) = mean(t_g² / μ_g) + 2 mean((r_g − t_g) t_g / μ_g): its own variance plus twice its covariance with the rest of the team-game's runs. For a component independent of the rest this is round 1's mean(V / μ).

| Candidate | Real size (Δφ) | SE | Share of .3945 | 95% upper bound of the share | Running total (share) | Running 95% upper bound |
|---|---|---|---|---|---|---|
| 11. Starter day-to-day form (5+ starts) | -0.032 | 0.055 | -8% | 19% | -0.032 ± 0.055 (-8%) | 19% |
| 12. Errors clustering in half-innings | +0.012 | 0.010 | +3% | 8% | -0.020 ± 0.056 (-5%) | 23% |
| 3. Times through the order, with the real hook | -0.105 | 0.012 | -27% | -20% | -0.125 ± 0.057 (-32%) | -3% |
| 4. Mop-up pitching, relief entries at a margin of 5+ | +0.066 | 0.019 | +17% | 26% | -0.059 ± 0.060 (-15%) | 15% |
| **Total of 11, 12, 3, 4** | **-0.059** | 0.060 | **-15%** | **15%** | | |
| Total without 3 (sources that add variance only) | +0.046 | 0.059 | +12% | 41% | | |

- These are real-data sizes of each mechanism, so they are upper bounds on what each could add to the sim. The sim side (how much of each the engine already produces) is not measured here; it comes later, on the new engine.
- Candidate 3 is negative: the times-through-the-order penalty is real and large per PA, but combined with the real hook it *reduces* the variance of runs per team-game (the long starts that take the penalty are the low-scoring ones). Built into the engine as it stands, it would widen the gap by about 0.09 rather than close it.
- Candidate 4 is the first positive, detectable size: +0.066 ± 0.019 (17% of the missing variance). The engine already has a blowout bin (|margin| ≥ 7) in its relief choice; entries at 7+ alone are worth +0.065 ± 0.017, so the part the engine's bins cannot represent at all (entries at 5–6) is about +0.001. The bin edge is not what is missing; whether the engine's blowout relievers are as much worse than its close-game relievers as the real ones are is the sim-side check.
- Four candidates together explain -15% (95% upper bound 15%). Round 1's pointer stands: most of the missing variance is a game-level shared part, between half-innings, that no single-pitcher mechanism sized so far supplies.

### 5. Times through the order (candidate 3)

**(a) The penalty per PA.** Method: every plate appearance's outcome (run value by linear weights, K, BB, HBP, HR, on base) regressed on dummies for the batter's 2nd, 3rd and 4th+ time facing the game's starter (counted by batter in the outing), with fixed effects for the batter, the pitcher (season) and the batting team-game; relief PAs stay in the regression (TTO dummies zero) so the batter and team-game effects use every PA. The team-game effect absorbs the game's shared part G (round 1); comparing within the team-game, not within the start, avoids the bias of a start-level effect under the hook (a start is cut right after a bad stretch, so its observed later PAs are worse than its mean). SEs cluster-robust by pitcher.
Linear weights (mean RE24 by result, complete half-innings of the sample): 1B 0.575, 2B 0.882, 3B 1.186, HR 1.421, BB 0.429, HBP 0.460, K -0.416, GO -0.338, FO -0.399.

| Outcome, change from the 1st time through | 2nd | 3rd | 4th+ |
|---|---|---|---|
| Runs per PA (linear weights) | +0.0317 ± 0.0039 | +0.0535 ± 0.0059 | +0.0785 ± 0.0196 |
| K% | -0.0371 ± 0.0031 | -0.0442 ± 0.0048 | -0.0620 ± 0.0137 |
| BB% | +0.0001 ± 0.0022 | +0.0122 ± 0.0033 | +0.0235 ± 0.0104 |
| HBP% | -0.0006 ± 0.0013 | +0.0042 ± 0.0018 | -0.0059 ± 0.0056 |
| HR% | +0.0059 ± 0.0013 | +0.0075 ± 0.0020 | +0.0116 ± 0.0062 |
| On-base rate | +0.0240 ± 0.0036 | +0.0447 ± 0.0051 | +0.0691 ± 0.0189 |
| Starter PAs | 29,794 | 12,134 | 755 (1st: 39,516) |

The same penalty in runs per PA under other designs (bias direction in brackets):

| Design | 2nd | 3rd | 4th+ |
|---|---|---|---|
| Batter + pitcher FE, no game effect (starters go deeper on good days: biased down) | +0.0244 ± 0.0039 | +0.0343 ± 0.0059 | +0.0324 ± 0.0189 |
| **Batter + pitcher + team-game FE (main)** | +0.0317 ± 0.0039 | +0.0535 ± 0.0059 | +0.0785 ± 0.0196 |
| Batter + start FE (cut after bad stretches: biased up) | +0.0347 ± 0.0042 | +0.0634 ± 0.0062 | +0.0854 ± 0.0200 |
| Batter + start FE, TTO by lineup turn (batters 1–9, 10–18, ...) | +0.0364 ± 0.0042 | +0.0669 ± 0.0062 | +0.0897 ± 0.0189 |
| Batter + start FE, only starts of 27+ batters, first 27 (survivors of the 3rd time through: biased down) | +0.0024 ± 0.0103 | -0.0176 ± 0.0100 | n/a |
| Main + the starter's pitch count before the PA (25/50/75/100 bins), TTO net of pitch count | -0.0191 ± 0.0066 | -0.0252 ± 0.0107 | -0.0063 ± 0.0233 |

- The penalty is large: +0.053 runs per PA the third time through, with K% down 4.4 points and BB% up 1.2. Its bracketing designs give +0.034 to +0.063. The balanced design (only starts that lasted 27 batters) finds none, which is the hook's selection: those starts are the ones where the third time through went well.
- Times through and pitch count cannot be told apart within a game: with pitch-count bins added, the pitch-count terms carry it (+0.047, +0.077, +0.096, +0.086 runs per PA at 26–50, 51–75, 76–100, 100+ pitches) and the TTO terms turn negative (-0.019 ± 0.007, -0.025 ± 0.011). The engine has neither (its fatigue is between games: rest days), so the combined within-game decline is what it lacks; the size below uses the main design's TTO terms.
- Not a game-time trend: relievers facing a batter for the first time (pitcher and batter FE, 84,910 PAs) allow no more in later innings (run value vs innings 1–3: 4–5 -0.0056 ± 0.0084, 6–7 -0.0010 ± 0.0081, 8+ -0.0029 ± 0.0081).
- Exposure per start (4,464 starts, 18.4 ± 6.6 batters): 1st time 8.85 PAs, 2nd 6.67 (SD 3.33), 3rd 2.72 (SD 3.19; any in 53% of starts), 4th+ 0.17.

**(b) What it adds to runs per team-game, with the hook.** Method: each batting team-game gets its expected TTO runs T_g = Σ over its PAs against the opposing starter of the penalty for that PA's time through (main design). T_g varies with how deep the starter went, which the hook sets. Its size is Δφ above with t_g = T_g centred, against round 1's r_g and μ_g; SE by bootstrap over games with the penalty drawn from its sampling distribution.

| | Value | SE |
|---|---|---|
| T_g, expected TTO runs per team-game: mean / SD | 0.371 / 0.275 | |
| Correlation of T_g with runs in the starter's half-innings (residual) | -0.345 | |
| Correlation of T_g with runs in the relief half-innings (residual) | -0.019 | |
| Variance part, mean(t² / μ) | +0.0125 | 0.0024 |
| Covariance part, 2 mean((r − t) t / μ) | -0.1176 | 0.0147 |
| of which with the starter's half-innings | -0.1104 | 0.0135 |
| of which with the relief half-innings | -0.0072 | 0.0036 |
| **Δφ, real (penalty with the real hook and the real game-to-game variation)** | **-0.105** | 0.012 |
| Δφ with the bracketing penalties (pitcher FE / start FE) | -0.067 / -0.122 | |
| Δφ if the engine had it (game-shared part removed, below) | -0.090 | 0.011 |

- Share of the missing .3945: -27% (95% upper bound -20%). The penalty's own variance is small (0.012); the covariance dominates and is negative, because a starter who lasts into the third time through is one who has allowed few runs. The penalty raises exactly the team-games that are low, which compresses the distribution.
- If the engine had it: the engine plays the same matchup rate every time through, with the 2025 pull hazard by pitch count and outing runs (item c), so its starters' exposure depends on their runs allowed as the real ones' does. What the engine would not reproduce is the part of the covariance that comes from the game's shared part G (bad days for the pitching side shorten starts and raise every inning's runs). That part shows in the covariance with relief half-innings (-0.0072), which the hook cannot cause; scaled to the starter's half-innings by their expected runs (eS / eR = 1.05) it is -0.0076. Removing both leaves -0.090 ± 0.011: an effect of this size in the engine would lower its dispersion, not raise it. This is an approximation from real data; the engine's own number needs the new engine's play-by-play.

**(c) Does the hook respond to damage beyond pitch count?** Method: every batter a starter faced that was not the game's last for his team (82,138 decisions, 4,403 pulls), pulled = a different pitcher faces the next batter, as the engine's table is built (`scripts/build_phase2_benchmarks.py`). Logit with a cell for every (outing pitches // 10, inning just ended, weekend), the engine's own conditioning, plus runs; SEs clustered by pitcher.

Real hazard of a pull at the end of an inning, by runs allowed in the outing (± binomial SE):

| Outing pitches | 0 runs | 1 | 2 | 3 | 4 | 5+ |
|---|---|---|---|---|---|---|
| 30-49 | 0.053 ± 0.005 (n 1901) | 0.061 ± 0.007 (n 1129) | 0.083 ± 0.010 (n 714) | 0.070 ± 0.013 (n 371) | 0.141 ± 0.024 (n 205) | 0.263 ± 0.041 (n 118) |
| 50-69 | 0.090 ± 0.009 (n 988) | 0.097 ± 0.010 (n 906) | 0.105 ± 0.011 (n 731) | 0.131 ± 0.016 (n 450) | 0.128 ± 0.020 (n 288) | 0.246 ± 0.028 (n 240) |
| 70-89 | 0.262 ± 0.021 (n 454) | 0.220 ± 0.018 (n 537) | 0.245 ± 0.019 (n 503) | 0.292 ± 0.024 (n 346) | 0.248 ± 0.029 (n 226) | 0.396 ± 0.031 (n 245) |
| 90-109 | 0.534 ± 0.043 (n 133) | 0.520 ± 0.037 (n 179) | 0.677 ± 0.034 (n 189) | 0.636 ± 0.044 (n 118) | 0.667 ± 0.046 (n 105) | 0.704 ± 0.043 (n 115) |

- Yes. At equal pitch count, each run allowed in the outing raises the log-odds of a pull by 0.285 ± 0.013 (odds × 1.33); by dummies: 1 run +0.35 ± 0.06, 2 runs +0.68 ± 0.06, 3 runs +0.92 ± 0.07, 4 runs +1.19 ± 0.08, 5 runs +1.69 ± 0.08 (5 = 5+).
- Beyond what the engine conditions on (log-odds, same model with outing runs linear): runs in the outing +0.115 ± 0.018; runs in the current half-inning +0.372 ± 0.020; runners on base after the PA +0.812 ± 0.026; trailing by 1-4 +0.082 ± 0.047; trailing by 5+ +0.292 ± 0.093; leading by 5+ -0.047 ± 0.063; next batter's 3rd+ time through +0.288 ± 0.072. Runs in the current half-inning and runners on base move the real hook strongly (a starter is lifted mid-inning with traffic), and so do a deficit of 5+ and the third time through the order.
- The engine (`engine/manager.py` `pitching_change` / `_hazard`): the 2025 table P(pulled | weekend rotation rank or midweek, outing pitches // 10 (cap 12), outing runs (cap 5), inning just ended), backed off to the table without runs when a cell has under MIN_HAZARD_N decisions, scaled by the pitcher's Stamina leash and the tier / season-week multipliers. Nothing else enters: no current-inning runs, runners, margin or times through the order. So the engine's hook responds to runs allowed as the real one does on the margins it has, but a starter in the engine is not lifted for the current inning's damage or for runners on base, and his exposure to the third time through is not part of the decision.

### 6. Mop-up pitching in blowouts (candidate 4)

**(a) Who enters.** Method: every relief outing of the 50 full-season teams (40+ parsed games; 9,193 entries), margin at entry from the pitching team's side. Quality is the reliever's season line without that game (leave-game-out): run value allowed per PA (linear weights) and a FIP-type rate per PA, (13 HR + 3 (BB + HBP) − 2 K) / PA; entries need 10+ batters faced outside the game (98.2% of entries). Means are weighted by batters faced in the outing; "− team" subtracts the team's relief mean. SEs by bootstrap over teams.

| Margin at entry | Entries | BF | Quality known (BF) | rv/PA allowed, season | − team | FIP-type/PA | − team | Position players' BF share |
|---|---|---|---|---|---|---|---|---|
| 0-1 | 2,390 | 16,715 | 100% | -0.0259 ± 0.0045 | -0.0057 ± 0.0017 | 0.304 ± 0.018 | -0.018 ± 0.009 | 0.6% |
| 2-3 | 2,581 | 17,102 | 100% | -0.0225 ± 0.0053 | -0.0034 ± 0.0018 | 0.315 ± 0.021 | -0.015 ± 0.008 | 0.8% |
| 4 | 985 | 6,324 | 99% | -0.0163 ± 0.0057 | -0.0018 ± 0.0023 | 0.341 ± 0.024 | -0.004 ± 0.010 | 0.3% |
| 5-7 | 1,902 | 11,648 | 98% | -0.0043 ± 0.0056 | +0.0105 ± 0.0018 | 0.403 ± 0.025 | +0.059 ± 0.010 | 0.7% |
| 8+ | 1,335 | 7,021 | 95% | +0.0150 ± 0.0075 | +0.0305 ± 0.0031 | 0.492 ± 0.032 | +0.145 ± 0.017 | 1.4% |
| Close, 0–3 | 4,971 | 33,817 | 100% | -0.0242 ± 0.0048 | -0.0045 ± 0.0015 | 0.310 ± 0.019 | -0.016 ± 0.007 | 0.7% |
| Late and close (7th+, 0–3) | 2,440 | 13,055 | 100% | -0.0317 ± 0.0044 | -0.0123 ± 0.0023 | 0.276 ± 0.020 | -0.050 ± 0.012 | 1.0% |
| **5+** | 3,237 | 18,669 | 97% | +0.0028 ± 0.0060 | +0.0179 ± 0.0016 | 0.436 ± 0.026 | +0.091 ± 0.010 | 0.9% |
| 7+ (engine's blowout bin) | 1,848 | 10,013 | 96% | +0.0116 ± 0.0069 | +0.0263 ± 0.0027 | 0.480 ± 0.031 | +0.131 ± 0.015 | 1.2% |
| **8+** | 1,335 | 7,021 | 95% | +0.0150 ± 0.0075 | +0.0305 ± 0.0031 | 0.492 ± 0.032 | +0.145 ± 0.017 | 1.4% |
| Leading by 5+ | 1,717 | 9,215 | 97% | -0.0133 ± 0.0051 | +0.0136 ± 0.0024 | 0.357 ± 0.022 | +0.055 ± 0.012 | 0.6% |
| Trailing by 5+ | 1,520 | 9,454 | 97% | +0.0187 ± 0.0072 | +0.0221 ± 0.0024 | 0.514 ± 0.032 | +0.126 ± 0.015 | 1.2% |

Leverage gap (blowout minus close, within team):

| | rv/PA − team | FIP-type/PA − team |
|---|---|---|
| 5+ vs close (0–3) | **+0.0224** ± 0.0021 | +0.107 ± 0.010 |
| 7+ vs close | **+0.0308** ± 0.0033 | +0.147 ± 0.017 |
| 8+ vs close | **+0.0350** ± 0.0037 | +0.161 ± 0.018 |
| 5+ vs late and close | **+0.0301** ± 0.0027 | +0.141 ± 0.016 |

- Blowout relievers are clearly worse: +0.022 runs per PA at 5+ and +0.035 at 8+ against the relievers of close games of the same team; with every reliever kept (1+ other batters faced) the 5+ gap is +0.0242. Trailing teams go deeper into the staff than leading ones (+0.126 against +0.055 FIP-type per PA). Position players pitching are rare (about 1% of blowout batters faced; a pitcher who also has 20+ PAs, two-way players included).
- By the engine's role definition (relief batters faced rank, `scripts/build_phase6_usage.py`), real season run value per PA: r1 -0.050, r2 -0.039, r3 -0.020, r4 -0.005, r5 -0.013, r6 -0.002, r7 +0.000, r8 +0.028 (r8 = 8th and deeper, 314 pitchers). The engine orders r1–r8+ by K − BB − HR talent instead, so its gradient by role is at least as steep.
- The engine (`engine/manager.py` `relief_pitcher`) does use the score: leverage is "blowout" at |margin| ≥ 7 (`config/phase6.LEVERAGE_BLOWOUT`, a GUESS bin edge), "late_close" from the 7th inning within 3, else "other"; the choice is the 2025 conditional logit of role × leverage plus rest. With everyone rested, the share of entries going to roles r6–r8+ is 45% in a blowout, 26% in "other" and 18% late and close; r1 gets 5%, 16% and 25%. Margins of 5–6 fall in "other", so the engine treats them like a 4-run game.

**(b) How they pitch against their quality.** Prediction for each outing: the reliever's leave-game-out rv per PA plus the batters' leave-game-out rv per PA above league (20+ other PAs, else 0). Observed minus predicted, per PA:

| Margin at entry | Observed rv/PA | Predicted | Batters' adjustment | Observed − predicted | Runs per 9 IP while in |
|---|---|---|---|---|---|
| Close, 0–3 | -0.0257 ± 0.0053 | -0.0188 | +0.0053 | -0.0068 ± 0.0027 | 6.36 ± 0.22 |
| Late and close | -0.0329 ± 0.0066 | -0.0251 | +0.0066 | -0.0078 ± 0.0050 | 6.28 ± 0.27 |
| 5+ | -0.0071 ± 0.0071 | +0.0067 | +0.0039 | -0.0138 ± 0.0033 | 7.87 ± 0.37 |
| 8+ | -0.0126 ± 0.0104 | +0.0170 | +0.0020 | -0.0297 ± 0.0064 | 8.01 ± 0.62 |
| Leading by 5+ | -0.0571 ± 0.0070 | -0.0152 | -0.0018 | -0.0419 ± 0.0059 | 5.25 ± 0.29 |
| Trailing by 5+ | +0.0420 ± 0.0068 | +0.0282 | +0.0095 | +0.0138 ± 0.0049 | 10.76 ± 0.45 |

- Blowout relievers allow more (+1.51 ± 0.31 runs per 9 at 5+ against close games), as their quality predicts, but not more than it predicts: observed − predicted is -0.0070 ± 0.0050 per PA relative to close games at 5+ and -0.0228 ± 0.0074 at 8+. There is no extra "garbage time" decline beyond who pitches. The split by side is the game's shared part again: relievers of a team leading by 5+ do much better than predicted (-0.042), those of a team trailing by 5+ worse (+0.014), the day's offense persisting into the late innings.

**(c) Do blowouts grow?** Method: games after inning k = 3..7 (both halves of 1..k played, the game continued; 8,445 game-states in 2,178 games, pooled, SE by bootstrap over games). Further runs of each side against the fit's expected runs for the half-innings played (a model with no state dependence, so no mop-up gap), and the mop-up gap the side's batters met: Σ over its later relief PAs of (the reliever's leave-game-out rv/PA − his team's relief mean), counted where the pitching team is full-season ("full" columns). Lineup gap: the same for the side's own batters against its team's batting mean.

| State after inning k | Side | n | Further runs | Expected (no gap) | Excess | Excess, full | Mop-up gap, full | Lineup gap | Dispersion of further runs |
|---|---|---|---|---|---|---|---|---|---|
| margin 5+ | lead | 3,350 | 2.706 | 2.382 | +0.324 ± 0.073 | +0.422 ± 0.109 | +0.274 ± 0.029 | -0.067 | 3.25 |
| margin 5+ | trail | 3,350 | 1.871 | 1.930 | -0.060 ± 0.063 | -0.016 ± 0.070 | +0.103 ± 0.019 | +0.032 | 2.03 |
| margin 5-7 | lead | 2,045 | 3.011 | 2.629 | +0.382 ± 0.089 | +0.435 ± 0.134 | +0.251 ± 0.033 | -0.050 | 3.18 |
| margin 5-7 | trail | 2,045 | 2.055 | 2.165 | -0.110 ± 0.072 | -0.063 ± 0.080 | +0.046 ± 0.021 | +0.045 | 2.05 |
| margin 8+ | lead | 1,305 | 2.227 | 1.995 | +0.232 ± 0.106 | +0.401 ± 0.154 | +0.312 ± 0.039 | -0.095 | 3.36 |
| margin 8+ | trail | 1,305 | 1.582 | 1.563 | +0.019 ± 0.084 | +0.055 ± 0.092 | +0.187 ± 0.026 | +0.013 | 2.01 |
| margin 0-2 | lead | 5,095 | 2.990 | 2.976 | +0.015 ± 0.065 | +0.051 ± 0.077 | -0.050 ± 0.019 | +0.034 | 2.78 |
| margin 0-2 | trail | 5,095 | 2.820 | 2.929 | -0.109 ± 0.061 | -0.139 ± 0.069 | -0.129 ± 0.015 | +0.054 | 2.55 |

- A 5+ margin grows: the leader outscores the trailer by 0.83 more runs (expected 0.45 from team strengths; margins of 0–2: 0.17 against 0.05). The leader's excess (+0.42 where its opponent's quality is known) is mostly the mop-up gap it meets (+0.27). The trailing side meets a smaller gap (+0.10) and scores below even the no-gap expectation (-0.02): its bad day persists. Lineup changes push the other way (the leader's lineup gap -0.07).

**Size on the common scale.** Method: t_g = Σ over the batting team-game's relief PAs against a full-season pitching team of (the reliever's leave-game-out rv/PA − his team's relief mean), for entries at the given margin; Δφ as above, the variance part corrected for the sampling noise of the leave-game-out rates (Σ PAs² σ² / n_other, σ² the within-pitcher per-PA variance of rv, 0.291); 2,852 team-games, SE by bootstrap over games.

| Entries counted | Variance part (noise-corrected) | Covariance part | of which relief half-innings | **Δφ** | Share of .3945 | Adds to the 15+ bin | Adds to P(margin ≥ 10) | Adds to the run-rule rate |
|---|---|---|---|---|---|---|---|---|
| Margin 5+ at entry | +0.0073 ± 0.0026 | +0.0587 ± 0.0183 | +0.0688 | **+0.066** ± 0.019 | +17% | +0.0038 ± 0.0009 | +0.0069 ± 0.0031 | +0.0054 ± 0.0025 |
| 7+ (the engine's blowout bin) | +0.0059 ± 0.0020 | +0.0592 ± 0.0158 | +0.0575 | **+0.065** ± 0.017 | +16% | +0.0032 ± 0.0008 | +0.0077 ± 0.0030 | +0.0060 ± 0.0023 |
| 8+ | +0.0064 ± 0.0018 | +0.0468 ± 0.0155 | +0.0462 | **+0.053** ± 0.016 | +13% | +0.0025 ± 0.0007 | +0.0051 ± 0.0025 | +0.0039 ± 0.0019 |
| Every relief entry (all leverage sorting) | +0.0109 ± 0.0041 | -0.0397 ± 0.0251 | +0.0606 | **-0.029** ± 0.025 | -7% | +0.0036 ± 0.0010 | +0.0057 ± 0.0041 | +0.0045 ± 0.0032 |

- The mop-up component adds variance through its covariance with the rest of the game: it lands on team-games already ahead (corr with the rest +0.12). Entries at 5+ are worth +0.066 ± 0.019, 17% of the missing variance (95% upper bound 26%). Counting every relief entry adds the close-game use of the best relievers, which offsets it.
- 15+ bin and run rule, to first order (the share of team-games, or games, at the boundary times the mean component there; the columns show what the component adds, i.e. what a sim without it would lack). In this sample P(15+) is 0.0375 (team-games against full-season, mostly P4, staffs) and P(margin ≥ 10) 0.1911. Entries at 5+: 15+ bin +0.0038 ± 0.0009, 10% of the sample's bin, which applied to the D1 bin (.065) is +0.0066, 56% of the gap to the sim (.0650 − .0533); run rule +0.0054 ± 0.0025 (P(margin ≥ 10) +0.0069 × P(ended early | 10+) .7805), 17% of the gap .1509 − .1201 (22% of .1440 − .1201). These are upper bounds: the engine's blowout bin already supplies part (7+ entries: 15+ +0.0032, run rule +0.0060).

### Not measured in round 2

- Every sim-side counterpart: the engine's own exposure-runs covariance under its hook, its blowout relievers' quality gap and the persistence of its margins. They need play-by-play from the new engine.
- Times through the order apart from pitch count: within a game the two are almost collinear; only their sum is sized.
- Relievers' quality on teams without a full season in the play-by-play (their opponents' relievers): the mop-up component is counted only against the 50 full-season staffs, so its sizes are a P4-heavy sample's.
- Heterogeneity of the TTO penalty across pitchers (a per-pitcher penalty would add variance of its own); not estimated.
<!-- /round2 -->
