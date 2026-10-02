"""Audit (informational, not a gate): national leaders per simulated season vs the real 2023-2026 leaders.

Per season of the report run (20 seasons from seed 20251000, as scripts/run_phase5.py): the HR
leader and the count of 20+/25+/30+ HR hitters, the qualified BA leader, the qualified ERA
leader, the strikeout leader, and the most innings by a pitcher with 3 or fewer starts.
Qualification is the NCAA's: BA 2.0 PA per team game and 75% of team games; ERA 1 IP per team
game. Real side: data/ncaa_leaders/ncaa_leaders.json (scripts/parse_ncaa_leaders.py).

    python3 scripts/audit_leaders.py           # writes reports/leaders_audit.md and .json
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import phase2  # noqa: E402
from engine.game2 import B_AB, B_G, B_H, B_HR, B_PA, P_ER, P_G, P_GS, P_K, P_OUTS  # noqa: E402
from engine.season import simulate_season  # noqa: E402

REAL = ROOT / "data/ncaa_leaders/ncaa_leaders.json"
OUT_MD, OUT_JSON = ROOT / "reports/leaders_audit.md", ROOT / "reports/leaders_audit.json"
RELIEF_MAX_GS = 3
APP_LIST = 50                 # NCAA.com's appearance leaders page: the top 50 by appearances
APP_IP = 60                   # innings mark counted among the appearance leaders


def one(seed: int) -> dict:
    res = simulate_season(phase2.load(), seed)
    lg, b, p = res["league"], res["bstats"], res["pstats"]
    tg = {t.tid: 0 for t in lg.teams}
    for r in res["team_game_rows"]:
        tg[int(r[0])] += 1
    team = {t.tid: t for t in lg.teams}
    bats = [x for x in lg.players if x.side == "bat"]
    pits = [x for x in lg.players if x.side == "pit"]
    ip = lambda x: p[x.pid][P_OUTS] / 3                                              # noqa: E731
    era = lambda x: 9 * p[x.pid][P_ER] / ip(x)                                       # noqa: E731
    ba = lambda x: b[x.pid][B_H] / b[x.pid][B_AB]                                    # noqa: E731
    rat = lambda x: {k: round(float(v), 1) for k, v in x.ratings.items() if v is not None}  # noqa: E731
    hr = np.array([b[x.pid][B_HR] for x in bats])
    qb = [x for x in bats if b[x.pid][B_PA] >= 2.0 * tg[x.team] and b[x.pid][B_G] >= 0.75 * tg[x.team] and b[x.pid][B_AB] > 0]
    qp = sorted([x for x in pits if p[x.pid][P_OUTS] >= 3 * tg[x.team]], key=era)
    hl, bl, kl = max(bats, key=lambda x: b[x.pid][B_HR]), max(qb, key=ba), max(pits, key=lambda x: p[x.pid][P_K])
    rel = [x for x in pits if p[x.pid][P_GS] <= RELIEF_MAX_GS]
    rl = max(rel, key=ip)
    return {"seed": seed, "team_games_max": max(tg.values()),
            "hr_top5": sorted(hr.tolist(), reverse=True)[:5],
            "n_hr_30": int((hr >= 30).sum()), "n_hr_25": int((hr >= 25).sum()), "n_hr_20": int((hr >= 20).sum()),
            "hr_leader": {"hr": int(b[hl.pid][B_HR]), "pa": int(b[hl.pid][B_PA]), "tier": team[hl.team].tier, "ratings": rat(hl)},
            "ba_top5": sorted((ba(x) for x in qb), reverse=True)[:5],
            "ba_leader": {"ba": ba(bl), "ab": int(b[bl.pid][B_AB]), "tier": team[bl.team].tier, "ratings": rat(bl)},
            "era_low5": [era(x) for x in qp[:5]],
            "era_low5_gs": [int(p[x.pid][P_GS]) for x in qp[:5]],
            "era_leader": {"era": era(qp[0]), "ip": ip(qp[0]), "gs": int(p[qp[0].pid][P_GS]), "tier": team[qp[0].team].tier, "ratings": rat(qp[0])},
            "k_top5": sorted((int(p[x.pid][P_K]) for x in pits), reverse=True)[:5],
            "k_leader": {"k": int(p[kl.pid][P_K]), "ip": ip(kl), "gs": int(p[kl.pid][P_GS]), "tier": team[kl.team].tier, "ratings": rat(kl)},
            "relief_ip_max": {"ip": ip(rl), "g": int(p[rl.pid][P_G]), "gs": int(p[rl.pid][P_GS]), "tier": team[rl.team].tier, "ratings": rat(rl)},
            "n_relief_60ip": sum(ip(x) >= 60 for x in rel), "n_relief_70ip": sum(ip(x) >= 70 for x in rel),
            "app_max": max(int(p[x.pid][P_G]) for x in pits),
            "app_top50": sorted(((int(p[x.pid][P_G]), ip(x)) for x in pits), reverse=True)[:APP_LIST],
            "ip_leader": {"ip": max(ip(x) for x in pits), "gs": int(p[max(pits, key=ip).pid][P_GS])}}


def summary(v) -> str:
    a = np.asarray(v, float)
    f = (lambda x: f"{x:.3f}".lstrip("0")) if a.max() < 1 else (lambda x: f"{x:.2f}") if a.max() < 10 else (lambda x: f"{x:.1f}")
    return f"{f(a.mean())} ({f(a.min())}–{f(a.max())})"


def report(sims: list[dict], real: dict) -> str:
    rs = real["seasons"]
    r = {y: rs[y] for y in ("2024", "2025", "2026")}
    lead = lambda y, k, col: r[y][k]["rows"][0]                                       # noqa: E731
    fmt3 = lambda x: f"{x:.3f}".lstrip("0")                                           # noqa: E731
    col = lambda f: " | ".join(f(y) for y in r)                                       # noqa: E731
    S = lambda key: [s[key] for s in sims]                                            # noqa: E731
    rows = [
        ("HR leader", summary([s["hr_leader"]["hr"] for s in sims]), f"{rs['2023']['hr'][0]['HR']}",
         col(lambda y: f"{int(r[y]['hr_top5'][0])} ({lead(y, 'hr', 'HR')['G']} G)")),
        ("HR #5", summary([s["hr_top5"][4] for s in sims]), "—", col(lambda y: f"{int(r[y]['hr_top5'][4])}")),
        ("Hitters with 30+ HR", summary(S("n_hr_30")), "≥2", col(lambda y: f"{r[y]['n_hr_30']}")),
        ("Hitters with 25+ HR", summary(S("n_hr_25")), "—", col(lambda y: f"{r[y]['n_hr_25']}")),
        ("BA leader (qualified)", summary([s["ba_leader"]["ba"] for s in sims]), fmt3(rs["2023"]["ba"][0]["BA"]),
         col(lambda y: fmt3(r[y]["ba_top5"][0]))),
        ("BA #5", summary([s["ba_top5"][4] for s in sims]), "—", col(lambda y: fmt3(r[y]["ba_top5"][4]))),
        ("ERA leader (qualified)", summary([s["era_leader"]["era"] for s in sims]), "—",
         col(lambda y: f"{r[y]['era_low5'][0]:.2f} ({lead(y, 'era', 'ERA')['IP']} IP)")),
        ("ERA #2", summary([s["era_low5"][1] for s in sims]), "—", col(lambda y: f"{r[y]['era_low5'][1]:.2f}")),
        ("ERA #5", summary([s["era_low5"][4] for s in sims]), "—", col(lambda y: f"{r[y]['era_low5'][4]:.2f}")),
        ("K leader", summary([s["k_leader"]["k"] for s in sims]), f"{rs['2023']['k'][0]['SO']}",
         col(lambda y: f"{int(r[y]['k_top5'][0])} ({lead(y, 'k', 'SO')['IP']} IP)")),
        ("K #5", summary([s["k_top5"][4] for s in sims]), "—", col(lambda y: f"{int(r[y]['k_top5'][4])}")),
        (f"Max IP, ≤{RELIEF_MAX_GS} GS", summary([s["relief_ip_max"]["ip"] for s in sims]), "—", col(lambda y: "n/a (no GS column)")),
        ("Most appearances", summary(S("app_max")), "—", col(lambda y: f"{int(r[y]['app_max'])}")),
        (f"Top {APP_LIST} by appearances: fewest appearances", summary([s["app_top50"][-1][0] for s in sims]), "—",
         col(lambda y: f"{min(int(x['App']) for x in r[y]['app']['rows'])}")),
        (f"Top {APP_LIST} by appearances: max IP", summary([max(i for _, i in s["app_top50"]) for s in sims]), "—",
         col(lambda y: max(r[y]["app"]["rows"], key=lambda x: _ip(x["IP"]))["IP"])),
        (f"Top {APP_LIST} by appearances: {APP_IP}+ IP", summary([sum(i >= APP_IP for _, i in s["app_top50"]) for s in sims]), "—",
         col(lambda y: f"{sum(_ip(x['IP']) >= APP_IP for x in r[y]['app']['rows'])}")),
    ]
    L = ["# National leaders audit (informational)", "",
         f"{len(sims)} simulated seasons (seeds {sims[0]['seed']}–{sims[-1]['seed']}, the report run), {sims[0]['team_games_max']} games per team, "
         "no postseason. Sim: mean (range) across seasons. Real: NCAA.com national leaders (2024–2026 seasons; "
         "data/ncaa_leaders/), 2023 from the NCAA record book. Real leaders' teams played 57–72 games, postseason included. "
         "Qualification is the NCAA's: BA 2.0 PA per team game and 75% of team games; ERA 1 IP per team game. No model change; not gated.", "",
         "| Stat | Sim, 20 seasons | 2023 | 2024 | 2025 | 2026 |", "|---|---|---|---|---|---|"]
    L += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    hl = [s["hr_leader"] for s in sims]
    kl = [s["k_leader"] for s in sims]
    el = [s["era_leader"] for s in sims]
    L += ["", "## Leader detail (sim)", "",
          f"- HR leader: PA {summary([x['pa'] for x in hl])}, Power {summary([x['ratings']['power'] for x in hl])}; "
          f"tiers {sum(x['tier'] == 'p4' for x in hl)} P4 / {sum(x['tier'] == 'mid' for x in hl)} mid / {sum(x['tier'] == 'low' for x in hl)} low. "
          f"Hitters with 20+ HR {summary(S('n_hr_20'))} (real top-50 lists end at {', '.join(str(int(r[y]['hr_list_min'])) for y in r)} HR).",
          f"- K leader: IP {summary([x['ip'] for x in kl])}, K/9 {summary([9 * x['k'] / x['ip'] for x in kl])}; "
          f"{sum(x['gs'] <= RELIEF_MAX_GS for x in kl)} of {len(kl)} made ≤{RELIEF_MAX_GS} starts. "
          f"Real K/9 of the leader: {', '.join(_k9(lead(y, 'k', 'SO')) for y in r)}.",
          f"- ERA leader: IP {summary([x['ip'] for x in el])}; {sum(x['gs'] <= RELIEF_MAX_GS for x in el)} of {len(el)} made ≤{RELIEF_MAX_GS} starts; "
          f"qualified relievers (≤{RELIEF_MAX_GS} GS) in the low five: {summary([sum(g <= RELIEF_MAX_GS for g in s['era_low5_gs']) for s in sims])}.",
          f"- Max IP with ≤{RELIEF_MAX_GS} GS: appearances {summary([s['relief_ip_max']['g'] for s in sims])}, "
          f"Stamina {summary([s['relief_ip_max']['ratings']['stamina'] for s in sims])}; "
          f"relievers with 60+ IP per season {summary(S('n_relief_60ip'))}, 70+ IP {summary(S('n_relief_70ip'))}. "
          f"The season's innings leader made ≤{RELIEF_MAX_GS} starts in {sum(s['ip_leader']['gs'] <= RELIEF_MAX_GS for s in sims)} of {len(sims)} seasons.",
          f"- BA leader: AB {summary([s['ba_leader']['ab'] for s in sims])}.", ""]
    return "\n".join(L)


def _k9(row: dict) -> str:
    return f"{9 * float(row['SO']) / _ip(row['IP']):.1f}"


def _ip(v: str) -> float:
    whole, _, frac = v.partition(".")
    return int(whole) + int(frac or 0) / 3


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20251000)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--from-json", action="store_true", help="rewrite the markdown from reports/leaders_audit.json")
    a = ap.parse_args()
    if a.from_json:
        sims = json.loads(OUT_JSON.read_text())
    else:
        with ProcessPoolExecutor(a.workers) as ex:
            sims = list(ex.map(one, [a.seed + i for i in range(a.seasons)]))
        OUT_JSON.write_text(json.dumps(sims, indent=1, default=float))
    md = report(sims, json.loads(REAL.read_text()))
    OUT_MD.write_text(md)
    print(md)


if __name__ == "__main__":
    main()
