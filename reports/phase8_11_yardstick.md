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
| 1a | Roster: class shares by tier | 2025 rosters, 8,577 players, 232 schools: Fr .29/.26/.22, So .22/.20/.19, Jr .28/.29/.29, Sr .16/.19/.22, Gr .05/.04/.04 (P4/mid/low). Redshirt marker on .13 / .17 / .12 of listed players (P4 seniors .18, mid sophomores .24). Pitchers are .50–.54 of every class at P4 | B | 2026 (post-limit) rosters |
| 1b | Roster: age by class | No roster page lists birthdates; a GUESS table from the clock rules and the class shares | D | Birthdates (GOALS ask added; the fetcher now keeps an age column when a page has one) |
| 1c | Roster size | Spring 2025 (pre-limit): P4 40.4 ± 3.4 listed players (p10–p90 36–44, 94% over 34); mid 37.1, low 33.9 (partial pages included) | B (P4), C (mid, low) | The 2026 rosters under the 34-man limit |
| 1d | Pitchers vs position players | Pitcher share of listed players .506 / .489 / .475 (P4/mid/low); with two-way players .536 / .523 / .504 | B | — |
| 2a | Player sources by tier | HS only .510/.515/.445, D1 transfer .196/.143/.087, JUCO .112/.177/.206, other four-year .048/.082/.097, unknown .134/.083/.166 (P4/mid/low) | B | — |
| 2b | Moves between tiers | Roster run of 2026-10-10: of D1 transfers on P4 rosters, the previous D1 school was P4 .44, mid .33, low .11 (unknown .12); on mid rosters P4 .40, mid .39, low .10; on low rosters P4 .26, mid .32, low .17 (unknown .25). NCAA: D1 transfers land D1 72–75%, D2 21–24%, D3 3%; 64 Analytics level matrices in `manual_entries.json` | B / A | Portal entrants by tier (none published) |
| 3a | Geography by tier | In-state .427 / .457 / .386; within 300 mi .59 / .64 / .65; foreign .025 / .024 / .033, Canada two-thirds of it | B | — |
| 3b | Talent-rich states | CA 1,081 players (13.1% of located players, 60% stay in state, 24% to P4); TX 745 (9.0%, 62% stay, 31% to P4); FL 614 (7.5%, 48% stay, 28% to P4); GA 394 (4.8%, 36% stay); NC 321 (70% stay). Schools in TX 69% in-state, FL 68%, CA 80%, GA 69%, NC 39% | B | — |
| 4a | Draft picks by round and source | Every pick 2021–2026 (3,685): HS 115–127 a year, JC 12–47, D1 420–461 (P4 238–279, mid 151–164, low 18–32), D2 9–22, D3 1–4, NAIA 1–8 | A (feed), B (tiers), C (D2/D3/NAIA split) | NCAA's own 2021, 2022, 2024 counts (page shows one edition) |
| 4b | Unsigned HS by round | 2021–25 pooled: 0 of 89 in round 1, 4 of 149 in rounds 2–5, 1 of 64 in 6–10, 137 of 295 (46%) in 11–20, rising to 70% (round 19) and 84% (round 20) | B (rounds 1–10), C (11–20) | Where the unsigned enrolled (case reports only) |
| 4c | College juniors drafted per D1 team | D1 draftees 1.37–1.50 per program (307); juniors 287 of 432 D1 picks in 2025 (.93 per program); NCAA: 15.3% of draft-eligible D1 players, 40.8% of P4's | A/B | NCAA eligible denominators for other years |
| 4d | Slot values | Every slot 2021–2026 (`data/mlb_draft/slot_values.csv`); No. 1 $11.35M in 2026, pools $358.7M; $150,000 late-round exemption; overage tiers; deadlines | A | 2021–23 pool totals |
| 4e | Proposed 12-round ruleset | MLB 2026-06-18: 12 rounds, hard slots, $200M, age 20 and two years past HS from 2028 (no HS or JUCO), sophomores eligible; MLBPA counter 07-21; no deal as of 10-10 | A/B | The signed agreement |
| 5a | Portal entries per year | NCAA dashboards, D1 baseball, Aug–Jul cohorts: 2,715 (2023), 2,855 (2024), 3,772 (2025); 2022 about 2,415 and 2021 2,126 (secondhand); D2 baseball 1,303 / 1,591 / 1,997 | A (2023–25), C (2021–22) | Official 2021–22 counts; December vs June split |
| 5b | Placement and landing tier | Of D1 entrants: transferred to an NCAA school 57% / 63% / 58%, withdrawn 8% / 6% / 5%, the rest still in the portal or outside the NCAA (35% / 31% / 37%). 2025 D1 transfers landed D1 72.5% (61.7% with aid, 10.8% without), D2 24.4%, D3 3.2%; graduate share 25% → 16%. 64 Analytics: 47% of all 2025 entrants appear in 2026 NCAA data | A | By conference tier (none published; SEC only) |
| 6 | Development: year-over-year change by class | WMT player seasons 2022–2026 (51 client programs a season, 9,890 player-seasons, 1,186 batter and 1,185 pitcher consecutive-season pairs over 50 PA/BF). Batters Fr→So: K% −.10 logit, BB% +.09, HR% +.18, OPS +.059; So→Jr OPS +.023; Jr→Sr +.027; Sr→5th −.033. Pitchers Fr→So: K% +.07 logit, BB% −.07, ERA −.20; later years flat. Retention to the same program: Fr .60, So .63, Jr .49, Sr .12; freshmen .53 in 2025→26 (first roster-limit season) | B (shapes; survivors only, P4-heavy) | Mid and low programs; opponent adjustment; the non-survivors |
| 7a | JUCO and D2 talent | D2 (8 conferences, 101 of 258 teams): .295/.396/.450, 0.91 HR and 6.86 runs a team-game, ERA 6.36; CCCAA (87 teams) .290/.393/.407, ERA 5.94; NJCAA D1 Kansas .309/.421/.486, Alabama .296/—/.423. D1 beat non-D1 opponents 90% of 90 games, 12.2 to 4.3 runs | B (rates), C (crossover) | NJCAA national lines; a cross-division rating (Massey blocked) |
| 7b | JUCO and D2 → D1 per year | CCCAA 2025 class: 185 to D1 of 600+ to four-year schools (A, California); NJCAA alumni 570+ in the 2026 D1 field across 59 of 64 teams (B); JUCO→D1 about 900–1,100 a year (C, derived); D2→D1: no source (D) | A/B/C/D | NJCAA national counts; D2→D1 (NCAA Research ask) |
| 8 | Recruiting calendar and rules | Every spec date verified against the 2026-27 calendar PDF and the 2026-27 Manual; no baseball date changed; eligibility clock gained sub-rules 12.6.1–12.6.3 on 9/9/26 | A | — |
| R1 | Recruit rankings → outcomes (round 2) | MLB Pipeline-ranked HS prospects 2019–24 (557): top 25 sign .97, 26–100 sign .64, 101–200 sign .33; commits P4 .90 / mid .08 / low .005; campus arrivals P4 .83 / mid .14; two-thirds of arrivals drafted within four years, one in six first round, 72 of 77 from P4 programs. BA's November HS top 100 (2018): .40 sign, .45 of arrivals drafted within five years | A / B | PG and PBR rankings (terms forbid fetching); BA lists (paywall) |
| R4 | Survivor bias in the development curves (round 2) | Fr→So curve biased down about .013 OPS (weak freshmen leave); Jr→Sr +.027 OPS is about +.024 regression to the mean (the draft takes the best juniors); pitchers' Jr→Sr K% gain is smaller than its RTM term | C (sizes) | Non-client leavers; a full-population r |
| R5 | Program money (round 2) | EADA 2024-25 total expenses median P4 $5.0M / mid $1.7M / low $0.9M (SEC $7.8M); MFRS FY2025 27 programs $4.6M–$13.0M; head coaches: top 15 $1.28M–$3.35M (median $1.5M), other P4 $0.5M–$1.7M, mid-majors $91K–$600K; revenue share to baseball documented only at Texas Tech (1.9%, $390K) and LSU (5% planned 2026-27); 54 schools opted out; scholarships 25–34 at documented P4 programs | A (EADA), B (MFRS, salaries), D (rev-share distribution) | NIL payrolls; conference-wide salary and scholarship tables; national attendance total |

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

