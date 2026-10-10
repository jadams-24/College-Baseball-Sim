"""The Draft tab's data (owner request 2026-10-10): the Top 100 board, the Round 1 mock draft and the user's program.
Display only. Projected value comes from each player's true rates through the engine's own maps (engine.matchup
against a league-average opponent) valued with linear weights (config/prospects.py), blended with the season line as
it accumulates so the board moves weekly. The Overall rating reuses `hitter_value` / `pitcher_value` later; no
number is shown as OVR (owner: OVR on hold). Rankings are deterministic for a dynasty state; the mock's small
randomness is seeded by the dynasty seed and the week and labeled as a projection.

Draft eligibility (class year and age) arrives with the roster rules (Phase 8); until then every D1 player is shown.
"""
from __future__ import annotations

import csv
import math
from functools import lru_cache
from pathlib import Path

import numpy as np

from config import prospects as P
from engine.matchup import OUTCOMES, matchup_probs

ROOT = Path(__file__).resolve().parents[1]
ORDER_CSV = ROOT / "app/mlb_draft_order_2025.csv"
BANNER = "Preview: draft eligibility (class year and age) arrives with roster rules; until then every D1 player is shown."
MOCK_LABEL = "Mock draft: projection, not results"


# ---------------------------------------------------------------- value
def _value_per_pa(p: dict) -> float:
    """Runs per plate appearance of an outcome distribution under the linear weights (an out is 0)."""
    return sum(P.LINEAR_WEIGHTS[o] * p[o] for o in OUTCOMES)


def _outs_per_pa(p: dict) -> float:
    return p["K"] + p["OUT"]


def league_point(d) -> dict:
    """The league-average matchup: outcome probabilities, runs per PA, outs per PA (cached on the dynasty)."""
    lp = getattr(d, "_league_point", None)
    if lp is None:
        zero = np.zeros(6)
        p = matchup_probs(d.cfg, zero, zero, d.league.location)
        lp = d._league_point = {"p": p, "value": _value_per_pa(p), "outs": _outs_per_pa(p)}
    return lp


def hitter_value(d, p) -> float:
    """Expected runs above average per 600 PA from the hitter's true rates against a league-average pitcher."""
    lg = league_point(d)
    probs = matchup_probs(d.cfg, p.z, np.zeros(6), d.league.location)
    return P.PA_PER_600 * (_value_per_pa(probs) - lg["value"])


def pitcher_value(d, p) -> float:
    """Runs prevented per 100 IP from the pitcher's true rates against a league-average hitter."""
    lg = league_point(d)
    probs = matchup_probs(d.cfg, np.zeros(6), p.z, d.league.location)
    pa_per_100 = 3 * P.IP_PER_100 / _outs_per_pa(probs)
    return pa_per_100 * (lg["value"] - _value_per_pa(probs))


def observed_hitter_value(d, row) -> tuple:
    """(runs above average per 600 PA, PA) from the season line's events; (None, 0) before a plate appearance."""
    from engine.game2 import B_2B, B_3B, B_BB, B_H, B_HBP, B_HR, B_PA, B_ROE
    pa = int(row[B_PA])
    if pa <= 0:
        return None, 0
    h, dbl, tri, hr = row[B_H], row[B_2B], row[B_3B], row[B_HR]
    w = P.LINEAR_WEIGHTS
    runs = w["BB"] * row[B_BB] + w["HBP"] * row[B_HBP] + w["1B"] * (h - dbl - tri - hr) + w["2B"] * dbl + w["3B"] * tri + w["HR"] * hr + w["ROE"] * row[B_ROE]
    return P.PA_PER_600 * (runs / pa - league_point(d)["value"]), pa


def observed_pitcher_value(d, row) -> tuple:
    """(runs prevented per 100 IP, batters faced) from the line; hits allowed split by the league's extra-base share."""
    from engine.game2 import P_BF, P_BB, P_H, P_HBP, P_HR, P_OUTS
    bf = int(row[P_BF])
    if bf <= 0 or row[P_OUTS] <= 0:
        return None, 0
    lg = league_point(d)["p"]
    hits = row[P_H] - row[P_HR]
    xb_share = (lg["2B"] + lg["3B"]) / (lg["1B"] + lg["2B"] + lg["3B"])
    w = P.LINEAR_WEIGHTS
    runs = w["BB"] * row[P_BB] + w["HBP"] * row[P_HBP] + w["HR"] * row[P_HR] + hits * ((1 - xb_share) * w["1B"] + xb_share * w["2B"])
    allowed_per_pa = runs / bf
    pa_per_100 = 3 * P.IP_PER_100 * bf / row[P_OUTS]
    return pa_per_100 * (league_point(d)["value"] - allowed_per_pa), bf


