# Roster building: recruiting, money, player flow, draft and career (design spec)

Source of truth for Phases 8–11 (owner decisions, 2026-10-08). Nothing here is built until those phases start, each under the normal gate rules (CLAUDE.md). This spec is documentation only.

**Owner's framing.** Roster building is the main draw of the game. Every system must be realistic and calibrated to data where data exists. Where no data exists, a value is marked GUESS with a confidence grade, as in the engine (`GUESSES.md`, benchmark `conf` A–D).

**Grades used here.**
- A: an official or primary source, directly usable.
- B: public, usable after processing.
- C: partial or a proxy.
- D: no data; a GUESS until data is found.

Section 12 holds the rule verification and the data inventory (research tasks of 2026-10-08). Section 13 gives the phase mapping and proposed gates. Section 14 lists the open issues.

---

## 1. Core pillars

- **Key moments.** Finding hidden gems. Beating blue bloods head to head. Building pipelines over years. Draft-day drama.
- **The user's role.** Hands-on recruiting, with staff extending reach. Staff can auto-handle lower-priority targets.
- **Heavy fog of war.** True ratings are hidden; the user sees scouted ranges only.
- **Coaching career mode.**
  - Start at JUCO, D2 or low D1.
  - The AD sets expectations each year.
  - The coach gets job offers or gets fired, and climbs.
- **Coach archetypes and skill tree** (Recruiter / Developer / Tactician).
  - XP comes from wins, signings and draft picks.
  - XP unlocks recruiting hours, pitch effectiveness, regional bonuses and development boosts.
  - AI coaches use the same tree and the same effects, so human and AI recruit on equal terms. This extends the engine's rule that human and AI decisions resolve with the same probabilities.
  - **Development boosts are bounded and centred** (owner decision 2026-10-08): a coach's boost moves his players relative to the league, and the league-wide development rate stays calibrated (Phase 10 gate), so levelling up across all coaches cannot inflate talent over the years.

## 2. School grade card (A+ to F, CFB-style)

| Group | Category | Definition |
|---|---|---|
| Earned (rolling windows) | Omaha Contender | Projected roster strength for the next 1–2 seasons, from actual (true) ratings |
| | Draft Development | About 5 years of draft results against the recruits' rankings on arrival |
| | Program Tradition | About 15 years: titles, Omaha trips, regionals hosted |
| | Coach Prestige | The head coach's record and reputation |
| | Coach Stability | Tenure, and the risk of leaving or being fired |
| | Conference Prestige | Rolling conference RPI and bids (engine Phase 7) |
| | Facilities | Includes the player development lab: pitch lab, TrackMan, analysts |
| | Ballpark Atmosphere | Attendance and stadium |
| | Brand Exposure | TV, social media, national profile |
| | Money | Revenue share plus NIL |
| Fixed (slow-moving) | Academic Prestige, Campus Life, Climate | |
| Personal (per recruit) | Playing Time | His position's depth chart |
| | Proximity to Home | Real distance |
| Hidden | Relationship | Exists and drives decisions; the user sees it only through the recruit's reactions |

**Priority weights.**
- The owner's instinct for the top priorities: Program Tradition, Money, Facilities, Omaha Contender, Playing Time.
- The weights are calibrated to data where possible, and the spec reports where the data disagrees with the instinct.

**Priority weights follow the data, not the first instinct** (owner decision 2026-10-08).
- **Playing Time and Proximity are the strongest priorities for most recruits; Money is weak overall.**
- Weights vary by recruit tier: draft-level recruits weight Money and Draft Development more.
- Calibrated where data allows:
  - GOALS endorsement shares (Section 12.2), and the baseball-level tables once received;
  - the 2025 roster geography below;
  - commit and portal behaviour as later data allows.
  The rest is GUESS, graded.

**Proximity, 2025 rosters** (`reports/proximity_2025.md`, `scripts/proximity_by_tier.py`, grade B):
- Data: hometown states from the roster aggregates; school locations from IPEDS (`data/ncaa_2025/school_locations_2025.csv`); out-of-state distances to the home state's Census centre of population.

| Tier | Schools | In-state | Within 300 mi | Within 500 mi | Within 1000 mi | Foreign | Mean miles, out-of-state players |
|---|---|---|---|---|---|---|---|
| P4 | 50 | .429 ± .221 | .586 ± .183 | .696 ± .166 | .869 ± .105 | .030 | 715 |
| Mid | 122 | .451 ± .260 | .640 ± .231 | .747 ± .192 | .876 ± .123 | .039 | 651 |
| Low | 60 | .386 ± .234 | .645 ± .227 | .721 ± .194 | .839 ± .136 | .048 | 612 |

- **Most rosters are regional at every tier.** About 60–65% of players come from within 300 miles and 84–88% from within 1,000.
- **P4 reaches modestly further:**
  - .586 within 300 miles against .64;
  - out-of-state players from 715 miles against 612.
- **School-to-school spread is wide in every tier** (SD about .2), so pipelines are school-specific.