**Redshirt and class by position (roster run of 2026-10-10, `class_detail_by_tier.csv`).** A redshirt marker
sits on .128 of P4, .168 of mid and .122 of low listed players; by class P4 .11 (Fr) / .12 (So) / .14 (Jr) /
.18 (Sr), mid .13 / .24 / .18 / .17, low .12 / .16 / .14 / .10. Pitchers are .50–.54 of P4 freshmen through
juniors and .44 of P4 seniors (the draft takes junior arms); catchers .08–.11, infielders .17–.22,
outfielders .12–.18, two-way players .05–.06 of freshmen falling to .01–.02 of seniors. No roster page in the
fetch lists a birthdate or age (`age_by_class.csv` is empty), so the age table stays a GUESS.

Class x origin (shares within class, `class_by_origin_2025.csv`): freshmen are .86 high-school-only
across tiers; D1 transfers peak among juniors and graduates; JUCO transfers enter mostly as juniors.

## 2. Player sources

Origins by tier as in the spec (Section 7), grade B. **The tier flow of D1 transfers** (`d1_transfer_flow.csv`,
roster run 38066352243 of 2026-10-10: the Phase 0 tier of the previous D1 school named first on the roster
page; `unknown` when only an alias matched):

| Roster tier | D1 transfers | From P4 | From mid | From low | Unknown |
|---|---|---|---|---|---|
| P4 | 396 | .444 | .333 | .106 | .116 |
| Mid | 645 | .405 | .394 | .096 | .105 |
| Low | 176 | .256 | .324 | .170 | .250 |

