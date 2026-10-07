# tools/

## fetch_rosters.py: 2025 rosters with bats/throws and player origins (Phase 3 and Phase 9 input)

This fetches 2025 baseball roster pages for the 283 teams in the WMT play-by-play sample (`roster_teams.csv`, busiest teams first). It writes one CSV with each player's bats and throws (Phase 3 handedness), and with hometown, high school and previous school where the page lists them (Phase 9: regional recruiting and the JUCO/D2 transfer portal).

### Run it in GitHub Actions (no local setup)

On GitHub: the repository's **Actions** tab → **fetch rosters** in the left list → **Run workflow** (top right of the run list) → choose the branch to commit the aggregates to and leave the delay at 3 → **Run workflow**. The job (`.github/workflows/fetch_rosters.yml`, up to 3 hours) installs `requirements.txt`, runs both self-tests (`fetch_rosters.py --selftest`, `aggregate_rosters.py --selftest`), then `--probe 5` (a few roster pages across Sidearm, WMT Digital and PrestoSports; the run summary shows counts by platform and status), then the full fetch with the same robots.txt rules and delays into the runner's temporary directory, then `aggregate_rosters.py`. Only the aggregate tables in `data/ncaa_2025/roster_aggregates/` are committed, to the branch the workflow was run on; no pull request is opened. The raw fetch (`rosters_2025.csv` with names, `raw/` pages, `state.json`, the log) never leaves the job: it is not committed, not uploaded as an artifact and not cached. Sites behind bot protection are logged and skipped, and so are hosts whose robots.txt asks for a Crawl-delay over 60 s and responses that take more than 90 s in all (a slow drip is treated as a block); the probe step has a 20-minute limit. If the fetch reaches its time limit it stops cleanly and the partial result is aggregated and committed (`coverage.csv` counts the teams not attempted); since nothing raw is kept between runs, a later run fetches every team again.

### Or run it on your own computer

```
cd College-Baseball-Sim            # repo root, on main
pip install requests               # the only dependency (Python 3.9+)
python tools/fetch_rosters.py --selftest      # offline parser check, should print "selftest passed"
python tools/fetch_rosters.py --only 596583   # one team (LSU) to try it
python tools/fetch_rosters.py --probe 5       # which platforms answer, which block
python tools/fetch_rosters.py                 # everything; about 30-60 minutes (output in data/ncaa_2025/rosters/, git-ignored)
```

**Already ran the earlier version?** Your `rosters_2025.csv` lacks the origin columns, and the script will stop and say so. Run `python tools/fetch_rosters.py --reparse` once: it rebuilds the CSV from the saved `raw/` pages without fetching anything (the old file is kept as `rosters_2025.old.csv`). Then rerun as normal to continue with any teams not yet done.

- **Pace:** it waits at least 3 seconds between requests (`--delay 5` to go slower) and obeys each site's robots.txt, including Crawl-delay.
- **Interrupting:** stop it any time with Ctrl-C. Rerunning skips teams already done.
- **Retrying:** `--retry-failed` tries the teams that failed again.
- **Fixing a domain:** if a team failed for lack of a domain, or the domain is wrong, edit `domain` in `tools/roster_teams.csv` and rerun with `--only <team_ncaa_id>`. The 14 rows marked `unverified` and the 4 marked `missing` were not screened.

### Output (in `data/ncaa_2025/rosters/`)

| File | What |
|---|---|
| `rosters_2025.csv` | One row per player: `team_ncaa_id, team, name, jersey, position, class, bats, throws, hometown_city, hometown_state, high_school, previous_school, source_url, wmt_person_id`. `bats` is L, R or S (switch), `throws` is L or R. The origin columns are blank when the page doesn't list them. `hometown_state` is as written on the page ("La.", "Texas", "Ontario, Canada"). `previous_school` is the school before this one, a junior college or a four-year school, as the page names it; `tools/aggregate_rosters.py` classifies it (high school, JUCO, D1 transfer, other four-year). `wmt_person_id` is filled only for WMT Digital sites; it does not join to the committed play-by-play, whose `batter_id` and `pitcher_id` are per-game ids (`game_player_id`), so the aggregation matches players by name within team. |
| `raw/<team_ncaa_id>.html.gz` | Every roster page fetched, so a team whose layout the parser missed can be parsed later without fetching again. |
| `failures.csv` | Teams it could not fetch or parse, with the reason for each URL tried. |
| `fetch_rosters.log`, `state.json` | Request log and progress. |
| `probe.md`, `probe.json` | The `--probe` result: platform and status (parsed, blocked, failed) per site tried. |

### Then: aggregate, and commit only the aggregates

Owner decision 2026-10-07: the game never uses real players, and only aggregated tables are committed (counts and shares by school, conference, region, position and handedness), never player names or individual rows. `data/ncaa_2025/rosters/` is in `.gitignore`. After a local fetch:

```
pip install -r requirements.txt
python tools/aggregate_rosters.py --in data/ncaa_2025/rosters      # writes data/ncaa_2025/roster_aggregates/
git add data/ncaa_2025/roster_aggregates                          # commit these only
```

`aggregate_rosters.py` joins roster hands to the committed play-by-play by name inside the script and writes counts and shares only; it scans every file it wrote for roster names and fails (deleting its output) if it finds one. `python tools/aggregate_rosters.py --selftest` runs the whole aggregation on synthetic rosters built from the play-by-play names. The tables, the classification rules and their confidence grades are in `data/README.md`.
