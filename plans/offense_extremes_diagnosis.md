# Diagnosis plan: "offense extremes compressed"

Status: for owner approval (2026-10-05, after the Phase 7 merge). Nothing below has been run yet.

## The seven rows (40-season report, 2026-10-05)

| Row | Sim | Real | Report |
|---|---|---|---|
| Run-rule frequency | .120 | .152 ± .016 | Phase 6 |
| Runs per team-game, 15+ bin | .053 | .066 ± .010 | Phase 6 |
| Qualified OBP p10 | .324 | .337 ± .011 | Phase 2 |
| Team R/G SD across teams (all) | 1.032 | 1.162 ± .142 | Phase 2 |
| P4 vs mid nonconference margin SD | 5.73 | 5.97 ± .30 (2025–26) | Phase 7 |
| Postseason upset rate (better seed, regional games without the host; normal-margin model) | .643 | ~.638 if the sim had the real spread (model estimate, not data) | Phase 7 |
| RPI of the team ranked 64 | .5487 | .5433 ± .0029 | Phase 7 |

What is already established:
- Scoreboard dispersion is 2.2 in the sim against 2.6 real.
- The within-game residual correlation is .046 against .073.
- Fit noise in team offense is .081 against .098.

About two-thirds of the missing variance is one team's game and one-third is shared by both teams. Already ruled out (PHASE0_NOTES):
- shortened games;
- in-season drift in team strength;
- pitcher day form (walks, BABIP);
- defensive days;
- week-level run environment;
- team-strength tails;
- schedule strength faced;
- park netting;
- the team draw.

## Step 0: one shared measurement before any candidate

Every row is driven by some part of the game-level variance, so I'll split the missing variance first. Using the existing 2025 scoreboard fit, decompose each team-game's residual (log runs given o, d, park, home) into:
- (a) the team's offense share;
- (b) the opponent's pitching share;
- (c) the shared game share.

I'll do this separately for weekend and midweek games, and for conference and nonconference games, in the real data and in sim seasons. Each candidate below predicts a different place for the gap:
- starter-dependent causes put it in (b) and on weekends;
- lineup causes put it in (a);
- weather and umpires put it in (c).

This is cheap: the data and the fit code exist (`scripts/build_phase2_teams.py`).

## Candidates, with the data that could test each

Ordered by how cheaply they can be tested with data already in the repository.

### 1. Run-rule rules by conference (engine understates the variety)
- **What is missing:** the engine plays one rule, 10 runs after 7 innings, in effect with a fitted probability. Real conferences differ: some add 15 after 5, some use 8 or 12, and some nonconference series agree on none. This is already listed in GUESSES.md as "per-conference rule table in Phase 7".
- **Rows it moves:** run-rule frequency directly, and the 15+ bin (a game that is not stopped keeps scoring).
- **Test (data in the repo):**
  - WarrenNolan 2025–26 `innings` column and final margins, and the 2025 scoreboard.
  - For every game that ended early, the inning it ended and the margin, by conference and by conference vs nonconference.
  - Then the published 2025 conference handbooks for the rule text. Fetch only where robots.txt allows; Sidearm bot protection blocks many, and blocked sites get logged, not worked around.
- **Note:** this is a rules fix, not a variance source, so it moves two rows without touching the others.

### 2. Handedness and platoon splits (missing in the engine; Phase 3)
- **What is missing:** a team's offense varies from game to game with the opposing starter's hand, its lineup's L/R mix and the bullpen matchups. The engine has no hands, so a lineup is equally good against every starter. Weekend rotations often mix hands, so this is game-to-game variance in (a) and (b), structured by opponent.
- **Rows it moves:** game-level dispersion (run rule, 15+, margin SD, upsets, RPI 64), and qualified OBP spread (players with big splits who face many same-hand pitchers).
- **Test:**
  - (i) Needs bats/throws: `data/ncaa_2025/rosters/` from `tools/fetch_rosters.py`, which has not landed.
  - Without it, a partial test works on the WMT play-by-play (40 programs). Infer each pitcher's hand where the play-by-play text names it, then compare runs scored against same-hand and opposite-hand starters.
  - (ii) Size the effect before building: from the play-by-play, take the per-game spread of a team's lineup quality against each starter (needs hands). If the platoon component of run variance is under about 10% of the gap, it cannot close the rows alone.
