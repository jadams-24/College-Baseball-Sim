"""Phase 8: class years on the five-year clock and the year-to-year turnover of rosters (the container).

Plan: plans/phase8_plan_2026-11-26.md. Numbers: config.phase8.roster() (the Phase 8-11 yardstick).

Class years. Every player has a year on the NCAA's five-year clock (Fr, So, Jr, Sr, 5th: five years to play five
seasons, no redshirts, from 8/1/26). The first season's classes are drawn per player from the 2025 class shares of
his team's tier, from their own stream: a label, read by no game.

Turnover (advance_year = plan_offseason + apply_offseason). After a season each player returns to his program
with the real rate of his class, role and playing time (config.phase8.retention: a freshman who played returns far
more often than one who did not, the most-used juniors leave most, the fifth year never returns: the clock) and
moves up a class; the others leave. The plan (who leaves, each player's stay rate, a display reason) is drawn first
and applied second, so a coach can see the Players Leaving list and persuade some to stay in between (`kept`).
Each leaver is replaced by a newcomer in the same roster slot (the leaver's pid, his role group and, for the nine
regulars, his position), whose class is drawn from the mix that brings the tier's class shares back to the rosters'
(freshmen, and transfers in the later classes).

A newcomer is the player a fresh draw of the league (the same talent model, another seed: the "donor" league) put in
that slot, moved from the donor team's level to this team's: z = donor z - donor team offsets + this team's offsets,
his ratings read again from z. So each season's league is a draw from the calibrated talent model around the same
teams: the talent and team-strength distributions cannot drift, which is the Phase 8 gate (every Phase 1-7 row
over 20+ years of turnover).

Development (2026-11-27): a returner's talent changes by his class's mean gain, his own rate and noise; newcomers
arrive lower so each group's league mean holds; a bench batter can take a regular's job (PHASE8_NOTES).

Not here yet (plans/phase8_retention_2026-11-26.md): the draft's
own sign-or-return decision and the portal's destinations (a leaver is gone), money, dealbreakers, rosters deeper than
the players who appear, cuts, and where newcomers come from (Phase 9).
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


def _dev_sd(scale, side: str, kind: str) -> np.ndarray:
    """SD per rate (logit) of the individual part of development: DEV_SD_POINTS rating points, on the developed rates."""
    role = "batter" if side == "bat" else "pitcher"
    return np.array([phase8.DEV_SD_POINTS[kind] / 10.0 * scale.ms(side, r)[1] if r in phase8.DEV_RATES[role] else 0.0 for r in RATES])


def draw_potential(league, rng) -> None:
    """Each player's own yearly gain beyond his class's (Player.dev), fixed for his career."""
    scale = RatingScale()
    sd = {side: _dev_sd(scale, side, "potential") for side in ("bat", "pit")}
    for p in league.players:
        p.dev = sd[p.side] * rng.standard_normal(len(RATES))


def _class_mean(side: str) -> dict:
    m = phase8.development()["mean"]["batter" if side == "bat" else "pitcher"]
    return {c: np.array([m[c][r] for r in RATES]) for c in CLASSES[:-1]}


def _set_z(scale, p, z) -> None:
    ratings, hidden = scale.split(p.side, np.asarray(z, float))
    p.ratings = dict({k: v for k, v in p.ratings.items() if k in _KEEP_RATINGS}, **ratings)
    p.hidden = hidden
    p.z = scale.compose(p.side, ratings, hidden)


def potential(p, scale=None) -> dict:
    """His ratings after his remaining seasons at his class's mean gains plus his own rate (no noise): the
    developed ratings only. A fifth-year's potential is his current ratings."""
    scale = scale or RatingScale()
    z = np.asarray(p.z, float).copy()
    if p.year in CLASSES[:-1]:
        mean = _class_mean(p.side)
        own = p.dev if getattr(p, "dev", None) is not None else 0.0
        for c in CLASSES[CLASSES.index(p.year):-1]:
            z = z + mean[c] + own
    return scale.split(p.side, z)[0]


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


def _rel(league, p) -> np.ndarray:
    t = league.teams[p.team]
    return np.asarray(p.z, float) - (t.tb if p.side == "bat" else t.tp)


