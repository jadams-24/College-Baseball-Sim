"""Bullpen deployment, mechanism sizes (2026-10-09, sizes only): does real relief usage react to results?
1. Workload against observed quality within staff (relief-only pitchers): the quality gap by workload tercile.
2. Feedback: the next relief entry's |margin| and blowout share on the previous outing's run value allowed, within pitcher.
Real: 2025 play-by-play, full-season staffs. Engine: the instrumented round-3 seasons (runs/round3/<key>).
    python3 scripts/diag_bullpen_feedback.py"""
sys.path.insert(0, "."); sys.path.insert(0, "scripts")
import numpy as np, pandas as pd
import diag_tto_mopup as m2, diag_round3 as r3

def feedback(pa, teams, order_col):
    """Relief-only pitchers' consecutive relief outings: next entry's |margin| (and late-close share) on the previous
    outing's run value allowed, both demeaned within pitcher. Slope per +1 run of rv; cluster-free SE."""
    d = pa[pa.pit_team_id.isin(teams)]
    sp = set(d[d.is_sp].pid)
    rl = d[~d.pid.isin(sp)]
    o = rl.groupby(["pit_team_id", "game_id", "outing"], sort=False).agg(pid=("pid", "first"), rv=("rv", "sum"), bf=("rv", "size"),
          margin=("margin", "first"), inning=("inning", "first"), order=(order_col, "first")).reset_index()
    o = o.sort_values(["pid", "order"])
    o["absm"] = o.margin.abs()
    o["close_late"] = ((o.inning >= 7) & (o.absm <= 3)).astype(float)
    o["blow"] = (o.absm >= 7).astype(float)
    g = o.groupby("pid")
    o["prev_rv"] = g.rv.shift(); o["prev_absm"] = g.absm.shift()
    o = o.dropna(subset=["prev_rv"])
    out = {"n_pairs": len(o)}
    for y in ("absm", "close_late", "blow"):
        yy = o[y] - o.groupby("pid")[y].transform("mean"); xx = o.prev_rv - o.groupby("pid").prev_rv.transform("mean")
        # control for persistence of game state: previous entry's |margin|
        zz = o.prev_absm - o.groupby("pid").prev_absm.transform("mean")
        X = np.column_stack([xx, zz]); b, *_ = np.linalg.lstsq(X, yy, rcond=None)
        res = yy - X @ b; s2 = res.var(); cov = s2 * np.linalg.inv(X.T @ X)
        out[y] = (float(b[0]), float(np.sqrt(cov[0, 0])))
    return out

pa = m2.plate_appearances()
def spread(pa, teams, min_bf=20):
    """Within-team true-quality SD among relief-only pitchers: var of (q - team mean) minus mean noise var (sig2/bf), BF>=min_bf.
    Also the same by workload tercile within team (low / mid / high relief BF): mean q gap to the team mean, noise-free."""
    d = pa[pa.pit_team_id.isin(teams)]
    sig2 = float(d.rv.var())
    sp = set(d[d.is_sp].pid)
    rl = d[~d.pid.isin(sp)]
    s = rl.groupby(["pit_team_id", "pid"]).agg(bf=("rv", "size"), rv=("rv", "sum"))
    s = s[s.bf >= min_bf].copy(); s["q"] = s.rv / s.bf
    s["dq"] = s.q - s.groupby(level=0).q.transform("mean")
    n_t = s.groupby(level=0).q.transform("size")
    true_var = float((s.dq ** 2).mean() - (sig2 / s.bf * (1 - 1 / n_t)).mean())
    s["wr"] = s.groupby(level=0).bf.rank(pct=True)
    terc = {lab: float(s[(s.wr > lo) & (s.wr <= hi)].dq.mean()) for lab, lo, hi in (("low", 0, 1/3), ("mid", 1/3, 2/3), ("high", 2/3, 1))}
    return {"true_sd": float(np.sqrt(max(true_var, 0))), "n": len(s), "bf_mean": float(s.bf.mean()), "dq_by_workload": terc,
            "n_relief_only_per_team": float(s.groupby(level=0).size().mean())}


def main() -> None:
    pa = m2.plate_appearances()
    meta = pd.read_csv("data/ncaa_2025/pbp/parsed/games_meta_2025.csv")
    pa = pa.merge(meta[["game_id", "local_date", "dbl_header_game_no"]], on="game_id", how="left")
    pa["order"] = pd.to_datetime(pa.local_date).astype("int64") // 10**9 + pa.dbl_header_game_no.fillna(0)
    t = pd.read_csv("data/ncaa_2025/pbp/teams_2025.csv"); tier = dict(zip(t.ncaa_team_id, t.tier))
    full = m2.full_season_teams()
    print("real all", feedback(pa, full, "order"), spread(pa, full))
    print("real p4", feedback(pa, {x for x in full if tier.get(x) == "p4"}, "order"))
    lw = r3.real_round2()["lw"]
    for f in sorted(glob.glob("runs/round3/57148fcc6c2ce905/season_*.pkl"))[:3]:
        r = pickle.load(open(f, "rb")); p, g = r3.frames(r, lw); p["order"] = p.gid
        print("sim all", feedback(p, set(r["teams"]), "order"), spread(p, set(r["teams"])))


if __name__ == "__main__":
    main()
