# data/

Scraped NCAA tables and play-by-play are committed here, not re-fetched each
session. Every file records its source URL and fetch date.

## data/phase0/conf2025.csv

- **Source:** FanGraphs, Michael Baumann, "The Ridiculous Firewagon Offenses of
  College Baseball" (Feb 13, 2026), per-conference 2025 table sourced from
  Baseball-Reference. https://blogs.fangraphs.com/the-ridiculous-firewagon-offenses-of-college-baseball/
- **Fetched:** 2026-09-29 (Phase 0, transcribed by hand).
- **Used by:** `derive.py` and the conf B entries in `benchmarks.json`.

## data/ncaa_2025/scoreboard/ — every 2025 D1 game's final score

- **Source:** `https://data.ncaa.com/casablanca/scoreboard/baseball/d1/YYYY/MM/DD/scoreboard.json`,
  the JSON feed behind ncaa.com's scoreboard, one file per day from
  2025-02-13 to 2025-06-23 (the MCWS final).
- **Fetched:** 2026-09-30 with `scripts/pull_scoreboard.py`. Details in
  `manifest.json` (120 game days, 11 days with no games, 8,615 entries,
  8,595 unique games; postponed and unplayed entries are kept but carry no score).
- **Files:** `raw/<date>.json.gz` untouched responses; `games_2025.csv` one row
  per entry with date, ids, state, teams, conferences and scores.
- **Derived:** `../run_distribution_2025.json` from `scripts/build_run_histogram.py`:
  runs-per-team-game histogram over 16,068 D1 team-games (8,079 final games),
  plus runs per game by conference. This fills
  `game_structure.run_distribution_per_team_game` in `benchmarks.json`.

## data/ncaa_2025/pbp/ — 2025 play-by-play and box lines from the WMT stats API

WMT hosts the live-stats platform behind many athletics sites. Its public API
(`https://api.wmt.games`, robots.txt allows all user agents) is keyed by NCAA
team id and serves the NCAA game XML as structured actions. Everything below
was fetched 2026-09-30 to 2026-10-01 at one request per second.

| File | Source | Content |
|---|---|---|
| `schedules/<ncaa_team_id>.json.gz` | `/api/statistics/teams/{id}/games?per_page=100` for all 307 D1 teams | 282 teams have games; 2,364 distinct games, 2,259 D1-vs-D1 with both teams' box totals and innings played (about 28% of the 8,079-game season) |
| `parsed/schedule_games_2025.csv` | flattened from the above | one row per game: innings, scores, both box lines (PA, AB, H, 2B, 3B, HR, BB, HBP, K, SF, SH, SB, CS, GO, FO, E, PO, A, IP, ER, pitching K/BB/HBP, WP) |
| `raw/<ncaa_team_id>.jsonl.gz`, `raw/other.jsonl.gz` | `/api/statistics/games/{id}?with[]=actions` | 2,264 game payloads, one JSON line each. The only transformation is dropping null fields and the ingestion timestamps |
| `games_index.csv`, `manifest.json` | puller | one row per pulled game; selection rules, counts, skipped programs |
| `programs_candidates.csv`, `programs_selected.csv` | puller | tier-stratified candidate list and the 54 programs that met the per-tier minimums (13 P4, 26 mid, 15 low); every other WMT-covered D1 game was then added under the pseudo-team `other` |
| `teams_2025.csv` | NCAA scoreboard conference tags, Phase 0 tiers | conference and tier for all 307 D1 teams (64 P4, 153 mid, 90 low) |
| `parsed/pa_events_2025.csv.gz` | `scripts/wmt_parse.py` | 178,073 plate appearances from 2,232 games: inning, half, pre-play outs and occupied bases, batter, pitcher, result, batted-ball type, pitch count and sequence, destination of the batter and of each runner (0 out, 1-3 base, 4 scored, same base held), outs and runs on the play, play text |
| `parsed/runner_events_2025.csv.gz` | same | 13,419 non-PA base-running events (SB, CS, pickoff, WP, PB, balk) with pre-state and destination |
| `parsed/games_2025.csv` | same | one row per parsed game with both box lines; `parsed/excluded_games.json` lists 5 tournament games whose payloads carry text but no structured actions |

`../derived/engine_tables_2025.json` (`scripts/build_engine_tables.py`) holds the
tables the Phase 1 engine samples: joint runner and batter destinations per
result and base-out state (with pooled and marginal fallbacks for sparse cells),
the in-play subtype shares (plain out / SF / SH / FC) by state class, and per-PA
base-running event rates and outcomes by state.

**Reconciliation** (`tests/test_pbp_data_integrity.py`): parsed hits, walks, HBP
and strikeouts equal the box totals exactly; plate appearances are within 0.04%;
runs from plate appearances plus base-running events equal the final score in
more than 90% of games and within 1% in aggregate.

**Coverage and bias.** WMT holds every game of its client schools and nothing
else, so the sample is 59% P4 plate appearances against 21% of D1 teams, and
mid and low programs appear mostly in games against P4 opponents. Per-tier
rates taken straight from the sample are therefore "that tier facing P4
pitching". `scripts/build_pbp_benchmarks.py` reweights every rate by batting
tier x opponent tier using the matchup mix of all 8,079 scoreboard games.
Validation: reweighted runs per team-game 6.64 against the scoreboard's 6.78
for D1-vs-D1 games (P4 7.23 vs 7.23, mid 6.61 vs 6.69, low 6.23 vs 6.59), BA
.282 vs the FanGraphs .280, K% .194 vs .193, HR per game 1.05 vs 1.05. The
low-vs-low cell holds only 68 team-games, so low-tier figures carry the most
uncertainty. Values derived from this sample are conf B in `benchmarks.json`.

## data/ncaa_2025/derived/ — Phase 2 inputs

