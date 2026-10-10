# Phase 8–11 data requests (owner decisions 2026-10-08; data-prep session 2026-10-10)

Items 1–3 are low priority and optional. Nothing here blocks the variance stage or any built phase.
Items 4–8 were added by the Phase 8–11 yardstick session (`reports/phase8_11_yardstick.md`): what the
cloud session could not reach and what only Jordan can export or ask for.

**Item 2 (Baseball-Reference exports) is no longer needed.** The MLB Stats API
(`https://statsapi.mlb.com/api/v1/draft/<year>`, MLB's own feed, no terms problem) lists every pick
2021–2026 with school, class, slot value and signing bonus; `tools/fetch_mlb_draft.py` builds the signing
rates by round and type and the picks by D1 program from it (`data/mlb_draft/`, grade A/B). Item 2 is kept
below only as a cross-check if ever wanted.

## 1. NCAA GOALS study: baseball tables (email for the owner to send)

**To:** research@ncaa.org
**Subject:** Request for baseball-specific tables from the 2025 GOALS study

> Hello,
>
> I am building a personal, non-commercial college baseball simulation that is calibrated to published NCAA data. The 2025 GOALS study slides for Division I report the factors in college choice for all men's sports combined. The survey instrument also asks about recruiting timing: the grade of first recruiting contact (Q48) and the grade of commitment (Q49).
>
> Would you be able to share aggregate tables for **baseball** (Division I, and Divisions II and III if available)? Specifically:
>
> 1. **College-choice factors:** the share of baseball student-athletes rating each factor important (chance to play, academics, cost, facilities, proximity to home, the coach, exposure, professional development, NIL and the others in the instrument). Split by first-time enrollees and transfers if possible.
> 2. **Recruiting timing:** the grade of first recruiting contact and the grade of commitment, as distributions.
> 3. **Transfers:** reasons for transferring, for baseball transfers.
> 4. **Decommitments:** if available, the share who verbally committed to one school and enrolled at another.
>
> I only need aggregate shares, with no individual responses. If a table exists only for a broader group (e.g. Division I men's team sports), that would still help. I'm happy to cite the NCAA GOALS study in my project notes as the source.
>
> Thank you,
> [Your name]

When the reply arrives:
- the tables go to `data/ncaa_goals/`, with the reply's date and terms in `data/README.md`;
- they replace the all-men's-sports shares in the spec (Section 12.2) as the calibration target for priority weights and commit timing.

## 2. Baseball-Reference draft exports (optional, by hand, later)

**Why:** MLB draft signing rates by round and by player type, which set the "current" ruleset's signability (spec Section 8). Today they are a grade-C fan summary.

**Terms:**
- Baseball-Reference's terms forbid automated access and tools built on scraped data, so these exports are made by hand in a browser.
- Use the site's "Share & Export → Get table as CSV".
- Respect its limit of 20 requests a minute, which applies to manual browsing too.
- Only aggregate counts are committed: no player names or rows, as with the rosters.

**Pages:** the draft round pages, one per year and round, at
`https://www.baseball-reference.com/draft/?year_ID=<YEAR>&draft_round=<ROUND>&draft_type=junreg&query_type=year_round`
for:
- **years 2022–2025** (the 20-round era; 2021 also had 20 rounds and can be added);
- **rounds 1–20.**

That is 80 pages, plus the supplemental and competitive-balance rounds, which appear as separate round codes on the same page type ("1C", "2C" and so on).

**Fields to keep from each export:**

| Field | Use |
|---|---|
| Year | Grouping |
| Rnd (round, including supplemental codes) | Signing rate by round |
| OvPck (overall pick) | Pick value from the slot tables |
| Type (HS / 4Yr / JC) | Signing rate by player type |
| Signed (Y/N) | The signing rate |
| Bonus | Signability against the slot value (rounds 1–10) and the $150,000 rule (rounds 11–20) |
| Drafted out of (school) | Only to classify four-year picks by D1 tier and conference through `data/ncaa_2025/pbp/teams_2025.csv`; dropped after aggregation |

**What gets committed** (`data/mlb_draft/signing_by_round.csv`, built by a script from the hand exports, which are not committed):
- signed and unsigned counts by year × round × type;
- the median bonus as a share of the slot value by round band;
- four-year picks by D1 tier.

## 3. NJCAA team stats (optional, by hand, the owner)

- **Today:** JUCO sits on the talent scale from roster origins plus documented guesses, graded D and marked for replacement (spec Section 7). No usable JUCO source is reachable from the cloud environment:
  - NJCAA stats sit behind a client-rendered app on an undocumented API;
  - the Presto region and CCCAA sites return 403.
- **The upgrade:** a hand export by the owner of the NJCAA composite **team** stats for Divisions I, II and III, if njcaa.org's terms allow personal use:
  - batting, pitching and fielding team tables for the 2025 season (2024 and 2026 too, if available);
  - about 3 divisions × 2–3 tables per season.
- **What it gives:**
  - JUCO league rates (BA, OBP, SLG, K, BB, HR) and team runs per game;
  - with transfers' outcomes, an estimate of the JUCO talent offset;
  - the JUCO grade would rise from D to B.
- Team-level tables only; no player rows are committed.


## 4. Re-run the roster workflow on the 2026 rosters (Actions, by hand)

- **Why:** the 2025 aggregates are the last pre-roster-limit season. Phase 8's gate rows (roster size,
  class shares, JUCO and transfer shares) need the first season under the 34-man limit, and the JUCO share
  after the cuts is unmeasured anywhere public.
- **How:** `tools/fetch_rosters.py` fixes the 2025 paths (`PATHS`); add a `--season 2026` option (the
  roster URLs become `/sports/baseball/roster/2026`, `/sports/bsb/roster/season/2026`, ...) and an output
  folder `data/ncaa_2026/roster_aggregates/`, then run the **fetch rosters** workflow from the Actions tab.
  About 4 hours. Only aggregates are committed, as now.
- **Also:** the run of 2026-10-10 on branch `claude/phase8-11-yardstick` (run 38066352243) adds
  `class_detail_by_tier.csv` (class x redshirt x position), `d1_transfer_flow.csv` (the P4 / mid / low
  tier of each D1 transfer's previous school) and `age_by_class.csv` (where a page lists a birthdate) for
  2025; it opens a pull request into that branch when it finishes. Merge it to main.

## 5. NJCAA: ask for the composite team-stat tables (email)

The NJCAA stats site is a client-rendered app whose API refuses public queries ("Not Authorized"), and
`stats.njcaa.org` returns 502 from the cloud environment. The conference proxies in
`data/phase8_11/d2_juco_league_rates_2025.csv` (KJCCC, ACCC, ICCAC, CCCAA, NWAC) stand in. A hand export of
the NJCAA D1/D2/D3 composite team batting and pitching tables for 2025 (and 2024, 2026), if the site's terms
allow personal use, would raise the JUCO league rates from B-by-proxy to A. Team tables only.

**To:** sports information at njcaa.org (the contact on the baseball page)
**Ask:** the season composite team batting and pitching statistics by division for 2025 (CSV or the page
export), and, if they keep it, the count of NJCAA baseball players who signed with NCAA Division I programs
by year (their "alumni in the NCAA tournament" release of 2026-05-29 counted 570+ in the 64-team field).

## 6. D2 → D1 transfer counts (NCAA Research, email)

No public table gives four-year transfers by division of origin and destination for baseball. The NCAA's
transfer dashboards are Tableau embeds without a download. Add to the GOALS email (item 1) or send
separately to research@ncaa.org: "the number of baseball student-athletes who transferred from a Division
II to a Division I program (and D1 to D2, D1 to D1) in each of the 2022–2026 portal cycles, and the share of
baseball portal entrants by division of origin who enrolled at a D1, D2, D3, NAIA or two-year school."

## 7. GOALS tables (item 1 above): add two asks

To the email of item 1 add: (a) the age distribution of baseball student-athletes by class year (the
age-based eligibility clock needs it; roster pages carry no birthdates), and (b) the share of baseball
freshmen who were redshirted or gray-shirted.

## 8. Massey Ratings (browser, by hand)

masseyratings.com returns 403 to the cloud environment. Its college baseball ratings place D1, D2, D3
and NAIA teams on one scale. In a browser: Massey Ratings → College Baseball → the 2025 season, all
divisions, export the rating table (team, division, rating). Commit team-level ratings only to
`data/phase8_11/massey_2025.csv` with the fetch date. It gives the D2 and NAIA talent offset directly
(grade B), replacing the 90-game crossover margin (grade C).
