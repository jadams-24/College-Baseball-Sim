# Phases 8–11 — The yardstick (data-prep notes)

`benchmarks_phase8_11.json` is the definition of "realistic" for roster rules, recruiting, development and
program building, the way `benchmarks.json` is for the on-field engine. It is built by
`tools/build_phase8_11_yardstick.py` from committed aggregates plus the hand-researched entries in
`data/phase8_11/manual_entries.json`. Every entry carries its source URL, fetch date, sample size and a
confidence grade (A official or primary, directly usable; B public, usable after processing; C partial or
a proxy; D no data, a GUESS). Nothing here feeds the engine; the Phase 8–11 gates read it
(`design/phase9_recruiting.md`, Section 13). The summary is `reports/phase8_11_yardstick.md`.

Session rules (owner, 2026-10-10): this session touches only `data/`, `design/`, `reports/`, `tools/`,
this file and the benchmarks file; aggregated tables only, never player names or rows; nothing is fetched
from www.ncaa.com.

## 1. Rule and calendar check (2026-10-10)

Sources read in full: the 2026-27 Division I baseball recruiting calendar
(https://ncaaorg.s3.amazonaws.com/compliance/recruiting/calendar/2026-27/2026-27D1Rec_MBARecruitingCalendar.pdf,
"Updated: July 30, 2026") and the 2026-27 Division I Manual as published by LSDBi on 2026-10-10
(https://web3.ncaa.org/lsdbi/reports/getReport/90008, page footers dated 10/10/26). Grade A for every
row below. Each spec date was checked against the bylaw text, not a secondary guide.

**Calendar, 2026-27 (Bylaw 13.17.1, revised 4/17/25; the PDF agrees with the formulas):**

| Period | 2025-26 (spec) | 2026-27 (verified) | Formula |
|---|---|---|---|
| Contact | Aug 1–17 | Aug 1–16 | March 1 through the Sunday before the third Monday of August |
| Quiet | Aug 18 – Sep 11 | Aug 17 – Sep 10 | third Monday of August through the second Thursday of September |
| Contact | Sep 12 – Oct 12 | Sep 11 – Oct 11 | Friday after the second Thursday of September through the second Sunday of October |
| Quiet | Oct 13 – Feb 28 | Oct 12 – Feb 28, 2027 | Monday after the second Sunday of October through February |
| Dead (signing week) | Nov 10–13 | Nov 9–12 | Monday–Thursday of the week of the initial signing date |
| Recruiting Shutdown | Nov 25–30 | Nov 24–29 | Tuesday before Thanksgiving through the Sunday after |
| Recruiting Shutdown | Dec 22–27 | Dec 22–27 | fixed |
| Dead (ABCA) | Jan 8–11 | Jan 7–10 | the convention's official days |
| Contact | Mar 1 – Jul 31 | Mar 1 – Jul 31 | March 1 through mid-August (see first row) |
| Dead | May 25 – Jun 1 | May 31 – Jun 7 | last Monday in May through the following Monday |
| Dead | Jun 20–22 | Jun 19–21 | Saturday before Father's Day through the Monday after |
| Dead | Jul 3–5 | Jul 3–5 | fixed |

Nothing changed in the formulas. One correction to the spec's wording: the contact period that "ends
July 31" in the spec's table actually runs through the Sunday before the third Monday of August, so the
August 1 rush sits inside a contact period that began March 1 (the spec's own first row already says
Contact Aug 1–17; the "Mar 1 – Jul 31" row should read "Mar 1 – Aug 16/17").

**Rules (bylaw, status on 2026-10-10):**

| Item | Spec (Section 12.1) | Manual 2026-27 | Change? |
|---|---|---|---|
| Calls to or from a prospect | from Aug 1 of the junior year | 13.1.3.2.3 (baseball): no calls received before Aug 1 at the beginning of the junior year (adopted 4/26/23) | none |
| Recruiting materials, electronic correspondence | Aug 1 of the junior year | 13.4.1.1 (baseball), adopted 4/26/23 | none |
| Off-campus contact | Sep 1 of the junior year | 13.1.1.1.1 (baseball), revised 6/24/26: still Sep 1 of the junior year | wording only |
| Official visits | Sep 1 of the junior year | 13.6.2.1.2 (baseball and women's lacrosse), revised 6/24/26 and 6/29/26: Sep 1 of the junior year | none |
| Unofficial visits with athletics involvement | Sep 1 of the junior year | 13.7.1.2, revised 6/24/26, 6/29/26: Sep 1 of the junior year | none |
| Official visits per school | one before Oct 15 after high school, one after; one more after a head-coach change | 13.6.2.2 and 13.6.2.2.1 | none |
| Written offers of aid or a settlement-related benefits agreement | not before Aug 1 of the senior year | 13.9.3.1, revised 10/8/25 | none |
| Signing date | second Wednesday in November, 7 a.m. (Nov 12, 2025; Nov 11, 2026) | 13.02.13.1(f): the second Wednesday (7 a.m.) in November for all other sports; undergraduate transfers from the first day (7 a.m.) of their notification-of-transfer period, postgraduate transfers from Oct 1 (13.02.13.2) | none |
| Signed prospect: other schools stop contact | yes, with five releases | 13.1.1.2 and 13.1.1.2.1 (a)–(e): aid reduced or cancelled, academically ineligible, not enrolled full time, a release requested within 30 days of the head coach's departure, or a granted release (two business days to answer, default grant) | none |
| Roster limit 34, due the day before the first counted contest or Dec 1 | yes | 17.2 (adopted 6/6/25 effective 7/1/25) and 17.2.1 (adopted 6/23/25); only the women's flag football limit was revised (8/25/26) | none |
| Portal windows | Dec 1–15 and 30 days from seven days after selections | 13.1.1.4.1(h), spring sports other than golf, outdoor track and softball; the bylaw was revised repeatedly through 10/8/26 but the baseball windows are unchanged | none |
| Portal exceptions | head coach leaves (30 days); aid reduced (30 days, from 1/14/26); grad transfers | 13.1.1.4.1.1.1(a) head-coach departure, 30 consecutive days; 13.1.1.4.2.1 postgraduates may use the undergraduate exceptions | none found |
| Eligibility clock | five years from the earlier of first full-time enrollment or the academic year after the 19th birthday; no waivers | 12.6, revised 6/24/26 effective 8/1/26 **and 9/9/26**: new 12.6.1 (a 19th birthday between Sep 1 and Dec 31 starts the clock the following fall), 12.6.2 (enrollment between May 1 and Nov 1 starts the clock that fall; Nov 1 to May 1 starts it the next regular term), 12.6.3 (a clock ending with a fall term runs to the day before the spring term; a championship that starts inside the period extends it to the team's last game); 12.6.10 no waivers | **clarified 9/9/26: add the three sub-rules to the Phase 8 clock** |
| Incremental scholarships above the 2024-25 limits | count against the cap up to $2.5M | 16.13.1.5 | none |

Not re-verified here (outside the Manual): the revenue-share cap for 2026-27, the MLB draft rules and
the GOALS tables; see the draft and portal sections.

## 2. Roster composition, 2025 (roster aggregates)

Source: `data/ncaa_2025/roster_aggregates/` (the fetch of 2026-10-09: 233 of 283 WMT-sample teams parsed,
8,620 players; 50 P4, 122 mid, 60 low schools; tiers from `pbp/teams_2025.csv`). These are spring 2025
rosters, the last season before the 34-man limit (effective 7/1/25), so roster sizes are a "before"
baseline; the first "after" season (2026) needs a new fetch (`design/phase9_data_requests.md`, item 4).
Computed by `tools/build_phase8_11_yardstick.py` into `benchmarks_phase8_11.json`
(`roster_composition_2025`) and `data/phase8_11/`.

- **Class shares** (listed class, redshirt markers dropped; `Gr` = graduate or 5th/6th year):

| Tier | Players | Fr | So | Jr | Sr | Gr | unknown |
|---|---|---|---|---|---|---|---|
| P4 | 2,020 | .290 | .219 | .281 | .158 | .050 | .003 |
| Mid | 4,524 | .255 | .201 | .286 | .195 | .044 | .019 |
| Low | 2,033 | .220 | .193 | .290 | .224 | .042 | .032 |
| All | 8,577 | .255 | .204 | .286 | .193 | .045 | .018 |

  Grade B (listed class strings; the redshirt flag and class by position come with the next roster run,
  `class_detail_by_tier.csv`). P4 rosters are younger (more freshmen, fewer seniors): the draft and the
  portal take P4 juniors.
- **Roster size** (players listed): P4 40.4 ± 3.4 (p10–p90 36–44), mid 37.1 ± 7.1, low 33.9 ± 9.3.
  The mid and low spread includes partially parsed pages (minimum 5), so the P4 figure is the clean one;
  grade B for P4, C for mid and low. 94% of P4 rosters exceeded 34 in spring 2025.
- **Pitchers**: share of listed players whose position is a pitcher .506 (P4), .489 (mid), .475 (low);
  with two-way players .536 / .523 / .504. Grade B.
- **Age**: no roster page in the 2025 fetch is known to list a birthdate (the fetcher now keeps one when
  a page does; `coverage.csv` will say how many). Age by class is therefore GUESS (D), built from the
  class shares plus the redshirt share and the usual 18-year-old freshman: see the yardstick report.

## 2a. Roster run of 2026-10-10 (run 38066352243)

The fetch rosters workflow rerun on the Phase 8 aggregator added `class_detail_by_tier.csv` (class x
redshirt marker x position group), `d1_transfer_flow.csv` (tier of each D1 transfer's previous school) and
`age_by_class.csv` (empty: no page lists a birthdate; `share_birthdate_or_age_filled` = 0). 233 teams and
8,620 players, as in the run of 2026-10-09. Results in the report, sections 1 and 2;
`roster_composition_2025.redshirt_by_class`, `.class_by_position` and `.d1_transfer_flow` in the benchmarks
file. The workflow pushed its branch but could not open a pull request (Actions may not create them), so
the four files were cherry-picked onto the round-2 branch.

## 3. Geography, 2025 (roster aggregates, IPEDS school states)

`geography_2025` in the benchmarks file; `data/phase8_11/players_by_home_state_2025.csv` (where each
state's players go, by tier) and `in_state_share_by_school_state_2025.csv` (how in-state the schools of
each state are). Grade B (state-level hometowns). The tier-level in-state shares match
`reports/proximity_2025.md` (P4 .427, mid .457, low .386).

## 4. Development and retention, 2022–2026 (WMT player seasons)

`tools/fetch_wmt_player_seasons.py`; aggregates in `data/wmt_player_seasons/` (fetched 2026-10-10). The
WMT stats API (`/api/statistics/teams?season_id=<id>`; `/teams/<id>/players?with[]=season_stats`)
lists, for each client school and season, every rostered player's season totals with class, position
and a person id that persists across seasons and schools, so consecutive seasons of the same player can
be paired without names leaving the working directory. Season ids: 2022 15860, 2023 16340, 2024 16580,
2025 16840, 2026 17040 (probed). Coverage is WMT's client list (51 D1 programs a season: 34–37 P4,
12–16 mid, 1 low), so the curves are "players who stayed in the WMT world": survivors.

Method. Rates per PA (batters: PA = AB + BB + HBP + SF + SH) or per BF (pitchers); a pair is the same
person in consecutive seasons with 50+ PA or 50+ BF in both (GUESS: the floor). Changes on the logit
scale for rates (smoothed (x + .5) / (n + 1)) and raw for ERA, SLG, ISO and OPS; mean, SD, SE and a
precision-weighted mean per class in the first season, also by tier and by first-season playing-time
tercile (the regression-to-the-mean diagnostic). Retention: a player-season's status the next season
(same program by name, another client program, absent), by class, tier, role x tercile and played /
rostered. Results in `reports/phase8_11_yardstick.md`, section 6; `development_2022_2026_wmt` in the
benchmarks file. Grade B for the shapes, C for the levels.

Findings to carry into Phase 10's gate design:
- Hitters: OPS +.059 Fr→So (K% −.10 logit, BB% +.09, HR% +.18), about +.025 a year afterwards,
  −.033 for fifth-years. Pitchers: K% +.07 logit and BB% −.07 Fr→So, flat afterwards.
- Regression to the mean is as large as the development signal (bottom-third freshmen +.087 OPS, top
  third +.046; top-third juniors −.014): the gate must compare like with like (the sim's survivors on
  the same selection), not the marginal curve against a true-talent change.
- Retention to the same program: Fr .60, So .63, Jr .49, Sr .12; the 2026 roster limit cut freshman
  retention to .525 and the P4 stat roster from 41.4 to 38.8.

## 4a. Transfer portal (NCAA Research dashboards)

The NCAA's DI and DII transfer-portal dashboards and the transfer-composition dashboard (Tableau Public,
NCAA Research) can be filtered to baseball; the baseball rows were pulled through the dashboards'
session API on 2026-10-10 (no download exists). `data/phase8_11/portal_ncaa_dashboard_2023_2025.csv`,
`transfer_composition_d1_baseball_2015_2024.csv`; `transfer_portal_2021_2026` in the benchmarks file;
report section 5. Grade A for 2023–2025; 2021–2022 only secondhand (C). The dashboards do not expose
month of entry (December vs June: D) or conference (P4 / mid / low: D). D2 → D1 baseball transfers
(162 / 203 / 261 in 2023–25) come from the DII dashboard's destination sheet.

## 5. Crossover games: D1 against non-D1 opponents, 2025 scoreboard

`d1_vs_non_d1_2025`: 90 finals with exactly one D1 team (after dropping TBA placeholders and the
New Orleans alias), 61 distinct non-D1 opponents, almost all tagged IND by the feed (D2, D3 and NAIA
mixed). D1 won 90%, 12.2 to 4.3 runs a game, a log run ratio of 1.05. Grade C: the opponents' level is
unknown and D1 hosted 93% of the games. A proper D2 placement needs the D2 scoreboard feed (data request).

## 6. MLB draft (MLB Stats API)

`https://statsapi.mlb.com/api/v1/draft/<year>`, MLB's own feed, lists every pick 2021–2026 with school
name, school class (HS SR, 4YR JR/SO/SR/5S/GR, JC J1–J3), slot value and signing bonus.
`tools/fetch_mlb_draft.py` matches four-year schools to the 307 D1 programs (`data/schools/schools.csv`,
`name_aliases.csv`, an alias table in the tool) on the current conference map and writes counts only to
`data/mlb_draft/`. Unsigned proxy: a pick with no bonus on file (equals MLB.com's deadline-day unsigned
counts in rounds 1–10 for 2021–2025 and Baseball America's 576 of 615 signed in 2025; an upper bound in
rounds 11–20, where bonuses are reported less completely). Validation: D1 count 428 = NCAA's 428 (2023),
432 against 431 (2025). This replaces the Baseball-Reference hand export of
`design/phase9_data_requests.md`, item 2. Report section 4; `mlb_draft_2021_2026` in the benchmarks file.

## 7. JUCO and D2 (conference team-stat pages)

`tools/fetch_d2_juco_team_stats.py` reads the team-totals tables of eight D2 conferences (Sidearm
`stats.aspx?path=baseball&year=2025`) and five junior-college leagues (PrestoSports
`/sports/bsb/2024-25/teams`) and pools them (`data/phase8_11/d2_juco_league_rates_2025.csv`). Team totals
include games against other levels; the D2 set is the hosts that answered (12 conferences returned 502,
TLS errors or 404), not a random sample. Grade B. The NJCAA national lines and NCAA's own D2 lines were
unreachable (data requests 5 and 8).

## 8. Survivor bias in the development curves (round 2, 2026-10-10)

`survivor_selection()` in `tools/fetch_wmt_player_seasons.py`. For each role, class and rate: the
season-t level of the players who enter a consecutive-season pair (survivors) against all players over
the floor in season t, and the leavers; the survivors' year-to-year correlation r; the implied
regression-to-the-mean part of the measured change, (1 − r) × (population mean − survivors' mean),
raw and on the logit scale. The rule is the first-order correction for selection on the observed
season-t value; r is the survivors' own correlation (attenuated by the selection itself), so the terms
are approximate. Results and reading: report section 9. Not applied to the curves (owner request).

## 9. Program money (EADA 2024-25)

`money_eada()` in `tools/build_phase8_11_yardstick.py`: the committed EADA baseball extract joined to
`data/schools/schools.csv` on UNITID, quantiles by tier of operating expenses, total expenses, revenue,
participants and assistant coaches, and conference medians. EADA's coaching-salary fields are
institution-level averages over all men's teams, so baseball coaching pay is not derivable from it.

## 10. Program money beyond EADA (round 2, 2026-10-10)

Web research (session subagent) on baseball-specific revenue share, scholarships, NIL, draft money, coaching
pay, attendance and public-records program finances; every row with URL, fetch date, n and grade in
`data/phase8_11/manual_entries.json` → `program_money_public_2025_26`, the MFRS table in
`data/phase8_11/mfrs_baseball_fy2025.csv`. Report section 11. The EADA User's Guide (September 2026
edition) confirms that EADA coaching salaries are institution-level averages across all men's teams.
Blocked: On3 (403), Forbes (403), the NCAA attendance page (redirects home), S3 guesses (404).

## Confidence summary

| Block | Grade | Why |
|---|---|---|
| Rules and calendar | A | Manual and calendar PDF read bylaw by bylaw |
| Roster composition, geography | B | Listed strings on 233 roster pages; state-level hometowns |
| Age by class | D | GUESS until a birthdate source exists |
| MLB draft | A/B | MLB's feed; D1 tiers by name match (validated); D2/D3/NAIA split C |
| Transfer portal 2023–25 | A | NCAA Research dashboards, baseball rows |
| Portal by conference tier, December vs June | D | Not published |
| Development curves | B/C | Survivors at 51 WMT client programs; regression to the mean sized |
| D2 and JUCO league rates | B | Conference proxies |
| JUCO → D1, D2 → D1 per year | C / A | Derived (JUCO); NCAA DII dashboard (D2) |
| D2 talent offset | C | 90 crossover games; Massey blocked |
