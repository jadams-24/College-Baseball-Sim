"""Diagnostic accumulators (speed pass, 2026-10-09): the per-plate-appearance tables only the reports read (the Phase 3
split, platoon, relief and pinch-hit tables, the Phase 4 forward test's expectations and opponent trials, the Phase 2
team-by-team cells, the Phase 5 pitch tables and the Phase 6 steal-path records). They draw nothing and feed no
decision. RECORD = False plays identical games (the same logs, box scores, season stats and standings; tests/test_speed.py
plays 300 games both ways) without them, for dynasty play; the realism reports need RECORD = True (the default)."""
RECORD = True
