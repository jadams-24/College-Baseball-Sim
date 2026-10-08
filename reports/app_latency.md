# UI connector latency

10 exhibition games, this machine. CPU is process time per call; the Render Free estimate is CPU x 10 (0.1 CPU share), before the API's own few milliseconds of HTTP and JSON work.

| Operation | Calls | CPU ms per call | Wall ms per call | Render Free estimate, ms |
|---|---|---|---|---|
| Startup: build the league and the engine (once per process) | 1 | 5174.66 | 5342.81 | 51747 |
| Create a game (manager, session) | 10 | 0.98 | 0.99 | 10 |
| Step: next pitch (snapshot + one pitch, or a boundary stop) | 3766 | 2.56 | 2.61 | 26 |
| Step: sim to pa | 797 | 12.91 | 13.17 | 129 |
| Step: sim to half | 176 | 40.02 | 40.89 | 400 |
| Step: sim to inning | 90 | 43.11 | 43.70 | 431 |
| Step: sim to three_innings | 31 | 52.46 | 53.50 | 525 |
| Step: sim to game | 10 | 67.87 | 69.14 | 679 |
| Snapshot alone (session pickle + accumulator rows) | 100 | 1.91 | 1.98 | 19 |
| Bench coach (dry run of the next window) | 20 | 3.35 | 3.35 | 33 |
| Save (bytes for the browser) | 1 | 4.33 | 4.33 | 43 |
| Load a save | 1 | 4.38 | 4.39 | 44 |

Boundary stops in the pitch-by-pitch runs: 787 (one per plate appearance of the user's side).
Save size: 126 KB. Process RSS after the league: 63 MB; after the runs: 111 MB (Render Free: 512 MB).
