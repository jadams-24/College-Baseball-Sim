"""56-game season: 14 weeks of a three-game weekend series plus one midweek game. Game dates
follow the real weekly calendar (Phase 6): the midweek game on Mon/Tue/Wed and the series on
Thu-Sat or Fri-Sun (doubleheaders included) at their 2025 rates. The last
`conference_weekends` weeks are conference series (round robin, circle method, home
sides alternating). Byes, independents, the early nonconference weekends and every
midweek game are paired by drawing the tier pair from the real joint mix of
nonconference games (weekend or midweek), and the host from the scoreboard hosting
model: P(a hosts b) = expit(tier-pair term + slope * (strength_a - strength_b)), where
strength = o + d in log runs.

Phase 6 (scripts/build_phase6_schedule.py): real nonconference schedules are matched by strength
within tier. The teams in cross-tier games are not a random draw from their tier (low teams that
play P4 teams sit well above their tier's mean; PHASE0_NOTES, Phase 6), and opponents' strengths covary. Each week's
tier pairs are drawn as before; then the teams of each tier fill their cross-tier slots, picked with
weight exp(beta[tier|opponent tier] * deviation) where deviation is the team's strength minus its
tier's mean (scoreboard totals), and the same-tier slots take the rest. Within each tier pair the
teams are matched by rank on z + sigma * N(0, 1), z the deviation in tier SD units."""
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
    date: int = 0     # days since opening day (Phase 6 calendar; rest between appearances)


def _calendar() -> tuple | None:
    """Real weekly game days (scripts/build_phase6_usage.py): the weekday of the midweek game and
    of the three series games, drawn independently (midweek day; series days as a triple, so
    Thursday starts and Saturday doubleheaders come at their real rates)."""
    from config import phase6
    if not phase6.on("calendar"):
        return None
    pats = phase6.load()["usage6"]["calendar"]["patterns"]
    mid, ser = {}, {}
    for k, v in pats.items():
        m, a, b, c = (int(x) for x in k.split("|"))
        mid[m] = mid.get(m, 0) + v
        ser[(a, b, c)] = ser.get((a, b, c), 0) + v
    mk, sk = sorted(mid), sorted(ser)
    return mk, np.array([mid[k] for k in mk]), sk, np.array([ser[k] for k in sk])


