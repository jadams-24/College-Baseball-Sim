# Combined report for approval (2026-10-06)

Three parts:
1. The revised diagnosis plan.
2. The in-game management audit and proposals.
3. Sequencing.

Nothing has been built or run in the engine. The only repository change is the product requirement recorded in CLAUDE.md (architecture constraints), as you asked. The facts below come from reading the code and the committed data.

---

## 1. "Offense extremes compressed": revised diagnosis plan

### How sizing works
The gap is game-level variance: scoreboard dispersion is 2.2 in the sim against 2.6 real, around the same team strengths. Two parts are missing:
- **Shared part** (both teams in a game): within-game residual correlation .046 against .073.
- **One-team part:** the rest.

For each candidate I'll report:
- its share of the missing variance (log runs, around the scoreboard fit);
- its effect on each of the seven rows;
- a **running total** after each candidate.

Sizing stops once the running total covers the gap. Then I'll propose fixes in order of size. Candidates that are benchmark-definition questions (non-D1 games, OBP p10) are sized in row units, not variance, and shown in their own column.

### Order

**Step 1. Non-D1 opponents (first, as you asked).** What the benchmark notes already say:
- **Team R/G SD:** already D1-vs-D1 only. The `team_strength_2025` block is built from "every 2025 D1-vs-D1 final", 7,938 games. Non-D1 games cannot explain this row.
- **15+ runs bin and run-rule rate:** built from all 8,079 games in the 2025 scoreboard feed, so about 141 games (1.7%) involve a non-D1 opponent.
  - The check: recompute both rows on D1-vs-D1 games only, using the scoreboard's opponent IDs and WarrenNolan's non-D1 flags.
  - Rough bound before measuring: if those games reach a 10-run margin at 50% (against 19.5% overall), they add about .004 to the run-rule rate against a .032 gap, and less to the 15+ bin.
- **Qualified OBP p10:** comes from the WMT play-by-play, which includes some non-D1 games. The check: recompute the percentiles excluding them.

If a benchmark moves, I'll report it and propose a definition change (with a PHASE0_NOTES note) before anything else.

**Step 0. The variance split (as approved).** I'll split each team-game's residual into:
- the batting team's offense;
- the opponent's pitching;
- the game's shared part.

Each is split by weekend/midweek and by conference/nonconference, real against sim. Every later candidate predicts where its share should land.

**Candidates, in sizing order:**

| # | Candidate | What the engine lacks | Data to size it (in the repository) |
|---|---|---|---|
| 1 | Run rules by conference | One rule (10 after 7) with a fitted probability of being in effect | WarrenNolan `innings` and margins, 2025–26, by conference and conference/nonconference |
| 6 | Non-D1 games | Step 1 above | Scoreboard, WarrenNolan non-D1 flags |
| 7 | OBP p10 level shift | Qualified OBP about .01 low in P4 and mid | Box scores with the sim's qualification rule; HBP spread of qualified players |
| 10 | **Fielding independent of pitching (new)** | See below | WMT box-score games (errors, runs, earned runs per game), NCAA.com 2025 team pages |
| 11 | **Starter day-to-day form (new, partly covered)** | Per-start variation in overall effectiveness | WMT play-by-play: runs allowed per start given true talent and opponent |
| 12 | **Errors clustering into big innings (new)** | Errors are drawn per play with no within-inning dependence | WMT play-by-play `errors_on_play` per half-inning |
| 3 | Times through the order | No times-through-the-order effect anywhere in the engine | WMT play-by-play: runs per PA by time through the order against the same starter |
| 4 | Mop-up pitching in blowouts | The worst pitchers may not be used, or not bad enough, in lopsided games | WMT play-by-play: relievers entering 5+ runs ahead or behind |
| 5 | Midweek lineups | Midweek starters are modeled, midweek lineups are not | Scoreboard residuals Tue/Wed against Fri–Sun |
| 2 | Handedness and platoon | No hands | **Size only**; built in Phase 3 once rosters land |
| 8 | Weather, umpires | Not in the repository | Only if the shared part is still open, and only with your approval for NOAA |
| 9 | RPI rank 64 | Consequence of the rest | Re-checked last |

**Candidate 10, fielding independent of pitching.** The engine's error-on-run-prevention slope is right (−.720 against −.685 on all of D1). But the sim's correlation is too tight (.727 against .655), and its 50 best ERA teams make too few errors (.757 against .912 per game). I'll size it in three steps:
- (a) **Disattenuate.** Split-half (odd/even games) reliabilities of team ERA and errors per game, real (WMT box-score games) against sim. If the sim's season stats are less noisy (its game-to-game variance is compressed), its observed correlation is tighter even with the same true correlation. That would make this candidate partly a symptom of the main gap.
- (b) **Estimate the true independent fielding variance.** That is the real error-rate variance left after run prevention, with noise removed. Compare it with the engine's (fielders .119, team .066, total residual .136, against .127 real on all of D1). Note that the engine holds total run prevention fixed and gives pitching the remainder, so a bad-fielding team gets better pitching. The check is whether that partition matches the real split of runs allowed between earned and unearned.
- (c) **Effect on teams under 4.00 ERA and elite run prevention.** Re-draw the sim's team fielding with the measured independent variance (an analysis draw, not an engine change), then recompute the count of teams under 4.00 ERA (13.8 against 6–12) and the best-50 RA/G (4.58 against 4.80–5.05).

