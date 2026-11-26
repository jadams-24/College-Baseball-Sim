"""Phase 8: class years on the five-year clock and the year-to-year turnover of rosters (the container).

Plan: plans/phase8_plan_2026-11-26.md. Numbers: config.phase8.roster() (the Phase 8-11 yardstick).

Class years. Every player has a year on the NCAA's five-year clock (Fr, So, Jr, Sr, 5th: five years to play five
seasons, no redshirts, from 8/1/26). The first season's classes are drawn per player from the 2025 class shares of
his team's tier, from their own stream: a label, read by no game.

Turnover (advance_year). After a season each player returns to his program with his class's rate (the fifth year
never returns: the clock) and moves up a class; the others leave. Each leaver is replaced by a newcomer in the same
roster slot (the leaver's pid, his role group and, for the nine regulars, his position), whose class is drawn from
the newcomers' class mix that keeps the class shares where the rosters have them (freshmen, and transfers in the
later classes).

A newcomer is the player a fresh draw of the league (the same talent model, another seed: the "donor" league) put in
that slot, moved from the donor team's level to this team's: z = donor z - donor team offsets + this team's offsets,
his ratings read again from z. So each season's league is a draw from the calibrated talent model around the same
teams: the talent and team-strength distributions cannot drift, which is the Phase 8 gate (every Phase 1-7 row
over 20+ years of turnover).

Not here yet (the plan's next steps): development (a returning player keeps his ratings), who leaves by talent (the
draft takes the best juniors, weak freshmen leave: departures here are by class only), rosters deeper than the
players who appear, cuts, and where newcomers come from (Phase 9).
"""
from __future__ import annotations

import copy

import numpy as np

from config import phase8
from config.phase2 import N_REGULARS, RATES
from engine.matchup import matchup_probs
from engine.ratings import RatingScale

CLASSES = phase8.CLASSES
_KEEP_RATINGS = ("speed", "glove", "arm", "stamina", "hold")      # ratings that are not read from z


def _pick(rng, dist: dict) -> str:
    keys = list(dist)
    return keys[int(rng.choice(len(keys), p=np.array([dist[k] for k in keys])))]


def draw_classes(league, rng) -> None:
    """The first season's class years: per player, from his tier's class shares; uid = pid."""
    shares = phase8.roster()["shares"]
    for p in league.players:
        p.year = _pick(rng, shares[league.teams[p.team].tier])
        p.uid = p.pid
    league.next_uid = len(league.players)


def class_shares(league) -> dict:
    """Class shares by tier (the gate row against the 2025 rosters)."""
    out = {}
    for tier in ("p4", "mid", "low"):
        ys = [p.year for p in league.players if league.teams[p.team].tier == tier]
        out[tier] = {c: ys.count(c) / max(len(ys), 1) for c in CLASSES}
    return out


def _bat_value(cfg, p) -> float:
    """Expected on-base plus slugging against a league-average pitcher (engine.league's lineup rank)."""
    pr = matchup_probs(cfg, p.z, np.zeros(6), {r: 0.0 for r in RATES})
    ob = pr["BB"] + pr["HBP"] + pr["1B"] + pr["2B"] + pr["3B"] + pr["HR"]
    return ob + (pr["1B"] + 2 * pr["2B"] + 3 * pr["3B"] + 4 * pr["HR"])


def _rank_team(cfg, t, rng) -> None:
    """A team's orders after its roster changed, by engine.league's rules: batters' batting order by hitting value
    within regulars and bench, their start rank by rho x standardized hitting value + noise (Phase 6), and each
    pitching group by K - BB - HR."""
    from config import phase6
    pt_rho = phase6.load().get("subs6", {}).get("bench_pick_weight", {}).get("playing_time_rho", {}).get("value") if phase6.on("subs") else None
    regs = [p for p in t.batters if p.group == "regular"]
    bench = [p for p in t.batters if p.group == "bench"]
    for grp, base in ((regs, 0), (bench, N_REGULARS)):
        v = np.array([_bat_value(cfg, p) for p in grp])
        for k, i in enumerate(np.argsort(-v)):
            grp[i].bat_order = base + k
        key = v
        if pt_rho is not None:
            z = (v - v.mean()) / (v.std() if v.std() > 0 else 1.0)
            key = pt_rho * z + np.sqrt(1 - pt_rho ** 2) * rng.standard_normal(len(v))
        for k, i in enumerate(np.argsort(-key)):
            grp[i].order = base + k
    t.batters = sorted(regs + bench, key=lambda p: p.order)
    quality = lambda p: p.z[0] - p.z[1] - p.z[3]
    for name in ("weekend_sp", "midweek_sp", "relievers"):
        lst = sorted(getattr(t, name), key=quality, reverse=True)
        for k, p in enumerate(lst):
            p.order = k
        setattr(t, name, lst)


