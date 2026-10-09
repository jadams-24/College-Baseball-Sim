"""The base-running tables' derived splits are cached on the cells themselves, never in module state keyed by id():
CPython reuses the id of a freed object, so an id-keyed cache handed a new cell a dead cell's split (found 2026-10-09,
when a fresh-process resume differed in CI after earlier tests had built and freed engines)."""
from __future__ import annotations

import gc

from engine import tables as T
from engine.rng import Categorical


def test_split_never_outlives_its_cell():
    # labels "r1,r2,r3,outs,err": error on the play 1 in 4, and no runner out 3 in 4
    olds = [Categorical(["2,,,0,1", "0,,,1,0"], [1, 3]) for _ in range(1000)] + [Categorical(["2,,,0,0", "0,,,1,0"], [3, 1]) for _ in range(1000)]
    for c in olds:
        T._err_split(c), T._ok_split(c)
    del olds, c
    gc.collect()
    news = [Categorical(["2,,,0,1", "0,,,1,0"], [1, 1]) for _ in range(2000)]   # error 1 in 2, no runner out 1 in 2
    for n in news:
        assert T._err_split(n)[0] == 0.5
        assert T._ok_split(n)[0] == 0.5
    # whether an id was reused above depends on the allocator's state (it is not guaranteed, so it is not asserted); the
    # structure guarantees the result: no module cache keyed by id, and each split lives on its own cell
    assert not any(isinstance(v, dict) for k, v in vars(T).items() if k.startswith("_") and k.isupper() or k in ("_SPLITS", "_OK", "_EXTRA"))
    assert all(n.split_err is T._err_split(n) and n.split_ok is T._ok_split(n) for n in news)


def test_extra_base_cache_per_table():
    # labels "r1,r2,r3,batter,outs,err": the runner from first goes to second (standard) or third (extra)
    a = T.AdvancementTable({"1B": {"0|100": {"2,,,1,0,0": 3, "3,,,1,0,0": 1}}}, 1)
    b = T.AdvancementTable({"1B": {"0|100": {"2,,,1,0,0": 1, "3,,,1,0,0": 1}}}, 1)
    assert a.extra_prob("1B", 0, "100", 1, ("3",), "2") == 0.25
    assert b.extra_prob("1B", 0, "100", 1, ("3",), "2") == 0.5
