# app/ — playable game UI prototype (2026-10-08)

A browser-playable single game on top of the engine: a connector around `engine.game2.GameSession`, a thin web
API, and a static frontend that works on a phone and on a desktop. Nothing here changes an outcome: the engine
(`engine/`) is used as it is, the human's answers go through the same `Controller.answer` call and the same
positioned random generator as the AI's, and the page narrates what the engine recorded. The engine, `config/`
and `benchmarks.json` are untouched by this workstream.

| Module | Role |
|---|---|
| `world.py` | the exhibition world: the determinism test's league (seed 20261006), one engine per process, rosters with 20–80 ratings |
| `catalogue.py` | the decision catalogue built from `engine.control.DECISIONS`: who is asked, when, the answer's shape, validation against the engine's eligibility rules, feed text; a kind without a specific descriptor gets a generic one, so a decision PR B adds appears in the UI on merge |
| `connector.py` | `HumanController` (orders, autopilot, "ask me"), `RecordingAI` (the opponent, recorded for the feed), `GameRunner` (snapshot and replay, sim targets, the bench coach, save and load) |
| `timeline.py` | play-by-play and box score from the event log, the marks taken at every ask, and the engine's accumulator rows |
| `menu.py` | the action menu of the manager screen: the calls legal now for the user's side, built on the server from the turn and the engine state so the page never decides legality |
| `api.py` | FastAPI: league, rosters, catalogue, games, sim, orders, questions, modes, coach, box, save, load; serves `static/` |
| `static/v2/` | the manager screen (v2, served at `/`): lobby, scoreboard bar, matchup banner, field, action menu, lineup panel with the pregame editor, play-by-play drawer with the box score, callouts |
| `static/` (root) | the first frontend (v1), still served at `/static/index.html`: the same API, plainer screens |

Run locally: `pip install -r requirements.txt && uvicorn app.api:app --reload`, then open http://127.0.0.1:8000.
Tests: `pytest tests/test_app_connector.py tests/test_app_api.py tests/test_app_menu.py` (a few minutes). Latency:
`python3 scripts/bench_app.py` writes `reports/app_latency.md`.

Workflow (owner decision 2026-10-08): `ui-prototype` is the single live branch; Render auto-deploys every push. The
app tests and the API-vs-engine equality tests run before every push (never push a failing build). CI runs only the
app tests for changes under `app/`, its tests, docs and deploy files (`.github/workflows/app.yml`); engine and
config changes run the full gates (`tests.yml`). Engine PRs merged to `main` are merged into `ui-prototype`
promptly; `ui-prototype` goes back into `main` through a PR at natural checkpoints.

## The manager screen (v2)

The layout follows a quick-manage structure (scoreboard, matchup, field, calls, lineup, play-by-play); the visual
design is original (an evening-ballpark palette, team marks as initials in a color hashed from the team's name,
fictional teams). Zones, top to bottom on a phone, three columns on a desktop:

