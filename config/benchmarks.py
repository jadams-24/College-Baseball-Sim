"""Constants of the benchmark builders (scripts/), shared across phases."""
from __future__ import annotations

# Tier-reweighted percentile benchmarks: a tier cell (a tier, or a batting-tier x pitching-tier
# pair) with fewer observations than this is pooled with its nearest cell before reweighting
# (scripts/lib/pooling.py). Owner decision on PR #7 (2026-10-01). With 50 observations a p10 has
# about 5 below it (rank SE ~2), so the quantile is bracketed by data on both sides; a 15-start cell
# whose minimum is above the pooled p10 cannot estimate its own p10, and a bootstrap of it never
# draws below its minimum, so the benchmark's SE is understated. GUESS (statistical floor).
MIN_CELL_N_PERCENTILE = 50
