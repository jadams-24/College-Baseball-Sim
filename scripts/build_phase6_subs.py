"""Phase 6 substitution inputs from the 2025 play-by-play: pinch hitters, pinch runners and
defensive (including blowout) substitutions.

Every non-pitcher who enters a game (players with a plate appearance before the entry are starters
changing position, not new players) is classified by how he first entered (subs_2025, from
scripts/build_phase6_events.py): 'ph' pinch hitter, 'pr' pinch runner, anything else (a fielding
position or dh) a defensive substitution. Hazards, by inning bin x margin bin (margin from the
substituting team's side, at the substitution):
  ph   per plate appearance of the team                 (opportunities: the team's PAs in the cell)
  pr   per batter reaching base (not on a home run)      (opportunities: such batters in the cell)
  def  per defensive half-inning of the team             (opportunities: half-innings in the field)
Cells with fewer than MIN_SUB_CELL opportunities back off to the inning bin alone.
Also: the lineup spot a pinch hitter or defensive substitute replaces (share of entries over
share of opportunities, by spot), a tier multiplier on all three hazards (substitutions per
team-game by tier over the pooled rate, from the same cells), and who comes in: the substitute's
rank on his team by games started (full-season teams), as entries per team-game in which that
rank did not start. The engine picks among the players not in the game in proportion to it.
Ranks are pooled from the top until a cell has MIN_SUB_CELL opportunities; the engine's last
roster rank (N_REGULARS + N_BENCH) pools every deeper rank. With it, by rank: the start share and
start persistence, P(start | started the team's previous game) and P(start | sat it); and how
closely playing time follows hitting among regulars (start share vs OBP and OPS within team,
disattenuated): about .46, so playing time also rewards defense, position and the rest.
Gate value: distinct batters per team-game (batters with a plate appearance).
Writes the "subs6" block of data/ncaa_2025/derived/phase6_inputs_2025.json.

    python3 scripts/build_phase6_subs.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config.phase2 import N_BENCH, N_REGULARS  # noqa: E402
from config.phase6 import FULL_SEASON_GAMES, INNING_BINS, INPUTS6, MARGIN_BINS, MIN_SUB_CELL  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
from lib.players import _toks, name_map  # noqa: E402

P = ROOT / "data/ncaa_2025/pbp/parsed"


def ibin(inning) -> np.ndarray:
    return np.searchsorted(np.array(INNING_BINS), np.asarray(inning), side="right") - 1


def mbin(margin) -> np.ndarray:
    return np.searchsorted(np.array(MARGIN_BINS), np.asarray(margin), side="right") - 1


def bench_pick_weight(pa: pd.DataFrame, s: pd.DataFrame) -> dict:
    """Substitute entries per team-game in which the player's start rank did not start, by rank."""
    s = s.copy()
    gk = pa.drop_duplicates(["game_id", "batter_id"]).set_index(["game_id", "batter_id"]).bkey
    s["bkey"] = gk.reindex(list(zip(s.game_id, s.game_player_id))).values
    keys = pa.groupby("bat_team_id").bkey.unique().to_dict()

    def match(team, name):            # substitutes without a plate appearance: by name tokens
        k = set(_toks(name))
        c = [x for x in keys.get(team, []) if k <= set(x.split())]
        return c[0] if len(c) == 1 else None
    miss = s.bkey.isna()
    s.loc[miss, "bkey"] = [match(t, n) for t, n in zip(s[miss].team_id, s[miss].name)]
    sub_ids = set(zip(s.game_id, s.game_player_id))
    b = pa.drop_duplicates(["game_id", "bat_team_id", "batter_id"])
    b = b[[(g, i) not in sub_ids for g, i in zip(b.game_id, b.batter_id)]]          # starters
    ng = b.groupby("bat_team_id").game_id.nunique()
    full = ng[ng >= FULL_SEASON_GAMES].index
    n_rank = N_REGULARS + N_BENCH
    ev, opp, starts = np.zeros(n_rank), np.zeros(n_rank), np.zeros(n_rank)
    n_used = []
    for t in full:
        bt = b[b.bat_team_id == t]
        order = bt.groupby("bkey").size().sort_values(ascending=False).index
        rank = {k: min(i, n_rank - 1) for i, k in enumerate(order)}
        started = bt.groupby("bkey").game_id.nunique()
        n_used.append(pa[pa.bat_team_id == t].bkey.nunique())
        for k, r in rank.items():
            opp[r] += ng[t] - started[k]
            starts[r] += started[k]
        st = s[(s.team_id == t) & s.bkey.notna()]
        for k in st.bkey:
            if k in rank:
                ev[rank[k]] += 1
    # pool from the top until a cell has MIN_SUB_CELL opportunities
    w, i = {}, 0
    while i < n_rank:
        j = i
        while opp[i:j + 1].sum() < MIN_SUB_CELL and j < n_rank - 1:
            j += 1
        rate = ev[i:j + 1].sum() / opp[i:j + 1].sum()
        for r in range(i, j + 1):
            w[str(r + 1)] = round(float(rate), 4)
        i = j + 1
    tg_total = float(ng[full].sum())
    # playing time vs hitting among regulars (start ranks 1-9): within-team correlation of start share with
    # OBP and with OPS, each disattenuated by the stat's reliability (within-team variance less sampling noise)
    pq = pa.assign(ob=pa.result.isin(["1B", "2B", "3B", "HR", "BB", "IBB", "HBP"]), den=~pa.result.isin(["SH", "CI"]),
                   tb=pa.result.map({"1B": 1, "2B": 2, "3B": 3, "HR": 4}).fillna(0), ab=~pa.result.isin(["BB", "IBB", "HBP", "SH", "SF", "CI"]))
    pq = pq.groupby(["bat_team_id", "bkey"]).agg(ob=("ob", "sum"), den=("den", "sum"), tb=("tb", "sum"), ab=("ab", "sum"))
    reg = []
    for t in full:
        bt = b[b.bat_team_id == t].groupby("bkey").size().sort_values(ascending=False).head(N_REGULARS)
        reg += [(t, n / ng[t], *pq.loc[(t, k)]) for k, n in bt.items() if (t, k) in pq.index]
    rg = pd.DataFrame(reg, columns=["t", "share", "ob", "den", "tb", "ab"])
    rg["obp"], rg["slg"] = rg.ob / rg.den, rg.tb / rg.ab
    rg["ops"] = rg.obp + rg.slg
    noise = {"obp": (rg.obp * (1 - rg.obp) / rg.den).mean(), "ops": (rg.obp * (1 - rg.obp) / rg.den + (1.6 * rg.slg - rg.slg ** 2) / rg.ab).mean()}
    s_ = rg.share - rg.groupby("t").share.transform("mean")
    rho = {}
    for c in ("obp", "ops"):
        x = rg[c] - rg.groupby("t")[c].transform("mean")
        v = float(x.var() * len(x) / (len(x) - len(full)))
        rho[c] = round(float(np.corrcoef(x, s_)[0, 1] / np.sqrt(max(v - noise[c], 1e-12) / v)), 3)
    # start persistence: P(start | started the team's previous game) and P(start | did not), by rank
    meta = pd.read_csv(P / "games_meta_2025.csv")
    meta["d"] = pd.to_datetime(meta.local_date)
    pos = {g: i for i, g in enumerate(meta.sort_values(["d", "dbl_header_game_no"]).game_id)}
    trans = np.zeros((n_rank, 2, 2))            # [rank, previous start, today start]
    for t in full:
        bt = b[b.bat_team_id == t]
        games = sorted(bt.game_id.unique(), key=pos.get)
        order = bt.groupby("bkey").size().sort_values(ascending=False).index
        for i, k in enumerate(order):
            started = set(bt[bt.bkey == k].game_id)
            x = np.array([g in started for g in games], dtype=int)
            np.add.at(trans[min(i, n_rank - 1)], (x[:-1], x[1:]), 1)
    return {"weight": w, "entries": ev.astype(int).tolist(), "opportunities": opp.astype(int).tolist(),
            "matched_share": round(float(s.bkey.notna().mean()), 4),
            # start share by rank on the same ranks (the last pools every deeper rank), and the roster depth
            "start_share_by_rank": {str(r + 1): round(float(starts[r] / tg_total), 4) for r in range(n_rank)},
            "start_after_start": {str(r + 1): round(float(trans[r, 1, 1] / max(trans[r, 1].sum(), 1)), 4) for r in range(n_rank)},
            "start_after_sit": {str(r + 1): round(float(trans[r, 0, 1] / max(trans[r, 0].sum(), 1)), 4) for r in range(n_rank)},
            "position_players_with_pa": {"mean": round(float(np.mean(n_used)), 2), "median": float(np.median(n_used))},
            # the engine orders start ranks by rho x hitting value + noise (an upper bound: hot streaks earn
            # starts, which the disattenuation reads as talent)
            "playing_time_rho": {**rho, "value": round(float(np.mean(list(rho.values()))), 3), "n_regulars": int(len(rg))}}


