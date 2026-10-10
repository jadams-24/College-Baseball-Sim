"""League batting and pitching rates of NCAA Division II and junior-college leagues from their conference
team-statistics pages, 2025 season (Phase 8-11 yardstick, 2026-10-10).

    python tools/fetch_d2_juco_team_stats.py --work /path/outside/the/repo [--aggregate]

Team totals only (no player pages): the Sidearm conference page `stats.aspx?path=baseball&year=2025`
(Overall Batting Stats and Overall Pitching Stats tables) for eight D2 conferences whose hosts answer,
and the PrestoSports `/sports/bsb/2024-25/teams` page for the junior-college leagues. One request per
page, 3 s apart, a browser-like user agent (the hosts answer plain requests; robots.txt is read first and
a disallow skips the host). Raw pages are kept in the working directory; data/phase8_11/
d2_juco_league_rates_2025.csv holds one row per league with the pooled rates and the sample sizes.
Grade B: team totals include games against other levels; the D2 set is the conferences that answered,
not a random sample (missing CCAA, PacWest, RMAC, Peach Belt, SAC, Conference Carolinas, NE10, CACC,
MEC, G-MAC, ECC, GAC: 502, TLS or 404 on 2026-10-10). The NWAC uses wood bats (unverified here, C).
"""
from __future__ import annotations

import argparse
import hashlib
import html
import re
import sys
import time
import urllib.robotparser
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/phase8_11/d2_juco_league_rates_2025.csv"
UA = "Mozilla/5.0 (compatible; college-baseball-sim data pull; github.com/jadams-24/College-Baseball-Sim)"
PAGES = [  # league, level, kind (sidearm / presto), url
    ("PSAC", "NCAA D2", "sidearm", "https://www.psacsports.org/stats.aspx?path=baseball&year=2025"),
    ("SSC", "NCAA D2", "sidearm", "https://www.sunshinestateconference.com/stats.aspx?path=baseball&year=2025"),
    ("GLIAC", "NCAA D2", "sidearm", "https://www.gliac.org/stats.aspx?path=baseball&year=2025"),
    ("GLVC", "NCAA D2", "sidearm", "https://glvcsports.com/stats.aspx?path=baseball&year=2025"),
    ("MIAA", "NCAA D2", "sidearm", "https://www.themiaa.com/stats.aspx?path=baseball&year=2025"),
    ("NSIC", "NCAA D2", "sidearm", "https://northernsun.org/stats.aspx?path=baseball&year=2025"),
    ("LSC", "NCAA D2", "sidearm", "https://lonestarconference.org/stats.aspx?path=baseball&year=2025"),
    ("GSC", "NCAA D2", "sidearm", "https://gscsports.org/stats.aspx?path=baseball&year=2025"),
    ("CCCAA", "JUCO (California)", "presto", "https://cccbca.com/sports/bsb/2024-25/teams"),
    ("KJCCC", "NJCAA D1 (Kansas)", "presto", "https://kjccc.org/sports/bsb/2024-25/teams"),
    ("ACCC", "NJCAA D1 (Alabama)", "presto", "https://www.acccathletics.com/sports/bsb/2024-25/teams"),
    ("ICCAC D2", "NJCAA D2 (Iowa)", "presto", "https://iccac.org/sports/bsb/2024-25/d2/teams"),
    ("NWAC", "JUCO (Northwest, wood bats)", "presto", "https://nwacsports.org/sports/bsb/2024-25/teams"),
]


def num(x):
    x = str(x).replace(",", "").strip().split("-")[0]
    try:
        return float(x)
    except ValueError:
        return None


def ip_to_f(v: float) -> float:
    w = int(v)
    return w + round((v - w) * 10) / 3


def cells(r: str) -> list[str]:
    return [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip() for c in re.findall(r"<t[hd].*?</t[hd]>", r, flags=re.S)]


def tables(text: str) -> list[tuple[str, list[str], list[list[str]]]]:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", text, flags=re.S)
    out = []
    for tb in re.findall(r"<table.*?</table>", text, flags=re.S):
        cap = re.search(r"<caption.*?>(.*?)</caption>", tb, flags=re.S)
        cap = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", cap.group(1))).strip() if cap else ""
        rows = re.findall(r"<tr.*?</tr>", tb, flags=re.S)
        if not rows:
            continue
        h = [c.lower() for c in cells(rows[0])]
        body = [cells(r) for r in rows[1:]]
        body = [r for r in body if len(r) == len(h) and not re.search(r"(?i)total", " ".join(r[:2]))]
        out.append((cap, h, body))
    return out


def col_sum(h, body, name):
    if name not in h:
        return None
    i = h.index(name)
    return sum(num(r[i]) or 0 for r in body)