1. **Scoreboard bar**: line score with R/H/E; inning and half; balls, strikes and outs as separate counters.
2. **Matchup banner**: the batter (position, bats L/R once Phase 3 lands, batting-order ordinal, today's
   AB/H/RBI/BB/K) and the pitcher (role, throws, IP/H/R/BB/K, pitch count) with his 20–80 ratings. The bar under
   the pitcher is labeled **pitch count**: the engine has no fatigue state (the AI's pull hazard reads the
   outing's pitches and runs, `engine/manager.py`); if the pitcher card ever carries `fatigue`, the page shows and
   labels that instead. It is never the AI's pull probability. Season stats (AVG/HR/SB, W-L/ERA/IP) have their
   slots in the banner, hidden until season play exists: never faked.
3. **Field**: runners as markers (tap or hover: name, Speed, Contact, Power, today's line), the fielders by
   position faintly, the batter at the plate, due up.
4. **Action menu** (`menu.py`): only the calls legal now for the side you are on. Batting: swing away (default),
   bunt, steal and hit-and-run (only when the engine's lead-runner rule allows a steal; the label names the runner
   who goes; the engine has no double steal, so none is offered), pinch hit, pinch run per runner on base.
   Pitching: pitch (default), intentional walk, pitchout (a runner on), mound visit (greyed with the NCAA 9-4
   reason when a second trip with the same batter at bat would be refused), pitching change and defensive change
   (now, mid at-bat, through the pre-pitch call; or after the at-bat, through the window's decision). Tapping
   queues the order (tap again to cancel); the sim buttons proceed with the AI handling anything not queued. A kind
   switched to "ask me" stops with its question, answered in place. "Ask bench coach" shows the AI's next calls for
   your team. `tests/test_app_menu.py`: every offered call validates against the engine's eligibility rules on
   paused games, batting calls only when the user's team bats the coming pitch, pitching calls only when it fields.
5. **Lineup panel**: your batting order with position, bats, today's results color-coded and H-AB, the batter up
   and on deck marked; the opponent's lineup; the bullpen with each pitcher's status and Stamina. Before the game
   the panel is the lineup and starter editor (the AI's picks prefilled; Play ball sends them).
6. **Play-by-play** drawer (a tab on a phone), newest first, non-events hidden (a call held off, a lineup set, a
   dropped order); moves the AI made for your team carry an **AI** badge, yours **YOU**, the opponent's **OPP**; a
   box score tab.
7. **Callouts**: a brief overlay for the turn's big moment (runs, home run, strikeout, double play, stolen base,
   pitching change, the final), auto-dismissing, a tap skips it; after a long sim only runs and the final.

## How a decision reaches the engine

The engine asks each side's controller for its decisions synchronously, between two pause points: it pauses only
before a pitch, and between the last pitch of one plate appearance and the first of the next it asks the fielding
side about a pitching change and the batting side about a steal, a pinch hitter and a bunt, all inside one step.
A browser cannot answer a synchronous call, and an order placed at the pause before a pitch cannot apply to a
question the engine has already asked. The connector therefore works by **snapshot and replay**:

1. Before a pitch whose aftermath could need the human, the runner snapshots the session (`GameSession.save`
   without the engine, the two teams and the AI manager's tables by reference, plus the engine's accumulator rows
   of this game's players; about 1 ms).
2. The human's controller answers from its order book. When the human must be consulted it raises `AskHuman`:
   *soft* at a boundary (the first ask of the human's team once the sim target is reached: the plate appearance
   ended, the half or inning turned) and *hard* for a kind the human switched to "ask me".
3. The runner restores the snapshot and shows the abandoned pitch's events (the pitch, the result, a steal) with
   the question or the decision buttons. Those events are the real ones: with PR A's keyed streams every draw
   before a decision point depends on the game state and the seed only, never on who answers or how, so the
   replay reproduces them exactly, and the runner checks that it did (`RuntimeError` otherwise).
4. Orders and answers are queued per decision window (the number of completed plate appearances) and consumed
   when the engine asks; the pitch is re-run; anything not queued the AI answers with the same positioned
   generator it would have used (`tests/test_app_connector.py`: the runner's game equals the engine's, the
   questions path and the orders path equal a scripted `Controller`, save and load replay identically). A kind
   asked inside the coming pitch (the pre-pitch calls) targets the pause's own window.

**This is a prototype workaround.** The final engine (Phase 12) should pause natively at decision points, a
change that goes through the engine session with full gates (CLAUDE.md, architecture constraints). What carries
over is the contract: a decision catalogue built from `DECISIONS`, orders and answers per window, a turn that
reports state, events and the pending question, and the signed save.

Decision flow (owner decision 2026-10-08): every kind is on AI autopilot by default; the decision buttons for the
legal actions are shown before every pitch; tapping one queues it, and "next pitch" or any sim button proceeds
with the AI handling anything not queued; settings switch a kind to "ask me", which blocks with the question;
a move the AI makes for the human's team is marked **AUTO** in the feed; "Ask bench coach" shows what the AI would
do next (a dry run on a copy of the game, nothing is changed). Pinch runners are position players only (the bench
has no pitchers). Fatigue is shown as the pitch count and the outing's line next to the Stamina rating; the AI's
pull probability is not displayed.

What the engine does with each answer is stated on each button (`catalogue.py`). With PR B merged (2026-10-08) the
calls before a pitch are live: the human's controller is asked before every pitch (`per_pitch`), so an order queued at
the pause before a pitch applies to that pitch. Batting: steal or hit-and-run (a runner on first with second open, or
on second with third open; resolved on a ball or strike, the runner goes back on a foul, he was running on a ball in
play), bunt, swing away, a pinch runner. Fielding: pitchout, intentional ball, intentional walk (awarded without
pitches, NCAA 8-2-b), mound visit (NCAA 9-4: a second trip to the same pitcher in an inning removes him, three free
trips a game; a second trip with the same batter at bat is refused by the engine and reported in the turn), a
pitching change or a defensive sub mid at-bat. Before the plate appearance: a called bunt (every pitch until two
strikes) and the intentional walk. The PR A engine's per-plate-appearance steal (`steal_attempt`) is not asked while
the per-pitch steal model is on. The owner's example, a steal on a 2-0 count, is `tests/test_app_connector.py`
(`test_steal_on_2_0_through_the_connector`) and `tests/test_app_api.py` (through HTTP).

## Sim targets and stops

`pitch` plays one pitch; when it ends the plate appearance the turn stops at the boundary with the result and
the buttons for the next one, and the next `pitch` plays through the asks to the first pitch. `pa` plays to the
next boundary. `half`, `inning`, `three_innings` and `game` run to the target with the AI handling anything not
queued; an "ask me" kind still stops with its question, and the same target continues after the answer.

## Saves

`GET /api/games/{id}/save` returns the game at its resumable point as a signed blob (HMAC-SHA256 under
`CBS_SAVE_SECRET`; unpickling untrusted bytes runs code, so an unsigned or foreign blob is refused). The browser
mirrors the latest blob to `localStorage` after every turn and keeps named saves there too; a save can also be
downloaded as a file and loaded back. When the server has forgotten a game (a restart, the free host's nap) the
page reloads the mirror and continues. A game resumes identically on the same machine (CLAUDE.md: determinism is
per machine).

## Engine notes for the owner

- `engine/tables.py` keeps module-level caches keyed by `id()` of its table objects (`_err_split`, `_ok_split`).
  Building more than one engine in a process lets a freed table's address be reused by the next engine's, and a
  stale entry changes a draw. The app therefore builds one engine per process (as a season run does); the engine
  change (key the caches by the table's identity for its lifetime, or hang them on the table) is for the engine
  workstream.
- The engine's accumulators (`bstats`, `pstats`) run across games; the app's lines are differences against the
  rows copied at the game's creation, and a snapshot carries this game's rows only. Two games of the same team in
  one process share rows: their lines interleave (play is unaffected).

## Hosting

`render.yaml` deploys one free Render web service that serves both the API and the frontend. The frontend is
static files and could move to Vercel (or any static host) later with the API's URL configured in `app.js`;
for the prototype one service is simpler. Latency on Render's Free plan (0.1 CPU share): `reports/app_latency.md`.
