# data/

Scraped NCAA tables and play-by-play are committed here, not re-fetched each
session. Every file records its source URL and fetch date.

## data/phase0/conf2025.csv

- **Source:** FanGraphs, Michael Baumann, "The Ridiculous Firewagon Offenses of
  College Baseball" (Feb 13, 2026), per-conference 2025 table sourced from
  Baseball-Reference. https://blogs.fangraphs.com/the-ridiculous-firewagon-offenses-of-college-baseball/
- **Fetched:** 2026-09-29 (Phase 0, transcribed by hand).
- **Used by:** `derive.py` and the conf B entries in `benchmarks.json`.

## data/ncaa_2025/ (EMPTY — Phase 1 pull blocked)

Intended contents: 2025 D1 team batting, pitching and fielding tables for all
~303 teams from stats.ncaa.org, plus raw and parsed play-by-play for at least
2,000 games.

**Attempted 2026-09-30. Nothing was pulled.** The session's network policy
denies every data host. Each attempt below returned `CONNECT tunnel failed,
response 403` from the egress proxy (a policy denial, not a rate-limit or a
site block), both through `curl` in the container and through the separate
WebFetch fetcher:

| Host | Purpose | Result |
|---|---|---|
| stats.ncaa.org | team tables, individual leaders, box scores / PBP | denied |
| www.ncaa.com, data.ncaa.com | scoreboard and box score JSON | denied |
| web.archive.org, archive.org | cached copies of the above | denied |
| ncaa-api.henrygd.me | third-party mirror of ncaa.com JSON | denied |
| www.baseball-reference.com | 2025 D1 register | denied |
| d1baseball.com | box scores | denied |
| cran.r-project.org, github.com, codeload.github.com | `baseballr` source | denied |
| huggingface.co | pre-scraped datasets | denied |
| pypi.org | `collegebaseball` package | reachable, but the package is not on PyPI (404) |
| raw.githubusercontent.com | raw files in public repos | **reachable** |

To unblock: allow `stats.ncaa.org` (and ideally `www.ncaa.com`,
`data.ncaa.com`) in the environment's network settings, or run the pull from a
machine with open egress and commit the results here.

When the pull runs, save:

- `team_batting_2025.csv`, `team_pitching_2025.csv`, `team_fielding_2025.csv`
  with `source_url` and `fetched` columns or a sidecar `manifest.json`.
- `pbp/raw/<game_id>.html|json` and `pbp/parsed/<game_id>.csv`.
- `individual_batting_2025.csv`, `individual_pitching_2025.csv` for the
  qualified-player percentiles.
