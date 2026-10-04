"""Build the empirical tables the Phase 1 engine samples from.

Input: data/ncaa_2025/pbp/parsed/{pa_events,runner_events}_2025.csv.gz
Output: data/ncaa_2025/derived/engine_tables_2025.json

Tables (all counts, the engine normalizes):
  pa_joint[result][state]    joint outcome of a plate appearance given the batter result
                             and the pre-play base-out state ("outs|b1b2b3"); an outcome
                             is "r1,r2,r3,b,outs_on_play,errors" with destinations
                             '' (no runner) / 0 (out) / 1-3 (base) / 4 (scored).
                             Also pooled over outs under "*|b1b2b3" and the per-runner
                             marginals under "from1/2/3" and "batter" for sparse cells.
  in_play_out_subtype        shares of SF / SH / FC / plain out among balls in play that are
                             not hits or errors, by feasibility class: "on3_lt2" (runner on
                             3rd, <2 outs), "on_lt2" (runners on, <2 outs, nobody on 3rd),
                             "on_2out" (runners on, 2 outs), "empty".
  pre_pa_events[state]       per base-running opportunity in that state: the count of
                             opportunities (n_opp), and for each non-PA event type (SB_ATT =
                             stolen base attempt incl. caught stealing, WP, PB, PO, BK, OTHER)
                             the count and the joint outcome distribution
                             "r1,r2,r3,outs_on_play,errors". An opportunity is every state a
                             half-inning passes through between plate appearances: the state
                             before each event, and the state the plate appearance is recorded
                             in. The feed records a plate appearance at its state after any
                             events during it (after a steal from first, the next PA reads
                             runner on second in 1,720 of 1,941 cases), so dividing by recorded
                             PAs alone left out the PAs in which a runner left the state and
                             inflated every event rate there (Phase 1 attempts 15% high). The
                             engine draws again after each event, so a PA can hold several.
Result classes: K, BB (incl. IBB), HBP (incl. CI), 1B, 2B, 3B, HR, SF, SH, IP_OUT
(FO/GO/GIDP/DP), ROE, FC.
"""
from __future__ import annotations

import datetime as dt
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

P = Path("data/ncaa_2025/pbp/parsed")
OUT = Path("data/ncaa_2025/derived/engine_tables_2025.json")
RES_MAP = {"IBB": "BB", "CI": "HBP", "FO": "IP_OUT", "GO": "IP_OUT", "GIDP": "IP_OUT", "DP": "IP_OUT"}


def dest(v) -> str:
    if v == "" or pd.isna(v):
        return ""
    return str(int(float(v)))


def main() -> None:
    pa = pd.read_csv(P / "pa_events_2025.csv.gz", low_memory=False)
    rev = pd.read_csv(P / "runner_events_2025.csv.gz", low_memory=False)
    pa["res"] = pa.result.replace(RES_MAP)
    pa["bases"] = pa.on1.astype(str) + pa.on2.astype(str) + pa.on3.astype(str)
    pa["state"] = pa.outs.astype(str) + "|" + pa.bases

    joint: dict = defaultdict(lambda: defaultdict(Counter))
    marg: dict = defaultdict(lambda: defaultdict(Counter))
    for r in pa.itertuples(index=False):
        tup = ",".join([dest(r.r1_to), dest(r.r2_to), dest(r.r3_to), dest(r.batter_to), str(int(r.outs_on_play)), str(int(r.errors_on_play))])
        joint[r.res][r.state][tup] += 1
        joint[r.res]["*|" + r.bases][tup] += 1
        for b, v in ((1, r.r1_to), (2, r.r2_to), (3, r.r3_to)):
            if dest(v):
                marg[r.res][f"from{b}"][dest(v)] += 1
        if dest(r.batter_to):
            marg[r.res]["batter"][dest(r.batter_to)] += 1
    pa_joint = {res: {st: dict(c) for st, c in d.items()} for res, d in joint.items()}
    for res, d in marg.items():
        for k, c in d.items():
            pa_joint[res][k] = dict(c)

    # in-play-out subtype by feasibility class
    ipo = pa[pa.res.isin(["IP_OUT", "SF", "SH", "FC"])].copy()
    on = (ipo.on1 + ipo.on2 + ipo.on3) > 0
    on3_lt2 = (ipo.on3 == 1) & (ipo.outs < 2)
    on_lt2 = on & (ipo.outs < 2) & (ipo.on3 == 0)
    on_2out = on & (ipo.outs == 2)
    cls = pd.Series("empty", index=ipo.index)
    cls[on_2out] = "on_2out"
    cls[on_lt2] = "on_lt2"
    cls[on3_lt2] = "on3_lt2"
    subtype = {c: dict(Counter(ipo.res[cls == c])) for c in ("on3_lt2", "on_lt2", "on_2out", "empty")}

    # pre-PA base running events
    pa_by_state = Counter(pa.state)
    pa_by_bases = Counter(pa.bases)
    rev["bases"] = rev.on1.astype(str) + rev.on2.astype(str) + rev.on3.astype(str)
    rev["state"] = rev.outs.astype(str) + "|" + rev.bases
    rev["etype"] = rev.event.replace({"SB": "SB_ATT", "CS": "SB_ATT"})
    events: dict = defaultdict(lambda: defaultdict(Counter))
    for gid, grp in rev.groupby("group_id"):
        first = grp.iloc[0]
        d = {1: "1" if first.on1 == 1 else "", 2: "2" if first.on2 == 1 else "", 3: "3" if first.on3 == 1 else ""}
        outs_play = 0
        for rr in grp.itertuples(index=False):
            to = dest(rr.to_base)
            if to == "":
                continue
            d[int(rr.from_base)] = to
            if to == "0":
                outs_play += 1
        tup = ",".join([d[1], d[2], d[3], str(outs_play), str(int(first.errors_on_play))])
        events[first.state][first.etype][tup] += 1
        events["*|" + first.bases][first.etype][tup] += 1
    pre_pa = {}
    for st in set(list(pa_by_state) + ["*|" + b for b in pa_by_bases]):
        n_pa = pa_by_state[st] if "*" not in st else pa_by_bases[st[2:]]
        n_ev = sum(sum(c.values()) for c in events.get(st, {}).values())
        pre_pa[st] = {"n_pa": n_pa, "n_opp": n_pa + n_ev, "events": {et: dict(c) for et, c in events.get(st, {}).items()}}

    out = {"_meta": {"built": dt.date.today().isoformat(), "n_pa": len(pa), "n_games": int(pa.game_id.nunique()),
                     "src": "WMT play-by-play, data/ncaa_2025/pbp/parsed; see scripts/build_engine_tables.py"},
           "pa_joint": pa_joint, "in_play_out_subtype": subtype, "pre_pa_events": pre_pa}
    OUT.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    thin = sum(1 for res in pa_joint for st, c in pa_joint[res].items() if "|" in st and "*" not in st and sum(c.values()) < 30)
    print(f"wrote {OUT} ({OUT.stat().st_size//1024} KB); joint cells <30 PA: {thin}; subtype: {subtype}")
    print("pre-PA event rates per PA, bases 100:", {et: round(sum(c.values()) / pre_pa['*|100']['n_opp'], 4) for et, c in pre_pa["*|100"]["events"].items()})


if __name__ == "__main__":
    main()
