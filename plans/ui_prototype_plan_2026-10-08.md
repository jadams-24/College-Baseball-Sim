# Playable game UI prototype — plan for approval (2026-10-08)

Workstream: a browser-playable single game on top of the engine as it stands after PR A (engine restructure:
`GameSession`, one controller per team, keyed random streams, save and restore). The engine (`engine/`), `config/`
and `benchmarks.json` are not touched. Everything new lives in `app/` (connector layer, web API, static frontend),
`tests/test_app_api.py` and the deploy files. The connector layer is designed to carry into Phase 12.

Approved 2026-10-08 with these changes (owner): Render's Free plan serves both the API and the frontend (Vercel for the
frontend is a possible later move, noted in `app/README.md`); the decision flow is non-blocking by default, every kind on AI
autopilot, the legal decision buttons shown before every pitch, orders queued and the AI handling anything not queued,
"ask me" per kind as a setting, AI moves for the user's team marked in the feed; the AI's pull probability is not shown
(pitch count and the outing's line are, plus an "Ask bench coach" button); pinch runners are position players only;
per-pitch and per-step latency measured for a 0.1 CPU / 512 MB host before building further (`reports/app_latency.md`);
CLAUDE.md notes that snapshot-and-replay is a prototype workaround and that the final engine should pause natively at
decision points. Built on branch `ui-prototype`; what was built is described in `app/README.md`.


## 1. What the engine offers today, and the one problem to solve

- `GameSession.run(stop)` plays forward and pauses **before a pitch**; `sim_ahead(target)` stops at the next
  pitch, plate appearance, half inning, inning, three innings or the end of the game, with an AI controller managing
  a side meanwhile; `save()` / `load()` pickle the session at a pause point (70 KB without the engine).
- Every decision goes through `GameSession.ask(side, kind, ...)` to that side's `Controller.answer(kind, state,
  rng, *args)`. The kinds are `engine.control.DECISIONS`: lineup, starting_pitcher (pregame); defensive_subs,
  relief_pitcher (start of a half in the field); steal_attempt, pinch_hit, intentional_walk, bunt (before a plate
  appearance); pinch_runner (right after the batter reaches); pitching_change (after every plate appearance).
- The problem: the engine asks these questions **between** two pause points. From the pause before the last pitch
  of one plate appearance to the pause before the first pitch of the next, the engine asks the fielding side about a
  pitching change and the batting side about a steal, a pinch hitter and a bunt, all inside one `run` step. A human
  cannot answer a synchronous call from a browser, and a standing order placed at the pause point would apply to the
  *next* batter, not the one the user is looking at.

**Solution (no engine change): ask by snapshot and replay.** The connector's `HumanController` answers from an
order book; when the engine asks a question the book does not cover, it raises `DecisionNeeded(kind, args)`. The
runner snapshots the session (`save(include_engine=False)`) before every step, so on `DecisionNeeded` it restores
the snapshot, reports the question to the user together with the events that happened before it (the previous
pitch, the plate appearance's result, a steal), and when the answer arrives it records it as an order and re-runs
the step. The events reported before the question are the real ones: with PR A's keyed streams every draw before
a decision point is a function of the game state and the seed only, never of who answers or how, so the replay
reproduces them exactly (the runner asserts this on every replay). Human and AI answers are then resolved by the
same engine code with the same positioned generator: identical odds (`tests/test_session_determinism.py`, part 3).

Accounting caveat, stated once: the engine's season accumulators (`bstats`, `pstats`, `outings`, pitch records)
count an aborted partial step twice. Play never reads them (the `save` docstring's guarantee), and the prototype
builds every box score and line from the session's own event log and state differences, never from the
accumulators. The engine the API holds is an exhibition engine whose accumulators are discarded.

## 2. Connector layer (`app/connector.py`) — the part that carries into Phase 12

- `HumanController(Controller)`: picklable (it is saved inside the session). Holds an order book keyed by decision
  kind, a per-kind **mode** and a reference to the AI controller of the same side.
  - mode `ask` (default for every kind): answer from the order book, else raise `DecisionNeeded`;
  - mode `auto`: hand the call to the AI controller with the same positioned generator (what the AI would do at
    this point, exactly; `MirrorHuman` in the determinism test is this);
  - every answer is validated against the engine's eligibility before it is placed: a pinch hitter or runner is a
    batter not yet in the game (`state.in_game`), a reliever is a staff pitcher not yet used (`state.used`), a
    defensive substitution is `[(slot, bench player)]`, a lineup is nine distinct batters of the team, a starting
    pitcher is any staff pitcher. (The AI restricts pinch runners to faster players; the human may pick anyone.)
- `GameRunner`: owns one `GameSession` plus its latest snapshot. `step(target)` runs `sim_ahead(target)` (or the
  first `run` for the pregame), catching `DecisionNeeded`; returns a **turn**: the events since the last turn,
  the state, and the pending question if any. `answer(kind, value)` places the order and re-runs the same step.
  While simming past a single pitch (`pa`, `half`, `inning`, `three_innings`, `game`) the AI controller manages
  the user's side (`sim_ahead(..., ai_side=user, ai=AIController(session.book))`, as the spec requires), and
  control returns at the stop.
- **Decision catalogue**, built at import from `engine.control.DECISIONS`: for each kind a descriptor says which
  side it belongs to, when the engine asks it, the answer type (`yes_no_league_rate`, `pick_batter`,
  `pick_pitcher`, `defensive_subs`, `lineup`, `pick_pitcher_or_none`) and the label. A kind present in
  `DECISIONS` without a descriptor gets a generic descriptor (yes / no / league rate, shown with its raw
  arguments), so a decision PR B adds appears in the UI automatically on merge; giving it a proper descriptor is a
  one-line follow-up. The API serves the catalogue; the frontend builds its buttons from it and hard-codes nothing.
- **Plate-appearance panel**: the engine asks a side's questions at a boundary in a fixed order (fielding:
  pitching_change, then relief_pitcher if yes; batting: steal_attempt if a runner is on, pinch_hit; fielding:
  intentional_walk; batting: bunt). The runner groups the user's side's questions at one boundary into one panel so
  the user answers once per plate appearance, with the defaults preselected (no change, let them play); each
  answer is matched to the engine's ask by kind and replay fills them in one by one. pinch_runner (after a hit)
  and defensive_subs / relief_pitcher at a half start are their own panels, each shown with the event that caused
  it. The pregame panel is lineup and starting pitcher, prefilled with the AI's suggestion (the AI's lineup and
  starter are computed by asking the AI controller at the same decision point, so "accept" gives exactly the AI's
  game).
- **Timeline** (`app/timeline.py`): turns the session's event log (`('p', pa, sym)`, `('pa', ...)`, `('run',
  ...)`, `('final', ...)`) plus state differences across each step (score, outs, bases, lineups, pitcher, pitch
  counts) into play-by-play lines and running batter and pitcher lines for the box score. The UI never computes an
  outcome; it narrates what the engine recorded.
- Fixed exhibition league: `build_league(cfg, Generator(PCG64(LEAGUE_SEED)))` once per process (2.8 s here;
  307 teams, 10,745 players; process RSS 55 MB with the engine and manager). Games are weekend games in week 1
  (the rotation's game-1 starter). The pickled session carries its own copies of both teams, so a save continues
  with the same players on any process.

## 3. Web API (`app/api.py`, FastAPI + uvicorn, JSON)

| Method, path | Purpose |
|---|---|
| `GET /api/league` | teams: id, name, conference, tier |
| `GET /api/teams/{tid}` | roster with 20–80 ratings, positions, roles (batting order rank, rotation slot, bullpen rank) |
| `GET /api/decisions` | the decision catalogue (kinds, side, answer type, labels) |
| `POST /api/games` | `{home, away, user_side, seed?, modes?}` → new game; returns the first turn (the pregame panel) |
| `GET /api/games/{id}` | current turn: state, pending question, events so far |
| `POST /api/games/{id}/sim` | `{target: pitch | pa | half | inning | three_innings | game}` → turn |
| `POST /api/games/{id}/decide` | `{kind, answer}` → answers the pending question, replays, returns the next turn |
| `POST /api/games/{id}/modes` | `{kind: ask | auto}` per decision kind (an autopilot toggle per decision) |
| `GET /api/games/{id}/box` | box score and play-by-play from the timeline |
| `GET /api/games/{id}/save` | the save blob (the session at the current pause point, base64) |
| `POST /api/games/load` | `{save}` → a game id for the restored session, and its turn |

State JSON (one object, every screen reads it): line score by inning, score, inning, half, outs, count, bases
with runner names, batter and pitcher (name, ratings, today's line, pitcher's pitches / runs / batters faced and
Stamina), due up, both lineups with substitutions, bench (eligible pinch hitters and runners), bullpen (unused
pitchers with ratings and role), pending question (kind, options, defaults), `phase` (`pregame`, `pitch`,
`over`). Fatigue is shown as the pitch count and outing runs next to the Stamina rating; the AI manager's pull
hazard at this count (its table, `Manager._hazard`, read-only) is shown as "the AI would pull here with p = …" —
informational, never an outcome.

Games live in server memory (a dict keyed by game id). The browser keeps the latest save blob in `localStorage`
after every turn; when the server has forgotten the game (restart, free-tier spin-down) the frontend re-uploads
the blob to `/api/games/load` and continues, so a sleeping host costs a wait, never the game. Named saves: the
same blob stored under a name in `localStorage` and offered as a file download; load accepts either.

## 4. Screen sketch (`app/static/`, one page, vanilla JS and CSS, no build step, mobile-first)

```
┌──────────────────────────────────────────────┐
│ Team picker: [home team ▾] [away team ▾]      │   307 teams, searchable, grouped by conference
│ Manage: (•) home ( ) away   [seed]  [Play]    │   and tier; "random matchup" button
└──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│ Line score  1 2 3 4 5 6 7 8 9 | R H E          │
│ Foxes       0 1 0 . . . . . . | 1 3 0          │
│ Rams        2 0 . . . . . . . | 2 4 1          │
│ ▲ Top 3   ● ○ outs   count 2-0    ◇ diamond   │   diamond: runners' names on the bases
├──────────────────────────────────────────────┤
│ AT BAT  J. Halvorson (CF, bats 3rd)           │   20–80: Contact Gap Power Eye AvoidK Speed
│   52 61 44 58 49 66    today 1-2, 2B          │
│ PITCHING  R. Thezang (SP1)  P 67  R 2  BF 15  │   20–80: Stuff Control Movement Stamina
│   46 53 35 54          AI pull p = .08        │
├──────────────────────────────────────────────┤
│ DECISIONS (your team, this plate appearance)  │   built from /api/decisions; only the kinds
│ [Pinch hit ▾] [Bunt: let them play ▾]         │   the engine asks your side at this point
│ [Steal: let them play ▾]   [Pull pitcher ▾]   │   are shown; the rest are greyed with the
│ [IBB: let them play ▾]   autopilot ⚙          │   reason ("not your team's call", "no runner")
├──────────────────────────────────────────────┤
│ [Next pitch] [At-bat] [½ inn] [Inning] [3 inn] [End]   [Save] [Load] [Box score]
├──────────────────────────────────────────────┤
│ PLAY-BY-PLAY (newest first)                   │
│ 2-0: Ball.                                    │
│ 1-0: Ball.                                    │
│ Halvorson doubles to left; Okafor scores.     │
│ Pitching change: Thezang out, Marsh in.       │
└──────────────────────────────────────────────┘
```

On a phone the panels stack in this order and the sim buttons are a fixed bar at the bottom; on desktop the
play-by-play sits in a right-hand column. Pickers (pinch hitter, pinch runner, reliever, defensive change, lineup
and starter) open as full-screen sheets listing the eligible players with their ratings and today's line. When a
question is pending, the sim buttons are disabled until it is answered (the engine is waiting). After the final
out the screen shows the box score: both line-ups' lines, both staffs' lines, the full play-by-play.

Pitch-by-pitch rhythm: "Next pitch" from a pause shows the next pitch; when a pitch ends the plate appearance the
turn stops at the boundary with the result and the user's panel for the next plate appearance (defaults
preselected, so one more tap continues). Sim-ahead buttons hand the user's side to the AI until the stop, as the
product requirement says; at the stop the user is back in charge. Pitch-level decisions from PR B (a steal on 2-0,
a pitchout) will show up at the pause before a pitch through the same `DecisionNeeded` path.

## 5. Tests (`tests/test_app_api.py`, FastAPI `TestClient`; seconds, not minutes)

1. **API equals the engine.** A seeded random policy makes a sequence of decisions (pinch hitters, pulls with a
   chosen reliever, forced steals and bunts, intentional walks, defensive changes, a chosen lineup and starter)
   through the API, mixing single pitches, sim-ahead targets and answered questions. The same seed and the same
   answers are given directly to a `GameSession` through a scripted `Controller`. The session event logs and final
   states are identical. This covers snapshot-and-replay, the panel grouping and the AI-managed sim-ahead.
2. **Save and load replay identically.** At random turns the game is saved through the API, the server copy is
   deleted, the blob is loaded through the API and the remaining script is played; the log equals the uninterrupted
   API game. One case loads the blob in a fresh process.
3. **Catalogue covers the engine.** Every kind in `engine.control.DECISIONS` has a descriptor (generic or
   specific), and every descriptor's answer type validates and serializes a round trip. When PR B adds a kind this
   test keeps passing on the generic descriptor and a second, informational check lists the kinds still on it.
4. **Equal odds through the API.** The same decisions given by the human controller through the API and by a
   policy-following AI manager give the same game (the API-level twin of determinism test 3).

Engine gate tests are untouched; the PR runs the whole suite in CI as every PR does. New dependencies, pinned in
`requirements.txt`: `fastapi`, `uvicorn`, `httpx` (for `TestClient`).

## 6. Hosting

Measured here: 55 MB RSS with the league, engine and manager loaded; 2.8 s to build the league at startup; one
turn is well under a millisecond of engine time, so any tier fits. The owner wants nothing installed locally, so
only platforms that deploy straight from the GitHub repository with a browser were compared (checked on the
platforms' own pages on 2026-10-08).

| Platform | Cost | Python backend | Sleeps? / cold start | Deploy from GitHub | Verdict |
|---|---|---|---|---|---|
| **Render, Free plan** | $0, no card needed; 750 free instance hours per month per workspace; 512 MB RAM, 0.1 CPU | Yes, native (`pip install -r requirements.txt`, start command) | Spins down after 15 min without traffic; about one minute to come back (Render shows a loading page) | Yes: connect the repo, auto-deploy on push; a `render.yaml` in the repo makes it one click | **Recommended** |
| Railway, Free plan | 30-day trial with $5 credit, then $1 per month; 1 vCPU / 0.5 GB per service; no card to start | Yes, native (detects Python) | Does not sleep by default | Yes, one click from the repo | Runner-up: no cold start, but not $0 after the trial |
| Fly.io | No free allowance for new organizations (short trial); a 256 MB machine that auto-stops costs about $2 per month plus $2 per month for a dedicated IPv4 if wanted | Yes (Dockerfile or buildpack) | Auto-stop on idle, roughly 5 s to wake | Only through a GitHub Action with an API token: more setup | Third: best wake time, but paid and more clicks |
| Hugging Face Spaces | Docker and Gradio Spaces now require a paid plan (PRO, $9 per month); static Spaces only are free | — | — | — | Out |
| Koyeb | A free web instance existed; the pricing page now lists free compute at a few hours and the company was acquired by Mistral in 2026 | Yes | Scale to zero | Yes | Not relied on |

**Recommendation: Render's Free plan.** It is the only option at $0 with no card, deploys from the repository
in a few clicks, runs Python natively and has room for the engine ten times over. Its one cost is the one-minute
wake after 15 idle minutes, and the design above makes that harmless: the browser holds the save, so a game
survives the spin-down. If the wait annoys, the same service upgrades to Starter ($7 per month, no spin-down) with
one setting. Railway is the fallback if Render's free tier changes.

Click-by-click (Render), once the PR is merged to `main`:
1. Go to https://render.com and click **Get Started**; sign up with **GitHub** (no card asked).
2. When GitHub asks which repositories Render may see, choose **Only select repositories** and pick
   `jadams-24/college-baseball-sim`; click **Install**.
3. On the Render dashboard click **New +** → **Blueprint**.
4. Pick `college-baseball-sim` from the list and click **Connect**. Render reads `render.yaml` from the repo
   (service name, Python runtime, build and start commands, Free plan, health check path): click **Apply**.
5. Wait for the first deploy (a few minutes: pip installs numpy and pandas). The service page shows a URL like
   `https://college-baseball-sim.onrender.com`. Open it on the phone and on the desktop.