def projected_value(d, p) -> dict:
    """The board's value: the rating-based value blended with the observed line, weight n / (n + K_OBS)."""
    if p.side == "bat":
        base = hitter_value(d, p)
        obs, n = observed_hitter_value(d, d.bstats[p.pid])
        k = P.K_OBS_BAT
    else:
        base = pitcher_value(d, p)
        obs, n = observed_pitcher_value(d, d.pstats[p.pid])
        k = P.K_OBS_PIT
    w = n / (n + k) if obs is not None else 0.0
    return {"value": (1 - w) * base + w * obs if obs is not None else base, "rating_value": base, "observed_value": obs, "n": n, "weight": w}


# ---------------------------------------------------------------- the board
def position_of(p) -> str:
    if p.side == "pit":
        return "SP" if p.group in ("sp_weekend", "sp_midweek") else "RP"
    return (p.pos or "DH").upper()


def position_group(pos: str) -> str:
    return {"C": "C", "1B": "IF", "2B": "IF", "3B": "IF", "SS": "IF", "LF": "OF", "CF": "OF", "RF": "OF", "DH": "DH", "SP": "SP", "RP": "RP"}.get(pos, pos)


def current_week(d) -> int:
    return int(d.date_now()) // 7 + 1


def board(d, size: int = P.BOARD_SIZE) -> list:
    """The Top `size` by projected value, deterministic for the dynasty's state: [(pid, value, detail), ...].
    Hitters (runs above average per 600 PA) and pitchers (runs prevented per 100 IP) merge by their percentile
    within their side (the normal score of the value's rank among D1 hitters or D1 pitchers), the value itself
    breaking ties: the two units are not one exchange rate (the hitters' D1 tail is the heavier), and the Overall
    rating will set that rate later (config/prospects.py). `detail["score"]` carries the merged score."""
    from statistics import NormalDist
    rows = []
    for t in d.league.teams:
        for p in list(t.batters) + list(_staff(t)):
            v = projected_value(d, p)
            rows.append([p.pid, v["value"], v, p.side])
    nd = NormalDist()
    for side in ("bat", "pit"):
        group = sorted((r for r in rows if r[3] == side), key=lambda r: (-r[1], r[0]))
        n = len(group)
        for i, r in enumerate(group):
            r[2]["score"] = nd.inv_cdf((n - i) / (n + 1))             # rank 1 -> the highest score
    rows.sort(key=lambda r: (-r[2]["score"], -r[1], r[0]))
    return [(pid, value, detail) for pid, value, detail, _ in rows[:size]]


def _staff(t):
    from app.world import staff
    return staff(t)


