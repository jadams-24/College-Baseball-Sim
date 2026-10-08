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

**First evidence on Proximity** (`data/ncaa_2025/roster_aggregates/hometown_by_school.csv`, 232 of 277 D1 teams, 2025 rosters):
- About 45% of D1 roster players come from their school's state, and the share barely moves by tier: P4 .449, mid .475, low .418 (mean over schools).
- About 73% come from the school's census region: P4 .724, mid .771, low .720.
- Foreign players: P4 .030, mid .039, low .048.
- Grade C. No school locations are committed, so a school's state here is its most common hometown state; real distances need school coordinates (Section 12.2).
- **This disagrees with the owner's instinct in two ways:**
  - Proximity looks like a top-tier priority for most recruits. It is not in the instinct's top five.
  - "Blue bloods recruit nationally; small schools mine their region" is not visible at the state or region level. P4 rosters are as local as low-tier rosters. P4 schools may still recruit more nationally at the very top of a class; the distance-by-ranking test needs school coordinates and recruit rankings.

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
- Verbals can flip at real-data rates: more for early verbals and after coaching changes.
- Signed players are locked except for the MLB draft (but see Section 12.1, item 3: the signing instrument has changed).

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
- home visit (contact periods only; the number allowed follows the NCAA's off-campus contact limits, Section 12.1);
- unofficial visit;
- official visit: one per school per recruit, hosted on a home-series weekend, so Ballpark Atmosphere and that weekend's results matter (but see Section 14, item 4: fall visits);
- offer.

**Pitches (CFB-style).**
- The coach sells grade categories. Matching the recruit's priorities builds influence fast.
- A hard sell late in the funnel is a big gain or a big backfire.

**Legality.** The NCAA calendar decides which actions are legal each week: Contact / Quiet / Dead (and any other period types the official calendar uses; Section 12.1).

## 6. Money: one roster budget

**Three pools:**
- **Scholarship dollars.** Capacity is school-specific; out-of-state costs more than in-state.
- **Revenue-share allocation.** Grows with revenue, attendance and winning.
- **NIL collective.** Grows with winning, Brand Exposure and facilities. The school cannot spend it directly (Section 14, item 6).

**Offers.**
- An offer is a dollar package: scholarship % + revenue-share $ + NIL $.
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
- **D1:** draft-eligible after the junior year or at age 21. Some players return for their senior year, often for NIL.

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

## 8. MLB draft

- **Teams.** The 30 real MLB team names (personal-use project: names only, no logos or official artwork). Each has its own draft board, needs and bonus pool.
- **Rules.** Real draft rules: rounds, eligibility, bonus values by pick (Section 12.1, item 6).
- **Signability.** His projected round, and his number against the pick's value. The relationship, the NIL package and the school's Draft Development grade can lower his number.
- **Draft day.** A live event the user can watch.

## 9. Staff, career and AI programs

- **Staff.** Recruiting coordinator, pitching coach, hitting coach and graduate assistants. Each has ratings, regional knowledge and scouting tendencies. Staff can be poached.
- **Job market and hot seat.** AD expectations, firings and offers. The coaching carousel runs late May through July.
- **AI programs.**
  - Distinct personalities: analytics, old-school, JUCO-heavy, portal-heavy, regional loyalist.
  - Distinct budgets.
  - Blue bloods recruit nationally and small schools mine their region. The 2025 rosters do not yet show this at the state level (Section 2); it is to be tested by distance and recruit ranking.

## 10. The annual calendar

From the 2025–26 NCAA D1 baseball recruiting calendar; each year's official calendar is reloaded. The verification of every period is in Section 12.1, item 1.

| When | Period | Game content |
|---|---|---|
| Aug 1–17 | Contact | August 1 rush, a live event: the new junior class opens; offers and calls fly |
| Aug 18 – Sept 11 | Quiet | Campus visits; roster cuts to 34 |
| Sept 12 – Oct 12 | Contact | Fall ball plus the main recruiting window: official and home visits, fall showcases |
| Oct 13 – Feb 28 | Quiet, with exceptions | Nov 10–13 Dead (signing week); Nov 25–30 and Dec 22–27 (label to be verified); Jan 8–11 Dead. Winter: staff hiring, budget allocation, facility projects, NIL / revenue-share renewals |
| Mid-February | Opening day | |
| Mar 1 – Jul 31 | Contact, with exceptions | May 25 – Jun 1, Jun 20–22 and Jul 3–5 Dead. Reduced recruiting hours in season; home series are visit weekends |
| June | | Postseason; the portal window (dates to be verified), with Omaha teams recruiting the portal while playing; the coaching carousel |
| July | | MLB draft (live event) and signing deadline; summer travel ball and showcases: gem season for sophomores you can watch but not contact |

**Rules to enforce** (wording to be checked against the official rules, Section 12.1, item 2):
- No recruiting communication before August 1 before the recruit's junior year of high school; watching only before then.
- Unofficial visits with recruiting talk from the date the rules allow.
- One official visit per school per recruit.

**Turns.**
- Weekly turns all year, with fast-forward through quiet stretches.
- Auto-pause on key events: a recruit narrowing his list, a decommit threat, a portal entry, a job offer, the draft. Settings can turn categories off.
- Summer collegiate leagues (fictional names) for the user's players' development and draft stock.

## 11. Not in this spec

The recruiting screens (board, recruit card, visit weekend, signing day, draft day) are designed separately and sent to the UI session.

## 12. Research (2026-10-08)

### 12.1 Rule verification
To be filled from the verification pass, with citations and grades.

### 12.2 Calibration data inventory
To be filled from the data inventory, with grades.

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

1. **"No communication before Aug 1 of junior year."** The NCAA rule reads "August 1 before the prospect's junior year in high school", that is, rising juniors. The spec's calendar ("August 1 rush: the new junior class opens") already uses that meaning. The wording should say "before the junior year" so the code doesn't wait a year.
2. **"Signed players are locked except for the MLB draft."** National Letters of Intent were replaced by athletic aid agreements, which changes what a signature binds (Section 12.1, item 3). "Locked" may need to become "locked unless the school releases him or the head coach leaves", per the current rules.
3. **"Home visit (once)."** The NCAA limits in-person, off-campus recruiting contacts per prospect; the limit isn't necessarily one home visit. The game should use the real contact limit (Section 12.1, item 2) rather than "once".
4. **"Official visits hosted on home-series weekends."** The main visit window in the calendar is September 12 – October 12, during fall ball, when there are no home series. Proposal:
   - fall visits feature fall ball, scrimmages and facilities;
   - spring visits feature a home series, where Ballpark Atmosphere and the weekend's results matter.
5. **"Roster cuts to 34" in the August–September quiet period.** When the 34-man limit applies (a date, or the first contest) is to be verified (Section 12.1, item 4). If it binds only at the first spring contest, fall rosters can be larger and the cut moves to winter.
6. **NIL in offers versus "NIL collective: not directly spendable".** An offer that names NIL dollars is a promise the school cannot make directly. Under the NIL clearinghouse rules a deal needs a valid business purpose. Proposal:
   - the NIL part of an offer is a collective commitment, drawn from the collective's capacity, which the school influences but does not control;
   - it can fall through (a renewal risk) and is not counted in the school's cap.
7. **Proximity as a priority.** The 2025 rosters (Section 2) suggest Proximity matters more than the owner's top five: about 45% in-state and 73% in-region in every tier. They also show "blue bloods recruit nationally" weakly or not at all at the state level. Calibrate before fixing the weights; distances need school coordinates.
8. **Coach skill-tree boosts against calibration.**
   - Development boosts and pitch effectiveness from XP must be bounded and centred: if every coach levels up, league-wide development cannot drift upward year over year. The engine rule against silent drift applies (CLAUDE.md, drift check).
   - AI coaches carry the same tree, so the effects are a distribution across programs, not a bonus for the user.
9. **Makeup, the relationship, pitch effectiveness, the hard-sell backfire, service biases and scout blind spots** have no data (grade D). They are GUESS by construction. They should be tuned only against the observable gates they move (decommit rates, portal rates, commit timing), never by feel.
10. **D2 and JUCO "fully simulated, stats real and scoutable".**
    - The repository has no D2 or JUCO play-by-play or box scores. The on-field model for those levels would be the D1 engine on a lower talent scale, which is a GUESS until D2/JUCO data is found.
    - The quick-sim must be validated against the full engine at those levels, as planned.
11. **Real MLB team names.** Fine for a personal-use project, as the owner states. It must stay names only, with no logos or official artwork, and no other real people (the game never uses real players).
12. **Calendar labels and dates** are pending verification (Section 12.1); a few came from a hard-to-read PDF. Each year's official calendar is to be loaded as data (`data/`), not hard-coded.

