"""Phase 0 derivation script.

Reproduces every computed value in benchmarks.json from the raw conference table
(data/phase0/conf2025.csv, FanGraphs/Baseball-Reference 2025) and checks that the league-average
PA outcome table reconciles with the published slash line. Run: python3 derive.py
"""
import json, pandas as pd

d = pd.read_csv("data/phase0/conf2025.csv")
cols = ["ba","obp","slg","bb_pct","k_pct","r_g","hr_g","sb_g","sh_g"]
print("== D1 2025, unweighted mean of 30 conference groups ==")
print(d[cols].mean().round(3).to_string())
for t in ["p4","mid","low"]:
    print(f"\n== tier {t} ==")
    print(d[d.tier==t][cols].mean().round(3).to_string())

b = json.load(open("benchmarks.json"))
t = b["pa_outcome_table_league_avg"]
outs = {k:v for k,v in t.items() if not k.startswith("_")}
assert abs(sum(outs.values())-1) < 1e-3, "outcome table must sum to 1"
AB = 1 - t["BB"] - t["HBP"] - t["SF"] - t["SH"]
H  = t["1B"]+t["2B"]+t["3B"]+t["HR"]
TB = t["1B"]+2*t["2B"]+3*t["3B"]+4*t["HR"]
ba, obp, slg = H/AB, (H+t["BB"]+t["HBP"])/(AB+t["BB"]+t["HBP"]+t["SF"]), TB/AB
pa_g = b["league_totals_2025"]["pa_per_team_game"]["value"]
print(f"\n== outcome table reconciliation ==")
print(f"BA {ba:.3f}  OBP {obp:.3f}  SLG {slg:.3f}  HR/G {t['HR']*pa_g:.2f}  BABIP {(H-t['HR'])/(AB-t['K']-t['HR']):.3f}")
lt = b["league_totals_2025"]
for k,v in [("ba",ba),("obp",obp),("slg",slg),("hr_per_team_game",t["HR"]*pa_g)]:
    ok = abs(v-lt[k]["value"]) <= lt[k]["tol"]
    print(f"  {k:18s} target {lt[k]['value']:.3f} ±{lt[k]['tol']}  got {v:.3f}  {'OK' if ok else 'FAIL'}")