P4 rosters refill mostly from other P4 programs and from the mid tier; a third of the mid tier's D1
transfers come down from P4; the low tier takes more from mid than from P4. Grade B (name match on the
2025 D1 list). The NCAA portal rows (section 5) give the level split (D1 → D1 72–75%), and 64 Analytics
the conference-third matrices; this is the first tier-to-tier table built on roster previous schools.

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

Source: the NCAA Research transfer dashboards (Tableau Public, filtered to Sport = Baseball; data as of
2026-01-05), `data/phase8_11/portal_ncaa_dashboard_2023_2025.csv` and
`transfer_composition_d1_baseball_2015_2024.csv`; `transfer_portal_2021_2026` in the benchmarks file.
A cohort runs Aug 1 to Jul 31 and is labelled by the later year.

| D1 baseball cohort | Entrants | Transferred (NCAA) | Withdrawn | Still active or non-NCAA | Undergrad / grad transfers |
|---|---|---|---|---|---|
| 2023 | 2,715 | 1,551 (.571) | 206 (.076) | 958 (.353) | 1,161 / 390 |
| 2024 | 2,855 | 1,810 (.634) | 157 (.055) | 888 (.311) | 1,489 / 321 |
| 2025 | 3,772 | 2,199 (.583) | 189 (.050) | 1,384 (.367) | 1,846 / 353 |

- Grade A. Earlier cohorts only secondhand (C): 2022 about 2,415 entrants with 48% transferred; 2021
  2,126. Other trackers for scale (B): D1Baseball 2,845 (2024); 64 Analytics June-window D1 entrants
  2,677 / 2,850 / 2,680 (2024–26) and all-NCAA 2025 entrants 6,254 (D1 3,525, D2 1,883, D3 846), of
  whom 47.4% appear in 2026 NCAA playing data.
- **Destination of D1 transfers** (2025, n = 2,184): D1 with aid .617, D1 without aid .108, D2 with aid
  .208, D2 without aid .036, D3 .032. D1-to-D1 is .748 / .750 / .725 of transfers in 2023–25; D1-to-D2
  .218 / .214 / .244. As a share of all 2025 entrants: landed D1 .42, D2 .14, D3 .02, withdrawn .05,
  still active or outside the NCAA .37 (NAIA, JUCO, pro ball, quit; untracked).
- **Aid**: of 2025 entrants aided at departure (2,288), .565 transferred with aid, .093 without, .342
  stayed active; of the unaided (1,295), .399 / .137 / .464.
- **D2 baseball**: entrants 1,303 / 1,591 / 1,997; transferred .33 / .36 / .32; of 2025 D2 transfers
  (637) .322 landed D1 with aid and .088 without, so **D2 → D1 was 162 / 203 / 261 players** in 2023–25,
  the flow the spec had no source for.