6. Auto-deploy is on by default: every push to `main` redeploys. To pause it: service → **Settings** →
   **Auto-Deploy** → No.
7. Later, to remove the spin-down: service → **Settings** → **Instance Type** → Starter.

If the owner prefers not to merge first, the same steps work on the branch: in step 4 Render asks which branch
to deploy; choose `ui-prototype`.

## 7. Build order (one PR on branch `ui-prototype`, built in this order, each step with its tests green)

1. **Connector** (`app/connector.py`): `HumanController`, `DecisionNeeded`, `GameRunner` with snapshot and
   replay, the decision catalogue from `engine.control.DECISIONS`, eligibility validation; tests 1, 3 and 4
   against the engine directly (no HTTP yet). This is the risky part; it is done first and proven before any UI.
2. **Timeline** (`app/timeline.py`): play-by-play lines and running box score from the log and state diffs.
3. **API** (`app/api.py`): the endpoints above; the state JSON; test 2 and the HTTP version of test 1.
4. **Frontend** (`app/static/`): team picker, game screen, pickers, play-by-play, box score, save and load with
   the `localStorage` mirror and server-restart recovery; checked on a phone-width and a desktop viewport with the
   pre-installed Chromium.
5. **Deploy files and docs**: `render.yaml`, `app/README.md` (run locally with one command, the API, the
   connector's contract for Phase 12), the hosting steps above, `requirements.txt` pins.
6. **PR**: description states that no engine, config or benchmark file changes (the realism reports are unchanged
   by construction) and includes the determinism and API test results.

Open choices for the owner (defaults in bold):
- Default for a decision the user has not set: **ask at the plate-appearance panel with no-action defaults** vs
  AI autopilot per kind (the per-kind toggle exists either way).
- Exhibition context: **weekend game, week 1** vs a selectable midweek game (changes the AI's starter choice and
  pull tables).
- Pinch runners: **any bench player** vs the AI's rule (faster only).