- **Note:** this is Phase 3 work and must not be built ahead of its phase gate. The diagnosis only sizes it.

### 3. Times through the order and within-game tiring (engine has none)
- **What is missing:** the engine has no times-through-the-order penalty. A starter who is hit hard the third time through, and a manager who leaves him in, produce the multi-run innings and the persistence the sim lacks (innings 1–3 vs 4–6 correlation .068 real against .041 sim).
- **Rows it moves:** the 15+ bin, run rule, margin SD; the within-game correlation diagnostic.
- **Test (WMT play-by-play, in the repo):**
  - wOBA or runs per PA by the batter's time through the order against the same starter, controlling for pitch count;
  - the same split in sim play-by-play;
  - the manager's hook as a function of runs allowed in the outing, real vs sim (Phase 6 has pull tables; check that they condition on in-game damage).

### 4. Mop-up and blowout pitching (engine understates the gap)
- **What is missing:** in lopsided games real teams use their worst pitchers, and sometimes position players. If the sim's blowout relievers are closer to average than real ones, blowouts don't grow and the 15+ bin and run rule shrink.
- **Test (WMT play-by-play):**
  - runs allowed per inning by relievers entering with a deficit or lead of 5+, against the same pitchers' other innings;
  - season quality (FIP-type rate) of pitchers used in those spots, real vs sim.

### 5. Midweek and day-of-week team strength (lineups, not only starters)
- **What is missing:** the sim models midweek starters, but real midweek lineups also differ (rest days, freshmen, travel). That makes a team's offense differ by day.
- **Test:**
  - Scoreboard 2025: a team's residuals in Tue/Wed games against Fri–Sun, offense and run prevention separately;
  - the variance of the midweek-minus-weekend offense effect across teams, real vs sim.

### 6. Non-Division I games (missing)
- **What is missing:** real season stats include games against non-D1 opponents; the sim has none. Teams that play several of them get inflated R/G and OBP, and teams that play none don't. That widens team R/G SD and the qualified OBP spread without touching D1 game dispersion.
- **Rows it moves:** team R/G SD (all) and OBP p10 only.
- **Test:** WarrenNolan 2025 schedules flag non-D1 games. Count them per team and recompute the real benchmarks on D1-only games. If the real rows move toward the sim, the benchmark definition is the cause, not the engine.

### 7. OBP p10 level shift (its own evidence)
- The sim's qualified OBP runs about .01 low across P4 and mid, while league OBP matches. Candidates:
  - the qualification rule against real (PA per team game, games share);
  - HBP talent spread (HBP is a "hidden" component);
  - playing-time allocation (real coaches play high-OBP hitters more).
- **Test:** the qualified-player percentiles with the sim's qualification applied to real box scores, and the HBP-rate spread of qualified players, real vs sim.

### 8. Shared game conditions: wind, temperature, umpires, field
- This is the shared third of the gap. Data not in the repository:
  - park orientation (not found);
  - per-game weather (NOAA hourly is reachable and allowed by robots.txt; it needs park coordinates);
  - umpire assignments (none found).
- **Test, if approved:** NOAA temperature and wind speed (no direction) for the 40 WMT programs' home games, regressed on the game's shared residual. Wind speed without direction can only show a variance increase, not a sign.

### 9. RPI rank 64 (consequence, checked last)
- The bubble's RPI depends on how far records spread, so it should follow the game-level fix. Also checked:
  - the sim has no non-D1 games, which RPI excludes anyway;
  - the nonconference schedule's tier mix by team, against WarrenNolan 2025–26.

## Proposed order and stopping rule

1. Step 0, then candidates 1, 6 and 7, which test benchmark definitions and rules, not variance. If they explain a row, that row is fixed at its cause.
2. Candidates 3, 4 and 5, which can be sized on the play-by-play in the repository.
3. Candidate 2 sized from partial hand data. Built only in Phase 3, once rosters land.
4. Candidate 8 only if the shared third is still open and the owner approves the NOAA pull.

Each candidate is sized before anything is built: the share of the missing variance (dispersion 2.2 against 2.6) it can explain. A mechanism goes in only if its own data fixes its parameters, with no noise term. After the changes, all seven rows are re-checked on one 40-season run.