- `phase2_inputs_2025.json` (`scripts/build_phase2_benchmarks.py`, then `scripts/build_phase2_gate.py` adds the schedule mix): league rates, tier effects, talent distributions by side, rate and role group, correlations, and usage tables (pitches per PA by result, starter and reliever pull hazards, lineup start shares, reliever usage by rank).
- `phase2_gate_2025.json` (`scripts/build_phase2_gate.py`): team R/G and RA/G spreads from the scoreboard, qualified-player percentiles (tiers with fewer than 50 qualified players pooled with the nearest tier; the unpooled values are kept under `unpooled`), leaderboard references.
- `phase2_location_2025.json` (`scripts/solve_phase2_location.py`): the six league intercepts (12 calibration seasons per iteration).
- `phase2_inputs_2025.json` also carries `team_talent` (`scripts/build_phase2_teams.py`): the quasi-Poisson decomposition of every 2025 D1-vs-D1 scoreboard final into team offense and run prevention (log runs), tier means, per-tier team and conference covariances with estimation noise removed, the matchup-controlled home effect and the nonconference hosting model; and usage tables for rotation churn (weekend start shares and three-game rank patterns, the rotation-rank leash, effective roster sizes).
- `phase2_gate_2025.json` also carries `tier_matrix_2025` (runs per team-game by batting tier x pitching tier) and `home_2025` (home win pct, home run differential), with two-way cluster-robust tolerances.
- `phase2_run_scale_2025.json` (`scripts/build_phase2_run_scale.py`): the engine's log-runs gradient by rate, the batting and pitching quality directions scaled to one log run per unit, linearity and additivity checks, and the batting-last home effect between identical teams.
- `phase2_game_scale_2025.json` (`scripts/solve_phase2_game_scale.py`): the map from a team's scoreboard rating x (log runs per game) to engine units, k x + q x² per side and the same for every team, and the home edge. They are solved so the scoreboard decomposition fitted on simulated seasons recovers each team's true (o, d) with slope 1 and no curvature, and reproduces the scoreboard's home effect (8 calibration seasons per iteration).
- `pbp/parsed/runs_charged_2025.csv.gz`: one row per run with the charged pitcher and an unearned flag (29,118 runs; earned 25,695 vs box 25,713).

## data/ncaa_2025/derived/ — true-talent shapes (Phase 2 generation)

- `talent_shapes_2025.json` from `scripts/build_talent_shapes.py`: per side and rate, the deconvolved individual true-talent distribution of the 2025 WMT play-by-play (Gaussian, sinh-arcsinh and NPMLE fits, the likelihood-ratio test, standardized quantile tables, fitted location and scale). Read by `config.phase2.load_talent_shapes` for the rates whose shape differs from Gaussian (batter HR). Report: `reports/talent_shapes.md`.

## data/ncaa_2025/pbp/parsed/ — Phase 6 event tables

From the same raw WMT payloads (`raw/`), by `scripts/build_phase6_events.py` (no new fetch):
`games_meta_2025.csv` (local date and start hour, venue with latitude and longitude, neutral site,
doubleheader number), `subs_2025.csv.gz` (every substitution action), `fielding_2025.csv.gz`
(every fielder credit: putouts, assists, errors, passed balls, by position) and
`runners_2025.csv.gz` (every runner action: on base, advances, steals, caught stealing, pickoffs).

## data/ncaa_2025/derived/ — Phase 6 inputs

`phase6_inputs_2025.json`, blocks written by `scripts/build_phase6_usage.py` (weekly calendar,
relief and midweek-start choice logits, usage benchmarks), `build_phase6_pull.py` (pull multipliers
by tier and season week, on the engine's split: Thu-Sun series games, Mon-Wed midweek),
`build_phase6_subs.py` (substitution hazards; who comes in, by start rank; start shares and start
persistence by rank; roster depth), `build_phase6_parks.py` (park covariance and tier means) and
`build_phase6_fielding.py` (errors, arms, speed, steal attempt and success by offense x defense tier
cell). The usage block also carries the 56-game conversion of the 50+ IP count. The park
magnitude comes from the scoreboard fit with a park term (`scripts/build_phase2_teams.py`, the
`parks` entry of `team_talent` in `phase2_inputs_2025.json`).

## data/ncaa_2025/derived/ — Phase 4 inputs

- `phase4_inputs_2025.json` (`scripts/build_phase4_inputs.py`): the individual pitcher leash (Stamina). Each decision after a batter in the 2025 play-by-play gets the Phase 2 baseline pull hazard; a pitcher's log hazard multiplier is fitted by empirical Bayes per role (starters 271 pitchers, log SD .54; relievers 847, log SD .62), with a method-of-moments check.
- `phase4_rating_scale_2025.json` (`scripts/build_phase4_scale.py`): the PA- or BF-weighted D1 mean and true SD of each rated rate (the 20-80 scale), from 8 simulated calibration seasons of the Phase 2 talent distributions.
- Both are written into `benchmarks.json` (`stamina_2025`, `ratings_scale_2025`) by `scripts/write_phase4_benchmarks.py`; changes are logged in `benchmark_changes_phase4.json`.

## data/ncaa_2025/derived/ — Phase 5 inputs

- `phase5_pitch_2025.json` (`scripts/build_phase5_benchmarks.py`): from the pitch sequences in `pbp/parsed/pa_events_2025.csv.gz`, reweighted to the D1 tier mix. Contents:
  - the pitch chain: events by count, and ball-in-play results by count of contact;
  - player directions: per-pitch event rates on true K% and BB%, split halves;
  - qualified players' pitch profiles;
  - the pitch-level benchmarks, with bootstrap SEs over games (starter pitch-count percentiles pool tier-pair cells with fewer than 50 starts, `percentile_pooling`);
  - the cleaning counts. No pitch type, velocity or location exists in the source.
- `phase5_chain_solved_2025.json` (`scripts/solve_phase5_chain.py`): the league base chain solved so simulated per-count event shares equal the data's (seeds 950001–950004).
- Written into `benchmarks.json` as `pitch_level_2025` by `scripts/write_phase5_benchmarks.py`; change logged in `benchmark_changes_phase5.json`.

## data/ncaa_2025/roster_aggregates/ — 2025 roster aggregates (handedness, roles, platoon, hometowns, origins)

**Rule (owner decision 2026-10-07).** The game never uses real players. Rosters are used only for
aggregate distributions: handedness shares by position and pitcher role, hometown regions by school
(recruiting pipelines), JUCO / D2 / transfer origins, and the Phase 3 platoon tables. Only aggregated
tables are committed (counts and shares by school, conference, tier, region, position, class and hand):
no player names, jerseys, hometown cities, high-school or previous-school names, and no individual rows.
Names are used only inside `tools/aggregate_rosters.py`, to join roster hands to the play-by-play.

- **Source:** the 2025 baseball roster pages of the 283 teams in the WMT play-by-play sample
  (`tools/roster_teams.csv`), fetched by `tools/fetch_rosters.py` (robots.txt obeyed, at least 3 s between
  requests to a site, bot-protected sites logged and skipped) in the GitHub Actions workflow `fetch rosters`
  (`.github/workflows/fetch_rosters.yml`, started by hand). The fetch dates are in `coverage.csv`
  (`fetch_first_date`, `fetch_last_date`) and the commit message; the roster URLs are the fetcher's fixed
  paths on each team's domain in `tools/roster_teams.csv`.
- **Not committed:** the fetcher's output (`rosters_2025.csv` with one row per player, `raw/` pages,
  `state.json`, the request log) stays in the job's temporary directory and is never committed, uploaded
  as an artifact or cached. Local runs write it to `data/ncaa_2025/rosters/`, which is git-ignored. The
  workflow runs `tools/aggregate_rosters.py` and commits only this folder to the branch the workflow was run on; no pull request is opened.
