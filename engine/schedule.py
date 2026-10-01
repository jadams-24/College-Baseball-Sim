"""56-game season: 14 weeks of a Fri-Sun series plus one midweek game. The last
`conference_weekends` weeks are conference series (round robin, circle method, home
sides alternating). Byes, independents, the early nonconference weekends and every
midweek game are paired by drawing the tier pair from the real joint mix of
nonconference games (weekend or midweek), and the host from the scoreboard hosting
model: P(a hosts b) = expit(tier-pair term + slope * (strength_a - strength_b)), where
strength = o + d in log runs."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from config.phase2 import GAMES_PER_WEEKEND, TIERS, WEEKS


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


def _pair(pool: list, pair_shares: dict, tier_of: dict, rng: np.random.Generator) -> list:
    """Pair a pool of teams by drawing tier pairs from the joint nonconference mix."""
    avail = {t: [x for x in pool if tier_of[x] == t] for t in TIERS}
    for t in TIERS:
        rng.shuffle(avail[t])
    types = [tuple(k.split("|")) for k in sorted(pair_shares)]
    pairs = []
    while True:
        ok = [(a, b) for a, b in types if (len(avail[a]) >= 2 if a == b else (avail[a] and avail[b]))]
        if not ok:
            break
        w = np.array([pair_shares[f"{a}|{b}"] for a, b in ok])
        a, b = ok[int(rng.choice(len(ok), p=w / w.sum()))]
        pairs.append((avail[a].pop(), avail[b].pop()))
    left = [x for t in TIERS for x in avail[t]]  # at most one team per tier can be left; pair them up
    rng.shuffle(left)
    pairs += [(left[i], left[i + 1]) for i in range(0, len(left) - 1, 2)]
    return pairs


def _host(a, b, host: dict, tier_of: dict, strength: dict, rng) -> tuple:
    x = host["strength_slope"] * (strength[a] - strength[b])
    ta, tb = tier_of[a], tier_of[b]
    for key, v in host["tier_pair_logit"].items():
        hi, lo = key.split("_vs_")
        if (ta, tb) == (hi, lo):
            x += v
        elif (ta, tb) == (lo, hi):
            x -= v
    return (a, b) if rng.random() < 1 / (1 + math.exp(-x)) else (b, a)


def make_schedule(cfg, league, rng: np.random.Generator) -> list:
    tier_of = {t.tid: t.tier for t in league.teams}
    strength = {t.tid: t.o + t.d for t in league.teams}
    host = cfg.team_talent["hosting"]
    mix = cfg.schedule_mix
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
        pairs += [_host(a, b, host, tier_of, strength, rng) for a, b in _pair(pool, mix["weekend_pairs"], tier_of, rng)]
        for home, away in pairs:
            for d in range(GAMES_PER_WEEKEND):
                games.append(Game(week, d, home, away, True))
        for a, b in _pair([t.tid for t in league.teams], mix["midweek_pairs"], tier_of, rng):
            h, aw = _host(a, b, host, tier_of, strength, rng)
            games.append(Game(week, 3, h, aw, False))
    games.sort(key=lambda g: (g.week, g.day if g.day < 3 else -1))
    return games