def _newcomer(scale, donor, d_team, leaver, t, year: str, uid: int):
    """The donor player in the leaver's slot on team t: the donor's own draw (his deviation from his team, his
    position, speed, glove, arm, hands, stamina, hold and name), on team t's level."""
    p = copy.copy(donor)
    off_d, off_t = (d_team.tb, t.tb) if p.side == "bat" else (d_team.tp, t.tp)
    z = np.asarray(donor.z, float) - off_d + off_t
    ratings, hidden = scale.split(p.side, z)
    p.ratings = dict({k: v for k, v in donor.ratings.items() if k in _KEEP_RATINGS}, **ratings)
    p.hidden = hidden
    p.z = scale.compose(p.side, ratings, hidden)
    p.pid, p.team, p.group, p.year, p.uid = leaver.pid, t.tid, leaver.group, year, uid
    return p


def advance_year(cfg, league, rng) -> dict:
    """One offseason, in place: returns, departures and newcomers (module docstring). `rng` gives the donor
    league's seed and the turnover's draws. Returns the counts by class and the leavers and newcomers by team."""
    from engine.league import build_league
    r = phase8.roster()
    if any(t.tb is None for t in league.teams):
        raise ValueError("this league was built before Phase 8 (no team offsets kept): start a new one")
    seeds = rng.bit_generator.seed_seq.spawn(2)
    donor = build_league(cfg, np.random.Generator(np.random.PCG64(seeds[0])))
    turn = np.random.Generator(np.random.PCG64(seeds[1]))
    scale = RatingScale()
    out = {"left": {c: 0 for c in CLASSES}, "arrived": {c: 0 for c in CLASSES}, "returned": 0, "teams": {}}
    for t, dt in zip(league.teams, donor.teams):
        roster = t.batters + t.weekend_sp + t.midweek_sp + t.relievers
        leavers = []
        for p in sorted(roster, key=lambda p: p.pid):
            if p.year != CLASSES[-1] and turn.random() < r["stay"][p.year]:
                p.year = CLASSES[CLASSES.index(p.year) + 1]
                out["returned"] += 1
            else:
                leavers.append(p)
        # donors: a regular's replacement plays his position; a bench batter's one a bench donor of his position when
        # there is one left, else any bench donor (with the donor's position); a pitcher's one the same roster slot
        d_reg = {p.pos: p for p in dt.batters if p.group == "regular"}
        d_bench = sorted((p for p in dt.batters if p.group == "bench"), key=lambda p: p.pid)
        by_pid = {p.pid: p for p in dt.weekend_sp + dt.midweek_sp + dt.relievers}
        new = {}
        for p in leavers:
            if p.side == "pit":
                d = by_pid[p.pid]
            elif p.group == "regular":
                d = d_reg[p.pos]
            else:
                same = [q for q in d_bench if q.pos == p.pos] or d_bench
                d = same[int(turn.integers(len(same)))]          # at random: the donor list is in start-rank order
                d_bench.remove(d)
            n = _newcomer(scale, d, dt, p, t, _pick(turn, r["entrants"][t.tier]), league.next_uid)
            league.next_uid += 1
            new[p.pid] = n
            league.players[p.pid] = n
            out["left"][p.year] += 1; out["arrived"][n.year] += 1
        t.batters = [new.get(p.pid, p) for p in t.batters]
        for name in ("weekend_sp", "midweek_sp", "relievers"):
            setattr(t, name, [new.get(p.pid, p) for p in getattr(t, name)])
        _rank_team(cfg, t, turn)
        out["teams"][t.tid] = {"left": [(p.uid, p.name, p.year, p.group, p.pos) for p in leavers],
                               "arrived": [(n.uid, n.name, n.year, n.group, n.pos) for n in new.values()]}
    return out
