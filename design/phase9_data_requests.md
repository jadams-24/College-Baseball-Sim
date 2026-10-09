# Phase 9 data requests (owner decisions 2026-10-08)

Both are low priority and optional. Nothing here blocks the variance stage or any built phase.

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

