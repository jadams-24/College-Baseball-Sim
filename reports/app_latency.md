# UI connector latency

10 exhibition games, this machine. CPU is process time per call; the Render Free estimate is CPU x 10 (0.1 CPU share), before the API's own few milliseconds of HTTP and JSON work.

| Operation | Calls | CPU ms per call | Wall ms per call | Render Free estimate, ms |
|---|---|---|---|---|
| Startup: build the league and the engine (once per process) | 1 | 3199.09 | 3087.43 | 31991 |
| Create a game (manager, session) | 10 | 0.50 | 0.50 | 5 |
| Step: next pitch (snapshot + one pitch, or a boundary stop) | 3855 | 1.43 | 1.45 | 14 |
| Step: sim to pa | 801 | 6.55 | 6.60 | 66 |
| Step: sim to half | 173 | 21.44 | 21.62 | 214 |
| Step: sim to inning | 89 | 22.32 | 22.35 | 223 |
| Step: sim to three_innings | 30 | 25.84 | 26.05 | 258 |
| Step: sim to game | 10 | 22.88 | 22.90 | 229 |
| Snapshot alone (session pickle + accumulator rows) | 100 | 0.87 | 0.87 | 9 |
| Bench coach (dry run of the next window) | 20 | 1.69 | 1.69 | 17 |
| Save (bytes for the browser) | 1 | 2.32 | 2.32 | 23 |
| Load a save | 1 | 2.35 | 2.35 | 23 |

Boundary stops in the pitch-by-pitch runs: 791 (one per plate appearance of the user's side).
Save size: 105 KB. Process RSS after the league: 56 MB; after the runs: 109 MB (Render Free: 512 MB).
