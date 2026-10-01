# tools/

## fetch_rosters.py: 2025 rosters with bats/throws (Phase 3 input)

This fetches 2025 baseball roster pages for the 283 teams in the WMT play-by-play sample (`roster_teams.csv`, busiest teams first). It writes one CSV with each player's bats and throws. Athletics sites block cloud machines, so run it on your own computer.

### Run it

```
cd College-Baseball-Sim            # repo root, on main
pip install requests               # the only dependency (Python 3.9+)
python tools/fetch_rosters.py --selftest      # offline parser check, should print "selftest passed"
python tools/fetch_rosters.py --only 596583   # one team (LSU) to try it
python tools/fetch_rosters.py                 # everything; about 30-60 minutes
```

- **Pace:** it waits at least 3 seconds between requests (`--delay 5` to go slower) and obeys each site's robots.txt, including Crawl-delay.
- **Interrupting:** stop it any time with Ctrl-C. Rerunning skips teams already done.
- **Retrying:** `--retry-failed` tries the teams that failed again.
- **Fixing a domain:** if a team failed for lack of a domain, or the domain is wrong, edit `domain` in `tools/roster_teams.csv` and rerun with `--only <team_ncaa_id>`. The 14 rows marked `unverified` and the 4 marked `missing` were not screened.

### Output (in `data/ncaa_2025/rosters/`)

| File | What |
|---|---|
| `rosters_2025.csv` | One row per player: `team_ncaa_id, team, name, jersey, position, class, bats, throws, source_url, wmt_person_id`. `bats` is L, R or S (switch), `throws` is L or R. `wmt_person_id` is filled only for WMT Digital sites and lets the play-by-play join on IDs instead of names. |
| `raw/<team_ncaa_id>.html.gz` | Every roster page fetched, so a team whose layout the parser missed can be parsed later without fetching again. |
| `failures.csv` | Teams it could not fetch or parse, with the reason for each URL tried. |
| `fetch_rosters.log`, `state.json` | Request log and progress. |

### Then

Commit the whole `data/ncaa_2025/rosters/` folder, raw pages included, and push. Failures are expected: some sites use layouts the three parsers (HTML table, embedded JSON, roster cards) don't know, and some will block or 404. The raw pages let those be handled in the cloud session. Add the date you ran it to the commit message; it goes into `data/README.md` as the fetch date.
