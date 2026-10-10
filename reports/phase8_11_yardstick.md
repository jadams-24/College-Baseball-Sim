# Phase 8–11 yardstick (data-prep session, 2026-10-10)

The benchmark set for roster rules, recruiting, development and program building, built the way Phase 0
built `benchmarks.json`: every number with its source, fetch date, sample size and a confidence grade
(A official or primary; B public, usable after processing; C partial or a proxy; D no data, a GUESS).
File: `benchmarks_phase8_11.json`, built by `tools/build_phase8_11_yardstick.py` from the committed
aggregates and `data/phase8_11/manual_entries.json`. Notes and derivations: `PHASE8_NOTES.md`.
Nothing here feeds the engine.

## Summary

| # | Target | What was found | Grade | Still missing |
|---|---|---|---|---|
| 1a | Roster: class shares by tier | 2025 rosters, 8,577 players, 232 schools: Fr .29/.26/.22, So .22/.20/.19, Jr .28/.29/.29, Sr .16/.19/.22, Gr .05/.04/.04 (P4/mid/low) | B | 2026 (post-limit) rosters; redshirt flag and class by position land with the roster run started today |
| 1b | Roster: age by class | No roster page lists birthdates; a GUESS table from the clock rules and the class shares | D | Birthdates (GOALS ask added; the fetcher now keeps an age column when a page has one) |
| 1c | Roster size | Spring 2025 (pre-limit): P4 40.4 ± 3.4 listed players (p10–p90 36–44, 94% over 34); mid 37.1, low 33.9 (partial pages included) | B (P4), C (mid, low) | The 2026 rosters under the 34-man limit |
| 1d | Pitchers vs position players | Pitcher share of listed players .506 / .489 / .475 (P4/mid/low); with two-way players .536 / .523 / .504 | B | — |
| 2a | Player sources by tier | HS only .510/.515/.445, D1 transfer .196/.143/.087, JUCO .112/.177/.206, other four-year .048/.082/.097, unknown .134/.083/.166 (P4/mid/low) | B | — |
| 2b | Moves between tiers | Pending: `d1_transfer_flow.csv` (previous D1 school's tier for every D1 transfer) comes from the roster run started today; among WMT client teams, see section 6 | B when it lands | The run opens a PR into this branch |
| 3a | Geography by tier | In-state .427 / .457 / .386; within 300 mi .59 / .64 / .65; foreign .025 / .024 / .033, Canada two-thirds of it | B | — |
| 3b | Talent-rich states | CA 1,081 players (13.1% of located players, 60% stay in state, 24% to P4); TX 745 (9.0%, 62% stay, 31% to P4); FL 614 (7.5%, 48% stay, 28% to P4); GA 394 (4.8%, 36% stay); NC 321 (70% stay). Schools in TX 69% in-state, FL 68%, CA 80%, GA 69%, NC 39% | B | — |
| 4a | Draft picks by round and source | Every pick 2021–2026 (3,685): HS 115–127 a year, JC 12–47, D1 420–461 (P4 238–279, mid 151–164, low 18–32), D2 9–22, D3 1–4, NAIA 1–8 | A (feed), B (tiers), C (D2/D3/NAIA split) | NCAA's own 2021, 2022, 2024 counts (page shows one edition) |
| 4b | Unsigned HS by round | 2021–25 pooled: 0 of 89 in round 1, 4 of 149 in rounds 2–5, 1 of 64 in 6–10, 137 of 295 (46%) in 11–20, rising to 70% (round 19) and 84% (round 20) | B (rounds 1–10), C (11–20) | Where the unsigned enrolled (case reports only) |
| 4c | College juniors drafted per D1 team | D1 draftees 1.37–1.50 per program (307); juniors 287 of 432 D1 picks in 2025 (.93 per program); NCAA: 15.3% of draft-eligible D1 players, 40.8% of P4's | A/B | NCAA eligible denominators for other years |
| 4d | Slot values | Every slot 2021–2026 (`data/mlb_draft/slot_values.csv`); No. 1 $11.35M in 2026, pools $358.7M; $150,000 late-round exemption; overage tiers; deadlines | A | 2021–23 pool totals |
| 4e | Proposed 12-round ruleset | MLB 2026-06-18: 12 rounds, hard slots, $200M, age 20 and two years past HS from 2028 (no HS or JUCO), sophomores eligible; MLBPA counter 07-21; no deal as of 10-10 | A/B | The signed agreement |
| 5a | Portal entries per year | Pending (research running when this draft was written; see section 7) | | |
| 5b | Placement and landing tier | Pending (section 7) | | |
| 6 | Development: year-over-year change by class | Pending: the WMT player-season fetch (2022–2026, 51 client programs a season) was running when this draft was written; see section 6 | B when it lands | Non-client (mid, low) programs |
| 7a | JUCO and D2 talent | D2 (8 conferences, 101 of 258 teams): .295/.396/.450, 0.91 HR and 6.86 runs a team-game, ERA 6.36; CCCAA (87 teams) .290/.393/.407, ERA 5.94; NJCAA D1 Kansas .309/.421/.486, Alabama .296/—/.423. D1 beat non-D1 opponents 90% of 90 games, 12.2 to 4.3 runs | B (rates), C (crossover) | NJCAA national lines; a cross-division rating (Massey blocked) |
| 7b | JUCO and D2 → D1 per year | CCCAA 2025 class: 185 to D1 of 600+ to four-year schools (A, California); NJCAA alumni 570+ in the 2026 D1 field across 59 of 64 teams (B); JUCO→D1 about 900–1,100 a year (C, derived); D2→D1: no source (D) | A/B/C/D | NJCAA national counts; D2→D1 (NCAA Research ask) |
| 8 | Recruiting calendar and rules | Every spec date verified against the 2026-27 calendar PDF and the 2026-27 Manual; no baseball date changed; eligibility clock gained sub-rules 12.6.1–12.6.3 on 9/9/26 | A | — |

## 1. Roster composition (2025 rosters)

Source: `data/ncaa_2025/roster_aggregates/` (fetched 2026-10-09; 233 of 283 WMT-sample teams parsed;
8,620 players). Tables: `benchmarks_phase8_11.json` → `roster_composition_2025`;
`data/phase8_11/class_by_origin_2025.csv`, `roster_size_by_school_2025.csv`.

| Tier | Schools | Players | Fr | So | Jr | Sr | Gr | Unknown | Listed per school | Pitcher share |
|---|---|---|---|---|---|---|---|---|---|---|
| P4 | 50 | 2,020 | .290 | .219 | .281 | .158 | .050 | .003 | 40.4 ± 3.4 | .506 (.536 with two-way) |
| Mid | 122 | 4,524 | .255 | .201 | .286 | .195 | .044 | .019 | 37.1 ± 7.1 | .489 (.523) |
| Low | 60 | 2,033 | .220 | .193 | .290 | .224 | .042 | .032 | 33.9 ± 9.3 | .475 (.504) |

- Classes are the listed strings with redshirt markers dropped (R-Fr counts as Fr). The redshirt share
  and class x position come with `class_detail_by_tier.csv` from today's roster run.
- P4 rosters skew young: more freshmen, fewer seniors. The draft takes P4 juniors (section 4) and the
  portal moves the rest.
- Roster sizes are spring 2025, before the 34-man limit took effect (7/1/25). 94% of P4 rosters listed
  more than 34. The mid and low means include partially parsed pages (minimum 5 listed), so their spread
  is overstated; the P4 distribution is clean.
- **Age (GUESS, D).** No fetched roster page lists birthdates. `age_by_class_guess` in the benchmarks
  file gives a placeholder distribution (freshmen 18–20, each class one year older, a tail for redshirts
  and JUCO transfers) to be replaced by `age_by_class.csv` if any page lists ages, or by the GOALS ask.

Class x origin (shares within class, `class_by_origin_2025.csv`): freshmen are .86 high-school-only
across tiers; D1 transfers peak among juniors and graduates; JUCO transfers enter mostly as juniors.

## 2. Player sources

Origins by tier as in the spec (Section 7), grade B. The tier-to-tier flow of D1 transfers
(`d1_transfer_flow.csv`: the Phase 0 tier of the previous D1 school named on the roster) is produced by
the roster run started 2026-10-10 (GitHub Actions run 38066352243 on this branch), which opens a pull
request into this branch when it finishes; the aggregator's selftest already writes the table. Among WMT
client teams (section 6) the moves are P4-heavy by construction.

## 3. Geography

`geography_2025` in the benchmarks file; `data/phase8_11/players_by_home_state_2025.csv` (each home
state's players by destination tier) and `in_state_share_by_school_state_2025.csv` (how in-state each
state's schools are). Hometowns are state-level; school states from IPEDS.

| Home state | Players | Share of located | Stay in state | To P4 | To mid | To low | In-state share of the state's schools (schools) |
|---|---|---|---|---|---|---|---|
| CA | 1,081 | .131 | .600 | .241 | .665 | .093 | .804 (21) |
| TX | 745 | .090 | .622 | .309 | .365 | .326 | .686 (19) |
| FL | 614 | .075 | .479 | .275 | .523 | .202 | .684 (11) |
| GA | 394 | .048 | .360 | .246 | .584 | .170 | .693 (5) |
| NC | 321 | .039 | .701 | .199 | .751 | .050 | .391 (17) |

- California exports little to the low tier because it has no low-tier schools in the sample, and its
  schools are the most in-state (.80). North Carolina's 17 schools are the least in-state (.39): many
  programs, a smaller talent pool.
- Foreign players are 2.5–3.3% of rosters; Canada is two-thirds of them, then Australia, the Dominican
  Republic, Venezuela and Japan.

## 4. MLB draft

Source: the MLB Stats API draft feed (`tools/fetch_mlb_draft.py`, `data/mlb_draft/`; every pick 2021–2026),
MLB.com's deadline and pick-value articles, the NCAA probability page. Grades as in the summary.

**Picks by source** (D1 tiers on the current conference map):

| Year | Picks | HS | JC | D1 | P4 | Mid | Low | D2 | D3 | NAIA | D1 per program | Programs with a pick |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 612 | 115 | 47 | 420 | 245 | 151 | 24 | 22 | 4 | 1 | 1.37 | 161 |
| 2022 | 616 | 118 | 42 | 434 | 265 | 151 | 18 | 16 | 2 | 1 | 1.41 | 148 |
| 2023 | 614 | 124 | 44 | 428 | 238 | 158 | 32 | 14 | 2 | 2 | 1.39 | 171 |
| 2024 | 615 | 116 | 27 | 445 | 255 | 164 | 26 | 14 | 3 | 7 | 1.45 | 168 |
| 2025 | 615 | 124 | 31 | 432 | 262 | 152 | 18 | 14 | 2 | 8 | 1.41 | 156 |
| 2026 | 613 | 127 | 12 | 461 | 279 | 162 | 20 | 9 | 1 | 3 | 1.50 | 166 |

Validation: the D1 count equals the NCAA's 428 in 2023 and is 432 against 431 in 2025.

**Round bands, 2021–2025 pooled** (supplemental and compensation picks folded into the round they
follow): R1+ 196 picks (HS 89, D1 105); R2–5 626 (HS 149, D1 462); R6–10 750 (HS 64, D1 630, non-D1
four-year 31); R11–20 1,500 (HS 295, JC 155, D1 962, non-D1 79). Per-round tables:
`data/mlb_draft/picks_by_round_source.csv`.

**Unsigned high schoolers** (no bonus on file; equals MLB.com's named unsigned picks in rounds 1–10):
0 of 89 in round 1; 4 of 149 in rounds 2–5; 1 of 64 in rounds 6–10; 137 of 295 in rounds 11–20,
from 10% in round 11 to 70% in round 19 and 84% in round 20. All sources: 39–53 unsigned of 612–616
picks a year (2025: 39, matching Baseball America's 576 of 615 signed). Compensation: an unsigned pick
in rounds 1–3 returns one slot later next year; later rounds nothing.

**College players drafted.** NCAA (2025 draft): 452 NCAA players of 615 picks (431 D1, 19 D2, 2 D3);
15.3% of draft-eligible D1 players (431 of 2,811); 40.8% of P4's eligible players (258 of 632). D1 picks
by class in 2025: juniors 287, sophomores 22, seniors 97, fifth-years 12, graduates 14. Juniors drafted
per D1 program: .93 (2025).

**Slot values** (`data/mlb_draft/slot_values.csv`, every pick with a value, 2021–2026): No. 1
$11,075,900 (2025) and $11,350,600 (2026); pools $350.4M (2025) and $358.7M (2026); 2026 round
first/last: R1 $11.35M–$3.70M, R2 $2.63M–$1.35M, R3 $1.10M–$763K, R5 $553K–$421K, R10 $202K–$192K.
Rounds 11–20: bonuses up to $150,000 outside the pool. Overage tiers: 75% tax to 5% over, a
first-round pick above 5%, and so on; no club has exceeded 5% in 14 drafts. Deadline about two weeks
after the mid-July draft (July 27, 2026). Lottery and PPI rules in `manual_entries.json`.

**Proposed ruleset** (MLB, 2026-06-18; re-tabled 10-08 with a cap-and-floor): 12 rounds, hard slots,
$200M domestic pool, eligibility age 20 by September 1 and two years past high school from the 2028
draft, so no high-school or junior-college picks; sophomores eligible; unlimited passed-over signings;
lottery 6 → 4; Competitive Balance picks gone. For the sim: the 115–127 HS and 12–47 JC picks a year
stay in the amateur pool, sophomores become draftable, about 360 picks instead of 614, and no
signability bargaining. The MLBPA countered on 07-21 (keep 20 rounds and HS/JUCO eligibility); the CBA
expires 2026-12-01 with no deal.

## 5. Transfer portal

Filled in section 7 below.

## 6. Development and retention (WMT player seasons, 2022–2026)

Filled when the fetch finishes (see the end of this report).

## 7. JUCO and D2

**League rates, 2025** (`data/phase8_11/d2_juco_league_rates_2025.csv`, `tools/fetch_d2_juco_team_stats.py`;
conference team-total pages; grade B):

| League | Teams | BA | OBP | SLG | HR per team-game | Runs per team-game | ERA | K/9 | BB/9 |
|---|---|---|---|---|---|---|---|---|---|
| NCAA D2, 8 conferences pooled (101 of 258) | 101 | .295 | .396 | .450 | 0.91 | 6.86 | 6.36 | 7.57 | 4.75 |
| CCCAA (California JUCO, all) | 87 | .290 | .393 | .407 | 0.55 | 7.17 | 5.94 | 7.24 | 4.69 |
| KJCCC (NJCAA D1, Kansas) | 20 | .309 | .421 | .486 | 0.92 | 7.42 | 7.13 | 8.27 | 5.27 |
| ACCC (NJCAA D1, Alabama) | 20 | .296 | — | .423 | 0.55 | 5.50 | 5.83 | 7.32 | 4.76 |
| ICCAC (NJCAA D2, Iowa) | 9 | .299 | .423 | .483 | 1.07 | 7.86 | 6.93 | 9.01 | 5.94 |
| NWAC (Northwest JUCO, wood bats) | 29 | .245 | — | .318 | 0.20 | 4.98 | 4.58 | 7.14 | 4.68 |

For comparison D1 2025: .280 / .381 / .440, 1.05 HR and 6.75 runs a team-game, ERA 6.08 (`benchmarks.json`, league totals). D2
hits for a higher average and walks more against weaker pitching; its power is below D1's. JUCO is a wide
distribution across leagues, not a point. The NCAA's own D2 lines are on stats.ncaa.org (403) and
www.ncaa.com (off limits).

**Crossover** (`d1_vs_non_d1_2025`): 90 D1 scoreboard finals against non-D1 opponents (D2, D3, NAIA
mixed, almost all tagged IND): D1 won 90%, 12.2 to 4.3 runs, D1 hosting 93%. Grade C. Massey Ratings,
which rates all divisions on one scale, is blocked from the cloud (data request 8).

**Flow to D1.** CCCAA 2025 class: 600+ players to four-year schools, 185 to NCAA D1 (A for California).
NJCAA: 570+ former players and coaches in the 2026 D1 tournament field, 59 of 64 teams, 210 NJCAA
schools (B). Programs: NJCAA 188 D1 / 130 D2 / 79 D3 (C), CCCAA 87, NWAC 29. JUCO to D1 per year:
about 900–1,100 (C, derived from the roster JUCO shares and the CCCAA rate). D2 to D1: no public count
(D); portal entrants from D2 were 1,374 / 1,883 / 1,772 in 2024–2026 (64 Analytics, B). Draft: D2 19
picks in 2025 (.074 per program), D3 2, JUCO 31 (Stats API). Older NCAA research: two-year transfers
were 19.2% of the D1 baseball population in 2015-16, four-year transfers 2.0%.

**D2 structure** (NCAA sponsorship report, A): 258 teams, 11,919 players, 46.2 per team in 2023-24
(39.5 in 2015-16); 9.0 scholarship equivalencies; no roster limit; no portal windows.

**Measurables by level**: a D1 in-game sample at 91.4 ± 2.7 mph (n = 57, elite-skewed), one D1
program's bullpens at 87.4 ± 4.0 (n = 30); recruiting-service guideline ranges by level only (D). No
level-split TrackMan data is public.

## 8. Recruiting calendar and rules

Every date in the spec's Section 10 and Section 12.1 was checked against the 2026-27 recruiting calendar
PDF (updated July 30, 2026) and the 2026-27 Division I Manual as of 2026-10-10 (bylaw by bylaw, in
`PHASE8_NOTES.md`, section 1). Findings:

- **No baseball recruiting date changed.** Calls and correspondence from Aug 1 of the junior year;
  off-campus contact, official and unofficial visits from Sep 1 of the junior year; written offers from
  Aug 1 of the senior year; signing from the second Wednesday in November (Nov 11, 2026); one official
  visit per school before Oct 15 after high school.
- **The 2026-27 calendar follows the 13.17.1 formulas exactly**: contact Aug 1–16 and Sep 11–Oct 11;
  quiet Aug 17–Sep 10 and Oct 12–Feb 28; dead Nov 9–12, Jan 7–10, May 31–Jun 7, Jun 19–21, Jul 3–5;
  shutdowns Nov 24–29 and Dec 22–27; contact Mar 1 to Aug 15, 2027. One wording fix for the spec: the
  spring contact period runs through the Sunday before the third Monday of August, not July 31.
- **Roster limit** 34 and the roster deadline (day before the first counted contest or Dec 1) stand.
- **Portal windows** stand: Dec 1–15 and 30 days from seven days after selections (Jun 7–Jul 6, 2027);
  the head-coach exception is 30 days.
- **Eligibility clock**: 12.6 was revised again on 9/9/26 with three sub-rules (a Sep–Dec 19th birthday
  starts the clock the next fall; enrollment between May 1 and Nov 1 starts it that fall, Nov 1 to May 1
  the next regular term; a clock ending in a fall term runs to the spring term and a championship that
  starts inside the period extends it). Phase 8 should carry these.

## Sources that blocked the cloud session (no workaround attempted)

www.ncaa.com (off limits by rule), stats.ncaa.org 403, masseyratings.com 403, warrennolan.com 503,
on3.com 403, spotrac.com 403, stats.njcaa.org 502 and njcaa.org's client-rendered app, web.archive.org
unreachable, thebaseballcube.com 403, baseball-reference.com (terms), mlb.com via WebFetch 406 (curl
with a browser user agent works), ESPN bot challenge. ncaa.org's legacy `.aspx` links redirect home; its
`/student-athletes/` and `/news/` paths work.