- **Leak check:** before writing, every text column of the five Phase 3 tables (`linear_weights`, `hand_by_talent_*`, `relief_by_hand`, `pinch_hit_by_hand`) must hold only its fixed labels and every other column numbers. The script then ends by scanning every file it wrote, cell by cell, for any roster full name
  (also inside a cell, as a run of words), any last name of 6+ letters, and any hometown city, high school
  or previous school, as whole cells (team, conference and place names and the tables' fixed labels are
  exempt); on a hit it deletes its output and fails, naming only the files. `--selftest` builds synthetic
  rosters from the play-by-play names (fake hands, hometowns, classes, origins), runs the whole aggregation
  and checks that the leak check catches injected names (`tests/test_roster_aggregates.py`).

| File | Content |
|---|---|
| `coverage.csv` | `scope, scope_value, metric, value`, scope all and tier (p4, mid, low, non_d1 for the 6 non-D1 teams; tiers from `pbp/teams_2025.csv`, joined on `team_ncaa_id` = `ncaa_team_id`). Teams listed, attempted, parsed, failed by reason class (`bot_protection`, `http_403`, `no_page`, `parse_failure`, `other`) and not attempted; players parsed; share of players with bats, throws, position, class, hometown, located hometown, high school, previous school, classified origin and WMT person id filled; teams whose page lists previous schools; play-by-play PA with both hands known (by batting tier); fetch dates |
| `failures.csv` | `team_ncaa_id, team, tier, conference, reason_class, reason`; the fetcher's reason per URL path with URLs removed. No player data |
| `handedness_by_position.csv` | `scope (all / tier / conference), scope_value, position_group, bats (R/L/S/unknown), throws (R/L/unknown), count, share` (share within scope x position group) |
| `linkage.csv` | per scope (all / team tier) and side (batter / pitcher): play-by-play names on teams with a parsed roster, matched / ambiguous / no candidate, names on teams without a roster, PA (BF) and the share of PA (BF) matched, roster players (non-pitchers for batters; P and two-way for pitchers) and the share matched |
| `pitcher_throws_by_role.csv` | `scope, scope_value, role (starter / reliever / unmatched), throws, pitchers, appearances, starts, batters_faced, share_pitchers, share_bf` (shares within scope x role) |
| `batter_bats_matched.csv` | `scope, scope_value, status (matched / roster_unmatched), bats, batters, pa, share_batters, share_pa`: roster batters matched to the play-by-play, with their PA |
| `platoon_league.csv` | `scope (all / bat_tier / pit_tier), scope_value, basis, bat_hand, pit_throws, pa`, then counts of the engine's result classes (`config.phase1.RESULTS`: K, BB incl. IBB, HBP incl. CI, 1B, 2B, 3B, HR, SF, SH, IP_OUT = FO/GO/GIDP/DP, ROE, FC; the map of `scripts/build_engine_tables.py`). Basis `side_used`: the side the batter hit from (a switch hitter bats opposite the pitcher); basis `listed`: L/R/S as listed. Only PA where both hands are known; their share of all PA is in `coverage.csv` |
| `platoon_spread.csv` | per side (batters: split by pitcher's hand; pitchers: by batter's side used), rate (K, BB, HR per PA; OB = on-base events H+BB+IBB+HBP per PA; BABIP = hits / balls in play excluding ROE, as in `scripts/build_phase2_benchmarks.py`) and the player's listed hand (all, L, R, S): `min_pa_each_hand` (50), players, mean trials and pooled rate vs each hand, `mean_split` (logit vs L minus logit vs R, on (x+.5)/(n+1)), `obs_var` and its SE, binomial noise variance (`mean_noise_var`: exact variance of the smoothed logit at the player's own rate; `mean_noise_var_delta`: the delta-method value, which overstates rare rates such as HR), `true_sd` = sqrt(max(0, obs - noise)), `null_obs_var` (opponents' hands permuted among opponents, 20 draws: noise plus each player's mix of opponents) and `true_sd_net` = sqrt(max(0, obs - null)). Cells with fewer than 5 players print the count only. No individual rows |
| `hometown_by_school.csv` | `team_ncaa_id, team, conference, tier, hometown_area, area_type, census_region, census_division, count` |
| `hometown_by_conference.csv` | `conference, census_region, census_division, count, share` (share within conference) |
| `origins_by_school.csv` | `team_ncaa_id, team, conference, tier, class, origin, count` |
| `origins_rules.csv` | `scope (all / tier), scope_value, origin, origin_rule, count, share`: which rule classified each player, for grading the rules |
| `linear_weights.csv` | `term, run_value, se, events, team_games, r2, rmse`: runs per event from an OLS of each team-game's runs (final score, `pbp/parsed/games_2025.csv`) on its counts of 1B, 2B, 3B, HR, BB (incl. IBB), HBP (incl. CI), ROE and outs (K, FO/GO/GIDP/DP, SF, SH, FC), intercept free; team-games whose parsed PA count differs from the box score are left out. Play-by-play only, no roster data |
| `hand_by_talent_pitchers.csv` | `scope (all / tier of the pitcher's team), scope_value, index, role, bin, bin_lo, bin_hi, throws (L/R), pitchers, bf_sum, index_mean, index_sd`: matched pitchers by role (as in `pitcher_throws_by_role.csv`) x talent bin. Index `k_minus_bb` (primary; per PA 1[K] - 1[BB]) or `run_value` (linear-weights runs per PA, lower is better), each net of the batter faced (his mean minus the league's, shrunk by n/(n+50); unmatched batters count, keyed by team and name) and of platoon (the league mean in the PA's batter side used x pitcher throws cell minus the hand-known mean). Bins `q1`-`q5`: quintiles within role among D1 pitchers with 30+ BF, the same edges in every scope (outer edges blank); `lt30` for the rest. Cells under 5 pitchers print counts only |
| `hand_by_talent_batters.csv` | `scope, scope_value, index, position_group, bin, bin_lo, bin_hi, throws, bats (L/R/S), batters, pa_sum, index_mean, index_sd`: matched batters with known hands, the same construction with roles swapped (net of the pitcher faced and of platoon). Index `run_value` (primary) or `on_base` (1[H, BB, IBB, HBP, CI]); quintiles among D1 batters with 50+ PA pooled over positions, `lt50` for the rest |
| `relief_by_hand.csv` | `scope (all / tier of the fielding team), scope_value, cur_throws, batter_bats (L/R/S/unknown), inning_bucket (1-6 / 7+), pas, changes, changes_to_L, changes_to_R, changes_to_unknown`: every PA after a fielding team's first in a game is an opportunity; a change is a different pitcher from that team's previous PA; `cur_throws` is the previous PA pitcher's hand, `batter_bats` the listed bats of the batter due up |
| `pinch_hit_by_hand.csv` | `scope (all / tier of the batting team), scope_value, inning_bucket, pitcher_throws, replaced_bats, ph_bats, n`: pinch hitters (`subs_2025` kind `in`, position `ph`) by the hand of the pitcher of their team's next PA, the replaced batter's (the `out` row at the same play and lineup spot) and their own listed bats. `subs_2025.play_by_play_id` and `pa_events_2025.group_id` are ids of play groups in the same per-game action sequence (never equal; a sub has its own group), so the next PA is the first with a larger group_id: it is the pinch hitter's own PA 98.9% of the time. Rows with `ph_bats = opportunity` count every PA by pitcher throws and the listed bats of the batter due up (`replaced_bats`) |