**Candidate 11, starter day-to-day form.** Partly covered already. Per-start dispersion is 1.02 for walks and 1.01 for BABIP (both match), and 1.37 against 1.12 for strikeouts, worth under 1% of run variance. Not yet sized: overall effectiveness per start, meaning runs allowed per start given talent and opponents, and whether a starter's innings 1–3 predict his innings 4–6 beyond talent. Real against sim, as a share of the one-team gap.

**Candidate 12, errors clustering into big innings.** Errors per game are only mildly overdispersed (1.11, checked). Within-inning clustering has not been checked. I'll measure, real against sim:
- the share of half-innings with 2+ errors against the Poisson expectation;
- P(3+ run inning | an error in the inning);
- unearned runs per error.

### What happens after sizing
Fixes are proposed in order of size, each tied to the mechanism its own data fixes, with no noise terms. All seven rows are re-checked on one 40-season run.

The at-large selection correction stays a GUESS (agreed).

---

## 2. In-game management: audit and proposals

### 2.1 Every place the engine asks for a decision (`engine/game2.py`)

| Call | When | Level | Answered now by | Gap against the requirement |
|---|---|---|---|---|
| `lineup(state, side)` | Game start | Game | AI manager | — |
| `starting_pitcher(state, side)` | Game start | Game | AI manager | — |
| `defensive_subs(state, side)` | Start of each half-inning in the field | Half-inning | AI manager | Not available before a pitch or mid-inning |
| `relief_pitcher(state, side)` | After `pitching_change` says yes (mid-inning), or at the next half if the pull came at an inning's end | Plate appearance | AI manager | — |
| `steal_attempt(state)` | Before each PA, repeated after each pre-PA running event | Before the PA | `LEAGUE_RATE`: the base-running table decides | **Only NO is honored; YES is ignored**, so a called steal is impossible today. The count is always 0-0 |
| `pinch_hit(state, side, slot)` | Before each PA | Plate appearance | AI manager | — |
| `intentional_walk(state)` | Before each PA | Plate appearance | `LEAGUE_RATE` | **The answer is ignored**: intentional walks sit inside the BB share |
| `bunt(state)` | Before each PA | Plate appearance | `LEAGUE_RATE` | **YES only turns an out into a sacrifice**: a called bunt does nothing when the drawn outcome is a hit or walk |
| `pinch_runner(state, side, slot)` | Right after the batter reaches | Plate appearance | AI manager | Not for runners already on base, not before a pitch |
| `pitching_change(state)` | After each PA | Plate appearance | AI manager (pull hazard) | Not mid-PA |
| `pinch_hitter(state)` | Never called in `game2` (only the Phase 1 engine) | — | — | Dead interface method |
| `record_game(state)` | After the game | Bookkeeping | AI manager | — |

Missing from the interface entirely:
- pitchout;
- hit-and-run;
- intentional ball;
- mound visit;
- defensive change mid-inning.

Also, **no call happens between pitches.** A plate appearance's outcome is drawn first. The pitch sequence is then drawn conditioned on that outcome (`engine/pitch.py`, Phase 5).

**Two structural findings that block the requirement:**
- **One Decider answers for both teams.** One `Manager` is passed to `play()`, and calls like `steal_attempt(state)` don't say which team is asking. So a human cannot be given one team.
- **The AI manager draws from the game's random stream** (`state.rng`: lineups, pulls, pinch hitters, relievers). If a human makes the same choices the AI would have made, every later draw still shifts, so results change.

### 2.2 Steals per pitch

**What the data allows (checked):** the play-by-play does **not** record the count at a steal for about 89% of steals.
- In the raw WMT actions, a steal's `pitch_count` equals the end of the PA it occurred in for 4,089 of 4,576 matched steals.
- Only 41 of 1,725 games stamp steals mid-PA consistently, too few to trust as an exact-count sample.
- The mid-sequence `P` code marks only 15–18% of PAs with a steal.

So "attempt and success rates by count fitted from the play-by-play" has to be a **latent-position fit**, not a tabulation. For each PA with an eligible runner, the pitch path is known (the sequence), and the steal happened on one of its pitches. The likelihood sums over those positions. It is identified because PAs pass through different count paths: three-pitch strikeouts, full counts, first-pitch outs.

