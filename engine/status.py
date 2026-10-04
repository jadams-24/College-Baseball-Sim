"""Gate verdicts with the numbers behind them.

A report's status is a dict of gate key -> True / False / None (reported, not gated). Status.vals
carries, for each gated row that has one, the simulated value and its standard error at the
number of seasons run. CI compares those numbers between its own run and the committed report
(tests/conftest.py): the simulation is deterministic per machine but not across machines
(CPU-dependent floating point changes the draws), so two runs of the same seeds agree within
sampling error, not exactly.
"""
from __future__ import annotations


class Status(dict):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.vals: dict = {}

    def record(self, key: str, value, se) -> None:
        if value is not None and se is not None and se > 0:
            self.vals[key] = [float(value), float(se)]
