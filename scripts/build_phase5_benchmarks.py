"""Phase 5 inputs and benchmarks: pitch sequences from the 2025 WMT play-by-play.

What the data has (audit of every action in data/ncaa_2025/pbp/raw, 2,264 games): per plate
appearance a pitch sequence over B (ball), K (called strike), S (swinging strike), F (foul),
P (ball put in play) and H (hit by pitch), the final balls and strikes, the pitch count and a
strikeout-looking flag. No pitch type, velocity or location anywhere. So the pitch model can
know take/swing outcomes (ball, called strike, whiff, foul, in play, HBP) by count, nothing about
location or pitch mix.

Cleaning (per plate appearance):
  - a P before the last pitch changes neither balls nor strikes (e.g. PFBSBS is a strikeout,
    FFFBFBFBPS is not a walk) and is counted in the official pitch count: a pitch with no
    ball/strike call recorded. It is kept as a neutral pitch, N.
  - an HBP whose last symbol is P (11.7% of HBPs, feed coding) ends in H.
  - intentional walks are excluded (mostly automatic, no pitches) and so are catcher's interference
    and sequences that break the count rules (0.4%); plate appearances without a sequence (2.8%)
    are excluded.
Everything is reweighted by batting-tier x pitching-tier cell to the full-season D1 matchup mix
(as in scripts/build_pbp_benchmarks.py). Standard errors: bootstrap over games (game clusters),
reweighting inside each replicate.

Outputs: data/ncaa_2025/derived/phase5_pitch_2025.json
  chain        pitch events by count (B, K, S, F, P, H, N) and batted-ball results by count of contact
  benchmarks   pitches per PA (mean, distribution), count reach, BA/K%/BB% after each count, first-pitch
               strike rate, foul rate with two strikes, pitches and innings per start (weekend, midweek)
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.players import load_pa  # noqa: E402

OUT = Path("data/ncaa_2025/derived/phase5_pitch_2025.json")
TIERS = ("p4", "mid", "low")
CELLS = [(t, o) for t in TIERS for o in TIERS]
COUNTS = [(b, s) for b in range(4) for s in range(3)]
EVENTS = ("B", "K", "S", "F", "P", "H", "N")
BIP = ("HR", "1B", "2B", "3B", "ROE", "OUT")
HITS = ("1B", "2B", "3B", "HR")
NOT_AB = ("BB", "HBP", "SF", "SH")
WEEKEND = {4, 5, 6}
N_BOOT = 200
SEED = 5001


def bip_class(res: str) -> str:
    return res if res in ("HR", "1B", "2B", "3B", "ROE") else "OUT"


def clean_seq(seq: str, res: str) -> str | None:
    """Neutral mid-sequence P -> N; HBP ending in P -> H; None if the count rules are broken."""
    seq = "".join("N" if (c == "P" and i < len(seq) - 1) else c for i, c in enumerate(seq))
    if res == "HBP" and seq.endswith("P"):
        seq = seq[:-1] + "H"
    b = s = 0
    for i, c in enumerate(seq):
        last = i == len(seq) - 1
        if c in "PH" and not last:
            return None
        if c == "B":
            b += 1
            if b == 4 and not last:
                return None
        elif c in "KS":
            s += 1
            if s == 3 and not last:
                return None
        elif c == "F":
            s = min(s + 1, 2)
    end = seq[-1]
    if res == "BB":
        return seq if (b == 4 and end == "B") else None
    if res == "K":
        return seq if (s == 3 and end in "KS") else None
    if res == "HBP":
        return seq if end == "H" else None
    return seq if end == "P" else None


def walk(seq: str):
    """Yield (count before the pitch, symbol) for every pitch."""
    b = s = 0
    for c in seq:
        yield (b, s), c
        if c == "B":
            b += 1
        elif c in "KS":
            s += 1
        elif c == "F":
            s = min(s + 1, 2)

SPREAD_EVENTS = ("B", "K", "S", "F", "P")
MIN_HALF = 75            # plate appearances (batters faced) per half for the split-half estimate
MIN_SPREAD = 150         # plate appearances (batters faced) for the spread comparison
N_BOOT_PLAYERS = 200


def _lg(p):
    return np.log(p / (1 - p))


def player_directions(v: pd.DataFrame) -> tuple[dict, dict]:
    """Per side (pitcher, batter): d logit(per-pitch rate of each event) / d logit(K%) and / d logit(BB%),
    true-talent slopes. Each player's plate appearances are split alternately into halves A and B;
    the slopes are Cov(X_A, X_B)^-1 Cov(X_A, y_B) (symmetrised), X = logit K%, logit BB%, y = logit
    event rate: the cross-half covariance of X is the covariance of true talent, so binomial noise
    neither attenuates the slopes nor (being independent across halves) correlates with y. HBP is left
    to its own tilt (too rare to estimate a direction). Bootstrap over players for the SE.
    Also the raw spread of qualified players' per-pitch rates and their correlation with K% and BB%,
    for comparison with the simulation (informational)."""
    ev = ("B", "K", "S", "F", "P", "H")
    d = v[["pit_team_id", "pkey", "bat_team_id", "bkey", "seq", "is_k", "is_bb"]].copy()
    for e in ev:
        d["n" + e] = d.seq.str.count(e)
    d["nc"] = d[["n" + e for e in ev]].sum(axis=1)
    d["one"] = 1
    cols = ["one", "is_k", "is_bb", "nc"] + ["n" + e for e in SPREAD_EVENTS]
    rng = np.random.default_rng(SEED)
    out, spread = {}, {}
    for side, key in (("pitcher", ["pit_team_id", "pkey"]), ("batter", ["bat_team_id", "bkey"])):
        d["half"] = d.groupby(key).cumcount() % 2
        g = d.groupby(key + ["half"])[cols].sum().unstack("half")
        g = g[(g[("one", 0)] >= MIN_HALF) & (g[("one", 1)] >= MIN_HALF)]
        arr = {c: (g[(c, 0)].values.astype(float), g[(c, 1)].values.astype(float)) for c in cols}

        def est(idx):
            def X(h):
                return np.column_stack([_lg((arr["is_k"][h][idx] + .5) / (arr["one"][h][idx] + 1)), _lg((arr["is_bb"][h][idx] + .5) / (arr["one"][h][idx] + 1))])
            XA, XB = X(0), X(1)
            XA, XB = XA - XA.mean(0), XB - XB.mean(0)
            C = (XA.T @ XB + XB.T @ XA) / 2 / len(idx)
            res = {}
            for e in SPREAD_EVENTS:
                yA = _lg((arr["n" + e][0][idx] + .5) / (arr["nc"][0][idx] + 1)); yB = _lg((arr["n" + e][1][idx] + .5) / (arr["nc"][1][idx] + 1))
                yA, yB = yA - yA.mean(), yB - yB.mean()
                res[e] = np.linalg.solve(C, (XA.T @ yB + XB.T @ yA) / 2 / len(idx))
            return res
        n = len(g)
        pt = est(np.arange(n))
        bs = [est(rng.integers(0, n, n)) for _ in range(N_BOOT_PLAYERS)]
        out[side] = {"n_players": int(n), **{rate: {e: {"value": round(float(pt[e][j]), 4), "se": round(float(np.std([b[e][j] for b in bs], ddof=1)), 4)}
                                                    for e in SPREAD_EVENTS} for j, rate in enumerate(("K", "BB"))}}
        # raw spread of qualified players (whole season)
        tot = {c: arr[c][0] + arr[c][1] for c in cols}
        q = tot["one"] >= MIN_SPREAD
        k, bb = tot["is_k"][q] / tot["one"][q], tot["is_bb"][q] / tot["one"][q]
        sp = {"n": int(q.sum())}
        for e in SPREAD_EVENTS:
            r = tot["n" + e][q] / tot["nc"][q]
            sp[e] = {"mean": round(float(r.mean()), 4), "sd": round(float(r.std()), 4), "corr_k": round(float(np.corrcoef(r, k)[0, 1]), 3),
                     "corr_bb": round(float(np.corrcoef(r, bb)[0, 1]), 3)}
        spread[side] = sp
    return out, spread


def main() -> None:
    pa = load_pa()
    teams = pd.read_csv("data/ncaa_2025/pbp/teams_2025.csv")
    tier_of = dict(zip(teams.ncaa_team_id, teams.tier.fillna("")))
    sb = pd.read_csv("data/ncaa_2025/scoreboard/games_2025.csv")
    sb = sb[(sb.state == "final") & sb.home_score.notna() & sb.away_score.notna()].drop_duplicates("url")
    tier_of_name = dict(zip(teams.team, teams.tier))
    cnt = Counter()
    for side, opp in (("home", "away"), ("away", "home")):
        for t, o in zip(sb[side].map(tier_of_name), sb[opp].map(tier_of_name)):
            if isinstance(t, str) and isinstance(o, str) and t and o:
                cnt[(t, o)] += 1
    mix = {c: cnt[c] / sum(cnt.values()) for c in CELLS}
    gm = pd.read_csv("data/ncaa_2025/pbp/parsed/games_2025.csv")
    gm["wd"] = pd.to_datetime(gm.game_date).dt.dayofweek
    pa = pa.merge(gm[["game_id", "wd"]], on="game_id").sort_values(["game_id", "group_id"]).reset_index(drop=True)
    pa["cell"] = list(zip(pa.bat_team_id.map(tier_of).fillna(""), pa.pit_team_id.map(tier_of).fillna("")))
    n_all = len(pa)
    res = pa.result.replace({"FO": "OUT", "GO": "OUT", "GIDP": "OUT", "DP": "OUT", "FC": "OUT"})
    pa["res"] = res
    keep = pa.pitch_seq.notna() & ~pa.result.isin(["IBB", "CI"])
    pa["seq"] = [clean_seq(q, r) if k else None for q, r, k in zip(pa.pitch_seq, pa.res, keep)]
    stats_counts = {"pa_total": int(n_all), "no_sequence": int(pa.pitch_seq.isna().sum()),
                    "ibb_or_ci": int(pa.result.isin(["IBB", "CI"]).sum()),
                    "broken_sequence": int((keep & pa.seq.isna()).sum()),
                    "neutral_pitches": int(sum(q.count("N") for q in pa.seq.dropna())), "hbp_P_recoded": int(((pa.res == "HBP") & pa.pitch_seq.fillna("").str.endswith("P")).sum())}
    v = pa[pa.seq.notna() & pa.cell.isin(mix)].copy()
    stats_counts["pa_used"] = int(len(v))

    # ---- per-PA features
    first_strike, reach, pitches, two_k_pitches, two_k_fouls = [], [], [], [], []
    ev = {c: Counter() for c in COUNTS}           # chain events by count, per cell
    for q in v.seq:
        pitches.append(len(q))
        fs = next((c for c in q if c != "N"), "B")
        first_strike.append(fs in "KSFP")
        seen = set()
        tk = tf = 0
        for c0, sym in walk(q):
            seen.add(c0)
            if c0[1] == 2 and sym != "N":
                tk += 1; tf += sym == "F"
        reach.append(seen); two_k_pitches.append(tk); two_k_fouls.append(tf)
    v["pitches"] = pitches
    v["fps"] = np.array(first_strike, float)
    v["k2p"], v["k2f"] = two_k_pitches, two_k_fouls
    for c in COUNTS:
        v[f"r_{c[0]}{c[1]}"] = np.array([c in s_ for s_ in reach], float)
    v["is_ab"] = (~v.res.isin(NOT_AB)).astype(float)
    v["is_h"] = v.res.isin(HITS).astype(float)
    v["is_k"] = (v.res == "K").astype(float)
    v["is_bb"] = (v.res == "BB").astype(float)

    # starts: the first pitcher of each team in each game, official pitch counts and outs
    first = pa.groupby(["game_id", "pit_team_id"]).pkey.transform("first")
    sp = pa[pa.pkey == first]
    starts = sp.groupby(["game_id", "pit_team_id"]).agg(pitches=("pitches", "sum"), npna=("pitches", lambda x: x.isna().sum()),
                                                        outs=("outs_on_play", "sum"), wd=("wd", "first"), cell=("cell", "first")).reset_index()
    starts = starts[(starts.npna == 0) & starts.cell.isin(mix)]
    starts["cell"] = [(b, p) for b, p in starts.cell]          # batting tier x pitching tier of the opponent faced
    starts["weekend"] = starts.wd.isin(WEEKEND)

    # ---- chain tables (event counts by count before the pitch; contact results by count of contact)
    def chain_tables(df):
        evc = {cell: {c: Counter() for c in COUNTS} for cell in CELLS}
        bipc = {cell: {c: Counter() for c in COUNTS} for cell in CELLS}
        for q, r, cell in zip(df.seq, df.res, df.cell):
            for c0, sym in walk(q):
                evc[cell][c0][sym] += 1
            if q[-1] == "P":
                last_c = list(walk(q))[-1][0]
                bipc[cell][last_c][bip_class(r)] += 1
        out_ev, out_bip = {}, {}
        for c in COUNTS:
            pe = np.zeros(len(EVENTS)); pb = np.zeros(len(BIP))
            for cell, w in mix.items():
                tot = sum(evc[cell][c].values()); tb = sum(bipc[cell][c].values())
                if tot:
                    pe += w * np.array([evc[cell][c][e] for e in EVENTS]) / tot
                if tb:
                    pb += w * np.array([bipc[cell][c][x] for x in BIP]) / tb
            out_ev[f"{c[0]}-{c[1]}"] = (pe / pe.sum()).round(6).tolist()
            out_bip[f"{c[0]}-{c[1]}"] = (pb / pb.sum()).round(6).tolist()
        n_ev = {f"{c[0]}-{c[1]}": int(sum(sum(evc[cell][c].values()) for cell in CELLS)) for c in COUNTS}
        return out_ev, out_bip, n_ev

    ev_tab, bip_tab, n_ev = chain_tables(v)

    # ---- benchmark statistics as reweighted ratios of sums over cells
    pdist_keys = [str(k) for k in range(1, 10)] + ["10+"]

    def stats(df, st_df) -> dict:
        out = {}
        g = {cell: d for cell, d in df.groupby("cell")}

        def rw(num, den, sub=None):
            tot = 0.0
            for cell, w in mix.items():
                d = g.get(cell)
                if d is None:
                    return float("nan")
                d = d if sub is None else d[d[sub] > 0]
                dn = d[den].sum() if den else len(d)
                tot += w * (d[num].sum() / dn if dn else 0.0)
            return tot
        out["pitches_per_pa"] = rw("pitches", None)
        pc = {}
        for cell, d in g.items():
            p_ = d.pitches.clip(upper=10).value_counts(normalize=True)
            pc[cell] = p_
        for k in range(1, 11):
            out[f"pitches_dist_{pdist_keys[k - 1]}"] = sum(w * pc[cell].get(k, 0.0) for cell, w in mix.items())
        out["first_pitch_strike"] = rw("fps", None)
        out["two_strike_foul_rate"] = rw("k2f", "k2p")
        for c in COUNTS:
            r = f"r_{c[0]}{c[1]}"
            if c != (0, 0):
                out[f"reach_{c[0]}-{c[1]}"] = rw(r, None)
            out[f"ba_after_{c[0]}-{c[1]}"] = rw("is_h", "is_ab", sub=r)     # hits / AB in the PAs that reach the count
            out[f"k_after_{c[0]}-{c[1]}"] = rw("is_k", None, sub=r)
            out[f"bb_after_{c[0]}-{c[1]}"] = rw("is_bb", None, sub=r)
        sg = {(cell, wk): d for (cell, wk), d in st_df.groupby(["cell", "weekend"])}
        for wk, lab in ((True, "weekend"), (False, "midweek")):
            for key, col, f in (("pitches_per_start", "pitches", 1.0), ("ip_per_start", "outs", 1 / 3)):
                tot = wsum = 0.0
                for cell, w in mix.items():
                    d = sg.get((cell, wk))
                    if d is not None and len(d):
                        tot += w * d[col].mean() * f; wsum += w
                out[f"{key}_{lab}"] = tot / wsum
            allp = []
            for cell, w in mix.items():
                d = sg.get((cell, wk))
                if d is not None and len(d):
                    allp.append((d.pitches.values, w / len(d)))
            vals = np.concatenate([a for a, _ in allp]); wts = np.concatenate([np.full(len(a), ww) for a, ww in allp])
            o = np.argsort(vals); cw = np.cumsum(wts[o]) / wts.sum()
            for qn in (0.1, 0.5, 0.9):
                out[f"pitches_per_start_{lab}_p{int(qn * 100)}"] = float(vals[o][np.searchsorted(cw, qn)])
        return out

    # player directions: how a player's per-pitch event rates move with his K and BB rates
    directions, spread = player_directions(v)
    point = stats(v, starts)
    # bootstrap over games
    rng = np.random.default_rng(SEED)
    games = v.game_id.unique()
    vg = {gid: d for gid, d in v.groupby("game_id")}
    sgames = {gid: d for gid, d in starts.groupby("game_id")}
    boots = []
    for _ in range(N_BOOT):
        pick = rng.choice(games, len(games), replace=True)
        bv = pd.concat([vg[gid] for gid in pick], ignore_index=True)
        bs = pd.concat([sgames[gid] for gid in pick if gid in sgames], ignore_index=True)
        boots.append(stats(bv, bs))
    se = {k: float(np.nanstd([b[k] for b in boots], ddof=1)) for k in point}
    bench = {k: {"value": round(float(point[k]), 5), "se": round(se[k], 5)} for k in point}
    res_out = {"_note": __doc__, "built": dt.date.today().isoformat(), "src": "WMT stats API play-by-play 2025, data/ncaa_2025/pbp (fetched 2026-10-01)",
               "cleaning": stats_counts, "matchup_mix_weights": {f"{t}_vs_{o}": round(w, 4) for (t, o), w in mix.items()},
               "n_bootstrap": N_BOOT, "n_games": int(len(games)), "n_starts": {"weekend": int(starts.weekend.sum()), "midweek": int((~starts.weekend).sum())},
               "chain": {"events": list(EVENTS), "by_count": ev_tab, "n_pitches_by_count": n_ev, "bip_results": list(BIP), "bip_by_count": bip_tab,
                         "directions": directions},
               "player_spread": spread, "benchmarks": bench}
    OUT.write_text(json.dumps(res_out, indent=1) + "\n")
    print(json.dumps(stats_counts), json.dumps({k: bench[k] for k in list(bench)[:8]}, indent=0))


if __name__ == "__main__":
    main()
