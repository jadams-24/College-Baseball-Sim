"""AI manager for Phase 2: answers the engine's Decider calls from empirical usage.

  lineup            each regular starts with the real start share for his rank; empty
                    spots go to bench players by their rank's share; batting order is
                    the team's talent order (best expected OBP+SLG first)
  starting_pitcher  weekend series game k -> k-th weekend starter; midweek alternates
  pitching_change   pull hazard from the play-by-play: P(replaced before the next batter |
                    starter or reliever, weekend, outing pitch count, outing runs, inning
                    just ended)
  relief_pitcher    an unused reliever, weighted by the real share of relief batters
                    faced by bullpen rank
Steals, bunts and intentional walks stay at league rates (Phase 6 is manager AI).
"""
from __future__ import annotations

import numpy as np

from config.phase2 import MIN_HAZARD_N, N_BENCH, N_REGULARS, Phase2Config
from engine.decider import Decision, LeagueAverageDecider


class Manager(LeagueAverageDecider):
    def __init__(self, cfg: Phase2Config):
        u = cfg.usage
        self.start = [u["batter_start_share_by_rank"][str(k + 1)] for k in range(N_REGULARS + N_BENCH)]
        self.relw = [u["reliever_bf_share_by_rank"][str(k + 1)] for k in range(len(u["reliever_bf_share_by_rank"]))]

        def table(block):
            t = {k: v for k, v in block["table"].items()}
            b = {k: v for k, v in block["backoff"].items()}
            return t, b
        self.sp_table, self.sp_back = table(u["starter_pull"])
        self.rp_table, self.rp_back = table(u["reliever_pull"])

    # ---- lineup ------------------------------------------------------------------------
    def lineup(self, state, team: str):
        tm = state.team_obj[team]
        rng = state.rng
        starters = [p for k, p in enumerate(tm.batters[:N_REGULARS]) if rng.random() < self.start[k]]
        bench = list(tm.batters[N_REGULARS:])
        while len(starters) < N_REGULARS and bench:
            w = np.array([self.start[p.order] for p in bench])
            pick = bench.pop(int(rng.choice(len(bench), p=w / w.sum())))
            starters.append(pick)
        starters += [p for p in tm.batters[:N_REGULARS] if p not in starters][: N_REGULARS - len(starters)]
        return sorted(starters, key=lambda p: p.order)

    def starting_pitcher(self, state, team: str):
        return state.scheduled_starter[team]

    # ---- pitching changes ------------------------------------------------------------------
    def _hazard(self, starter: bool, weekend: int, pitches: int, runs: int, inning_end: int) -> float:
        pb, rb = min(pitches // 10, 12), min(runs, 5)
        if starter:
            c = self.sp_table.get(f"{weekend}|{pb}|{rb}|{inning_end}")
            if c is None or c[1] < MIN_HAZARD_N:
                c = self.sp_back.get(f"{weekend}|{pb}|{inning_end}")
        else:
            c = self.rp_table.get(f"{pb}|{rb}|{inning_end}")
            if c is None or c[1] < MIN_HAZARD_N:
                c = self.rp_back.get(f"{pb}|{inning_end}")
        if c is None or c[1] == 0:
            return 1.0 if pitches >= 120 else 0.0  # beyond the observed range: the data's maximum
        return c[0] / c[1]

    def pitching_change(self, state):
        o = state.outing[state.fielding_side]
        if not state.bullpen_left(state.fielding_side):
            return Decision.NO
        h = self._hazard(o["starter"], int(state.weekend), o["pitches"], o["runs"], int(state.inning_end))
        return Decision.YES if state.rng.random() < h else Decision.NO

    def relief_pitcher(self, state, team: str):
        avail = [p for p in state.team_obj[team].relievers if p.pid not in state.used[team]]
        if not avail:
            return None
        w = np.array([self.relw[p.order] for p in avail])
        return avail[int(state.rng.choice(len(avail), p=w / w.sum()))]
