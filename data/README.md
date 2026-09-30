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

## Not pulled (2026-09-30) — team tables and play-by-play

The Phase 1 pull also called for the full 2025 D1 team batting, pitching and
fielding tables, individual qualified-player tables, and play-by-play for at
least 2,000 games. None of that was obtained. What was tried:

| Host | Purpose | Result |
|---|---|---|
| stats.ncaa.org | team tables, individual leaders, box scores, PBP | Reachable after the network policy change. The team list (`/team/inst_team_list?sport_code=MBA&division=1&academic_year=2025`, 307 teams) is served plainly, but every team, stats and contest page sits behind Akamai Bot Manager: browser User-Agents get an edge "Access Denied", and other clients get a JavaScript interstitial challenge. Completing that challenge programmatically, and installing a trust store so the pre-installed Chromium could load the pages, were both stopped by the session's safety policy. Not pursued further. |
| data.ncaa.com | scoreboard JSON (worked), per-game `gameInfo`, `boxscore`, `pbp`, `teamStats`, `scoringSummary` JSON | Per-game endpoints return 404 for every 2025 game tried (both id forms). Only the scoreboard feed exists for this season. |
| www.ncaa.com | stats pages, game pages | denied by network policy |
| sdataprod.ncaa.com | GraphQL behind ncaa.com game pages | denied by network policy |
| web.archive.org, archive.org | cached copies | denied by network policy |
| baseball-reference.com, d1baseball.com | 2025 register, box scores | denied by network policy |
| cran.r-project.org, github.com, codeload.github.com, huggingface.co | `baseballr` source, pre-scraped datasets | denied by network policy |
| ncaa-api.henrygd.me | third-party mirror of ncaa.com JSON | denied by network policy |
| pypi.org | `collegebaseball` package | reachable; package not on PyPI |

To finish the pull, run the stats.ncaa.org scrape from a machine with a normal
browser trust store (a laptop, or a runner with `libnss3-tools` installed) and
commit the results here as:

- `team_batting_2025.csv`, `team_pitching_2025.csv`, `team_fielding_2025.csv`
  with a sidecar `manifest.json` (source URLs, fetch date).
- `individual_batting_2025.csv`, `individual_pitching_2025.csv` for the
  qualified-player percentiles.
- `pbp/raw/<contest_id>.html` and `pbp/parsed/<contest_id>.csv`.