def board_json(d, size: int = P.BOARD_SIZE) -> dict:
    """The Top 100 with ranks, the change since last week (from the dynasty's stored weekly snapshots), the key
    ratings by position, the season line, the school; and the snapshot of this week stored for next week's change."""
    from app import schools
    from app.world import player_json
    from engine.ratings import display
    week = current_week(d)
    top = board(d, size)
    hist = getattr(d, "board_history", None)
    if hist is None:
        hist = d.board_history = {}
    ranks_now = {pid: i + 1 for i, (pid, _, _) in enumerate(top)}
    if week not in hist:
        hist[week] = [pid for pid, _, _ in top]
    prev_week = max((w for w in hist if w < week), default=None)
    prev_rank = {pid: i + 1 for i, pid in enumerate(hist[prev_week])} if prev_week is not None else {}
    out = []
    for pid, value, detail in top:
        p = d.league.players[pid]
        t = d.league.teams[p.team]
        pos = position_of(p)
        keys = P.KEY_RATINGS.get(pos, P.KEY_RATINGS["DH" if p.side == "bat" else "RP"])
        if p.side == "bat":
            from app.dynasty import _bat_stats
            s = _bat_stats(d.bstats[pid]); line = {"avg": s["avg"], "obp": s["obp"], "slg": s["slg"], "hr": s["hr"], "pa": s["pa"]} if s["pa"] else None
        else:
            from app.dynasty import _pit_stats
            s = _pit_stats(d.pstats[pid]); line = {"era": s["era"], "ip": s["ip"], "k": s["k"], "bb": s["bb"], "bf": s["bf"]} if s["bf"] else None
        pj = player_json(p)
        disp = schools.display(t.tid) or {}
        rk = ranks_now[pid]
        out.append({"rank": rk, "change": (prev_rank[pid] - rk) if pid in prev_rank else (None if prev_week is None else "new"),
                    "pid": pid, "name": p.name, "pos": pos, "group": position_group(pos), "side": p.side, "hand": f"{pj['bats'] or '–'}/{pj['throws'] or '–'}",
                    "tid": t.tid, "school": d.tname(t.tid), "abbr": d.tabbr(t.tid), "conference": disp.get("conference") or d.real_conf[t.tid], "tier": t.tier,
                    "mine": t.tid == d.tid, "key_ratings": [(k, int(display(pj["ratings"][k])) if pj["ratings"].get(k) is not None else None) for k in keys],
                    "line": line, "value": round(value, 2), "score": round(detail["score"], 3), "rating_value": round(detail["rating_value"], 2),
                    "observed_value": round(detail["observed_value"], 2) if detail["observed_value"] is not None else None, "weight": round(detail["weight"], 3)})
    return {"week": week, "prev_week": prev_week, "rows": out, "unit": {"bat": "runs above average per 600 PA", "pit": "runs prevented per 100 IP"}}


# ---------------------------------------------------------------- the mock draft
@lru_cache(maxsize=1)
def draft_order() -> list:
    with ORDER_CSV.open() as f:
        return [dict(r, pick=int(r["pick"])) for r in csv.DictReader(f)]


def mock_draft(d, board_rows: list) -> dict:
    """Round 1 (through Competitive Balance Round A) from the board: each slot takes one of the best available, the
    k-th best with weight exp(-k / MOCK_TAU) among the top MOCK_TOP, drawn from a stream seeded by the dynasty seed
    and the week (deterministic within a week, labeled as a projection). Every slot used once, no player twice."""
    order = draft_order()
    rng = np.random.Generator(np.random.PCG64([int(d.seed) & 0xFFFFFFFF, current_week(d), 2025]))
    avail = list(board_rows)
    picks = []
    for slot in order:
        if not avail:
            break
        k = min(P.MOCK_TOP, len(avail))
        w = np.exp(-np.arange(k) / P.MOCK_TAU); w /= w.sum()
        j = int(rng.choice(k, p=w))
        r = avail.pop(j)
        picks.append({"pick": slot["pick"], "round": slot["round"], "team": slot["team"], "note": slot["note"], "pid": r["pid"], "name": r["name"], "pos": r["pos"],
                      "tid": r["tid"], "school": r["school"], "abbr": r["abbr"], "board_rank": r["rank"], "reach": r["rank"] - slot["pick"], "mine": r["mine"]})
    return {"label": MOCK_LABEL, "randomness": f"picks follow the board with a small seeded shuffle (the k-th best available with weight exp(-k/{P.MOCK_TAU}), top {P.MOCK_TOP})",
            "source": order[0]["source"] if order else "", "fetch_date": order[0]["fetch_date"] if order else "", "picks": picks, "slots": len(order)}


def round_range(rank: int) -> str:
    """A board rank's projected round range: the real first-round slots, then PICKS_PER_ROUND a round, one round wide."""
    n1 = len(draft_order())
    if rank <= n1:
        return "Round 1" if rank <= 27 else "Round 1 (comp)"
    r = 2 + (rank - n1 - 1) // P.PICKS_PER_ROUND
    return f"Rounds {r}–{r + 1}"


def program_json(d, board_rows: list) -> dict:
    mine = [dict(r, round_range=round_range(r["rank"])) for r in board_rows if r["mine"]]
    return {"players": mine, "history": [], "history_note": "Draft history fills in once seasons carry over."}


def draft_json(d) -> dict:
    b = board_json(d)
    return {"banner": BANNER, "week": b["week"], "prev_week": b["prev_week"], "unit": b["unit"], "board": b["rows"],
            "mock": mock_draft(d, b["rows"]), "program": program_json(d, b["rows"]),
            "live": {"enabled": False, "text": "Live draft: arrives with recruiting and signability (Phase 9)"}}