- **Graduate share** of D1 transfers .251 / .177 / .161. Portal windows and exceptions: section 8.
- **No source splits entrants or destinations by P4 / mid / low** (D). SEC 2025: 170 in, 223 out (C).
  61 D1 programs took 10+ transfers in 2025 (36 in 2024, 20 in 2023; Baseball America, B).
- **Moves between levels** (64 Analytics "Relative Jumps", 2021–26, D1 split into thirds of its 30
  conferences by RPI, players with 25+ PA or 10+ IP at both stops, B): hitters leaving the upper third
  go upper .59, middle .20, lower .09, D2 .11; leaving the middle third .44 upper, .27 middle, .18 D2;
  leaving the lower third .37 upper, .25 D2. Of hitters arriving in the upper third, .49 come from the
  upper third, .25 middle, .15 lower, .07 D2, .05 D3. Moving up one level, 36% of hitters and 39% of
  pitchers improve; moving down one, 71% and 69%. Full 5x5 matrices in `manual_entries.json`.
- **Transfer composition of aided D1 baseball cohorts** (NCAA, A): four-year plus graduate transfers
  .020 (2015) → .052 (2021) → .098 (2022) → .131 (2023) → .166 (2024); two-year transfers .19–.22
  throughout. The 2024 figure sits between the roster shares of P4 (.196) and mid (.143).
- Timing: Dec 1–15 and the June window; no published December-vs-June count (D).

## 6. Development and retention (WMT player seasons, 2022–2026)

Source: `tools/fetch_wmt_player_seasons.py` → `data/wmt_player_seasons/` (fetched 2026-10-10; season
ids 15860, 16340, 16580, 16840, 17040). WMT's stats API lists, for each of its 51 client programs a
season (34–37 P4, 12–16 mid, 1 low), every rostered player's season totals with class, position and a
person id that persists across seasons and programs. 9,890 player-seasons; classes known for 99.9%.
Pairs: the same person in consecutive seasons at any client program with 50+ PA (batters) or 50+ BF
(pitchers) in both seasons: 1,186 batter pairs, 1,185 pitcher pairs. `development_2022_2026_wmt` in the
benchmarks file; per class, tier and playing-time tercile in `aging_curves.csv`.

**Year-over-year change by class** (class in the first season; logit scale for rates, raw for ERA, SLG,
ISO, OPS; mean ± SE across players):

| Batters | Pairs | K% | BB% | HR% | OBP | SLG | ISO | OPS | BABIP |
|---|---|---|---|---|---|---|---|---|---|
| Fr → So | 283 | .212→.197 (−.100 ± .022) | .111→.121 (+.086 ± .027) | .031→.037 (+.177 ± .048) | .383→.400 (+.070 ± .016) | .458→.501 (+.042 ± .008) | .174→.206 (+.030 ± .005) | .841→.900 (+.059 ± .010) | +.006 ± .019 |
| So → Jr | 434 | −.074 ± .016 | +.034 ± .018 | +.081 ± .038 | +.026 ± .011 | +.016 ± .005 | +.012 ± .004 | +.023 ± .008 | −.014 ± .014 |
| Jr → Sr | 386 | −.072 ± .017 | +.001 ± .021 | +.159 ± .038 | +.023 ± .012 | +.021 ± .006 | +.018 ± .004 | +.027 ± .009 | −.027 ± .016 |
| Sr → 5th | 83 | +.021 ± .040 | +.030 ± .037 | −.014 ± .084 | −.041 ± .026 | −.023 ± .013 | −.010 ± .009 | −.033 ± .018 | −.061 ± .036 |

| Pitchers | Pairs | K% | BB% | HR% | Hits per BF | ERA |
|---|---|---|---|---|---|---|
| Fr → So | 346 | .224→.236 (+.072 ± .020) | .109→.102 (−.065 ± .025) | −.003 ± .046 | −.010 ± .016 | 5.53→5.25 (−.20 ± .17) |
| So → Jr | 434 | +.023 ± .016 | −.013 ± .022 | +.058 ± .037 | −.010 ± .014 | −.03 ± .15 |
| Jr → Sr | 334 | +.053 ± .021 | +.007 ± .027 | +.066 ± .043 | −.015 ± .017 | +.06 ± .17 |
| Sr → 5th | 71 | −.021 ± .040 | −.008 ± .060 | −.123 ± .108 | +.011 ± .031 | +.11 ± .39 |

