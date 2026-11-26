"""Phase 8, class years and turnover (engine/roster.py; plan: plans/phase8_plan_2026-11-26.md).

1. Class years are a label from their own stream: the league is identical with them on and off.
2. Offseasons keep the roster container whole (pids are the slots, every regular position filled, orders complete,
   unique people) and the class shares where the 2025 rosters have them.
3. Turnover does not move the talent distributions: each role group's mean and SD of every rate stay where the drawn
   league had them (the Phase 8 gate's fast form; the 40-season rows run in the reports).
"""
import numpy as np

from config import phase2, phase8
from engine import roster
from engine.league import build_league


def _league(cfg, seed):
    return build_league(cfg, np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed).spawn(3)[0])))


def test_class_years_move_no_other_draw():
    cfg = phase2.load()
    old = phase8.FEATURES["classes"]
    try:
        phase8.FEATURES["classes"] = False
        a = _league(cfg, 11)
        phase8.FEATURES["classes"] = True
        b = _league(cfg, 11)
    finally:
        phase8.FEATURES["classes"] = old
    assert all(p.year == "" for p in a.players) and all(p.year in phase8.CLASSES for p in b.players)
    for p, q in zip(a.players, b.players):
        assert np.array_equal(p.z, q.z) and (p.name, p.pos, p.bats, p.throws, p.order, p.bat_order, p.run, p.err, p.arm, p.hold, p.log_theta) == \
            (q.name, q.pos, q.bats, q.throws, q.order, q.bat_order, q.run, q.err, q.arm, q.hold, q.log_theta)
    assert all((t.o, t.d) == (u.o, u.d) for t, u in zip(a.teams, b.teams))


def test_turnover_keeps_the_container_the_classes_and_the_talent():
    cfg = phase2.load()
    lg = _league(cfg, 12)
    groups = ("regular", "bench", "sp_weekend", "sp_midweek", "rp")
    stat = lambda L, g: np.array([p.z for p in L.players if p.group == g])
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(13)))
    target = phase8.roster()["shares"]
    year0 = {g: stat(lg, g) for g in groups}        # the same teams before any turnover: the team offsets stay, the players change
    years = []
    for _ in range(5):
        info = roster.advance_year(cfg, lg, rng)
        years.append({g: stat(lg, g) for g in groups})
        assert sum(info["left"].values()) == sum(info["arrived"].values()) and info["left"]["5th"] > 0
        assert all(p.pid == i for i, p in enumerate(lg.players))
        assert len({p.uid for p in lg.players}) == len(lg.players)
        for t in lg.teams:
            assert sorted(p.pos for p in t.batters if p.group == "regular") == ["1b", "2b", "3b", "c", "cf", "dh", "lf", "rf", "ss"]
            assert sorted(p.order for p in t.batters) == list(range(len(t.batters))) == sorted(p.bat_order for p in t.batters)
            assert all(p.team == t.tid for p in t.batters + t.weekend_sp + t.midweek_sp + t.relievers)
        sh = roster.class_shares(lg)
        for tier in ("p4", "mid", "low"):
            n = sum(1 for p in lg.players if lg.teams[p.team].tier == tier)
            for c in phase8.CLASSES:           # 5 binomial SEs around the 2025 rosters' share
                assert abs(sh[tier][c] - target[tier][c]) < 5 * np.sqrt(target[tier][c] * (1 - target[tier][c]) / n) + .005, (tier, c, sh[tier][c], target[tier][c])
    for g in groups:                            # mean and SD of every rate: the turnover years against the drawn league
        f_mean, f_sd = year0[g].mean(0), year0[g].std(0)
        t_mean = np.mean([y[g].mean(0) for y in years], 0); t_sd = np.mean([y[g].std(0) for y in years], 0)
        n = len(stat(lg, g))
        assert np.all(np.abs(t_mean - f_mean) < 6 * (f_sd + 1e-9) / np.sqrt(n) + .01), (g, t_mean, f_mean)
        assert np.all(np.abs(t_sd - f_sd) < .06 * f_sd + .01), (g, t_sd, f_sd)
    # a returning player keeps his ratings (no development yet) and moves up one class
    before = {p.uid: (p.year, p.z.copy()) for p in lg.players}
    roster.advance_year(cfg, lg, rng)
    back = [p for p in lg.players if p.uid in before]
    assert back and all(phase8.CLASSES.index(p.year) == phase8.CLASSES.index(before[p.uid][0]) + 1 and np.array_equal(p.z, before[p.uid][1]) for p in back)


