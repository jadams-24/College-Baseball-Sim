"""Latency of the UI connector (owner condition, 2026-10-08): per pitch, per sim target, snapshot, save and load.

Measures CPU time (process_time) and wall time here, and reports the CPU time scaled by 10 as the estimate for
Render's Free plan (0.1 CPU, 512 MB): a throttled share runs a CPU-bound step about ten times slower than a full
core; the HTTP and JSON work of the API (app/api.py) adds a few milliseconds. Writes reports/app_latency.md.

Run: python3 scripts/bench_app.py
"""
from __future__ import annotations

import resource
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.connector import GameRunner          # noqa: E402
from app.world import World                   # noqa: E402

N_GAMES = 10
SCALE = 10          # 0.1 CPU


def _timed(fn):
    c0, w0 = time.process_time(), time.perf_counter()
    out = fn()
    return out, time.process_time() - c0, time.perf_counter() - w0


def main():
    rows = []
    world, c, w = _timed(lambda: World())
    rows.append(("Startup: build the league and the engine (once per process)", 1, c, w))
    rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    rng = np.random.default_rng(5)
    pairs = [(int(a), int(b)) for a, b in rng.choice(len(world.league.teams), size=(N_GAMES, 2), replace=True) if a != b]

    # new game
    cs = ws = 0.0
    for i, (h, a) in enumerate(pairs):
        _, c, w = _timed(lambda: GameRunner.new(world, h, a, "home", i))
        cs += c; ws += w
    rows.append(("Create a game (manager, session)", len(pairs), cs, ws))

    # pitch by pitch: every pause (pre-pitch and boundary)
    n = cs = ws = 0.0
    nb = 0
    for i, (h, a) in enumerate(pairs):
        r = GameRunner.new(world, h, a, "home", i)
        while not r.over:
            tr, c, w = _timed(lambda: r.step("pitch"))
            n += 1; cs += c; ws += w
            nb += tr["phase"] == "boundary"
    rows.append(("Step: next pitch (snapshot + one pitch, or a boundary stop)", int(n), cs, ws))

    # sim targets
    for target in ("pa", "half", "inning", "three_innings", "game"):
        n = cs = ws = 0.0
        for i, (h, a) in enumerate(pairs):
            r = GameRunner.new(world, h, a, "home", i)
            while not r.over:
                _, c, w = _timed(lambda: r.step(target))
                n += 1; cs += c; ws += w
        rows.append((f"Step: sim to {target}", int(n), cs, ws))

    # snapshot, recommend, save and load
    r = GameRunner.new(world, pairs[0][0], pairs[0][1], "home", 1)
    r.step("three_innings")
    _, c, w = _timed(lambda: [r.snapshot() for _ in range(100)])
    rows.append(("Snapshot alone (session pickle + accumulator rows)", 100, c, w))
    _, c, w = _timed(lambda: [r.recommend() for _ in range(20)])
    rows.append(("Bench coach (dry run of the next window)", 20, c, w))
    data, c, w = _timed(lambda: r.save_bytes())
    rows.append(("Save (bytes for the browser)", 1, c, w))
    _, c, w = _timed(lambda: GameRunner.load_bytes(world, data))
    rows.append(("Load a save", 1, c, w))
    rss1 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

    lines = ["# UI connector latency", "",
             f"{len(pairs)} exhibition games, this machine. CPU is process time per call; the Render Free estimate is CPU x {SCALE} "
             "(0.1 CPU share), before the API's own few milliseconds of HTTP and JSON work.", "",
             "| Operation | Calls | CPU ms per call | Wall ms per call | Render Free estimate, ms |", "|---|---|---|---|---|"]
    for name, k, c, w in rows:
        lines.append(f"| {name} | {k} | {1000 * c / k:.2f} | {1000 * w / k:.2f} | {1000 * c / k * SCALE:.0f} |")
    lines += ["", f"Boundary stops in the pitch-by-pitch runs: {nb} (one per plate appearance of the user's side).",
              f"Save size: {len(data) / 1024:.0f} KB. Process RSS after the league: {rss0:.0f} MB; after the runs: {rss1:.0f} MB (Render Free: 512 MB)."]
    out = Path(__file__).resolve().parents[1] / "reports" / "app_latency.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