def main() -> None:
    meta = pd.read_csv(P / "games_meta_2025.csv")
    teams = pd.read_csv(ROOT / "data/ncaa_2025/pbp/teams_2025.csv")
    tier = dict(zip(teams.ncaa_team_id, teams.tier))
    pa = pd.read_csv(P / "pa_events_2025.csv.gz", low_memory=False)
    pa = pa[pa.game_id.isin(meta.game_id)].copy()
    bm = name_map(pa, "bat_team_id", "batter")
    pa["bkey"] = [bm[(t, n)] for t, n in zip(pa.bat_team_id, pa.batter)]
    home = dict(zip(meta.game_id, meta.home_team_id))
    # the batting team's margin before the plate appearance
    bat_home = pa.bat_team_id.values == pa.game_id.map(home).values
    pa["margin"] = np.where(bat_home, pa.home_score - pa.away_score, pa.away_score - pa.home_score)
    pa["ib"], pa["mb"] = ibin(pa.inning), mbin(pa.margin)
    pa["slot"] = pa.groupby(["game_id", "bat_team_id"]).cumcount() % 9 + 1
    pa["reach"] = pa.batter_to.isin([1, 2, 3]) | pa.batter_to.isin(["1", "2", "3"])
    # defensive half-innings: first PA of each half-inning, from the fielding team's side
    hi = pa.drop_duplicates(["game_id", "inning", "half"]).copy()
    hi["margin_f"] = -hi.margin
    hi["ib"], hi["mb"] = ibin(hi.inning), mbin(hi.margin_f)

    s = pd.read_csv(P / "subs_2025.csv.gz")
    s = s[(s.kind == "in") & (s.position != "p") & s.game_id.isin(meta.game_id)].copy()
    s = s.drop_duplicates(["game_id", "team_id", "game_player_id"])      # first entry of each player
    # a starter who moves position (DH to first base, say) is logged as entering at the new position:
    # not a new player. Players with a plate appearance before the substitution are dropped.
    first_pa = pa.groupby(["game_id", "batter_id"]).group_id.min()
    fp = first_pa.reindex(list(zip(s.game_id, s.game_player_id))).values
    s = s[~(pd.notna(fp) & (fp < s.play_by_play_id.values))]
    s["home"] = s.team_id.values == s.game_id.map(home).values
    s["margin"] = np.where(s.home, s.home_score - s.visitor_score, s.visitor_score - s.home_score)
    s["kind6"] = np.where(s.position == "ph", "ph", np.where(s.position == "pr", "pr", "def"))
    s["ib"], s["mb"] = ibin(s.inning), mbin(s.margin)
    opp = {"ph": pa.groupby(["ib", "mb"]).size(), "pr": pa[pa.reach].groupby(["ib", "mb"]).size(),
           "def": hi.groupby(["ib", "mb"]).size()}
    opp_i = {k: v.groupby(level=0).sum() for k, v in opp.items()}
    out = {"_note": __doc__, "built": dt.date.today().isoformat(), "inning_bins": list(INNING_BINS), "margin_bins": list(MARGIN_BINS),
           "n_games": int(meta.shape[0]), "hazard": {}}
    for k in ("ph", "pr", "def"):
        ev = s[s.kind6 == k].groupby(["ib", "mb"]).size()
        ev_i = ev.groupby(level=0).sum()
        tab = {}
        for (i, m), n in opp[k].items():
            if n >= MIN_SUB_CELL:
                tab[f"{i}|{m}"] = round(float(ev.get((i, m), 0)) / n, 5)
            else:
                tab[f"{i}|{m}"] = round(float(ev_i.get(i, 0)) / opp_i[k][i], 5)
        out["hazard"][k] = tab
    # lineup spot of a pinch hitter / defensive substitute: entry share over opportunity share
    pa_slot = pa.slot.value_counts(normalize=True)
    for k in ("ph", "def"):
        sp = s[(s.kind6 == k) & s.lineup_spot.between(1, 9)].lineup_spot.value_counts(normalize=True)
        rel = (sp / (pa_slot if k == "ph" else 1 / 9)).reindex(range(1, 10)).fillna(0)
        out[f"{k}_slot_factor"] = {str(int(i)): round(float(v / rel.mean()), 4) for i, v in rel.items()}
    # tier multiplier: substitutions per team-game by tier over the pooled rate
    tg = pd.concat([meta.home_team_id, meta.away_team_id]).map(tier).value_counts()
    per = s.team_id.map(tier).value_counts() / tg
    pooled = len(s) / tg.sum()
    out["tier_multiplier"] = {t: round(float(per.get(t, pooled) / pooled), 4) for t in ("p4", "mid", "low")}
    out["subs_per_team_game"] = round(float(pooled), 4)
    # positions of defensive substitutes (fielding positions only): the bench's positions in the engine
    dp = s[(s.kind6 == "def") & s.position.isin(["c", "1b", "2b", "3b", "ss", "lf", "cf", "rf"])].position.value_counts(normalize=True)
    out["def_position_shares"] = {k: round(float(v), 4) for k, v in dp.items()}
    out["bench_pick_weight"] = bench_pick_weight(pa, s)
    out["subs_per_team_game_by_kind"] = {k: round(float((s.kind6 == k).sum() / tg.sum()), 4) for k in ("ph", "pr", "def")}
    # gate value: distinct batters with a plate appearance per team-game, with a bootstrap SE over games
    nb = pa.groupby(["game_id", "bat_team_id"]).batter_id.nunique()
    g = nb.groupby(level=0).mean()
    rng = np.random.default_rng(6)
    bs = [g.values[rng.integers(0, len(g), len(g))].mean() for _ in range(400)]
    out["batters_per_team_game"] = {"value": round(float(nb.mean()), 4), "se": round(float(np.std(bs, ddof=1)), 4)}
    cur = json.loads(INPUTS6.read_text()) if INPUTS6.exists() else {}
    cur["subs6"] = out
    INPUTS6.write_text(json.dumps(cur, indent=1, default=float) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("_note", "hazard")}, indent=1))
    print({k: dict(list(v.items())[:12]) for k, v in out["hazard"].items()})


if __name__ == "__main__":
    main()
