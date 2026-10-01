# tools/

## fetch_rosters.py: 2025 rosters with bats/throws and player origins (Phase 3 and Phase 9 input)

This fetches 2025 baseball roster pages for the 283 teams in the WMT play-by-play sample (`roster_teams.csv`, busiest teams first). It writes one CSV with each player's bats and throws (Phase 3 handedness), and with hometown, high school and previous school where the page lists them (Phase 9: regional recruiting and the JUCO/D2 transfer portal). Athletics sites block most cloud machines, so run it on your own computer.

### Run it

```
cd College-Baseball-Sim            # repo root, on main
pip install requests               # the only dependency (Python 3.9+)
python tools/fetch_rosters.py --selftest      # offline parser check, should print "selftest passed"
python tools/fetch_rosters.py --only 596583   # one team (LSU) to try it
python tools/fetch_rosters.py                 # everything; about 30-60 minutes
```

**Already ran the earlier version?** Your `rosters_2025.csv` lacks the origin columns, and the script will stop and say so. Run `python tools/fetch_rosters.py --reparse` once: it rebuilds the CSV from the saved `raw/` pages without fetching anything (the old file is kept as `rosters_2025.old.csv`). Then rerun as normal to continue with any teams not yet done.

- **Pace:** it waits at least 3 seconds between requests (`--delay 5` to go slower) and obeys each site's robots.txt, including Crawl-delay.
- **Interrupting:** stop it any time with Ctrl-C. Rerunning skips teams already done.
- **Retrying:** `--retry-failed` tries the teams that failed again.
- **Fixing a domain:** if a team failed for lack of a domain, or the domain is wrong, edit `domain` in `tools/roster_teams.csv` and rerun with `--only <team_ncaa_id>`. The 14 rows marked `unverified` and the 4 marked `missing` were not screened.

### Output (in `data/ncaa_2025/rosters/`)

| File | What |
|---|---|
| `rosters_2025.csv` | One row per player: `team_ncaa_id, team, name, jersey, position, class, bats, throws, hometown_city, hometown_state, high_school, previous_school, source_url, wmt_person_id`. `bats` is L, R or S (switch), `throws` is L or R. The origin columns are blank when the page doesn't list them. `hometown_state` is as written on the page ("La.", "Texas", "Ontario, Canada"). `previous_school` is the school before this one, a junior college or a four-year school, as the page names it; classifying it (JUCO, D1, D2, NAIA) is left for Phase 9. `wmt_person_id` is filled only for WMT Digital sites and lets the play-by-play join on IDs instead of names. |
| `raw/<team_ncaa_id>.html.gz` | Every roster page fetched, so a team whose layout the parser missed can be parsed later without fetching again. |
| `failures.csv` | Teams it could not fetch or parse, with the reason for each URL tried. |
| `fetch_rosters.log`, `state.json` | Request log and progress. |

### Then

Commit the whole `data/ncaa_2025/rosters/` folder, raw pages included, and push. Failures are expected: some sites use layouts the three parsers (HTML table, embedded JSON, roster cards) don't know, and some will block or 404. The raw pages let those be handled in the cloud session. Add the date you ran it to the commit message; it goes into `data/README.md` as the fetch date.