**Proposal:**
- **Decision point:** before every pitch with a runner on base and the next base open. The human or the AI answers per team: steal, hit-and-run, pitchout, intentional ball, mound visit, pinch runner, defensive change, pitching change.
- **Pitch engine:** draw the PA outcome first, as now, then reveal the sequence one pitch at a time through the existing exact conditioning (the h-transform). With no intervention, every PA-level and pitch-level rate is unchanged by construction. When an intervention forces a count change (pitchout, intentional ball) or changes the batter's approach (hit-and-run), the outcome is redrawn from the chain's own absorption probabilities at the new count. Hit-and-run needs its own swing model; it's fitted only if the data identifies it, otherwise it's a listed GUESS.
- **Attempt hazard (AI):** logit by count, score difference, inning, outs and bases, plus runner speed and the existing tier cells. Fitted by the latent-position likelihood on all 2025 WMT PAs with an eligible runner.
- **Success:** logit by count, runner speed, catcher arm and a new pitcher hold/time-to-plate rating. The rating is a pitcher random effect fitted from attempts and caught stealing against each pitcher, deconvolved like the other ratings.
- **Identification check first:** simulate PAs with known count effects, fit, and recover them. If the count term for success can't be recovered at useful precision, I'll report that and hold it at zero, not guess it.
- **Pitch events during a steal:**
  - On a ball, called strike or swinging strike, the steal resolves.
  - On a foul, the runner returns.
  - On a ball in play, the runner was moving, and advancement uses the existing tables. The data cannot tell runners in motion; that is a listed GUESS.
- **Other pre-PA events:** wild pitches, passed balls, pickoffs and balks move to per-pitch the same way, so all between-pitch events share one mechanism.
- **Inning-ending caught stealing:** this truncates the PA, and the batter leads off the next inning at 0-0, as in the rules.

**Gates:**
- Kept as now:
  - stolen bases per team-game, 1.098 ± .100 (sim 1.006);
  - success rate, .760 ± .030 (sim .770).
- Added:
  - **attempts per team-game** (1.436 real, sim 1.307, now report-only) becomes gated;
  - **attempts and success by observed count path:** steals per eligible PA by the PA's number of pitches and final count, real against sim. The sim's exact count is coarsened to what the play-by-play shows, so both sides are measured the same way. This is the testable form of "by count";
  - **attempts by game state** (score difference × inning group × outs), observed directly.
- Reported only: the fitted by-count attempt and success curves, with their SEs.
- Every Phase 1, 2, 4, 5 and 6 row re-run on the same 40 seasons.

### 2.3 Stop before any pitch, switch control, resume with identical results

**Not possible today.** Four reasons:
1. `play()` runs a game to the end in one loop, with no pause points.
2. The AI manager draws from the engine's random stream, so changing who decides shifts every later draw.
3. One Decider serves both teams.
4. In-game state is spread across the game state, the engine's season accumulators and the manager's bookkeeping, with no snapshot or restore.

**Proposal:**
- **A step-driven game session.** `next_decision()` returns the pending decision point (before each pitch, at PA boundaries and at half-inning starts). Each team gets its own controller, human or AI. Sim-ahead ("next at-bat", "half inning", "inning", "three innings", "end of game") hands the user's team to the AI until the stopping point, then returns control.
- **Keyed random streams.** Engine draws come from a counter-based generator keyed by (game seed, pitch number, draw slot). Each AI decision comes from its own stream keyed by (game seed, team, decision point). Who answered, or how many draws an earlier decision used, never shifts a later draw. The AI's answer at any point is a pure function of the state and the seed. This is per machine, consistent with the existing constraint.
- **One resolver.** The resolver takes (state, action), with no argument for who chose the action. That is what makes human and AI odds identical.
- **Serializable state.** The game state, generator counters and the manager's in-game bookkeeping. Season accumulators are updated from the finished game's log, not during play.

**The test** (`tests/test_session_determinism.py`), on 200 seeded games:
1. **Pause and restore:** run each game uninterrupted with AI on both sides and record the full pitch-by-pitch event log. Then, at random pitches, serialize, restore in a fresh process and resume. The logs must be byte-identical.
2. **Control switch:** a scripted "human" who asks the AI for its answer and gives the same one. Switch control on random teams at random pitches (AI → human → AI), including sim-ahead stops. The logs must be identical to the uninterrupted run.
3. **Equal odds:** the same states resolved through the human path and the AI path, with the same keys, give identical outcomes. A 100,000-trial forced steal from a fixed state gives the same success rate both ways.
4. **The 2-0 steal:** a scripted human calls a steal before the 2-0 pitch. It resolves on that pitch, and the log shows it.

---

## 3. Sequencing: recommendation

**Do the per-pitch engine change first (steals, the step session and keyed streams). Run only the data-side parts of the diagnosis in parallel.**

- The per-pitch change touches the engine's random structure, pause points and base running. Every gate needs a full 40-season re-validation afterwards, even though it is designed to be distribution-neutral away from steals.
- If the variance fixes went in first, they would be validated on the current engine, then re-validated after the restructure: two full re-validations, with any interaction found late.
- Doing the restructure first means one validation for it. Then the diagnosis sizes and fixes on the final engine, with one more validation for the fixes.
- The diagnosis's real-data measurements don't depend on the engine and can run now without touching it:
  - step 1 (non-D1);
  - step 0's real side;
  - candidates 1, 7, 10a/b, 11 and 12 (real side).
- The sim-side comparisons and any fix wait for the new engine.
- One caution: the restructure is the larger job (session API, keyed streams, the latent-position steal fit and its identification test, new gate rows). If you'd rather close the realism watch item first, the reverse order works but costs the extra re-validation.

Waiting for your approval on all three.