def _steady(scale, league, donor, newcomers) -> None:
    """Hold the league's talent where it was calibrated: returners gained (and the ones who left were not a random
    draw), so the newcomers of each role group arrive lower by the shift that brings the group's mean talent,
    relative to its teams, back to a fresh league's (the donor's). Classes then differ (freshmen below, seniors
    above) while each group's league mean, rate by rate, stays the calibrated one."""
    for g in sorted({p.group for p in league.players}):
        new = [n for n in newcomers if n.group == g]
        if not new:
            continue
        target = np.mean([_rel(donor, p) for p in donor.players if p.group == g], axis=0)
        now = [_rel(league, p) for p in league.players if p.group == g]
        shift = (target - np.mean(now, axis=0)) * len(now) / len(new)
        for n in new:
            n.z = np.asarray(n.z, float) + shift
    for n in newcomers:
        _set_z(scale, n, n.z)


def _promote(cfg, t) -> None:
    """A bench batter who now out-hits the regular at his own position takes the job (the roles swap; positions,
    gloves and arms stay each player's own). Pitchers keep their role groups for now, and the DH his."""
    for reg in [p for p in t.batters if p.group == "regular"]:
        cand = [p for p in t.batters if p.group == "bench" and p.pos == reg.pos]
        if cand:
            best = max(cand, key=lambda p: _bat_value(cfg, p))
            if _bat_value(cfg, best) > _bat_value(cfg, reg):
                best.group, reg.group = "regular", "bench"


