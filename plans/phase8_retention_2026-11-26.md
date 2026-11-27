# Phase 8: who stays, who leaves, and what the coach can do about it

Owner request, 2026-11-26: departures by class only are wrong (a star junior was no more likely to leave than a weak
one). Model the system on College Football 27's roster retention, avoid what its players complain about, and
calibrate it to our data.

## What College Football 27 does
- Every player shows a **Risk of Leaving** on the roster screen, with a reason: NIL (he wants more money), a
  dealbreaker (the school's grade in something he cares about fell below his line, usually playing time), or the NFL
  Draft.
- After the season a **Players Leaving** stage lists who intends to go. The coach gets a limited number of persuasion
  attempts, each with a shown chance; a failed attempt is final.
- One shared budget pays for recruits, transfers and retention.

## What its players complain about (EA forums and guide sites; Reddit could not be reached from this workspace)
- Persuasion chance shown as "None" for players the coach most wants to keep.
- Players who were paid and left anyway.
- A dealbreaker that fails suddenly, with no warning during the season.
- Reasons that make no sense (a starter leaving for playing time).
- Transfers who vanish instead of landing somewhere.
- No control over how many players declare for the draft.

## Our rules, from those complaints
1. The risk and its reason are visible all season, from the same numbers the offseason uses.
2. The reason must be true: it is derived from the player's class and playing time, the things that set his rate.
3. Every persuasion chance is a number, never "None", except where a rule forbids staying (the fifth year).
4. Rates come from data: `data/wmt_player_seasons/retention_by_class.csv` (class x role x playing time, 2022-2025).

## The data (same program next season, seasons pooled)
| Class | Under 50 PA/BF | Least-used third | Middle third | Most-used third |
|---|---|---|---|---|
| Fr batters / pitchers | .47 / .44 | .82 / .77 | .87 / .89 | .92 / .84 |
| So | .46 / .46 | .71 / .64 | .77 / .75 | .73 / .73 |
| Jr | .43 / .43 | .59 / .52 | .63 / .57 | .42 / .40 |
| Sr | .13 / .16 | .12 / .08 | .12 / .16 | .11 / .11 |

Playing time is most of the story for underclassmen (a freshman who played stays about twice as often as one who
did not); the most-used juniors leave most (the draft). Seniors' rates predate the five-year clock.

## Steps
1. **Who leaves by class, role and playing time** (built 2026-11-26, `engine/roster.py`, `config/phase8.py`): the
   table above; a plan step (who leaves, each rate, a reason) and an apply step, so the app shows the Risk of Leaving
   column and the Players Leaving stage in between. Persuasion (owner, 2026-11-26): one attempt per player, 3 to 8
   attempts per offseason by coaching attributes (the skill tree, later; 3 until then). GUESS: an attempt succeeds
   with the player's own stay rate. Reasons are display labels until steps 2 and 3 give them mechanisms.
2. **The draft**: the sign-or-return decision from draft position and signability (`mlb_draft_2021_2026` in the
   yardstick), replacing the "MLB Draft" label; a draft-rules setting.
3. **Money pools and persuasion levers**: one roster budget (scholarship, revenue share, NIL collective); retention
   offers raise a player's stay rate; a paid player who still leaves refunds the offer.
4. **Dealbreakers on the 13 report-card grades**, with an in-season warning before one fails.
5. **Development** (built 2026-11-27, out of order by owner decision): a returner changes by his class's mean gain plus his own rate plus noise; potential is his projected ratings; newcomers arrive lower so the league holds (PHASE8_NOTES, Development).
6. **Rosters deeper than the players who appear**, then cuts to 34.
7. Where leavers land (the portal) and where newcomers come from: Phase 9.
Coaching trees after these; injuries much later.

## Development multipliers (owner decision 2026-11-27; to build with Phases 10 and 11, not yet built)
Development gets multipliers from the program, on top of the class gains, the player's own rate and luck:
- **Facilities**, by what they train: an indoor hitting lab develops hitters better (Contact, Power, Eye, Avoid K), a
  pitching lab pitchers (Stuff, Control, Movement), a weight room and training staff the tools (Stamina, Arm, Speed),
  a fielding facility Glove. Each is a bounded multiplier on the mean gain of its ratings.
- **Coaching trees**: the Developer branch raises gains, by side (hitting coach, pitching coach), also bounded.
- **Playing time** (candidate): a player who plays develops faster than one who sits.
Rules: multipliers are bounded and centred (the spec's "coach development boosts are bounded and centred"), so the
league's mean talent holds: a program above the average boost gains what programs below it lose, and the newcomers'
shift (`engine/roster.py` `_steady`) absorbs the rest. AI programs get them from the same facilities and coaches.
Hook: `engine/roster.py` applies `cmean[side][class]` and `DEV_TOOLS[tool][class]` per player; the multiplier is a
per-team, per-rating factor on those two terms.