def _circle(teams: list) -> list:
    t = list(teams) + ([None] if len(teams) % 2 else [])
    n = len(t)
    rounds = []
    for r in range(n - 1):
        pairs = [(t[i], t[n - 1 - i]) for i in range(n // 2)]
        rounds.append(pairs)
        t = [t[0]] + [t[-1]] + t[1:-1]
    return rounds


def _pair(pool: list, pair_shares: dict, tier_of: dict, rng: np.random.Generator, sel: dict | None = None) -> list:
    """Pair a pool of teams by drawing tier pairs from the joint nonconference mix. With sel (Phase 6
    schedule selection), which teams fill the drawn tier pairs and who meets whom follow strength."""
    avail = {t: [x for x in pool if tier_of[x] == t] for t in TIERS}
    for t in TIERS:
        rng.shuffle(avail[t])
    types = [tuple(k.split("|")) for k in sorted(pair_shares)]
    pairs, drawn = [], []
    while True:
        ok = [(a, b) for a, b in types if (len(avail[a]) >= 2 if a == b else (avail[a] and avail[b]))]
        if not ok:
            break
        w = np.array([pair_shares[f"{a}|{b}"] for a, b in ok])
        a, b = ok[int(rng.choice(len(ok), p=w / w.sum()))]
        if sel is None:
            pairs.append((avail[a].pop(), avail[b].pop()))
        else:
            drawn.append((a, b))
            avail[a].pop(); avail[b].pop()      # counts only; the teams are assigned below
    left = [x for t in TIERS for x in avail[t]]  # at most one team per tier can be left; pair them up
    rng.shuffle(left)
    if sel is not None:
        pairs = _select(drawn, [x for x in pool if x not in set(left)], tier_of, sel, rng)
    pairs += [(left[i], left[i + 1]) for i in range(0, len(left) - 1, 2)]
    return pairs


def _select(drawn: list, teams: list, tier_of: dict, sel: dict, rng: np.random.Generator) -> list:
    """Fill the drawn tier pairs with teams: cross-tier slots first (random order), each taking a team of
    its tier with weight exp(beta * deviation); same-tier slots take the rest. Then match within each
    tier pair by rank on z + sigma * noise."""
    dev, z, beta, sig = sel["dev"], sel["z"], sel["beta"], sel["sigma"]
    free = {t: [x for x in teams if tier_of[x] == t] for t in TIERS}
    slots = [(a, b) for a, b in drawn if a != b] + [(b, a) for a, b in drawn if a != b]
    order = rng.permutation(len(slots))
    filled: dict = {}
    for k in order:
        t, u = slots[k]
        c = free[t]
        w = np.exp(beta[f"{t}|{u}"] * np.array([dev[x] for x in c]))
        i = int(rng.choice(len(c), p=w / w.sum()))
        filled.setdefault((t, u), []).append(c.pop(i))
    for a, b in drawn:
        if a == b:
            filled.setdefault((a, a), []).append(free[a].pop(int(rng.integers(len(free[a])))))
            filled[(a, a)].append(free[a].pop(int(rng.integers(len(free[a])))))

    def ranked(xs):
        key = np.array([z[x] for x in xs]) + sig * rng.standard_normal(len(xs))
        return [xs[i] for i in np.argsort(key)]
    pairs = []
    for (t, u), xs in sorted(filled.items()):
        if t < u:
            pairs += list(zip(ranked(xs), ranked(filled[(u, t)])))
        elif t == u:
            r = ranked(xs)
            pairs += [(r[i], r[i + 1]) for i in range(0, len(r) - 1, 2)]
    return pairs


def _selection(league) -> dict | None:
    """Phase 6 schedule selection inputs: each team's deviation from its tier's mean strength (scoreboard
    totals) and in tier SD units, and the fitted weights."""
    from config import phase6
    if not phase6.on("schedule"):
        return None
    blk = phase6.load().get("schedule6")
    if not blk:
        return None
    s = {t.tid: t.s_total for t in league.teams}
    dev, z = {}, {}
    for tr in TIERS:
        ids = [t.tid for t in league.teams if t.tier == tr]
        m, sd = float(np.mean([s[i] for i in ids])), float(np.std([s[i] for i in ids]))
        for i in ids:
            dev[i] = s[i] - m; z[i] = dev[i] / sd
    return {"dev": dev, "z": z, "beta": blk["beta"], "sigma": blk["sigma"]}


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
    cal = _calendar()
    # calendar draws use their own stream so the pairings and hosts are unchanged for a given seed
    cal_rng = np.random.Generator(np.random.PCG64(rng.bit_generator.seed_seq.spawn(1)[0]))
    sel = _selection(league)
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
        pairs += [_host(a, b, host, tier_of, strength, rng) for a, b in _pair(pool, mix["weekend_pairs"], tier_of, rng, sel)]
        for home, away in pairs:
            days = cal[2][int(cal_rng.choice(len(cal[2]), p=cal[3] / cal[3].sum()))] if cal else (4, 5, 6)
            for d in range(GAMES_PER_WEEKEND):
                games.append(Game(week, d, home, away, True, 7 * week + days[d]))
        for a, b in _pair([t.tid for t in league.teams], mix["midweek_pairs"], tier_of, rng, sel):
            h, aw = _host(a, b, host, tier_of, strength, rng)
            md = cal[0][int(cal_rng.choice(len(cal[0]), p=cal[1] / cal[1].sum()))] if cal else 1
            games.append(Game(week, 3, h, aw, False, 7 * week + md))
    games.sort(key=lambda g: (g.date, g.week, g.day if g.day < 3 else -1))
    return games