**Rules.**
- *Position group* (from the roster's position string, split on `/ - , & +`): RHP, LHP, P, SP, RP -> P;
  C -> C; 1B -> 1B; 2B, SS, 3B, INF, IF, MIF -> IF; OF, LF, CF, RF -> OF; UT, UTL, DH -> UT/DH. A pitcher token
  with any other token is `two-way` (1B/RHP, RHP/OF); otherwise the first listed group decides (C/OF -> C,
  INF/OF -> IF, C/1B -> C). Blank or unrecognised -> `unknown`.
- *Class:* Fr / So / Jr / Sr / Gr / unknown; redshirt markers (R-, RS-, Redshirt) are dropped, so R-Fr is Fr;
  5th, 6th, Graduate, Grad, Super Senior -> Gr.
- *Hometown area:* the state field read right to left: a US state (postal codes, full names, AP and other
  abbreviations such as La., Calif., N.C., W.Va.) -> postal code with its Census region and division; Puerto
  Rico, Guam and the other territories -> `us_territory`; a Canadian province, an Australian state or a
  foreign country -> the country (`international`); "Texas, USA" -> TX. A blank state with a city field that
  is itself a state or country uses it; anything else is `unrecognized`, blank is `unknown`. Only these
  canonical labels are written.
- *Failure reason class* (over every URL tried): bot challenge page (Incapsula, Cloudflare) > HTTP 403 > a
  page with fewer than 10 players carrying bats/throws (parse failure) > HTTP 404/410 or a redirect away from
  the 2025 baseball roster (no page) > other (no domain, robots.txt, network errors, HTTP 429).
- *Linkage:* the play-by-play `batter_id` and `pitcher_id` are WMT `game_player_id` values, unique to one
  game (every id appears in exactly one game), so they do not equal the roster's `wmt_person_id`. Players are
  matched by name within team: the check name ("Gholston, J.", "J. Jones", "T Head", "Herrera lll",
  "Justin Heffl"; WMT cuts names at 12 characters) is read as a last name and a first-name prefix, and matched
  to the roster's last name (any trailing run of words, or one part of a hyphenated name; a prefix when the
  check name is 12+ characters) plus first initial or the longer prefix given. One candidate -> matched; more
  -> ambiguous (unmatched); none -> no candidate. Each spelling of a player (scorers differ by game) is matched
  separately and summed per roster player.
