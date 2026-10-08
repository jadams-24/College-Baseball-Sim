# Dynasty mode latency

This machine; the Render Free estimate is CPU x 10 (0.1 CPU share). The world has 7991 regular-season games after drops and cancellations over 14 weeks (571 a week), plus about 320 postseason games.

| Operation | Calls | CPU ms per call | Wall ms per call | Render Free estimate |
|---|---|---|---|---|
| Build the world: league of 307 teams (once per dynasty) | 1 | 5061.8 | 5266.6 | 50.6 s |
| Start: schedule, drops and cancellations, engine | 1 | 574.2 | 577.9 | 5.7 s |
| Sim one game (AI both sides; 400 games) | 400 | 63.8 | 65.8 | 0.6 s |
| Hub: standings, conference records and the RPI over the games so far | 5 | 0.6 | 0.6 | 0.0 s |
| Save the dynasty (compressed pickle) | 1 | 892.9 | 901.2 | 8.9 s |
| Load the dynasty | 1 | 526.6 | 544.1 | 5.3 s |

| Sim | This machine | Render Free estimate |
|---|---|---|
| One week of the D1 world (571 games) | 36 s | 6.1 min |
| The regular season (7991 games) | 8.5 min | 85 min |
| A full season with the postseason | 8.8 min | 88 min |

Save size: 2.27 MB after 400 games (about 26 MB for a whole season: the box scores of every game are kept as int32 rows). Process RSS after the world: 31 MB; after the runs: 259 MB (Render Free: 512 MB).

## What the numbers mean for the free tier

A sim of the whole world cannot run inside one request on 0.1 CPU: a week takes minutes and a season over an hour. The app therefore runs
every sim as a background job in the server process (the hub polls progress; the engine lock serializes it with other games) and
autosaves after each job, so the page can be closed and reopened. That is the baseline in place. Options beyond it, for the owner:

1. **Batch by week** (built: the hub's sim targets). A week-at-a-time flow keeps each job to a few minutes on the free tier.
2. **Sim other games in the background while the user plays**: start the next week's other games as soon as the user's game opens; the
   engine lock would need to be per game, and the determinism of the user's game is unaffected (per-game seeds). Hides most of the wait.
3. **A paid instance** (Render Starter, 0.5 CPU): a season in about 15 minutes, a week in about a minute, no change to the app.
4. **Fewer other games** is not an option: every D1 game feeds RPI and selection, and the engine's season is the realism gate.
5. **Multiprocessing** does not help on a 0.1 CPU share; on a paid instance with 2 CPUs the other teams' games could run in a second
   process (same per-game seeds; the Decider's rest history would need merging by date), roughly halving the season.