def test_who_leaves_follows_class_role_and_playing_time():
    """The plan's stay rates are the source's cells (data/wmt_player_seasons/retention_by_class.csv), the buckets
    are the source's cut (floor, then thirds within the role), the draws recover the rates, and a persuaded player
    stays while a fifth-year never does."""
    cfg = phase2.load()
    lg = _league(cfg, 21)
    ret = phase8.retention()
    assert ret["stay"]["batter"]["Fr"]["t3"] > ret["stay"]["batter"]["Fr"]["unknown"] + .3      # freshmen who play stay
    assert ret["stay"]["batter"]["Jr"]["t3"] < ret["stay"]["batter"]["Jr"]["t2"] - .1           # the most-used juniors leave
    assert all(ret["stay"][r]["5th"][b] == 0 for r in ret["stay"] for b in phase8.BUCKETS)
    urng = np.random.Generator(np.random.PCG64(5))
    usage = {p.pid: int(urng.integers(0, 260)) for p in lg.players}
    b = roster.buckets(lg, usage)
    for side in ("bat", "pit"):
        over = [p.pid for p in lg.players if p.side == side and usage[p.pid] >= phase8.USAGE_FLOOR]
        assert all(b[p.pid] == "unknown" for p in lg.players if p.side == side and usage[p.pid] < phase8.USAGE_FLOOR)
        n3 = [sum(1 for pid in over if b[pid] == t) for t in ("t1", "t2", "t3")]
        assert max(n3) - min(n3) <= 1
        assert max(usage[pid] for pid in over if b[pid] == "t1") <= min(usage[pid] for pid in over if b[pid] == "t3")
    cell = {}
    for s in range(6):                                                  # six plans of the same league: no one moves
        plan = roster.plan_offseason(lg, np.random.Generator(np.random.PCG64(100 + s)), usage)
        for p in lg.players:
            d = plan[p.pid]
            assert d["p"] == ret["stay"]["batter" if p.side == "bat" else "pitcher"][p.year][b[p.pid]] and (d["reason"] is None) == d["stays"]
            c = cell.setdefault((p.side, p.year, b[p.pid]), [0, 0, d["p"]])
            c[0] += d["stays"]; c[1] += 1
    for k, (st, n, pr) in cell.items():
        assert abs(st / n - pr) < 5 * np.sqrt(max(pr * (1 - pr), 1e-9) / n) + 1e-9, (k, st / n, pr)
    plan = roster.plan_offseason(lg, np.random.Generator(np.random.PCG64(1)), usage)
    again = roster.plan_offseason(lg, np.random.Generator(np.random.PCG64(1)), usage)
    assert plan == again
    leaving = [p for p in lg.players if not plan[p.pid]["stays"]]
    keep = {p.pid for p in leaving[:40]}
    uid = {p.pid: (p.uid, p.year) for p in lg.players}
    info = roster.apply_offseason(cfg, lg, plan, np.random.Generator(np.random.PCG64(np.random.SeedSequence(2))), kept=keep)
    for pid in keep:
        u, y = uid[pid]
        assert (lg.players[pid].uid == u) == (y != "5th")                # persuaded: back, unless the clock ran out
    gone = {pid for pid in uid if lg.players[pid].uid != uid[pid][0]}
    assert gone == {p.pid for p in leaving if p.pid not in keep or uid[p.pid][1] == "5th"}
    assert all(len(x) == 6 and x[5] for t in info["teams"].values() for x in t["left"])