- **Shape**: hitters gain most from freshman to sophomore year (OPS +.059: fewer strikeouts, more
  walks and a fifth more home runs per PA), keep gaining about +.025 OPS a year through the senior
  year, and fifth-years decline (−.033). Pitchers gain strikeouts and shed walks in the first step and
  are flat after; ERA pairs are noisy (SD about 3.1 runs).
- **Regression to the mean is large and must be modelled, not read as development**: by first-season
  tercile, freshman hitters in the bottom third gain +.087 OPS and the top third +.046; junior hitters
  in the top third lose −.014; bottom-third freshman pitchers cut ERA by .83 and top-third pitchers
  add .47. The curves above are the marginal change of a survivor; the Phase 10 gate should compare
  the sim's survivors on the same selection (50+ PA both seasons) with the sim's own regression to the
  mean included.
- **Survivorship**: a pair needs the player to stay at a client program and play both seasons; the
  players who left (section on retention), were cut or stopped playing are missing. P4-heavy (about
  70% of pairs). Opponent quality and the 2022–26 run environment are not adjusted. Grade B for the
  shapes, C for the levels.

**Retention: where a player is the next season** (2022–2025 cohorts; the same program is recognised
by name, since WMT team ids are per season):

| Class | Player-seasons | Same program | Another WMT program | Absent (non-client school, drafted, graduated, cut, quit) |
|---|---|---|---|---|
| Fr | 2,224 | .601 | .044 | .355 |
| So | 1,900 | .634 | .062 | .305 |
| Jr | 2,127 | .489 | .038 | .473 |
| Sr | 1,692 | .122 | .020 | .858 |

- Freshmen who played a game stay .68, freshmen rostered without a game .40. Juniors in the top third
  of playing time stay .42 (batters) and .40 (pitchers) against .59 and .52 in the bottom third: the
  draft takes the regulars. P4 juniors stay .446, mid .577.
- **The roster limit shows**: freshman retention into 2026 fell to .525 (293 of 558) from .60–.65 in
  the three earlier cohorts; sophomores .63, juniors .46, unchanged. The P4 stat roster (everyone WMT
  lists, including players without a game) fell from 41.4 ± 2.9 (2025) to 38.8 ± 2.2 (2026, max 44);
  the number who played a game stayed 34–35. Seniors' share of P4 stat rosters rose from .214 to .238
  (fifth-years and designated student-athletes).
- Moves between client programs by tier (P4-heavy by construction, so not a gate): 2025→26 p4→p4 82,
  mid→p4 13, p4→mid 14, p4→low 4, mid→mid 9.
- "Absent" is the sum of transfers to non-client schools, the draft, graduation and cuts; the NCAA
  portal rows (section 5) and the draft rows (section 4) split it from the other side.

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

## 9. Survivor bias in the development curves (round 2, owner request)

`data/wmt_player_seasons/survivor_selection.csv`; `development_2022_2026_wmt.survivor_bias` in the
benchmarks file. For each class and rate, the first-season level of the players who enter a pair
(over the floor in both seasons at a client program) against every player over the floor that season,
and the leavers' level. With r the survivors' own year-to-year correlation of the rate, the
regression-to-the-mean part of their measured change is about (1 − r) × (population mean − survivors'
mean). Reported, not applied.

| Role, class → next | Survivor share | Survivors' level vs all (SD units) | Leavers' level | r | RTM bias in the measured change | Measured change |
|---|---|---|---|---|---|---|
| Batters Fr → So, OPS | .76 | +.13 (.841 vs .820) | .720 | .41 | −.013 | +.059 |
| Batters So → Jr, OPS | .71 | .00 (.879 vs .880) | .881 | .47 | .000 | +.023 |
| Batters Jr → Sr, OPS | .52 | −.22 (.847 vs .881) | .917 | .30 | **+.024** | +.027 |
| Batters Sr → 5th, OPS | .11 | +.17 (.895 vs .870) | .867 | .35 | −.016 | −.033 |
| Batters Jr → Sr, HR% | .52 | −.21 | .039 vs .029 | .46 | +.083 logit | +.159 logit |
| Pitchers Fr → So, ERA | .70 | −.07 (5.53 vs 5.73) | 6.32 | .17 | +.16 | −.20 |
| Pitchers Jr → Sr, K% | .41 | −.42 (.203 vs .231) | .249 | .40 | **+.099 logit** | +.053 logit |
| Pitchers Jr → Sr, BB% | .41 | −.08 | .101 | .37 | +.025 logit | +.007 logit |