- *Role:* a start is being the first pitcher of his team's half-innings in a game; a pitcher matched to the
  play-by-play is a starter when at least half his appearances (games) are starts, else a reliever. Roster P
  and two-way players not found in the play-by-play are `unmatched`.
- *Origin* (previous-school field; several schools are each classified and the most informative kept,
  D1 > JUCO > other four-year > high school):
  1. JUCO marker: Community College, CC, C.C., JC, J.C., Junior College, Jr. College, City College -> `juco`;
  2. a 2025 D1 program (`ncaa_d1_teams_2025.csv`, `pbp/teams_2025.csv`) or an alias, after normalising
     St./State/Saint, the NCAA abbreviations (Ark., Fla., Caro., Miss., So., U.) and "University of" -> `d1_transfer`;
  3. "College of the ..." or a name on the constant JUCO list in the script (Chipola, San Jacinto, Walters
     State, McLennan, ... 258 names) followed only by College / CC / campus words -> `juco`;
  4. the player's own high school, or High School, HS, Academy, Prep, School, Catholic, Jesuit, Bishop,
     Country Day without University or College -> `high_school_only`;
  5. anything else -> `other_four_year` (D2, D3, NAIA, and anything unclassified; rule `four_year_keyword`
     when the name says University, College, State, Institute or Tech, `residual_unclassified` otherwise),
     except that a freshman's residual is taken as his high school (`freshman_residual_as_high_school`).
  A blank previous school is `high_school_only` when the team's page lists previous schools for anyone, and
  `unknown` when it lists none (the column is missing).

**Confidence grades** (A best, D worst). The share classified will be read from `coverage.csv`
(`share_origin_classified`) and `origins_rules.csv` after the first run of the workflow with this script; no
roster fetch has been aggregated yet, and the selftest's synthetic shares measure nothing real. Grades
may be revised once the real shares are in.

| Item | Grade | Why |
|---|---|---|
| Bats and throws | A | As printed on the roster page; parsers checked by `fetch_rosters.py --selftest` |
| Position group, class | B | Free-text strings; the first-listed rule decides multi-position players |
| Hometown area and Census region | A for US states and Canada, B overall | Canonical lists; unrecognised entries are counted (`share_hometown_located`) |
| Origin `d1_transfer` | A | Exact match on 2025 D1 names and aliases. Misses programs that left D1 or names written unusually; "Butler" alone is read as D1 Butler, not Butler CC |
| Origin `juco` | B | Markers plus a list; a junior college without a marker and not on the list falls into `other_four_year` |
| Origin `high_school_only` | B | Depends on the page listing previous schools; the freshman rule may move a few freshman transfers here |
| Origin `other_four_year` | C | A residual: D2, D3 and NAIA, plus unlisted junior colleges and unmarked high schools |
| Origins overall | B | |
| Name linkage, roles | B | Name match within team. On synthetic rosters built from the play-by-play names (8% left off), 88% of PA and BF matched; the real rate is in `linkage.csv` |
| Platoon league table | B | Limited by linkage coverage (share of PA in `coverage.csv`) and by WMT's tier mix (59% P4 PA; reweight as in `scripts/build_pbp_benchmarks.py`) |
| Platoon spread | C | About 200 qualified players a side: `obs_var_se` is about .02 on K's logit variance, so true SDs below about .15 logits are not distinguishable from zero; on fake hands `true_sd_net` is about .1, the method's floor |

## data/ncaa_2025/sidearm/ — 13 Sidearm season pages (cross-check)

- **Source:** `https://<school>/sports/baseball/stats/2025` for the 13 programs
  whose Sidearm Sports site answered plainly (Alabama, Baylor, Brown, Bucknell,
  California, Cal Poly, Mississippi State, Missouri State, Pittsburgh, Sam
  Houston, Stephen F. Austin, St. Thomas, Troy). Fetched 2026-09-30.
- **Files:** `raw/<domain>.html.gz` untouched pages; `team_totals_2025.csv`
  the Totals and Opponents rows (hitting, fielding, pitching) extracted by
  `scripts/sidearm_totals.py` from the embedded season payload.
- 202 of 252 D1 athletics domains screened sit behind Imperva Incapsula, which
  refuses this container after a first request, so Sidearm was not usable for
  bulk play-by-play. PrestoSports sites (e.g. Tennessee Tech) serve full
  play-by-play at a 10-second crawl delay and were not needed.

## data/ncaa_leaders/ — national individual and team leaders, 2023–2026 seasons

**Status (owner decision 2026-10-08):**
- www.ncaa.com's robots.txt now disallows AI agents (ClaudeBot and others).
- When these pages were fetched (2026-10-01 to 2026-10-05), robots.txt allowed /stats/ for every agent.
- Only the extracted tables are kept. The raw pages (36 gzipped HTML files: individual leaders, team leaders and the all-team ERA and fielding pages) were removed from the repository.
- **www.ncaa.com is never fetched again** (data.ncaa.com is fine). Future checks use Warren Nolan or the project's own computation.

**Extracted tables (committed):**
- `ncaa_leaders.json` (`scripts/parse_ncaa_leaders.py`, now historical: its inputs are gone). It is what the Phase 2 leader and team-leader gates read, through `scripts/write_leader_benchmarks.py`.
  - **Individual leaders:** top 50 and ties per stat, for 470 (HR), 200 (BA), 205 (ERA), 356 (SO) and 863 (appearances). Source `https://www.ncaa.com/stats/baseball/d1/{year}/individual/{stat}`, page 1, URL years 2023–2025, fetched 2026-10-01.
  - **Team leaders:** top 50 for 210 (batting average), 211 (ERA) and 323 (home runs per game). Source `https://www.ncaa.com/stats/baseball/d1/{year}/team/{stat}`, page 1, URL years 2023–2025, fetched 2026-10-04.
  - The 2023 season is transcribed from the NCAA record book's 2023 leaders (`http://fs.ncaa.org/Docs/stats/baseball_RB/2024/D1.pdf`).
  - NCAA.com labels a season by the academic year it starts: /2023/ is the 2024 season, /2024/ is 2025, /2025/ is 2026 (/2022/ has no tables). The mapping was checked against the 2025 scoreboard: the /2024/ table's games match each listed team's 2025 games (Coastal Carolina 69, Georgia 60, Northeastern 60).
