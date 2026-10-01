"""56-game season: 14 weeks of a Fri-Sun series plus one midweek game. The last
`conference_weekends` weeks are conference series (round robin, circle method); byes,
independents, the early nonconference weekends and every midweek game are paired by
sampling the opponent tier from the real nonconference mix for the team's tier."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config.phase2 import GAMES_PER_WEEKEND, P_FIRST_TEAM_HOSTS, TIERS, WEEKS


@dataclass(frozen=True)
class Game:
    week: int
    day: int          # 0-2 weekend series game, 3 midweek
    home: int
    away: int
    weekend: bool


def _circle(teams: list) -> list:
    t = list(teams) + ([None] if len(teams) % 2 else [])
    n = len(t)
    rounds = []
    for r in range(n - 1):
        pairs = [(t[i], t[n - 1 - i]) for i in range(n // 2)]
        rounds.append(pairs)
        t = [t[0]] + [t[-1]] + t[1:-1]
    return rounds


def _pair(pool: list, mix: dict, tier_of: dict, rng: np.random.Generator) -> list:
    pool = list(pool)
    rng.shuffle(pool)
    unpaired = set(pool)
    pairs = []
    for a in pool:
        if a not in unpaired:
            continue
        unpaired.discard(a)
        if not unpaired:
            break
        m = mix[tier_of[a]]
        labels = [t for t in TIERS if t in m]
        want = labels[int(rng.choice(len(labels), p=np.array([m[t] for t in labels]) / sum(m[t] for t in labels)))]
        cands = sorted(b for b in unpaired if tier_of[b] == want) or sorted(unpaired)
        b = cands[int(rng.integers(len(cands)))]
        unpaired.discard(b)
        pairs.append((a, b))
    return pairs


def make_schedule(cfg, league, rng: np.random.Generator) -> list:
    tier_of = {t.tid: t.tier for t in league.teams}
    conf_rounds = {cid: _circle(c[1]) for cid, c in league.conferences.items() if not c[3] and len(c[1]) > 1}
    first_conf_week = WEEKS - cfg.conference_weekends
    games = []
    for week in range(WEEKS):
        pool = [t.tid for t in league.teams]
        pairs = []
        if week >= first_conf_week:
            k = week - first_conf_week
            in_series = set()
            for cid, rounds in conf_rounds.items():
                for a, b in rounds[k % len(rounds)]:
                    if a is not None and b is not None:
                        pairs.append((a, b) if (k + a) % 2 else (b, a))
                        in_series.update((a, b))
            pool = [t for t in pool if t not in in_series]
        pairs += _pair(pool, cfg.schedule_mix["weekend"], tier_of, rng)
        for home, away in pairs:
            if rng.random() < P_FIRST_TEAM_HOSTS and week < first_conf_week:
                home, away = away, home
            for d in range(GAMES_PER_WEEKEND):
                games.append(Game(week, d, home, away, True))
        for a, b in _pair([t.tid for t in league.teams], cfg.schedule_mix["midweek"], tier_of, rng):
            games.append(Game(week, 3, a, b, False) if rng.random() < P_FIRST_TEAM_HOSTS else Game(week, 3, b, a, False))
    games.sort(key=lambda g: (g.week, g.day if g.day < 3 else -1))
    return games