**Pipelines (owner decision 2026-10-08).**
- Regional pipelines are central to recruiting at every tier.
- Blue bloods reach further only for the very top recruits. That reach is calibrated to the distance rows above: the P4 shortfall within 300 miles and the longer out-of-state distances.
- A distance-by-recruit-rank test needs recruit rankings, which are not public as data (Section 12.2).

## 3. The recruit

**Multi-class board.** Sophomores, juniors and seniors are tracked at once. Early commits are real.

**Each recruit has:**
- hidden true ratings and potential, on the engine's 20–80 scale (engine Phase 4);
- a development curve, with late bloomers possible (Phase 10);
- position, handedness and two-way ability;
- measurables: FB velocity, exit velocity, 60-yard time, pop time, height and weight. They are noisy, and correlated with the true ratings but not equal to them;
- academics (a GPA and test profile), which gate admission at elite academic schools;
- hidden makeup: loyalty, competitiveness, coachability and work ethic. Makeup affects decommits, portal risk and development;
- his top 3 priorities from the grade card, plus possibly one dealbreaker;
- a draft profile: projected round and signability ask;
- an asking price.

**Hand draws.** Handedness follows engine Phase 3's draw, by talent and position, and must also carry the Phase 9 requirement of 2026-10-08: recruiting values handedness beyond talent. At equal talent, left-handed pitchers end up at P4 more than at low-tier programs by +1.19 ± .50 log-odds (PHASE0_NOTES, Phase 3). In the recruiting loop that requirement becomes a preference: schools value left-handed arms beyond their ratings. It is gated by the left-handers-by-tier rows that are a watch item since Phase 3.

**Funnel.** Open → Top 8 → Top 5 → Top 3 → Verbal → Signed.
- Verbals can flip at real-data rates: more for early verbals and after coaching changes. A verbal is non-binding by rule: written aid offers are not allowed before August 1 of the senior year.
- Signed players are locked against other schools' contact, except through the MLB draft and the release conditions of Section 12.1, item 3: aid reduced, the head coach leaving (30 days), the school's release.

## 4. Scouting and information

- **Ranges.** Ratings are shown as OOTP-style ranges for current ability and potential (potential foggier). Ranges narrow with scouting.
- **Recruiting services.** 3–4 fictional services with different coverage maps and biases:
  - one driven by showcases and velocity;
  - one regional;
  - one that misses cold-weather kids.
  Their rankings disagree.
- **Events.** The user picks which showcases and travel-ball events to send staff to. Each event has its own talent mix and region.
- **Hidden gem sources:**
  - kids who skip showcases (cold-weather, rural, low-income);
  - late bloomers (a senior-year jump in velocity or size);
  - JUCO bounce-backs;
  - position or two-way surprises.
- **Who scouts.** There are no area scouts. Scouting is done by the recruiting coordinator, the pitching coach, the hitting coach and graduate assistants.
  - Each has an accuracy and learnable blind spots ("overrates velo", "knows Texas").
  - The pitching coach evaluates arms better; the hitting coach evaluates bats better.
  - GAs are cheap, improve each year and can become coordinators.
- **Measurables data.** Showcase distributions start from published averages, graded low confidence (C–D); most detailed data is paywalled.

## 5. The recruiting week (CFB model, real baseball calendar)

**Hours budget.**
- Each week has an hours budget (CFB-style): base hours plus staff contributions, with a per-recruit weekly cap.
- Staff and coach skills add hours. Hours drop during the user's own season.

**Actions:**
- text or DM;
- social media check (reveals a priority or a dealbreaker);
- phone call;
- watch him play;
- send staff to a showcase;
- camp invite;
- home visit (contact periods only; the number allowed follows the NCAA off-campus contact rules: from September 1 of the junior year, in contact periods; the per-prospect contact limit is not yet verified);
- unofficial visit;
- official visit: one per school per recruit (owner decision 2026-10-08):
  - **fall visits** (September to the fall-ball window) happen during fall ball: scrimmages and campus events, with facilities and campus life to the fore;
  - **spring visits** use home-series weekends, where Ballpark Atmosphere and that weekend's results matter;
- offer.

**Pitches (CFB-style).**
- The coach sells grade categories. Matching the recruit's priorities builds influence fast.
- A hard sell late in the funnel is a big gain or a big backfire.

**Legality.** The NCAA calendar decides which actions are legal each week: Contact / Quiet / Dead / Recruiting Shutdown (Section 12.1, item 1: a shutdown allows nothing, a dead period still allows calls and messages).

## 6. Money: one roster budget

**Three pools:**
- **Scholarship dollars.** Capacity is school-specific; out-of-state costs more than in-state.
- **Revenue-share allocation.** No per-sport rule exists (Section 12.1, item 4). Each athletic director's baseball allocation is school-specific, out of the athletics-wide cap (about $21.6M in 2026-27). It is scaled by the school's EADA baseball budget, and grows with revenue, attendance and winning. Graded GUESS (owner decision 2026-10-08).
- **NIL collective.** Grows with winning, Brand Exposure and facilities. The school cannot spend it directly.

