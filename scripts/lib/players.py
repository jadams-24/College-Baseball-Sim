"""Shared helpers for building player-season data from the parsed WMT play-by-play."""
from __future__ import annotations

import collections
import re

import pandas as pd

SUFFIX = {"jr", "sr", "ii", "iii", "iv"}
PBP = "data/ncaa_2025/pbp/parsed"


def _toks(name) -> tuple:
    t = [x for x in re.sub(r"[^a-z ]", " ", str(name).lower().replace(",", " ").replace(".", " ")).split() if x]
    return tuple(sorted(t))


def name_map(df: pd.DataFrame, team_col: str, name_col: str) -> dict:
    """Map (team, raw name) -> canonical key. The home and away scorers spell the same
    player differently ("Jones" / "JONES", "Pearson, Js." / "JS. PEARSON"); names are
    reduced to sorted lowercase tokens, and a surname-only key is merged into the
    unique fuller key on the same team that contains it."""
    m = {}
    for team, names in df.groupby(team_col)[name_col]:
        cnt = names.value_counts()
        keys = {n: _toks(n) for n in cnt.index}
        total = collections.Counter()
        for n, k in keys.items():
            total[k] += cnt[n]
        canon = {}
        for k in total:
            core = [x for x in k if x not in SUFFIX]
            if len(core) == 1:
                sup = [k2 for k2 in total if k2 != k and core[0] in k2 and len([x for x in k2 if x not in SUFFIX]) >= 2]
                canon[k] = sup[0] if len(sup) == 1 else k
            else:
                canon[k] = k
        for n, k in keys.items():
            m[(team, n)] = " ".join(canon[k])
    return m


def load_pa() -> pd.DataFrame:
    pa = pd.read_csv(f"{PBP}/pa_events_2025.csv.gz", low_memory=False)
    bm = name_map(pa, "bat_team_id", "batter")
    pm = name_map(pa, "pit_team_id", "pitcher")
    pa["bkey"] = [bm[(t, n)] for t, n in zip(pa.bat_team_id, pa.batter)]
    pa["pkey"] = [pm[(t, n)] for t, n in zip(pa.pit_team_id, pa.pitcher)]
    return pa
