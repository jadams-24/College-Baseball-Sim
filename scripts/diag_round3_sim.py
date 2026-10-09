"""Round 3 of the variance-stage sizes, sim side: a play-by-play of the current engine for the same estimators round 2 ran on
the real play-by-play (scripts/diag_tto_mopup.py). Measurement only; the engine is not changed.

The instrumentation wraps GameSession._finish_pa and PlayerGameEngine._record in the worker processes: it reads the game state
before and after each plate appearance and draws no random numbers, so every game plays exactly as it does uninstrumented.
Per plate appearance: game, inning, half, outs, bases, the score, batting and fielding team, batter and pitcher (the pitcher
on the mound), the side the batter hit from, his listed bats and the pitcher's hand, the result as recorded, pitches (pitch symbols, not the
non-pitch events) and runs scored on the play. Per game: teams, final score, innings, the run rule, weekend, postseason, and
the half-inning runs. Per team: tier and the drawn strengths.

Seeds ROUND3_SEEDS (980001+), disjoint from the report's (20251000+), the solvers' (9x0000+) and the drift check's (970001+).
Writes one pickle per season to the scratch directory given (default runs/round3/<engine key>/), keyed like the season
checkpoints (scripts/run_phase5.py _code_id), so a rerun of the same code reuses finished seasons.
    python3 scripts/diag_round3_sim.py [--seasons 8] [--workers 4]
"""
from __future__ import annotations

import argparse
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

ROUND3_SEEDS = tuple(range(980001, 980041))
_STATE: dict = {}


def _instrument() -> None:
    from engine import game2
    if getattr(game2.GameSession, "_r3", False):
        return
    orig_finish, orig_record, orig_final = game2.GameSession._finish_pa, game2.PlayerGameEngine._record, game2.GameSession._final

    def record(self, st, batter, pitcher, res, seq, *a, **k):
        cap = getattr(self, "_r3cap", None)
        if cap is not None and "res" not in cap:
            cap["res"], cap["seq"] = res, seq
        return orig_record(self, st, batter, pitcher, res, seq, *a, **k)

    def finish(self):
        st, pa, eng = self.st, self.pa, self.eng
        if not hasattr(self, "_r3gid"):
            _STATE["gid"] = self._r3gid = _STATE.get("gid", 0) + 1
        bat, fld = st.batting_side, st.fielding_side
        b, p = pa["batter"], pa["pitcher"]
        pre = (self._r3gid, st.inning, 0 if st.half == "T" else 1, st.outs, int(st.bases[0] is not None), int(st.bases[1] is not None),
               int(st.bases[2] is not None), st.score[bat], st.score[fld], st.team_obj[bat].tid, st.team_obj[fld].tid, int(bat == "home"),
               b.pid, p.pid, game2.PlayerGameEngine.side_used(b, p) if getattr(b, "bats", "") else "", getattr(p, "throws", ""),
               getattr(b, "bats", ""))
        eng._r3cap = {}
        out = orig_finish(self)
        cap, eng._r3cap = eng._r3cap, None
        seq = cap.get("seq") or ""
        _STATE["pa"].append(pre + (cap.get("res", ""), sum(c != "N" for c in seq), st.score[bat] - pre[7], st.outs))
        return out

    def final(self):
        out = orig_final(self)
        st = self.st
        gid = getattr(self, "_r3gid", None)
        if gid is not None:
            _STATE["games"].append((gid, st.team_obj["home"].tid, st.team_obj["away"].tid, st.score["home"], st.score["away"], st.inning,
                                    bool(st.ended_by_run_rule), bool(st.weekend), bool(st.tournament), bool(self.neutral),
                                    tuple(st.half_innings)))
        return out

    game2.GameSession._finish_pa, game2.PlayerGameEngine._record, game2.GameSession._final = finish, record, final
    game2.GameSession._r3 = True


PA_COLS = ("gid", "inning", "half", "outs", "on1", "on2", "on3", "bat_score", "pit_score", "bat_team", "pit_team", "bat_home",
           "batter", "pitcher", "side", "throws", "bats", "res", "pitches", "runs", "outs_after")
GAME_COLS = ("gid", "home", "away", "home_score", "away_score", "innings", "run_rule", "weekend", "tournament", "neutral", "half_innings")


def season(seed: int) -> dict:
    from config import phase2
    from engine.season import simulate_season
    _instrument()
    _STATE.update(gid=0, pa=[], games=[])
    res = simulate_season(phase2.load(), seed)
    lg = res["league"]
    teams = {t.tid: {"name": t.name, "tier": t.tier, "conference": t.conference, "o": t.o, "d": t.d} for t in lg.teams}
    pa = {c: np.array([r[i] for r in _STATE["pa"]]) for i, c in enumerate(PA_COLS)}
    return {"seed": seed, "pa": pa, "games": list(_STATE["games"]), "teams": teams}


def out_dir() -> Path:
    from run_phase5 import _code_id
    return ROOT / "runs" / "round3" / _code_id()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", type=int, default=8)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    d = out_dir(); d.mkdir(parents=True, exist_ok=True)
    todo = [s for s in ROUND3_SEEDS[:a.seasons] if not (d / f"season_{s}.pkl").exists()]
    with ProcessPoolExecutor(a.workers) as ex:
        for r in ex.map(season, todo):
            tmp = d / f"season_{r['seed']}.tmp"
            tmp.write_bytes(pickle.dumps(r))
            tmp.replace(d / f"season_{r['seed']}.pkl")
            print(f"season {r['seed']}: {len(r['pa']['gid'])} PAs, {len(r['games'])} games", flush=True)
    print(d)


if __name__ == "__main__":
    main()