- **Size.** Freshman survivors are the better freshmen (the weak ones leave or stop playing), so the
  Fr→So curve is biased *down* by about .013 OPS: true development from freshman to sophomore year is
  closer to +.07 than +.06. Sophomore survivors are unselected. **Junior survivors are the weaker
  juniors** (the draft takes the best: leavers hit .917 OPS and struck out 24.9% of batters faced
  against survivors' .847 and 20.3%), so the Jr→Sr curve is almost entirely regression to the mean:
  of the measured +.027 OPS, about +.024 is RTM; the pitchers' Jr→Sr strikeout gain (+.053 logit) is
  smaller than its RTM term (+.099), so the true change is flat or negative. Fifth-year survivors are
  the better seniors (−.016 bias), so their decline (−.033) is overstated by half.
- **Method caveats.** The (1 − r) rule uses the survivors' own correlation, which selection attenuates,
  so the RTM terms are rough (±30%); it assumes development does not depend on level. The leavers who
  went to a non-client school are mixed with the drafted and the cut. Grade C for the sizes.
- **For Phase 10:** gate the sim's survivors on the same selection rule (50+ both seasons, same
  program population), not the marginal curve, and expect a true Jr→Sr change near zero.

## 10. Program money (EADA 2024-25, by tier)

`program_money_eada_2024_25` in the benchmarks file; `data/phase8_11/eada_baseball_by_tier_2024_25.csv`.
Source: the committed EADA extract (304 institutions; the service academies do not file), the last
reporting year before revenue sharing. Grade A for the figures as filed; EADA's "revenue" equals
expenses at many schools by convention (institutional support), so it is not profit.

| Tier | Schools | Operating (game-day) expenses, median | Total expenses, median (p10–p90) | Revenue, median | Participants, median | Assistant coaches |
|---|---|---|---|---|---|---|
| P4 | 64 | $1.19M | $5.01M ($2.9M–$8.7M) | $4.08M | 41 | 3 |
| Mid | 152 | $0.44M | $1.71M ($1.0M–$2.7M) | $1.68M | 40 | 3 |
| Low | 88 | $0.26M | $0.92M ($0.5M–$1.4M) | $0.91M | 39 | 2–3 |

- By conference (median total expenses): SEC $7.8M, ACC $5.1M, Big 12 $4.4M, Big Ten $4.0M; the WCC
  leads the mid tier at $2.6M. Full table in the benchmarks file.
- **Coaching salaries are not in EADA by sport**: the file reports average salaries per head coach and
  per assistant across all men's teams of an institution. Baseball-specific salaries come only from
  public-records reporting (section 11, round 2 research).

## 11. Program money beyond EADA: revenue share, scholarships, NIL, salaries, attendance (round 2)

`program_money_public_2025_26` in the benchmarks file; `data/phase8_11/mfrs_baseball_fy2025.csv`. Only
baseball-specific figures are graded for use.

- **Revenue share to baseball (B for the two documented schools, D as a distribution).** Texas Tech
  2025-26: 1.9% of the $20.5M pool, $389,500 (football 74%, men's basketball 17–18%, women's basketball 2%,
  volleyball 4–5%). LSU 2025-26: baseball inside the 5% "everyone else" bucket (about $900K shared with four
  or five sports); for 2026-27 LSU plans its own slice of about 5% (about $1.08M of $21.58M, derived). UNC
  includes baseball "with little money"; Ohio State excludes it; Purdue's non-revenue sports got about
  $300K combined. The industry split is 75 / 15 / 5 / 5. The CSC's $1.77B filing has no by-sport table;
  the "13% of the pool to baseball" figure attributed to Baseball America is secondhand and contradicts
  every school figure (D). 54 D1 baseball schools did not opt in (Ivy 8, Patriot 10, NEC 8, Big Sky 5,
  ASUN 5, Big South 4 and others) and stay at 11.7 scholarships with no roster limit (B). **For the spec:**
  a P4 baseball revenue-share budget of $0–$1.1M with a median well under $500K, mid and low mostly zero
  (GUESS, D).