**Offers.**
- An offer is a dollar package: scholarship % + revenue-share $ + an NIL collective commitment (owner decision 2026-10-08).
  - The NIL part is a commitment drawn from the collective's capacity, which the school influences but does not control.
  - It can fall through: a renewal and retention risk, more likely after losing seasons or a shrinking collective.
  - It is not counted in the school's cap.
  - Real deals are reported to NIL Go.
- Top recruits have asking prices tied to their ranking and draft projection.
- Money's pull depends on whether Money is one of his priorities.

**The cap.**
- One budget covers recruits and returning players, like a salary cap.
- Breakout players expect raises; underpaid players risk the portal.
- AI schools follow the same rules; blue bloods have far deeper pools.

**Data.** School-level baseball budgets are not public. Start from documented figures, scaled by conference and program revenue, graded C–D. The EADA and Knight Commission data are in Section 12.2.

## 7. Player flow between levels

**Paths.**
- HS → MLB draft (sign pro or go to college) → D1 / D2 / JUCO. No NAIA.
- **JUCO:** draft-eligible every year; transfers to D1 or D2 after 1–2 years. A hired JUCO coach brings his pipeline.
- **D2:** fully simulated, so its stats are real and scoutable; breakout players portal up to D1.
- **D1:** draft-eligible after the junior year or at age 21. Some players return for another year, often for NIL.
- **Eligibility** (owner decision 2026-10-08, as verified, Section 12.1, item 5): the five-year age-based clock from the earlier of first full-time college enrollment or the year after the 19th birthday. JUCO time counts; there are no redshirts and no seasons cap. Returning for "a senior year" is a question of years left on the clock.

**Transfer portal.**
- Opens at the real window dates, with the coaching-change and scholarship-change exceptions (Section 12.1, item 7).
- No AI tampering.
- Retention fights happen only at portal windows and at NIL / revenue-share renewal: meetings, raises, role promises.

**Roster limit.** The real 34-man limit (Section 12.1, item 4). The user makes his own cuts, with AI suggestions; AI programs cut automatically.

**Calibration.** Every flow rate is calibrated to real data: D2→D1, JUCO→D1, and the share of draftees who sign. The committed roster aggregates already give the previous-school origin of D1 players by tier (`origins_by_school.csv`, 2025):

| Tier | High school only | D1 transfer | JUCO | Other four-year | Unknown |
|---|---|---|---|---|---|
| P4 | .510 | .196 | .112 | .048 | .134 |
| Mid | .515 | .143 | .177 | .082 | .083 |
| Low | .445 | .087 | .206 | .097 | .166 |

Grade B: roster-listed previous schools, classified by rules in `origins_rules.csv`.

**Other levels.** The JUCO and D2 worlds are fully simulated on the same talent scale. For the levels the user isn't coaching, plan a quick-sim, validated against the full engine. The user's own games always use the full engine.

**On-field data for D2 and JUCO** (search of 2026-10-08):
- **D2: scores only, grade B.**
  - The data.ncaa.com scoreboard feed works for D2 with the same pattern as the D1 pulls (no robots file). About 135 requests per season.
  - Final scores, records, conferences and extra-inning markers; no box scores.
  - A scoreboard strength fit of D1 and D2 together places D2 on the one talent scale through crossover games. It gives D2 run distributions, home edge, extra-inning and run-rule rates.
  - League rates (K%, BB%, HR%) need box scores or season stats. Those are on www.ncaa.com, whose robots.txt now disallows AI agents, or on stats.ncaa.org (excluded). Not fetched; a hand export by the owner is possible.