- `team_era_2025.csv` and `team_fielding_2025.csv`: every D1 team's 2025 full season (299 teams each), columns as published.
  - ERA: Rank, Team, G, IP, R, ER, ERA. Fielding: Rank, Team, G, PO, A, E, PCT.
  - Source `https://www.ncaa.com/stats/baseball/d1/2024/team/211` and `.../team/212`, pages 1–6, fetched 2026-10-05.
  - Extracted 2026-10-08 from the raw pages before their removal. `scripts/build_phase7_era_fielding.py` reproduces the committed `era_fielding` benchmark block exactly from them; `scripts/diag_sizes.py` reads them too.

## data/ncaa_brackets/ — NCAA tournament fields and brackets, 2015–2025 (no 2020)

- **Source:** English Wikipedia, `https://en.wikipedia.org/wiki/<YEAR>_NCAA_Division_I_baseball_tournament`
  for 2015–2019 and 2021–2025 (robots.txt allows these pages). A secondary source, not
  the NCAA's own bracket. Fetched 2026-10-05, one request per second, one page per season.
- **Files:** `raw/wikipedia_<YEAR>.html.gz` untouched pages; `brackets_2015_2025.json`,
  rebuilt from the raw pages by `scripts/parse_brackets.py` (`--check` compares a rebuild
  with the committed file). Per season: the 64 teams (conference, automatic or at-large
  bid, national seed, regional host), the 16 regionals (site, host, seeds 1–4, winner), the
  8 super regionals (teams, host, winner), the 8 CWS teams, champion and runner-up. Each
  season carries its own validation result and notes.
- **Inferred, not stated by the page:** regional hosts for 2015–2018 (the regional 1 seed;
  the 2018 page says the 16 national seeds hosted); at-large bids in seasons whose page has
  only the automatic-bid table (2015–2018, 2022, 2023: the field is automatic plus at-large);
  some super regional hosts (marked `inferred` in `host_source`). The 2021 Columbia super
  regional was played at a neutral site (host `null`).

## data/ncaa_brackets/ — NCAA bracketing principles (prechampionship manuals)

- **Source:** NCAA Division I Baseball Prechampionship Manuals, official NCAA PDFs:
  `https://ncaaorg.s3.amazonaws.com/championships/sports/baseball/d1/2024-25D1MBA_PreChampsManual.pdf`
  (2025 championship) and `.../2025-26D1MBA_PreChampsManual.pdf` (2026, kept for comparison).
  The host has no robots.txt (404). Fetched 2026-10-05.
- **Files:** `raw/*.pdf` untouched; `raw/*.txt` text extracted with pypdf 5.1.0. pypdf was
  installed only in the session scratchpad, not in `requirements.txt`, and pdftotext was not
  available. `bracketing_principles.json` has the verbatim rule quotes with PDF and printed
  page numbers, plus a machine-readable summary: 16 national seeds, super regional pairings
  1v16 to 8v9, regional 1v4/2v3, hosting, the same-conference rule, geography and regions.

## data/conf_tournaments/ — 2025 conference tournament formats

- **Source:** English Wikipedia, `https://en.wikipedia.org/wiki/2025_<Conference>_baseball_tournament`,
  one page per conference in `teams_2025.csv` (DI Independent skipped). SoCon has no
  standalone page and redirects to `2025_Southern_Conference_baseball_season#Tournament`.
  A secondary source. Two official conference pages confirm details: necsports.com (NEC) and
  bigeast.com (Big East). Most other conference sites (Sidearm) answered robots.txt with 403
  bot protection and were not fetched. Fetched 2026-10-05, one request per second.
- **Files:** `raw/<conf>__<source>.html.gz` untouched pages; `formats_2025.json`, one record
  per conference: teams, qualification, format code, bracket description, site, auto bid,
  games_min/games_max and games played in 2025.