- **Scholarships after 11.7 (A rules, B counts).** 34 is the ceiling; opt-outs stay at 11.7; up to $2.5M of
  new aid above the old limit counts against the cap. Going from 11.7 to 34 costs $1.0–1.2M a year
  (Baseball America 2024); only about half of D1 funded 11.7 before (AP 2025). Documented 2026-27 counts:
  Arizona State 34, Texas Tech 34 (from 11.7), West Virginia 28, Texas 25 (C). Shape for the spec: full
  funding at a minority of P4 programs, 20–30 at most of the rest of P4, 11.7 or less at most mid and low,
  a hard 11.7 at the 54 opt-outs (GUESS, D).
- **NIL (C/D).** No verified baseball payroll or deal. Best anecdotes: a mid-major ace offered $400K to
  transfer; a low-major coach lost players worth over $1M (Baseball America, Jan 2026). NIL Go cleared
  34,195 deals worth $355M through 2026-06-30 across all sports, 44% of athletes with deals outside
  football and men's basketball; no sport table (A, context). Valuation lists ($125K–$850K) are D.
- **Draft money (B).** Two documented college players declined slots for NIL or revenue share: a $950K
  third-round slot in 2024 and a $425,400 fifth-round slot in 2026; two top-10-round picks went unsigned in
  each of 2025 and 2026.
- **Head-coach salaries (B/C).** Top 15 (Baseball America 2026, documents): n = 15, $1.28M–$3.35M, median
  $1.5M, nine of them SEC. Other documented P4: n = 9, $0.49M–$1.7M, median about $0.77M. Documented
  mid-majors: n = 6, $91K–$600K (AAC and Sun Belt top end $350K–$600K; low-major $90K–$130K). Tennessee's
  assistant and support pool was about $1.5M in 2024. No conference-wide table exists (On3's database
  returns 403). EADA cannot supply this: its coaching salaries are institution-level averages across all
  men's teams (User's Guide, September 2026 edition).
- **Attendance (B school releases, C forum tracker matching them).** 2025 totals with postseason: LSU
  458,606 (11,186 a game), Arkansas 407,196, Ole Miss 344,364, Mississippi State 330,009, then South
  Carolina, Texas, Tennessee, Florida, Texas A&M, Auburn (201,703). 2025 conference per-game averages: SEC
  6,020, Big 12 2,480, ACC 2,151, Sun Belt 1,672, AAC 1,378, Big Ten 1,307, Big West 1,137. All 16 SEC
  per-game averages in the benchmarks file. National total and average across all 307 teams: not found
  (the NCAA attendance PDF is unreachable).
- **Program finances, FY2025 (B).** NCAA financial reports obtained by public records for 27 programs
  (`mfrs_baseball_fy2025.csv`): operating expenses from Tennessee $13.0M, LSU $11.0M, Ole Miss $10.6M down to
  Missouri $4.6M; SEC public-school mean $8.07M expenses against $5.13M revenue; Mississippi State ticket
  revenue $2.7M; LSU's title-year baseball lost just under $1M. Consistent with EADA 2024-25 (SEC median
  total expenses $7.8M).

## 12. Recruit rankings → outcomes (round 2): the real "5-star vs 3-star" odds

Source: MLB's prospect registry (`statsapi.mlb.com/api/v1/draft/prospects/<year>`: every draft-eligible player
MLB Pipeline tracked, with its rank 1–200, 250 from 2025, the school class and a blurb naming the high
schooler's commitment), matched by MLB person id to the draft feeds 2019–2026. `tools/build_recruit_outcomes.py`
→ `data/recruiting/recruit_outcomes.csv` (4,238 aggregate rows, no names) and `summary_tables.md`;
`recruit_rankings_outcomes_2019_2024` in the benchmarks file. 557 ranked HS prospects, classes 2019–2024.
Grade A for the draft and signing columns, B for commitments (parsed from blurbs) and for 2019's inferred
HS status. **What the ranking is:** MLB Pipeline's draft-week board in the senior spring, HS and college on
one list, signability-blind. It is sharper than a recruiting ranking made a year earlier (section 6b of
the research notes shows how much); Perfect Game and Prep Baseball Report forbid automated access, so no
page of theirs was fetched, and Baseball America's 2019–2024 HS lists are paywalled.

