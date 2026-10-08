"""Dynasty mode latency (owner condition 10, 2026-10-08): how long simming a week and a full season of the whole D1
world takes, measured here and scaled to Render's Free plan (0.1 CPU share: CPU x 10, as reports/app_latency.md).

    python3 scripts/bench_dynasty.py        -> reports/dynasty_latency.md

Measures: building the world (league, schedule, masks), N simmed games (per-game CPU), the save (bytes and time),
a reload, the hub (standings and RPI over the games so far). The week and season figures extrapolate the per-game
cost to the schedule's games per week and the season's games after drops and cancellations; the postseason adds
about 320 games (29 conference tournaments, 16 regionals, 8 supers, the CWS)."""
from __future__ import annotations

import resource
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import dynasty as dm            # noqa: E402
from config import phase2                # noqa: E402

SCALE = 10
N_GAMES = 400


def main():
    cfg = phase2.load()
    rss = lambda: resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    rows = []

    def timed(label, fn, calls=1):
        c0, w0 = time.process_time(), time.perf_counter()
        out = fn()
        c, w = (time.process_time() - c0) / calls, (time.perf_counter() - w0) / calls
        rows.append((label, calls, c * 1000, w * 1000))
        return out
    r0 = rss()
    d = timed("Build the world: league of 307 teams (once per dynasty)", lambda: dm.Dynasty(cfg, 7, "bench"))
    timed("Start: schedule, drops and cancellations, engine", lambda: d.start(5))
    n_total = int((~d.skip).sum())
    weeks = max(g.week for g in d.schedule) + 1
    per_week = n_total / weeks
    k = [0]

    def games():
        while k[0] < N_GAMES:
            i = d.next_index()
            d._play(i); d.pos = i + 1; k[0] += 1
    timed(f"Sim one game (AI both sides; {N_GAMES} games)", games, N_GAMES)
    per_game_cpu = rows[-1][2]
    timed("Hub: standings, conference records and the RPI over the games so far", lambda: d.hub(), 5)
    blob = timed("Save the dynasty (compressed pickle)", lambda: dm.save_bytes(d))
    timed("Load the dynasty", lambda: dm.load_bytes(cfg, blob))
    r1 = rss()
    week_s, season_s = per_game_cpu * per_week / 1000, per_game_cpu * (n_total + 320) / 1000
    md = ["# Dynasty mode latency", "",
          f"This machine; the Render Free estimate is CPU x {SCALE} (0.1 CPU share). The world has {n_total} regular-season games after drops and "
          f"cancellations over {weeks} weeks ({per_week:.0f} a week), plus about 320 postseason games.", "",
          "| Operation | Calls | CPU ms per call | Wall ms per call | Render Free estimate |", "|---|---|---|---|---|"]
    for label, calls, c, w in rows:
        md.append(f"| {label} | {calls} | {c:.1f} | {w:.1f} | {c * SCALE / 1000:.1f} s |")
    md += ["", "| Sim | This machine | Render Free estimate |", "|---|---|---|",
           f"| One week of the D1 world ({per_week:.0f} games) | {week_s:.0f} s | {week_s * SCALE / 60:.1f} min |",
           f"| The regular season ({n_total} games) | {per_game_cpu * n_total / 1000 / 60:.1f} min | {per_game_cpu * n_total / 1000 / 60 * SCALE:.0f} min |",
           f"| A full season with the postseason | {season_s / 60:.1f} min | {season_s / 60 * SCALE:.0f} min |", "",
           f"Save size: {len(blob) / 1e6:.2f} MB after {N_GAMES} games (about {len(blob) / 1e6 * (n_total + 320) / N_GAMES * .5 + 2:.0f} MB for a whole season: the box "
           f"scores of every game are kept as int32 rows). Process RSS after the world: {r0:.0f} MB; after the runs: {r1:.0f} MB (Render Free: 512 MB).", "",
           "## What the numbers mean for the free tier", "",
           "A sim of the whole world cannot run inside one request on 0.1 CPU: a week takes minutes and a season over an hour. The app therefore runs",
           "every sim as a background job in the server process (the hub polls progress; the engine lock serializes it with other games) and",
           "autosaves after each job, so the page can be closed and reopened. That is the baseline in place. Options beyond it, for the owner:", "",
           "1. **Batch by week** (built: the hub's sim targets). A week-at-a-time flow keeps each job to a few minutes on the free tier.",
           "2. **Sim other games in the background while the user plays**: start the next week's other games as soon as the user's game opens; the",
           "   engine lock would need to be per game, and the determinism of the user's game is unaffected (per-game seeds). Hides most of the wait.",
           "3. **A paid instance** (Render Starter, 0.5 CPU): a season in about 15 minutes, a week in about a minute, no change to the app.",
           "4. **Fewer other games** is not an option: every D1 game feeds RPI and selection, and the engine's season is the realism gate.",
           "5. **Multiprocessing** does not help on a 0.1 CPU share; on a paid instance with 2 CPUs the other teams' games could run in a second",
           "   process (same per-game seeds; the Decider's rest history would need merging by date), roughly halving the season.", ""]
    Path("reports/dynasty_latency.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
