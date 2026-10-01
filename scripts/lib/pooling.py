"""Pooling of sparse tier cells for tier-reweighted percentile benchmarks.

A reweighted percentile gives each tier cell (a tier, or a batting-tier x pitching-tier pair) its
share of the full-season D1 mix and spreads it evenly over that cell's observations. A cell with
few observations then carries a large weight on a handful of values, and its share of the tail is
not identified (15 starts with a minimum of 28 pitches say nothing about a 10th percentile near 24).
Rule: while any group has fewer than config.benchmarks.MIN_CELL_N_PERCENTILE observations, merge the
smallest group with its smallest neighbour, a neighbour being a group holding a cell one tier step
away on one side (p4 - mid - low). Sparse cells are therefore pooled with each other first, which
keeps them near their own tier pairing, and only then with a large cell. The pooled group keeps the
sum of its cells' weights; its observations share it evenly. The pooling is fixed from the full
sample and held fixed in every bootstrap replicate.
"""
from __future__ import annotations

TIER_ORDER = ("p4", "mid", "low")


def _step_neighbors(cell) -> list:
    cells = []
    parts = cell if isinstance(cell, tuple) else (cell,)
    for i, t in enumerate(parts):
        k = TIER_ORDER.index(t)
        for j in (k - 1, k + 1):
            if 0 <= j < len(TIER_ORDER):
                q = list(parts)
                q[i] = TIER_ORDER[j]
                cells.append(tuple(q) if isinstance(cell, tuple) else q[0])
    return cells


def pool_cells(counts: dict, weights: dict, floor: int) -> tuple[dict, list]:
    """counts, weights: cell -> observations, mix weight (cells are tier names or tier tuples).
    Returns (cell -> group id, list of groups [{cells, n, weight}])."""
    groups = [{"cells": [c], "n": int(counts.get(c, 0)), "weight": float(weights[c])} for c in weights]
    while True:
        small = [g for g in groups if g["n"] < floor]
        if not small or len(groups) == 1:
            break
        g = min(small, key=lambda x: (x["n"], str(x["cells"])))
        near = {nb for c in g["cells"] for nb in _step_neighbors(c)} - set(g["cells"])
        cand = [h for h in groups if h is not g and set(h["cells"]) & near]
        h = min(cand, key=lambda x: (x["n"], str(x["cells"])))
        h["cells"] += g["cells"]; h["n"] += g["n"]; h["weight"] += g["weight"]
        groups.remove(g)
    group_of = {c: i for i, g in enumerate(groups) for c in g["cells"]}
    return group_of, groups


def describe(groups: list) -> list:
    """JSON-friendly record of the groups that pooled more than one cell."""
    name = lambda c: "_vs_".join(c) if isinstance(c, tuple) else c
    return [{"cells": [name(c) for c in g["cells"]], "n": g["n"], "weight": round(g["weight"], 4)} for g in groups if len(g["cells"]) > 1]