- **JUCO: no usable source from here, grade D.**
  - NJCAA stats sit behind a client-rendered app on an undocumented API with unreadable terms.
  - The California and NJCAA region stats sites (Presto) return 403 to this environment; nothing was worked around.
  - JUCO is placed on the talent scale from the roster origin data (JUCO transfers' shares by tier, Section 7) plus documented guesses. Graded D and marked for replacement (owner decision 2026-10-08).
  - Options for the owner: a hand export of the NJCAA composite team stats, or asking the NJCAA for a data file.

## 8. MLB draft

- **Teams.** The 30 real MLB team names (personal-use project: names only, no logos or official artwork). Each has its own draft board, needs and bonus pool.
- **Rules: a selectable ruleset, stored as data** (owner decision 2026-10-08):
  - **"current"** (the default): 20 rounds; HS, JUCO and eligible four-year players; bonus pools with slot values for rounds 1–10 and the $150,000 rule after; the July signing deadline; the lottery (Section 12.1, item 6);
  - **"proposed"**: MLB's June 2026 proposal of 12 rounds, no high school or junior college players, hard slots.
  - The default is updated when the new labor agreement is signed.
- **Signability.** His projected round, and his number against the pick's value. The relationship, the NIL package and the school's Draft Development grade can lower his number.
- **Draft day.** A live event the user can watch.

## 9. Staff, career and AI programs

- **Staff.** Recruiting coordinator, pitching coach, hitting coach and graduate assistants. Each has ratings, regional knowledge and scouting tendencies. Staff can be poached.
- **Job market and hot seat.** AD expectations, firings and offers. The coaching carousel runs late May through July.
- **AI programs.**
  - Distinct personalities: analytics, old-school, JUCO-heavy, portal-heavy, regional loyalist.
  - Distinct budgets.
  - Regional pipelines are central at every tier; blue bloods reach further only for the very top recruits (Section 2: P4 rosters draw modestly further, .586 within 300 miles against .64).

## 10. The annual calendar

From the 2025–26 NCAA D1 baseball recruiting calendar; each year's official calendar is reloaded. The verification of every period is in Section 12.1, item 1.

| When | Period | Game content |
|---|---|---|
| Aug 1–17 | Contact | August 1 rush, a live event: the new junior class opens; offers and calls fly |
| Aug 18 – Sept 11 | Quiet | Campus visits (official and unofficial visits open September 1 of the junior year) |
| Sept 12 – Oct 12 | Contact | Fall ball plus the main recruiting window: official and home visits, fall showcases |
| Oct 13 – Feb 28 | Quiet, with exceptions | Nov 10–13 Dead (signing week; signing opens the second Wednesday of November); Nov 25–30 and Dec 22–27 Recruiting Shutdown (nothing allowed, not even calls); Jan 8–11 Dead (ABCA convention). December portal window Dec 1–15. Rosters due at 34 the day before the first counted contest or December 1, whichever is earlier, so cuts happen in late fall. Winter: staff hiring, budget allocation, facility projects, NIL / revenue-share renewals |
| Mid-February | Opening day | |
| Mar 1 – Jul 31 | Contact, with exceptions | May 25 – Jun 1, Jun 20–22 and Jul 3–5 Dead. Reduced recruiting hours in season; home series are visit weekends |
| June | | Postseason; the spring portal window (30 days from seven days after selections: June 1–30 in 2026, June 7 – July 6 in 2027), with Omaha teams recruiting the portal while playing; the coaching carousel |
| July | | MLB draft (live event) and signing deadline; summer travel ball and showcases: gem season for sophomores you can watch but not contact |

**Rules to enforce** (verified, Section 12.1, items 1–3 and 7):
- Calls and messages: from August 1 at the start of the junior year of high school. Before that, watching only.
- Off-campus contact, official visits and unofficial visits with athletics: from September 1 of the junior year.
- Written aid offers: from August 1 of the senior year. Earlier "offers" are verbal and non-binding, which is why early verbals flip.
- Official visits: one per school before October 15 after high school (one more if the head coach changes); no total cap.
- Signing: from the second Wednesday of November.
- Shutdown periods allow nothing; dead periods allow calls and correspondence.
- The calendar is generated from the Bylaw 13.17.1 formulas each year.

**Turns.**
- Weekly turns all year, with fast-forward through quiet stretches.
- Auto-pause on key events: a recruit narrowing his list, a decommit threat, a portal entry, a job offer, the draft. Settings can turn categories off.
- Summer collegiate leagues (fictional names) for the user's players' development and draft stock.

## 11. Not in this spec

The recruiting screens (board, recruit card, visit weekend, signing day, draft day) are designed separately and sent to the UI session.

## 12. Research (2026-10-08)

### 12.1 Rule verification

Checked 2026-10-08. The main source is the 2026-27 NCAA Division I Manual (LSDBi, https://web3.ncaa.org/lsdbi/reports/getReport/90008), whose bylaw revision dates show what applied in 2025-26. Grades as above.

mlb.com refused the fetches (HTTP 406, not worked around), so the MLB items rest on Baseball America and AP reporting. stats.ncaa.org and web.archive.org were not used.

**1. The 2025-26 recruiting calendar is confirmed as drafted (A).**
- Source: "2025-26 NCAA Recruiting Calendar, Division I Baseball", https://ncaaorg.s3.amazonaws.com/compliance/recruiting/calendar/2025-26/2025-26D1Rec_MBARecruitingCalendar.pdf; both text and grid were read.
- Nov 25–30 and Dec 22–27 are **Recruiting Shutdown**, a separate period type. During a shutdown nothing is allowed: no contacts, evaluations, visits, correspondence or calls. A dead period still allows calls and correspondence.
- The periods follow formulas in Bylaw 13.17.1, so future years can be generated (the 2026-27 calendar follows the same formulas):
  - signing week, Monday to Thursday;
  - Tuesday before Thanksgiving through Sunday;
  - the ABCA convention;
  - last Monday in May through the next Monday;
  - Saturday before Father's Day through the Monday after.

**2. Visits, contact and offers (A).**
- **Official visits:** not before September 1 of the junior year in high school (13.6.2.1.2). August 1 is the rule for other sports; secondary guides that say August 1 for baseball are wrong.
- **Unofficial visits** involving athletics: September 1 of the junior year (13.7.1.2).
- **Calls and electronic correspondence:** both ways from August 1 at the start of the junior year (13.1.3.1.1, 13.4.1.1; adopted 4/26/23).
- **Off-campus in-person contact:** September 1 of the junior year (13.1.1.1.1).
- **Written offers of athletics aid:** not before August 1 of the senior year (13.9.3.1).
- **Official visits per school:** one per school before October 15 after finishing high school and one after that (13.6.2.2), plus one more if the head coach changes. There is no cap on total official visits (removed 7/1/23).

**3. Signing (A).**
- The National Letter of Intent was replaced on October 8–9, 2024 by signing rules and written offers of athletics aid (Council proposal 2024-55).
- From 10/8/25 a revenue-share contract can be signed on the same dates.
- Baseball signing opens the second Wednesday in November at 7 a.m. (Nov 12, 2025; Nov 11, 2026) and stays open (13.02.13.1). Undergraduate transfers can sign from their window's first day; graduate transfers from October 1.
- **What a signature binds:** every other D1 or D2 school giving athletics aid must stop all contact (13.1.1.2). That ends only if:
  - the aid is reduced or cancelled;
  - the player becomes academically ineligible;
  - the player does not enroll full time;
  - the player asks for a release within 30 days of the head coach leaving; or
  - the school grants a release. It must answer a request within two business days, or the release is granted by default.

**4. Roster limit, aid and revenue sharing under the House settlement (A unless noted).**
- **Roster limit:** baseball 34 (Bylaw 17.2, effective 7/1/25), for the five defendant conferences and schools that opt in.
  - Rosters are due the day before the first contest counted for selection, or December 1, whichever is earlier.
  - Replacements after the deadline are allowed only for: injury before the first contest, exhausted eligibility, permanent ineligibility, or a player entering a professional draft.
  - Exempt from the limit:
    - designated student-athletes (those cut or at risk in 2025-26, reported by July 6, 2025), for as long as their eligibility lasts;
    - season-ending injuries before the deadline and medical disqualifications;
    - from 1/16/26, aid kept after a head coach leaves.
- **Scholarship limits:** sport-specific scholarship limits are gone (Board, June 23, 2025), so the 11.7 limit no longer exists. Aid above a sport's 2024-25 limit counts against the revenue-share cap, up to $2.5M (16.13.1.5).
- **Revenue-share cap:**
  - 22% of average Power 5 revenue (media, tickets, sponsorship): about **$21.58M per school in 2026-27**, +4% expected in 2027-28, then recalculated every three years (collegesportscommission.org). 2025-26: $20.5M (B).
  - No per-sport allocation rule. Every payment needs a written agreement entered in the College Athlete Payment System within five business days.
  - Non-opt-in schools: no roster limit under 17.2, and revenue sharing is for participating schools only (B/C).
- **NIL:** every D1 athlete must report third-party deals of $600 or more to NIL Go, run by the College Sports Commission (Bylaw 22.2.2).

**5. Eligibility: an age-based clock from August 1, 2026 (A for the rule, B for the litigation).**
- Adopted by the D1 Cabinet on 6/23–24/26, effective 8/1/26 (Manual 12.6; ncaa.org news 2026-06-23).
- The clock: five years from the earlier of first full-time college enrollment (including JUCO) or the academic year after the 19th birthday.
- No pause for a redshirt, transfer or time off; no four-seasons cap; no waivers except military service, religious missions and pregnancy.
- Transition:
  - mandatory for students first enrolling in fall 2027;
  - current athletes and fall-2026 enrollees get whichever rules favour them;
  - athletes whose eligibility ran out in 2025-26 get nothing more.
- Litigation (Pavia v. NCAA):
  - injunctions and a Board waiver in December 2024;
  - the Sixth Circuit dismissed the NCAA's appeal as moot on October 1, 2025;
  - the merits are pending; later 2026 rulings are reported but not verified (D).

**6. MLB draft (B; mlb.com refused).**
- **Eligibility:**
  - high school graduates who have not attended college;
  - four-year college players after the junior year, or at age 21 within 45 days of the draft;
  - junior college players in any year.
  Rule 4 itself was not read.
- **Format:** 20 rounds between June 1 and July 20, under the labor agreement that expires December 1, 2026.
- **Bonus pools:**
  - Rounds 1–10 carry slot values that sum to each team's pool.
  - In rounds 11–20, bonuses up to $150,000 don't count against the pool.
  - 2026: No. 1 slot $11,350,600, pools about $358.7M in total. 2025: No. 1 slot $11,075,900, pools $350.4M.
- **Overage penalties:** up to 5% over the pool, a 75% tax; more than 5%, at least a future first-round pick (higher tiers not verified).
- **Signing deadline 2026:** July 27, 5 p.m. ET.
- **Unsigned picks:** an unsigned second-rounder (No. 59) gave the team No. 60 the next year; the other compensation rules are not verified.
- **Lottery:** the top six picks among the 18 non-playoff teams; the three worst teams each have 16.5% at No. 1, with limits on repeat top-six picks.
- **Prospect Promotion Incentive:** a team earns a pick after round 1 when an eligible top prospect is on its Opening Day roster and meets the service-time and award conditions.
- **NCAA side:** MLB may pay a prospect's combine expenses (12.2.1.2.1). Players may not have an agent after enrolling; prospects enrolling from 8/1/26 may before.
- **Pending (a proposal, not a rule):** in June 2026 MLB proposed a 12-round draft from 2027 with no high school or junior college players and hard slots totalling $200M (AP). The new labor agreement could change the draft fundamentally (Section 14, item 13).

**7. Transfer portal (A).**
- **Windows:** two a year for baseball. Dec 1–15, and 30 days starting seven days after championship selections (13.1.1.4.1(h)).
  - 2025-26: Dec 1–15, 2025 and June 1–30, 2026.
  - 2026-27: Dec 1–15, 2026 and June 7–July 6, 2027.
  - The 45-day window of 2022 was cut to 30 days in October 2023.
- **Exceptions:**
  - head coach leaves or announces it: 30 days;
  - aid reduced, cancelled or not renewed: 30 days (from 1/14/26);
  - sport discontinued: any time;
  - graduate transfers: from October 1 to the end of the last window.
  - No exception was found for players cut because of the roster limit (D).
- **After the draft:** baseball has no draft declaration and no draft-based portal exception. The June window closes before the draft, so a drafted player who doesn't sign can move only through one of the exceptions above (B/C, inferred).

### 12.2 Calibration data inventory

Checked 2026-10-08; nothing was downloaded in bulk.

**Sites that blocked the check** (stopped at each, no workaround):
- knightnewhousedata.org: 403
- mlb.com/draft/tracker: 406
- cccbca.com: 403
- thebaseballcube.com: 403

**Not blocks, but worth knowing:**
- Old ncaa.org `.aspx` links (the 2022 transfer-portal dashboard) now redirect to the home page.
- The Perfect Game commitments page returned a server error.
- The EADA and NJCAA pages are JavaScript apps.

| Target | Best source | Contents | Access and terms | Grade |
|---|---|---|---|---|
| Proximity | Repo `hometown_by_school.csv`, `hometown_by_conference.csv` | Hometown state (and census region) by school, tier and conference; 233 of 283 teams; 99.3% of hometowns located | Committed, own | A for in-state and region shares; state-level only |
| | IPEDS directory (HD) / College Scorecard | Latitude and longitude of every institution, joinable by UNITID (also to EADA) | Free, public domain | A (school locations, not yet committed) |
| | Census state centroids | For school-to-home-state distances (hometowns are state-level) | Free, public domain | B |
| | Wikipedia, list of NCAA D1 baseball programs | State and conference of 304 programs | Free, CC BY-SA | B |
| | Repo `pbp/parsed/games_meta_2025.csv` | Venue coordinates for 173 home teams | Committed | C (stadiums, not campuses) |
| Flow rates | NCAA "Probability of Competing Beyond High School" (March 2026) | Baseball 2024-25: 472,598 HS players, 41,580 NCAA. HS to NCAA 8.8% (D1 2.7%, D2 2.6%, D3 3.5%). 2025 draft: 452 NCAA players drafted (431 D1); 15.3% of draft-eligible D1 players; 40.8% from the four P4 conferences | Free, official | A |
| | NFHS participation; NCAA sports sponsorship report | HS participants by state; NCAA squad sizes by division | Free | A |
| | Repo `origins_by_school.csv` | Roster origins by class, school and tier (Section 7) | Committed | A for stocks, not yearly flows |
| | NCAA transfer research dashboards | DI transfer composition by sport and year | Free; embedded dashboards, no download | B |
| | 64 Analytics | 2025 baseball portal: 6,255 entrants; 47.4% appeared in 2026 NCAA data | Free article (commercial firm) | C (NCAA landings only) |
| | D1Baseball transfer tracker | Portal movers | Paywall | D |
| | NJCAA / CCCBCA releases | "570+ NJCAA alumni" in the 2026 D1 tournament; about 185 Californian JUCO players to D1 a year | JS-rendered / blocked | C/D |
| Draft signing | Baseball-Reference draft pages | Every pick since 1965: round, signed Y/N, bonus, HS/4Yr/JC | Free to browse; ToS forbids automated access and tools built on scraped data; 20 requests a minute | B if exported by hand, no script |
| | Fan-compiled 2021–24 summary | HS picks sign about 100% in rounds 1–10, about 80% in 11–14, 50–60% in 15–18, 15–26% in 19–20; four-year college players about 97% | Message board, unsourced | C (to cross-check) |
| | MLB.com tracker, Baseball America, The Baseball Cube | | Blocked / paywall | D |
| Commit timing, decommits | NCAA GOALS 2025 instrument | Asks the grade of first contact and of commitment; sport-level answers not published (available on request from research@ncaa.org) | Free | C |
| | 2017 DI SAAC survey (secondary reports) | Baseball: 23% had verbal offers by sophomore year; 46% of men committed by 10th grade enrolled elsewhere | Free | C (before the 2022 contact rule) |
| | PBR "Data Dive: New Age Early Recruiting" (Indiana, Dec 2025) | Commit windows under the Aug 1 rule; 12.5% of early D1 commits decommitted (n = 32) | Free article | C |
| | Perfect Game commitment lists | | Login / error; ToS forbids automated access | D |
| Priority weights | NCAA GOALS 2025, DI slides | Factors in the choice, DI men (N = 2,990): chance to play 90%, academics 72%, liked the team 63%, cost 59%, facilities 56%, proximity 55%, the coach 55%, exposure 50%, pro-development reputation 40%, promised role 37%, NIL 23%. Transfer reasons: a higher level 46%, playing time 28%, coaching change 24% | Free, official | B (all DI men's sports; endorsement shares, not weights) |
| Showcase measurables | Rapsodo averages by age; Eisenmann velocity percentiles (ages 13–18); PMC10071191 (age drafted pitchers reached 90/92/95 mph); PBR / PG leaderboards | Medians and percentiles of user bases, and top-end tails | Free (some email or paywall) | C; no free distribution by grade or for D1 commits; pop time not found |
| Budgets, NIL | Dept. of Education EADA | Per institution and per sport (baseball): participants, revenue, expenses, yearly; Excel | Free, public domain | A |
| | NCAA finances dashboard and reports | Medians by subdivision | Free | B |
| | Knight-Newhouse | | Blocked | D |
| | Revenue-share and NIL by sport | Scattered reports only (e.g. one school's baseball share of its pool) | | C/D |

**Must be GUESS for now:**
- yearly JUCO→D1 and D2→D1 flow rates (only roster stocks exist);
- portal landing rates by destination level;
- the commit-grade distribution and decommit rates under the 2022 contact rule;
- baseball-specific priority weights;
- showcase distributions by grade and level, and pop time;
- baseball NIL and revenue-share amounts.

**Owner's calls before any of this is committed as data:**
- request the GOALS sport-level tables (commit timing; baseball priorities) from research@ncaa.org;
- whether hand-exported Baseball-Reference round pages are acceptable for draft signing rates, within its terms (no script);
- whether to commit IPEDS school coordinates (public domain) for real distances.

**What the data says about the owner's priority instinct:**
- **GOALS.** All DI men's sports, so endorsement shares, not weights. Playing time leads ("chance to play" 90%). Proximity (55%) sits with facilities (56%) and cost (59%). NIL is near the bottom (23%), and program tradition is not an item at all.
- **2025 rosters.** 39–45% in-state and 59–65% within 300 miles in every tier (Section 2, real distances).
- **Together.** They support Playing Time and Proximity as top priorities. They do not support Money as a top priority for most recruits; it may still be one for the top of a class, where asking prices live. Program Tradition is untested.


## 13. Phase mapping and proposed gates

**The principle.** Rosters stop being drawn and start being built. Every on-field gate of Phases 1–7 must still pass when rosters come from recruiting and development instead of from the talent draw. The recruiting loop has to reproduce, in steady state, the talent and team-strength distributions the engine is calibrated to. That is the gate that protects everything already built.

### Phase 8: roster rules (the container)

**Scope:**
- the 34-man roster limit, and roster composition by class, position and handedness;
- the eligibility clock and class years;
- redshirts, injuries and medical exemptions where the rules provide them;
- the money pools and cap accounting: scholarship %, revenue share, NIL as a separate collective;
- cuts (the user's, with AI suggestions; AI programs automatic);
- the rule side of player flow: portal windows and exceptions, draft eligibility, JUCO and D2 transfer rules.

No recruiting behaviour yet: rosters are filled by the existing talent draw, aged one year at a time.

**Proposed gate:**
- Roster size and class composition per team against the 2025 rosters. The roster aggregates have class year by school (`origins_by_school.csv`, class x origin).
- Origin shares by tier (the table in Section 7).
- Every Phase 1–7 row unchanged over 20+ simulated years of roster turnover, with the drawn-roster world as the baseline. Each year, the talent and team-strength distribution by tier must match the scoreboard decomposition.

### Phase 9: recruiting (this document's core)

**Scope:**
- recruit generation on the engine's talent scale;
- measurables, scouting and fog, services, staff evaluation;
- the recruiting week, the grade card, pitches, the funnel, offers and money decisions;
- AI schools and their personalities;
- portal recruiting and retention;
- the MLB draft, signability and the draft-day event;
- the calendar.

**Proposed gate** (40 simulated recruiting cycles, as the engine's 40 seasons):
- **Steady state:**
  - team strength by tier (means, SDs, conference effects) against the scoreboard decomposition;
  - year-to-year persistence of team strength against the real 2021–2025 scoreboards (Phase 7 data);
  - the talent distribution of each incoming class.
- **Geography:** in-state and in-region shares by tier (Section 2; school coordinates for distances).
- **Origins:** D1 transfers and JUCO shares of rosters by tier (Section 7).
- **Timing:** commit timing (grade at commitment) and decommit rates, if the data inventory finds a usable source; otherwise reported.
- **Draft:** draftees by level and tier, and signing rates by round, high school against college.
- **Handedness:** the left-handers-by-tier rows (the Phase 3 watch item; the Phase 9 requirement).
- **Equal terms:** human and AI recruiting on equal terms. An AI-coached copy of the user's program, given the same staff, budget and grade card, recruits classes of the same distribution (the recruiting analogue of the engine's equal-odds rule).

### Phase 10: development

**Scope:**
- development curves and aging, late bloomers, potential;
- makeup effects;
- coach and facility development effects (bounded and centred, so the league-wide development rate stays calibrated);
- summer collegiate leagues;
- draft stock as it evolves.

**Proposed gate:**
- Year-over-year changes in players' rates by class year against real multi-season college data, which is to be found (Section 12.2; the committed play-by-play has 2025 only).
- Draft results by draft class against recruit rank (the Draft Development grade's own definition).
- Every on-field gate unchanged.

### Phase 11: program, facilities and career

**Scope:**
- the grade card's earned categories and how they move;
- facilities projects;
- revenue and attendance growth, Brand Exposure;
- coach careers, the AD's expectations, the hot seat and the job market;
- staff hiring and poaching;
- AI program personalities over time.

**Proposed gate:**
- Head-coach turnover per year by tier against real D1 coaching changes (to be sourced).
- Persistence of program prestige: the correlation of team strength over 5 and 10 years against the scoreboard history.
- Budget distributions against EADA (Section 12.2).

### Phase 12

The UI, as already planned: the recruiting screens are designed separately.

## 14. Open issues: internal consistency and data risk

1. **Resolved: first contact.** Calls and messages open August 1 at the start of the junior year; visits and off-campus contact open September 1 (Section 12.1, item 2). The calendar and rules above now say so. The spec's "official visits" in the August 1 rush move to September 1.
2. **Resolved: signing.** Letters of intent no longer exist. A signature locks the player against other schools' contact, with defined releases (aid reduced, the head coach leaving, the school's release), and the funnel says so.
3. **"Home visit (once)."** The NCAA limits in-person, off-campus recruiting contacts per prospect; the limit isn't necessarily one home visit. The game should use the real contact limit (Section 12.1, item 2) rather than "once".
4. **Resolved (owner 2026-10-08): fall visits in fall ball, spring visits on home series** (Section 5).
5. **Resolved: roster cuts.** The 34-man roster is due the day before the first counted contest or December 1, whichever is earlier. Fall rosters can be larger, and cuts happen in late fall rather than August. The limit binds only at opted-in schools, so non-opt-in programs in the simulated world need their own roster model (Phase 8).
6. **Resolved (owner 2026-10-08): NIL in an offer is a collective commitment that can fall through** (Section 6).
7. **Resolved (owner 2026-10-08): priorities follow the data.** Playing Time and Proximity are strongest; Money is weak overall and stronger for draft-level recruits; regional pipelines are central. Real distances (IPEDS) show P4 reaching modestly further (Section 2).
8. **Resolved (owner 2026-10-08): coach skill-tree boosts are bounded and centred.** The original concern, kept for the build:
   - Development boosts and pitch effectiveness from XP must be bounded and centred: if every coach levels up, league-wide development cannot drift upward year over year. The engine rule against silent drift applies (CLAUDE.md, drift check).
   - AI coaches carry the same tree, so the effects are a distribution across programs, not a bonus for the user.
9. **Makeup, the relationship, pitch effectiveness, the hard-sell backfire, service biases and scout blind spots** have no data (grade D). They are GUESS by construction. They should be tuned only against the observable gates they move (decommit rates, portal rates, commit timing), never by feel.
10. **D2 and JUCO on-field data.** D2 has scores (data.ncaa.com, B) for a joint strength fit; JUCO has no usable source (D), so it is placed from roster origins and documented guesses (Section 7). Both levels' league rates are D1 engine rates at their talent level, a GUESS until box scores or season stats are available.
11. **Real MLB team names.** Fine for a personal-use project, as the owner states. It must stay names only, with no logos or official artwork, and no other real people (the game never uses real players).
12. **Resolved: calendar labels.** Confirmed, with the two holiday periods as Recruiting Shutdown. Each year's calendar is generated from the bylaw formulas and checked against the official PDF, stored as data, not hard-coded.
13. **Resolved (owner 2026-10-08): draft rules are a selectable ruleset** ("current" default, "proposed" option), updated when the new labor agreement is signed (Section 8).
14. **Eligibility is now an age-based five-year clock** (from 8/1/26): no seasons cap, no redshirt, no waivers, with JUCO time counting. That replaces class-year bookkeeping in Phase 8. "Some return for a senior year" becomes a question of how many years are left on the player's clock.
15. **Resolved (owner 2026-10-08): revenue share is a school-specific baseball allocation, scaled by EADA baseball budgets, graded GUESS** (Section 6).
16. **"No AI tampering" holds by rule.** Signing locks out other schools' contact, and the portal has fixed windows.
17. **www.ncaa.com disallows AI agents in its robots.txt** (found 2026-10-08). The project fetched its RPI page on 2026-10-05 (`data/README.md`). Nothing more is fetched from www.ncaa.com; data.ncaa.com (no robots file) is unaffected. The owner decides whether the committed copy stays.

