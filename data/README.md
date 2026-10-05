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

## data/ncaa_2025/rosters/ — 2025 rosters with bats/throws (to be supplied)

- Produced by `tools/fetch_rosters.py`, run by the GitHub Actions workflow `fetch rosters` (`.github/workflows/fetch_rosters.yml`, started by hand from the Actions tab), which commits this folder to a new branch and opens a pull request; the fetch date is in the commit message and the run summary. One CSV: team_ncaa_id, team, name, jersey, position, class, bats, throws, source_url (see `tools/README.md`). Scope: the 283 teams in the WMT play-by-play sample (`tools/roster_teams.csv`). Phase 3 (handedness) starts once it is committed here.

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

- **Source:** NCAA.com D1 baseball national leader pages,
  `https://www.ncaa.com/stats/baseball/d1/{year}/individual/{stat}`, page 1 (top 50
  and ties) for stats 470 (HR), 200 (BA), 205 (ERA), 356 (SO) and 863 (appearances),
  URL years 2023–2025. NCAA.com labels a season by the academic year it starts, so
  /2023/ is the 2024 season, /2024/ is 2025 and /2025/ is 2026 (/2022/ has no tables).
  robots.txt allows /stats/. Fetched 2026-10-01, one page per request. The 2023 season
  is transcribed from the NCAA record book's 2023 leaders
  (`http://fs.ncaa.org/Docs/stats/baseball_RB/2024/D1.pdf`).
- **Team pages:** `https://www.ncaa.com/stats/baseball/d1/{year}/team/{stat}`, page 1 (top 50)
  for stats 210 (batting average), 211 (ERA) and 323 (home runs per game), URL years 2023–2025
  (/2022/ has no tables). Fetched 2026-10-04, one page per request (robots.txt allows /stats/).
  The year mapping is checked against the 2025 scoreboard: the /2024/ table's games match each
  listed team's 2025 games (Coastal Carolina 69, Georgia 60, Northeastern 60).
- **Files:** `raw/s<stat>_<url year>.html.gz` and `raw_team/s<stat>_<url year>.html.gz` untouched
  pages; `ncaa_leaders.json` the parsed tables plus top-five values, HR threshold counts and each
  season's team leaders (`scripts/parse_ncaa_leaders.py`).
- **Used by:** `scripts/write_leader_benchmarks.py` (benchmark blocks `individual_leaders_2023_2026`
  and `team_leaders_2024_2026`, Phase 2 gate rows) and `scripts/audit_leaders.py`
  (`reports/leaders_audit.md`).

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

- `rpi/ncaa_rpi_through_2026-05-24.html.gz`: https://www.ncaa.com/rankings/baseball/d1/rpi,
  fetched 2026-10-05; the page reads "Through Games May. 24 2026". Parsed to
  `rpi/ncaa_rpi_through_2026-05-24.csv` (rank, school, record, conference, road,
  neutral, home, non_d1, prev; W-L strings as published, 308 schools; `record` is
  the D1 record, road + neutral + home).
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