**Pooled 2019–2024, by Pipeline overall rank:**

| Band | HS prospects | Committed P4 / mid / low / JUCO / not stated | Drafted out of HS | Signed | Signed in R1 / R2 / R3 / R4–5 / R6–10 / R11+ | Drafted, unsigned | Reached campus |
|---|---|---|---|---|---|---|---|
| 1–25 | 59 | 53 / 0 / 0 / 0 / 6 | 58 | **57 (.97)** | 49 / 5 / 2 / 1 / 0 / 0 | 1 | **2 (.03)** |
| 26–100 | 205 | 175 / 8 / 1 / 0 / 21 | 153 | **131 (.64)** | 43 / 53 / 19 / 9 / 5 / 2 | 22 | **74 (.36)** |
| 101–200 | 238 | 168 / 28 / 1 / 5 / 36 | 116 | **78 (.33)** | 2 / 6 / 20 / 27 / 11 / 12 | 38 | **160 (.67)** |

By rank among high schoolers only (the closer analogue of a recruiting service's HS top 100): HS 1–10
sign .97 (2 of 60 reach campus); 11–25 sign .82; 26–50 sign .47; 51 to about 105 sign .29 (182 of 257
reach campus).

- **Where they commit.** Among the 439 with a stated commitment: P4 .90, mid .08, low .005, JUCO .01. The
  P4 share falls with rank (100% in the top 25 of each class, 61–79% stated-P4 in the 101–200 band); mid
  commitments sit almost entirely in the 101–200 band. "Not stated" (21%) is not "uncommitted": top-25
  blurbs talk about slot money, not campuses.
- **Who D1 actually receives.** Of the 236 campus arrivals with a stated tier, P4 .83, mid .14, low .01,
  JUCO .02. The low tier gets essentially none of the ranked HS talent.
- **Drafted from college later** (classes 2019–2022, campus arrivals): 26–100 band, 52 players: drafted
  in year three or four .58, any of years two to four .77, 13 first-round picks; 101–200 band, 102
  players: .56 and .68, 10 first-round picks. About two-thirds are drafted within four years and one in
  six becomes a first-rounder. 72 of 77 year-three picks came from P4 programs, 3 from mid, none from low;
  mid-major commits were drafted at about the same rate as P4 commits (.60 against .70); drafted-from tier
  equals committed tier in about 99% of cases.
- **A recruiting-style list for comparison** (Baseball America's HS Top 100 for the 2018 draft, published
  November 2017, n = 100, B): commits P4 92, mid 8; signed out of HS .80 (1–10), .40 (11–25), .52 (26–50),
  .26 (51–100), .40 overall; 36% had fallen off Pipeline's top 200 by draft day; of the 60 who reached
  campus, .35 were drafted in years three or four and .45 within five, against .68 for the draft-week
  cohort. All 15 later year-three picks came from P4 programs. The gap between the two lists is the size of
  senior-year information, and the recruiting model should carry that noise.
- **Published cross-checks** (B): Baseball America's one-year-out HS top 100 sent 68% to college in 2023–24
  (top 10: 9 of 20; 26–50: 30 of 50; 51–100: 81 of 100); of 163 unsigned BA top-100 preps 2001–2016, 26%
  were later first-rounders and 9% never redrafted; HS seniors were 25% of picks in 2019 and 19–21% in the
  20-round drafts, signing at 72–79%.
- **Still missing**: a recruiting ranking at scale (PG and PBR terms; BA paywall: data request 9), ranks
  101–500, where the unsigned enrolled, year-five drafts for 2022, bonus distributions by band.

## Sources that blocked the cloud session (no workaround attempted)

www.ncaa.com (off limits by rule), stats.ncaa.org 403, masseyratings.com 403, warrennolan.com 503,
on3.com 403, spotrac.com 403, stats.njcaa.org 502 and njcaa.org's client-rendered app, web.archive.org
unreachable, thebaseballcube.com 403, baseball-reference.com (terms), mlb.com via WebFetch 406 (curl
with a browser user agent works), ESPN bot challenge. ncaa.org's legacy `.aspx` links redirect home; its
`/student-athletes/` and `/news/` paths work.
