# Speed pass (2026-10-09)

No outcome changes: every draw is the same.

- `scripts/check_log_identity.py`: the 300-game log hash `e1f77488…585bf1` is unchanged from main, with the diagnostics on and off. The stat-line hash is also equal in both modes.
- Full season, seed 20251000: 8,042 regular-season games plus the postseason, every result field compared with the pre-change commit. 0 differences.
- `tests/test_speed.py`: each rewrite checked against the form it replaced.

## Timings

All runs on this machine, one after another on a quiet machine.

| | Before | After, full | After, lean (`config.diagnostics.RECORD = False`) |
|---|---|---|---|
| ms per game (600 games, median of 3; mean of the repeated runs) | 36.2 | 29.0 (1.25×) | 24.0 (1.51×) |
| One season (seed 20251000, 8,042 games + postseason) | 315 s | 264 s (1.20×) | 216 s (1.46×) |
| Season on a 0.1-CPU host (process time × 10) | ≈ 53 min | ≈ 44 min | ≈ 36 min |

- **Full** records everything the realism reports read. Every report and gate runs this way.
- **Lean** skips the report-only tables (split, platoon, relief and pinch-hit tables; Phase 4 expectations and opponent trials; team-by-team cells; pitch tables; steal-path records; leash records). Games, box scores, season stats and standings are the same. It is meant for dynasty play.
- **0.1-CPU estimate:** process time × 10, the same rule as `reports/app_latency.md`, before the host's own overhead.

## What changed

All changes keep each floating-point operation and its order.

- **Pitch chain (`engine/pitch.py`):**
  - K, BB and HBP absorption in one pass, using `absorb()`'s operations minus exact no-ops (adding `x * 0.0` to a non-negative sum, multiplying by 1.0).
  - The LAPACK solve called through numpy's own gufunc with the same signature, without `np.linalg.solve`'s checks and error-state context.
  - `np.add.reduce` and `np.add.accumulate` in place of the `sum` and `cumsum` wrappers.
  - The chain passed as an array where it is used as one.
- **AI decisions (`engine/decisions.py`, `engine/manager.py`):**
  - Bunt, intentional-walk and steal probabilities, the pull hazards and the leash transforms are computed once per discrete input. These caches are left out of session saves.
  - `bisect` is used in place of `np.searchsorted` for bins.
- **Recorder (`engine/game2.py`):** report-only accumulators moved behind `config.diagnostics.RECORD`.

## Why not 2×

- **The pitch-chain math is about 40% of a lean game.** Each new batter–pitcher pairing needs the tilt solve (3 quasi-Newton steps), the absorption solve and the forward table, about 58 pairings per game.
  - What remains there is mostly numpy's exp, log, matrix products and LAPACK solve on tiny arrays. Their results can differ in the last bit from a pure-Python or closed-form equivalent, so replacing them would move draws.
  - A pure-Python chain was tried and is slower (20 µs against 12 µs).
  - Batching pairings across the lineup gains only 1.45× on the tilt solve, because the absorption loop and the matrix products stay per pairing. It also computes pairings that never happen.
- **The rest is spread thinly.** It is the AI's ten decision kinds (10–25 µs per call, about 450 calls per game) and the session's per-pitch logic. No single piece is above 5%.
- **Not levers:** garbage collection is 2.5% of a season, and cross-game caching hits 4% of pairings.

## Options for more speed (owner decision)

1. **Allow last-bit numeric changes in the pitch chain:**
   - plain-float exp and log;
   - back-substitution in place of the LAPACK solve (the count chain is triangular);
   - plain-float matrix products.

   Draws change, so every report is regenerated and the 40-season gates must pass again. The estimated gain is roughly 1.3× more on top of the current numbers. That is an estimate, not measured.
2. **A compiled extension for the pitch chain** (Cython). It keeps today's numbers if it reproduces the same operations, but adds a build step on the host.