- **Inferred, not stated by the page:** games_min/games_max (derived from the format), and
  the OVC bracket shape (taken from the schedule table, which contradicts the page's prose).

## data/ncaa_<season>/scoreboard/ — scoreboard feed 2015-2019, 2021-2024 (Phase 7)

- **Source:** the same feed as 2025, `https://data.ncaa.com/casablanca/scoreboard/baseball/d1/YYYY/MM/DD/scoreboard.json`,
  every day from Feb 10 to Jun 30 of each season (`scripts/pull_scoreboard.py --season Y --start Y-02-10 --end Y-06-30
  --out data/ncaa_Y/scoreboard`). Fetched 2026-10-05, 0.3 s between requests. 2020 (season stopped in March) and
  2026 (not served: HTTP 404) are not pulled.
- **Coverage varies by season:** 2015 and 2016 leave many games without results (1,109 and 949 entries still `pre`);
  2017 and 2018 have no conference names; from 2019 on, results and conferences are nearly complete. Conference
  tournament games are often placeholders against `TBA` with no score (most of them in 2025, some in 2021).
  `manifest.json` per season lists days without games and errors (none).

- **2025 (Phase 7, conference tournament format check and cancellations):** the same team schedule pages for 2025
  (`https://www.warrennolan.com/baseball/2025/schedule/<slug>`), fetched 2026-10-05 with
  `scripts/fetch_warrennolan_2026.py 2025` and parsed with `scripts/parse_warrennolan_2026.py 2025` into
  `data/ncaa_2025/warrennolan/`. WarrenNolan has no 2025 sitemap (HTTP 404), so the 2026 sitemap's 308 slugs were used;
  56 opponents have no 2025 page under those slugs (they appear as opponents only). Conference tournament games carry
  an event label ("SEC Tournament - Game 7"); all of them are labelled neutral, even at a member's park.

- **WarrenNolan access** (rechecked 2026-10-05): `https://www.warrennolan.com/robots.txt` reads
  `User-agent: * / Allow: /`, so the schedule pages and the sitemap fetched are allowed. `scripts/fetch_warrennolan_2026.py`
  waits 1.5 s between requests, retries a reset connection at most 3 times (after 5, 10, 20 s), sends a descriptive
  User-Agent, and stops on a 403/407/429 or a bot-protection page. Each page was fetched once per season and is committed.

## data/ncaa_2025/derived/ — PR B decision inputs

- `prb_steals.json`: steal attempt and success by count and game state, fitted by EM on the pitch paths of the 2025 WMT play-by-play (`scripts/build_prb_steals.py`, built 2026-10-07; report `reports/prb_steals.md`).
- `prb_inputs.json`: the AI's bunt and intentional-walk rates by game state, a called bunt's pitches and its outcome table, the pitcher's hold, pickoff scoring, and the gate benchmarks (`scripts/build_prb_decisions.py`, built 2026-10-07).
- Both are built from `data/ncaa_2025/pbp/parsed/` only; nothing is fetched. Method and caveats: PHASE0_NOTES, "Decisions that change outcomes".


## data/ncaa_2025/derived/ — Phase 3 inputs (handedness and platoon)

- `phase3_inputs_2025.json` (built 2026-10-08 from `roster_aggregates/` and the engine):
  - `hands_pitchers`, `hands_batters`, `hand_checks` (`scripts/build_phase3_hands.py`): P(throws L | role, true K-BB); throws by position group; bats L / R / S by position group, throws and true run value; the fit's checks (tier effect at equal talent, run-value sensitivity, the simulated players' spread over the table's bins).
  - `usage` (`scripts/build_phase3_usage.py`): pull and pinch-hit multipliers by hand, the relief choice's and bench pick's platoon terms.
  - `platoon` (`scripts/build_phase3_platoon.py`): the logit shifts by side used x pitcher's hand, net of who faced whom and centred on the league mix.
  - The simulated populations behind the fits are seasons of the engine (seeds in `config/phase3.py`), cached under `runs/` (not committed).
- `benchmark_changes_phase3.json`: the `handedness_platoon_2025` block added to `benchmarks.json` (`scripts/write_phase3_benchmarks.py`).
## data/ncaa_rules/ — NCAA baseball rules (PR B)

Fetched 2026-10-07 from the NCAA's public document store:
- `PRMBA_RulesBook.pdf`: NCAA Baseball 2025 and 2026 Rules (the rules book), https://ncaaorg.s3.amazonaws.com/championships/sports/baseball/rules/PRMBA_RulesBook.pdf
- `2025-26PRMBA_RulesChanges.pdf`: the 2025-26 rules changes, https://ncaaorg.s3.amazonaws.com/championships/sports/baseball/rules/2025-26PRMBA_RulesChanges.pdf

Used for the limits on in-game calls (`config/decisions.py`): coach trips to the mound (9-4), the intentional walk without pitches (8-2-b), the walk charged to the previous pitcher (10-22-b), and a foul bunt on strike three (10-23).

## Not pulled

- **stats.ncaa.org team, individual and contest pages.** The team list is
  served plainly, but every other page sits behind Akamai Bot Manager's
  JavaScript challenge; completing it from this environment was stopped by the
  session's safety policy. The full 303-team rankings tables are to be supplied
  separately. The conf B `league_totals_2025` line (BA, OBP, SLG, BB%, K%, R/G,
  HR/G, SB/G, SH/G) is unchanged and cross-checked in
  `league_totals_2025_team_weighted_wmt`.
- **Qualified-player percentiles** (`batting_distribution_2025`, conf D): need
  the individual tables above.
- data.ncaa.com serves only the scoreboard feed for 2025 (no per-game JSON);
  www.ncaa.com and sdataprod.ncaa.com were denied by the network policy at the
  time of the pull.

## data/ncaa_2026/ — 2026 D1 game results for the RPI formula check

- `rpi/ncaa_rpi_through_2026-05-24.csv`: the NCAA's published 2026 RPI rankings table, extracted from
  https://www.ncaa.com/rankings/baseball/d1/rpi (fetched 2026-10-05; the page read "Through Games May. 24 2026"):
  rank, school, record, conference, road, neutral, home, non_d1, prev; W-L strings as published, 308 schools;
  `record` is the D1 record, road + neutral + home. Used by the RPI formula check (`scripts/check_rpi_2026.py`).
  **www.ncaa.com's robots.txt now disallows AI agents (found 2026-10-08).** Owner decision 2026-10-08:
  - only this extracted table is kept; the raw page snapshot was removed from the repository;
  - www.ncaa.com is never fetched again (data.ncaa.com is fine);
  - future RPI checks use Warren Nolan or the project's own computation.
- `warrennolan/raw/<slug>.html.gz`: every team's 2026 schedule page,
  `https://www.warrennolan.com/baseball/2026/schedule/<slug>` (robots.txt: Allow /),
  fetched 2026-10-05 by `scripts/fetch_warrennolan_2026.py` (1.5 s delay, up to 3
  retries); slugs from the site's sitemap, saved as
  `warrennolan/sitemap_college-baseball-2026.xml.gz`. 308 pages, 0 failures
  (`warrennolan/fetch_log.json`).
- `warrennolan/games_2026.csv` (`scripts/parse_warrennolan_2026.py`): one row per
  game, 2026-02-13 to 2026-06-22, deduplicated across both teams' pages; site as
  WarrenNolan marks it (home / "AT" / "VS" = neutral; for neutral games `home` is
  the team batting last in the box score), both pages' labels kept;
  `neutral_at_home_venue_of` names a participant whose main home park hosted a
  game WarrenNolan calls neutral. `team_games_2026.csv` has every page entry,
  `parse_report.json` the counts and anomalies.
- `team_name_map.csv`: NCAA.com name to WarrenNolan slug (244 by normalised
  name, 64 by hand).
- `warrennolan/record_check_through_2026-05-24.csv`
  (`scripts/check_warrennolan_vs_ncaa_2026.py`): per school, the NCAA's road /
  neutral / home / non-D1 W-L against the same splits from `games_2026.csv`
  (final games through 2026-05-24). The D1 W-L total matches for all 308
  schools (8,297 decided D1 games plus 7 ties WarrenNolan shows and the NCAA
  page does not print). Site splits differ for 48 schools (106 team-games):
  WarrenNolan calls conference-tournament games at a participant's park and
  some alternate-site "home" games neutral where the NCAA counts home/road.
  Non-D1 records differ for 11 schools (WarrenNolan omits some non-D1 games).

## data/ipeds/, data/census/ and the school locations (Phase 9 spec, owner approval 2026-10-08)

- `ipeds/HD2024.zip`: the IPEDS institutional directory, 2024 (U.S. Department of Education, NCES; public domain). Fetched 2026-10-08 from https://nces.ed.gov/ipeds/datacenter/data/HD2024.zip; robots.txt allows the path.
- `census/CenPop2020_Mean_ST.txt`: Census 2020 state centres of population (U.S. Census Bureau; public domain). Fetched 2026-10-08 from https://www2.census.gov/geo/docs/reference/cenpop2020/CenPop2020_Mean_ST.txt.
- `ncaa_2025/school_locations_2025.csv` (`scripts/build_school_locations.py`): IPEDS unit id, institution, city, state and coordinates for the 307 D1 baseball programs.
  - 228 matched by name and 79 by explicit override.
  - Each match was checked against the school's most common roster hometown state; the 51 schools whose rosters lean elsewhere were each checked by hand.
  - Corrected 2026-10-08: Florida and North Florida had matched Florida College and North Florida College (same states, so the state check passed); EADA's Division I list exposed both. They now point to the University of Florida (134130) and the University of North Florida (136172). `reports/proximity_2025.md` was rerun (P4 within 300 miles .586 → .588; nothing else moved).
- `reports/proximity_2025.md` (`scripts/proximity_by_tier.py`): roster geography by tier, for the Phase 9 spec.
- `ipeds/DRVADM2023.zip`, `ipeds/DRVGR2023.zip`, `ipeds/DRVEF2023.zip`: IPEDS derived admissions (DVADM01, percent admitted), graduation rates (GBA6RTT, six-year bachelor's) and fall enrollment (ENRTOT), 2023, the latest published (the 2024 files return 404). NCES, public domain. Fetched 2026-10-08 from https://nces.ed.gov/ipeds/datacenter/data/<FILE>.zip; robots.txt allows the path. For the school report cards.

## data/schools/, data/eada/, data/noaa/: school identity and report cards (Phase 9 prep, owner request 2026-10-08)

- `schools/schools.csv` (`scripts/build_report_cards.py`): every sim team (tid = its row in `ncaa_2025/pbp/teams_2025.csv`, the order `config.phase2` reads) with its real school name, IPEDS institution and unit id, conference, tier, city, state and campus coordinates (from `ncaa_2025/school_locations_2025.csv`). School names only: no logos, mascots or artwork; players stay fictional.
- `schools/report_cards.csv` (`scripts/build_report_cards.py`, `config/report_cards.py`): the starting year's A+ to F grade card for the 307 programs, each category with its percentile score, confidence, raw inputs and source. Recruiting and display only: never read by the engine (`tests/test_report_cards.py`). Method: `design/phase9_recruiting.md`, Section 15; distribution and examples: `reports/report_cards.md`.
- `eada/baseball_eada_2024_25.csv` (`scripts/extract_eada.py`): the baseball rows (participants, coaches, operating and total expenses, revenue) of the EADA 2024-25 data file for 304 of the 307 institutions (the service academies do not file). Source: U.S. Department of Education, Equity in Athletics Disclosure Act data, https://ope.ed.gov/athletics/api/dataFiles/file?fileName=EADA_2024-2025.zip (the download the site's Data File page links; https://ope.ed.gov/robots.txt redirects to an ed.gov page, so no rule applies), fetched 2026-10-08. The 12 MB archive is not committed; re-download it to rerun the extract.
- `noaa/climate_normals_by_school.csv` (`scripts/fetch_climate_normals.py`): NOAA NCEI 1991-2020 monthly climate normals, February-May mean temperature, days with 0.01" or more of precipitation and precipitation, at the nearest normals station with both (station id, name, distance), for every campus. Source: NCEI Search and Data access services, https://www.ncei.noaa.gov/access/services/search/v1/data and https://www.ncei.noaa.gov/access/services/data/v1 (dataset normals-monthly-1991-2020), fetched 2026-10-08; public domain. NCEI's robots.txt disallows `/data*`, so the bulk normals files were not used; the access-services paths are outside every disallow rule. 1.5 s between requests, a descriptive User-Agent, a stop on 403/407/429 or a bot-protection page (`noaa/fetch_log.json`). The station responses are cached in `noaa/raw/data/` (gzipped JSON, committed); the search responses are not committed (rerunning refetches them).

- **Note (2026-10-08):** www.ncaa.com's robots.txt now disallows AI agents (ClaudeBot and others). Nothing more is fetched from www.ncaa.com. data.ncaa.com has no robots file and is unaffected.