def parse(text: str, kind: str) -> dict | None:
    hit = pit = run = None
    for cap, h, body in tables(text):
        if kind == "sidearm":
            if cap == "Overall Batting Stats" and hit is None:
                hit = (h, body)
            elif cap == "Overall Pitching Stats" and pit is None:
                pit = (h, body)
        else:
            if "ab" in h and "h" in h and hit is None:
                hit = (h, body)
            elif "era" in h and "ip" in h and pit is None:
                pit = (h, body)
            elif h[:3] == ["rk", "team", "gp"] and "r" in h and "tb" in h and run is None:
                run = (h, body)
    if not hit:
        return None
    h, b = hit
    S = lambda n: col_sum(h, b, n)
    g = S("g") if "g" in h else S("gp")
    ab, H, bb, hr, d2, d3 = S("ab"), S("h"), S("bb"), S("hr"), S("2b"), S("3b")
    k = S("so") if "so" in h else S("k")
    hbp, sf = S("hbp"), S("sf")
    r = S("r") if "r" in h else (col_sum(run[0], run[1], "r") if run else None)
    sb = S("sb") if "sb" in h else (col_sum(run[0], run[1], "sb") if run else None)
    tb = S("tb") if "tb" in h else H + d2 + 2 * d3 + 3 * hr
    out = {"teams": len(b), "team_games": g, "ab": ab, "pa_approx": ab + bb + (hbp or 0) + (sf or 0), "ba": H / ab, "slg": tb / ab,
           "obp": (H + bb + (hbp or 0)) / (ab + bb + (hbp or 0) + (sf or 0)) if hbp is not None else None,
           "hr_per_team_game": hr / g, "runs_per_team_game": r / g if r else None, "k_per_ab": k / ab, "bb_per_ab": bb / ab,
           "hbp_per_pa": hbp / (ab + bb + hbp + (sf or 0)) if hbp is not None else None, "sb_per_team_game": sb / g if sb else None}
    if pit:
        ph, pb = pit
        ipi = ph.index("ip")
        ip = sum(ip_to_f(num(r[ipi]) or 0) for r in pb)
        P = lambda n: col_sum(ph, pb, n)
        kk = P("so") if "so" in ph else P("k")
        out.update({"ip": ip, "era": 9 * P("er") / ip, "k_per_9": 9 * kk / ip, "bb_per_9": 9 * P("bb") / ip, "hr_per_9": 9 * P("hr") / ip,
                    "h_per_9": 9 * P("h") / ip})
    return out


def allowed(url: str) -> bool:
    import requests
    m = re.match(r"(https?://[^/]+)", url)
    rp = urllib.robotparser.RobotFileParser()
    try:
        r = requests.get(m.group(1) + "/robots.txt", headers={"User-Agent": UA}, timeout=30)
        if r.status_code == 200:
            rp.parse(r.text.splitlines())
            return rp.can_fetch("*", url)
    except requests.RequestException:
        pass
    return True


def fetch(work: Path) -> None:
    import requests
    work.mkdir(parents=True, exist_ok=True)
    for league, level, kind, url in PAGES:
        p = work / (hashlib.md5(url.encode()).hexdigest()[:8] + ".html")
        if p.exists():
            continue
        if not allowed(url):
            print(f"{league}: robots.txt disallows; skipped", flush=True)
            continue
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
            print(f"{league}: HTTP {r.status_code} {len(r.text)} bytes", flush=True)
            if r.status_code == 200:
                p.write_text(r.text)
        except requests.RequestException as e:
            print(f"{league}: {e}", flush=True)
        time.sleep(3)


def aggregate(work: Path, out: Path = OUT) -> pd.DataFrame:
    rows = []
    for league, level, kind, url in PAGES:
        p = work / (hashlib.md5(url.encode()).hexdigest()[:8] + ".html")
        if not p.exists():
            rows.append({"league": league, "level": level, "status": "not fetched", "source_url": url})
            continue
        d = parse(p.read_text(encoding="utf-8", errors="ignore"), kind)
        if not d:
            rows.append({"league": league, "level": level, "status": "no team table parsed", "source_url": url})
            continue
        rows.append({"league": league, "level": level, "status": "ok", **d, "source_url": url, "fetched": time.strftime("%Y-%m-%d"), "grade": "B"})
    df = pd.DataFrame(rows)
    ok = df[df.status == "ok"]
    d2 = ok[ok.level == "NCAA D2"]
    if len(d2):   # pooled D2 line, AB- and IP-weighted
        w = d2.ab
        pooled = {"league": "D2 pooled", "level": "NCAA D2", "status": "ok", "teams": int(d2.teams.sum()), "team_games": float(d2.team_games.sum()),
                  "ab": float(d2.ab.sum()), "pa_approx": float(d2.pa_approx.sum())}
        for c in ("ba", "slg", "obp", "k_per_ab", "bb_per_ab"):
            pooled[c] = float((d2[c] * w).sum() / w.sum())
        pooled["hbp_per_pa"] = float((d2.hbp_per_pa * d2.pa_approx).sum() / d2.pa_approx.sum())
        for c in ("hr_per_team_game", "runs_per_team_game", "sb_per_team_game"):
            pooled[c] = float((d2[c] * d2.team_games).sum() / d2.team_games.sum()) if d2[c].notna().all() else None
        if "ip" in d2:
            pooled["ip"] = float(d2.ip.sum())
            for c in ("era", "k_per_9", "bb_per_9", "hr_per_9", "h_per_9"):
                pooled[c] = float((d2[c] * d2.ip).sum() / d2.ip.sum())
        pooled.update({"source_url": "the eight D2 rows", "fetched": time.strftime("%Y-%m-%d"), "grade": "B"})
        df = pd.concat([df, pd.DataFrame([pooled])], ignore_index=True)
    num_cols = [c for c in df.columns if c not in ("league", "level", "status", "source_url", "fetched", "grade")]
    df[num_cols] = df[num_cols].astype(float).round(4)
    df.to_csv(out, index=False)
    return df


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True)
    ap.add_argument("--aggregate", action="store_true")
    a = ap.parse_args()
    work = Path(a.work).resolve()
    if not a.aggregate:
        fetch(work)
    df = aggregate(work)
    print(df[["league", "level", "status", "teams", "ba", "obp", "slg", "hr_per_team_game", "runs_per_team_game", "era"]].to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