def buckets(league, usage=None) -> dict:
    """pid -> playing-time bucket ("unknown", "t1", "t2", "t3": config.phase8). `usage` is pid -> the season's PA
    (batters) or BF (pitchers): under the floor "unknown", over it thirds of playing time within the role, as the
    source cuts them. Without usage (no season played) the role-rank GUESS of config.phase8.role_bucket."""
    if usage is None:
        return {p.pid: phase8.role_bucket(p.group, p.order) for p in league.players}
    out = {}
    for side in ("bat", "pit"):
        over = sorted((p.pid for p in league.players if p.side == side and usage.get(p.pid, 0) >= phase8.USAGE_FLOOR),
                      key=lambda pid: (usage[pid], pid))
        for k, pid in enumerate(over):
            out[pid] = ("t1", "t2", "t3")[min(3 * k // max(len(over), 1), 2)]
    return {p.pid: out.get(p.pid, "unknown") for p in league.players}


def stay_rate(p, bucket: str) -> float:
    return phase8.retention()["stay"]["batter" if p.side == "bat" else "pitcher"][p.year][bucket]


def plan_offseason(league, rng, usage=None) -> dict:
    """Who leaves, before anything moves: pid -> {"p": stay rate, "bucket", "stays", "reason" (leavers)}. One
    draw per player in pid order."""
    b = buckets(league, usage)
    plan = {}
    for p in league.players:
        pr = stay_rate(p, b[p.pid])
        stays = bool(rng.random() < pr)
        plan[p.pid] = {"p": pr, "bucket": b[p.pid], "stays": stays, "reason": None if stays else phase8.reason(p.year, b[p.pid])}
    return plan


def advance_year(cfg, league, rng, usage=None) -> dict:
    """One offseason, in place (module docstring): the plan, then its application with nobody persuaded."""
    s_plan, s_apply = rng.bit_generator.seed_seq.spawn(2)
    plan = plan_offseason(league, np.random.Generator(np.random.PCG64(s_plan)), usage)
    return apply_offseason(cfg, league, plan, np.random.Generator(np.random.PCG64(s_apply)))


def apply_offseason(cfg, league, plan: dict, rng, kept=()) -> dict:
    """Apply a plan in place: returns move up a class, leavers (less the pids in `kept`, persuaded to stay) are
    replaced by newcomers. `rng` gives the donor league's seed and the newcomers' draws. Returns the counts by
    class and each team's leavers (uid, name, class, group, pos, reason) and newcomers (uid, name, class, group, pos)."""
    from engine.league import build_league
    shares = phase8.roster()["shares"]
    kept = set(kept)
    if any(t.tb is None for t in league.teams):
        raise ValueError("this league was built before Phase 8 (no team offsets kept): start a new one")
    seeds = rng.bit_generator.seed_seq.spawn(2)
    donor = build_league(cfg, np.random.Generator(np.random.PCG64(seeds[0])))
    turn = np.random.Generator(np.random.PCG64(seeds[1]))
    scale = RatingScale()
    out = {"left": {c: 0 for c in CLASSES}, "arrived": {c: 0 for c in CLASSES}, "returned": 0, "teams": {}}
    going = {p.pid for p in league.players if p.year == CLASSES[-1] or not (plan[p.pid]["stays"] or p.pid in kept)}
    left_year = {}
    dev_on = phase8.on("development")
    s_dev = seeds[1].spawn(1)[0]                                         # development's own stream: the other draws stay put
    devr = np.random.Generator(np.random.PCG64(s_dev))
    cmean = {side: _class_mean(side) for side in ("bat", "pit")}
    ysd = {side: _dev_sd(scale, side, "year") for side in ("bat", "pit")}
    for p in league.players:
        if p.pid in going:
            left_year[p.pid] = p.year
        else:
            if dev_on:                                                   # a returner's season-to-season change
                noise = ysd[p.side] * devr.standard_normal(len(RATES))
                before = dict(p.ratings)
                _set_z(scale, p, np.asarray(p.z, float) + cmean[p.side][p.year] + (p.dev if getattr(p, "dev", None) is not None else 0.0) + noise)
                p.last_dev = {k: p.ratings[k] - before[k] for k in p.ratings if k not in _KEEP_RATINGS}
            p.year = CLASSES[CLASSES.index(p.year) + 1]
            out["returned"] += 1
    # the newcomers' class mix, by tier: in proportion to each class's shortfall against the rosters' shares once
    # the returners have moved up (all freshmen are new; the later classes' newcomers are transfers)
    mix = {}
    for tier in shares:
        ys = [p.year for p in league.players if league.teams[p.team].tier == tier]
        back = [p.year for p in league.players if league.teams[p.team].tier == tier and p.pid not in going]
        short = {c: max(shares[tier][c] * len(ys) - back.count(c), 0.0) for c in CLASSES}
        tot = sum(short.values())
        mix[tier] = {c: short[c] / tot for c in CLASSES} if tot > 0 else dict(shares[tier])
    newcomers = []
    for t, dt in zip(league.teams, donor.teams):
        roster = t.batters + t.weekend_sp + t.midweek_sp + t.relievers
        leavers = [p for p in sorted(roster, key=lambda p: p.pid) if p.pid in going]
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
            n = _newcomer(scale, d, dt, p, t, _pick(turn, mix[t.tier]), league.next_uid)
            league.next_uid += 1
            n.last_dev = None
            if dev_on and n.year != CLASSES[0]:                          # a transfer arrives with his earlier seasons' gains
                k = CLASSES.index(n.year)
                own = n.dev if getattr(n, "dev", None) is not None else 0.0
                n.z = np.asarray(n.z, float) + sum(cmean[n.side][c] + own for c in CLASSES[:k])
            newcomers.append(n)
            new[p.pid] = n
            league.players[p.pid] = n
            out["left"][left_year[p.pid]] += 1; out["arrived"][n.year] += 1
        t.batters = [new.get(p.pid, p) for p in t.batters]
        for name in ("weekend_sp", "midweek_sp", "relievers"):
            setattr(t, name, [new.get(p.pid, p) for p in getattr(t, name)])
        out["teams"][t.tid] = {"left": [(p.uid, p.name, p.year, p.group, p.pos, plan[p.pid]["reason"] or phase8.reason(p.year, plan[p.pid]["bucket"])) for p in leavers],
                               "arrived": [(n.uid, n.name, n.year, n.group, n.pos) for n in new.values()]}
    if dev_on:
        _steady(scale, league, donor, newcomers)
    for t in league.teams:
        if dev_on:
            _promote(cfg, t)
        _rank_team(cfg, t, turn)
    return out
