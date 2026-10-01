"""AI manager for Phase 2: answers the engine's Decider calls from empirical usage.

  lineup            each regular starts with the real start share for his rank; empty
                    spots go to bench players by their rank's share; batting order is
                    the team's talent order (best expected OBP+SLG first)
  starting_pitcher  weekend: each series draws a real three-game pattern of starter ranks
                    (the team's 1st..8th most frequent weekend starter in games 1, 2, 3 of a
                    weekend; the top three make ~79% of weekend starts); ranks map to staff
                    slots (config ROTATION_STAFF), a repeated pooled rank takes the next
                    reliever. Midweek: the two midweek starters alternate.
  pitching_change   pull hazard from the play-by-play: P(replaced before the next batter |
                    starter or reliever, weekend, outing pitch count, outing runs, inning
                    just ended); weekend starters use the table for their rotation rank
                    (1, 2, 3, spot starter), which carries the aces' longer leash; the
                    pitcher's own leash (Stamina, Phase 4) scales it: h' = 1 - (1 - h)^theta
  relief_pitcher    an unused reliever, weighted by the real share of relief batters
                    faced by bullpen rank
Steals, bunts and intentional walks stay at league rates (Phase 6 is manager AI).
"""
from __future__ import annotations

import numpy as np

from config.phase2 import GAMES_PER_WEEKEND, MIN_HAZARD_N, N_BENCH, N_REGULARS, ROTATION_STAFF, SPOT_STARTER_RANK, Phase2Config
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
        pats = u["weekend_series_rank_patterns"]
        self.patterns = [tuple(int(x) for x in k.split("|")) for k in pats]
        w = np.array([pats[k] for k in pats], float)
        self.pattern_w = w / w.sum()
        self.series_plan: dict = {}
        self.midweek_count: dict = {}
        self.sp_table, self.sp_back = table(u["starter_pull"])
        self.wr_table, self.wr_back = table(u["weekend_starter_pull_by_rank"])
        self.rank_now: dict = {}  # team id -> rotation rank class of today's weekend starter
        self.rp_table, self.rp_back = table(u["reliever_pull"])
        # pull decisions per pitcher, for estimating leash back from simulated seasons (Phase 4 round trip):
        # sum of log(1 - h) where he stayed, baseline h at each decision where he was pulled
        self.leash_survive: dict = {}
        self.leash_pulls: dict = {}

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
        tm = state.team_obj[team]
        if not state.weekend:
            k = self.midweek_count.get(tm.tid, 0)
            self.midweek_count[tm.tid] = k + 1
            return tm.midweek_sp[k % len(tm.midweek_sp)]
        key = (tm.tid, state.week)
        if key not in self.series_plan:
            ranks = self.patterns[int(state.rng.choice(len(self.patterns), p=self.pattern_w))]
            plan, taken = [], set()
            for r in ranks:
                grp, i = ROTATION_STAFF[r - 1]
                p = getattr(tm, grp)[i]
                if p.pid in taken:  # pooled deepest rank repeated: next unused reliever
                    p = next(x for x in tm.relievers if x.pid not in taken)
                taken.add(p.pid); plan.append((p, r))
            self.series_plan[key] = plan
        pitcher, rank = self.series_plan[key][min(state.day, GAMES_PER_WEEKEND - 1)]
        self.rank_now[tm.tid] = min(rank, SPOT_STARTER_RANK)
        return pitcher

    # ---- pitching changes ------------------------------------------------------------------
    def _hazard(self, starter: bool, weekend: int, pitches: int, runs: int, inning_end: int, rank: int | None = None) -> float:
        pb, rb = min(pitches // 10, 12), min(runs, 5)
        if starter and weekend and rank is not None:
            chain = ((self.wr_table, f"{rank}|{pb}|{rb}|{inning_end}"), (self.wr_back, f"{rank}|{pb}|{inning_end}"),
                     (self.sp_table, f"{weekend}|{pb}|{rb}|{inning_end}"), (self.sp_back, f"{weekend}|{pb}|{inning_end}"))
        elif starter:
            chain = ((self.sp_table, f"{weekend}|{pb}|{rb}|{inning_end}"), (self.sp_back, f"{weekend}|{pb}|{inning_end}"))
        else:
            chain = ((self.rp_table, f"{pb}|{rb}|{inning_end}"), (self.rp_back, f"{pb}|{inning_end}"))
        c = None
        for tab, key in chain:
            c = tab.get(key)
            if c is not None and c[1] >= MIN_HAZARD_N:
                break
        if c is None or c[1] == 0:
            return None  # beyond the observed range
        return c[0] / c[1]

    def pitching_change(self, state):
        o = state.outing[state.fielding_side]
        if not state.bullpen_left(state.fielding_side):
            return Decision.NO
        rank = self.rank_now.get(state.team_obj[state.fielding_side].tid) if state.weekend else None
        h = self._hazard(o["starter"], int(state.weekend), o["pitches"], o["runs"], int(state.inning_end), rank)
        if h is None:  # no hazard cell has data (pitch counts past the sample's maximum): the data's maximum
            return Decision.YES if o["pitches"] >= 120 else Decision.NO
        pid = state.pitcher[state.fielding_side].pid
        theta = np.exp(state.pitcher[state.fielding_side].log_theta)
        pulled = state.rng.random() < -np.expm1(theta * np.log1p(-min(h, 1 - 1e-9)))
        if pulled:
            self.leash_pulls.setdefault(pid, []).append(h)
        else:
            self.leash_survive[pid] = self.leash_survive.get(pid, 0) + np.log1p(-min(h, 1 - 1e-9))
        return Decision.YES if pulled else Decision.NO

    def relief_pitcher(self, state, team: str):
        avail = [p for p in state.team_obj[team].relievers if p.pid not in state.used[team]]
        if not avail:
            return None
        w = np.array([self.relw[p.order] for p in avail])
        return avail[int(state.rng.choice(len(avail), p=w / w.sum()))]
