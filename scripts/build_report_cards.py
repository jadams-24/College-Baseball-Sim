"""School identity and report cards for the 307 D1 programs (Phase 9 prep, owner request 2026-10-08). Data only: nothing in
engine/ reads these files, and no grade feeds team strength or a gated row.

Writes
  data/schools/schools.csv        every sim team (tid = its row in data/ncaa_2025/pbp/teams_2025.csv, the order config.phase2
                                  reads) with its real school name, IPEDS institution, conference, tier and campus location.
                                  School names only: no logos, mascots or artwork. Players stay fictional.
  data/schools/report_cards.csv   one row per program: for each category its grade (A+ to F), the score it was graded on
                                  (percentile across D1), the raw inputs, the source and a confidence grade
  reports/report_cards.md         the grade distribution of each category and example report cards
Grading: config/report_cards.py (percentile cutoffs, weights; the spec: design/phase9_recruiting.md, Section 15).

Inputs (all committed; sources and fetch dates in data/README.md)
  Program Tradition    data/ncaa_brackets/brackets_2015_2025.json (field, hosts, supers, Omaha, finals, titles), recency
                       weighted; the D1 win pct 2021-2025 (scoreboard feeds) breaks ties among programs without postseason points
  Conference Prestige  the 2025 conference map; members' RPI (engine.rpi on each season's D1 scoreboard games, 2021-2025) and NCAA
                       bids per member (brackets), recency weighted
  Omaha Contender      the sim's drawn team strength (o + d, log runs) in a reference world (REFERENCE_SEED, the report's first
                       seed); a dynasty regrades it from its own draw (config.report_cards.grade_values)
  Academic Prestige    IPEDS DRVGR2023 (GBA6RTT, six-year bachelor's graduation rate) and DRVADM2023 (DVADM01, percent admitted;
                       none reported: open admission, 100%)
  Campus Life          IPEDS DRVEF2023 (ENRTOT, total enrollment) and HD2024 (LOCALE)
  Climate              NOAA 1991-2020 monthly normals at the nearest normals station (data/noaa/climate_normals_by_school.csv)
  Money                EADA 2024-25 (data/eada/baseball_eada_2024_25.csv): baseball total expenses
  Facilities, Ballpark Atmosphere, Brand Exposure, Draft Development: GUESS proxies of the above (confidence D)
  Coach Prestige, Coach Stability: the neutral baseline for a new coach
    python3 scripts/build_report_cards.py
"""
from __future__ import annotations

import json
import math
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from config import report_cards as rc  # noqa: E402
from lib.brackets import brackets, name_map  # noqa: E402

OUT = ROOT / "data/schools"
TEAMS = ROOT / "data/ncaa_2025/pbp/teams_2025.csv"
LOC = ROOT / "data/ncaa_2025/school_locations_2025.csv"
EADA = ROOT / "data/eada/baseball_eada_2024_25.csv"
NOAA = ROOT / "data/noaa/climate_normals_by_school.csv"
IPEDS = ROOT / "data/ipeds"
REFERENCE_SEED = 20251000
LAST = 2025
RPI_SEASONS = (2021, 2022, 2023, 2024, 2025)
# bracket spellings of programs whose 2025 name differs beyond the general rules (scripts/lib/brackets.py name_map)
BRACKET_ALIASES = {"Lamar": "Lamar University", "Long Island": "LIU", "Northern Illinois": "NIU", "Saint Mary's": "Saint Mary's (CA)"}
MIN_CONF_ENTRIES = 50       # a feed conference with this many team-game entries is Division I (non-D1 opponents appear rarely)


def w(season: int) -> float:
    return 0.5 ** ((LAST - season) / rc.TRADITION_HALF_LIFE)


def ipeds(name: str) -> pd.DataFrame:
    z = zipfile.ZipFile(IPEDS / f"{name}.zip")
    d = pd.read_csv(z.open([n for n in z.namelist() if n.lower().endswith(".csv")][0]), encoding="latin-1", low_memory=False)
    d.columns = [c.strip() for c in d.columns]
    return d.set_index("UNITID")


# ----------------------------------------------------------------------------------------------------------------------

def schools() -> pd.DataFrame:
    t = pd.read_csv(TEAMS)
    t = t[t.tier.notna() & (t.tier != "")].reset_index(drop=True)
    loc = pd.read_csv(LOC).set_index("ncaa_team_id")
    s = pd.DataFrame({"tid": np.arange(len(t)), "ncaa_team_id": t.ncaa_team_id, "school": t.team, "conference": t.conference, "tier": t.tier})
    for c_out, c_in in (("institution", "instnm"), ("unitid", "unitid"), ("city", "city"), ("state", "state"),
                        ("latitude", "latitude"), ("longitude", "longitude")):
        s[c_out] = s.ncaa_team_id.map(loc[c_in])
    s["unitid"] = s.unitid.astype(int)
    return s


def our_name(team: str, ours: set, m: dict):
    for c in dict.fromkeys((team, BRACKET_ALIASES.get(team), m.get(team), team.replace("–", "-"), (m.get(team) or team).replace(" State", " St."),
                            team.replace("–", "-").replace(" State", " St."))):
        if c and c in ours:
            return c
    return None


def tradition(s: pd.DataFrame) -> pd.DataFrame:
    ours, m = set(s.school), name_map()
    pts = {k: 0.0 for k in ours}
    cnt = {k: {f: 0 for f in ("field", "host", "super", "omaha", "title")} for k in ours}
    hosting = {k: 0.0 for k in ours}
    unmatched = set()
    for y, b in brackets().items():
        yr = int(y)
        sets = {"field": {x["team"] for x in b["teams"]}, "host": {r["host"] for r in b["regionals"] if r.get("host")},
                "super": {t for sp in b["supers"] for t in sp["teams"]}, "omaha": set(b["cws"]),
                "final": {b["champion"], b["runner_up"]}, "title": {b["champion"]}}
        for k, teams in sets.items():
            for team in teams:
                n = our_name(team, ours, m)
                if n is None:
                    unmatched.add(team); continue
                pts[n] += w(yr) * rc.TRADITION_POINTS[k]
                if k in cnt[n]:
                    cnt[n][k] += 1
                if k == "host":
                    hosting[n] += w(yr)
    out = pd.DataFrame({"school": list(ours)})
    out["tradition_points"] = out.school.map(pts)
    out["hosting_points"] = out.school.map(hosting)
    for f in ("field", "host", "super", "omaha", "title"):
        out[f"n_{f}_2015_2025"] = out.school.map(lambda k: cnt[k][f])
    out.attrs["unmatched"] = sorted(unmatched)
    return out.set_index("school")


def seasons_rpi(s: pd.DataFrame) -> tuple:
    """Per season 2021-2025: RPI and D1 win pct of every current program (the 2025 feed's seo slug names it in older feeds)."""
    from engine.rpi import rpi
    f25 = pd.read_csv(ROOT / "data/ncaa_2025/scoreboard/games_2025.csv")
    seo = dict(zip(f25.home, f25.home_seo)); seo.update(dict(zip(f25.away, f25.away_seo)))
    by_seo = {seo[n]: n for n in s.school if n in seo}
    R, WP = {}, {}
    for y in RPI_SEASONS:
        d = pd.read_csv(ROOT / f"data/ncaa_{y}/scoreboard/games_{y}.csv")
        d = d[(d.state == "final") & d.home_score.notna() & d.away_score.notna() & (d.home_score != d.away_score)]
        if "url" in d:
            d = d.drop_duplicates("url")
        conf_n = pd.concat([d.away_conf, d.home_conf]).value_counts()
        d1c = set(conf_n[conf_n >= MIN_CONF_ENTRIES].index)
        d = d[d.home_conf.isin(d1c) & d.away_conf.isin(d1c)]
        key = lambda name, slug: by_seo.get(slug, name)
        g = [(key(h, hs), key(a, as_), hsc > asc, False) for h, hs, a, as_, hsc, asc in
             zip(d.home, d.home_seo, d.away, d.away_seo, d.home_score, d.away_score)]
        r = rpi(g)
        R[y] = {t: v["rpi"] for t, v in r.items()}
        WP[y] = {t: v["w"] / max(v["w"] + v["l"], 1) for t, v in r.items()}
    return R, WP


def conference(s: pd.DataFrame, R: dict) -> pd.DataFrame:
    """Members' mean RPI and NCAA bids per member, seasons 2021-2025, recency weighted (seasons with no member in the feed
    skipped), on the 2025 map. An independent has no conference: its row is left empty and graded NEUTRAL (main)."""
    ours, m = set(s.school), name_map()
    bids = {y: set() for y in RPI_SEASONS}
    for y, b in brackets().items():
        if int(y) in bids:
            bids[int(y)] = {our_name(x["team"], ours, m) for x in b["teams"]} - {None}
    rows = []
    for conf, g in s.groupby("conference"):
        members = list(g.school)
        if conf == "DI Independent":
            rows += [(t, np.nan, np.nan) for t in members]
            continue
        yrs = [y for y in RPI_SEASONS if any(t in R[y] for t in members)]
        rp = sum(w(y) * np.mean([R[y][t] for t in members if t in R[y]]) for y in yrs) / sum(w(y) for y in yrs)
        bd = sum(w(y) * len(bids[y] & set(members)) / len(members) for y in RPI_SEASONS) / sum(w(y) for y in RPI_SEASONS)
        rows += [(t, rp, bd) for t in members]
    return pd.DataFrame(rows, columns=["school", "conf_rpi_mean", "conf_bids_per_member"]).set_index("school")


def omaha(s: pd.DataFrame) -> pd.Series:
    from config import phase2
    from engine.league import build_league
    ss = np.random.SeedSequence(REFERENCE_SEED)
    s_league, _, _ = ss.spawn(3)
    lg = build_league(phase2.load(), np.random.Generator(np.random.PCG64(s_league)))
    return pd.Series([lg.teams[i].o + lg.teams[i].d for i in s.tid], index=s.school.values)


# ----------------------------------------------------------------------------------------------------------------------

def blend(df: pd.DataFrame, weights: dict) -> np.ndarray:
    return sum(wt * df[k].values for k, wt in weights.items()) / sum(weights.values())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    s = schools()
    s.to_csv(OUT / "schools.csv", index=False)
    card = s[["tid", "ncaa_team_id", "school", "conference", "tier"]].copy().set_index("school", drop=False)
    pct = pd.DataFrame(index=card.index)

    # Program Tradition
    tr = tradition(s)
    R, WP = seasons_rpi(s)
    wp = {t: sum(w(y) * WP[y].get(t, np.nan) for y in RPI_SEASONS if t in WP[y]) / max(sum(w(y) for y in RPI_SEASONS if t in WP[y]), 1e-9)
          for t in card.index}
    card = card.join(tr)
    card["d1_winpct_2021_2025"] = card.index.map(wp)
    score = card.tradition_points + rc.TRADITION_WINPCT_WEIGHT * card.d1_winpct_2021_2025.fillna(card.d1_winpct_2021_2025.median())
    card["program_tradition_score"] = score
    pct["program_tradition"] = rc.percentile(score)
    pct["hosting"] = rc.percentile(card.hosting_points)
    pct["omaha_hist"] = rc.percentile(card.n_omaha_2015_2025 + 0.5 * card.n_super_2015_2025 + 0.01 * card.tradition_points)

    # Conference Prestige
    card = card.join(conference(s, R))
    ind = card.conf_rpi_mean.isna()
    pr = rc.percentile(card.conf_rpi_mean.fillna(card.conf_rpi_mean.median()))
    pb = rc.percentile(card.conf_bids_per_member.fillna(card.conf_bids_per_member.median()))
    cp = rc.percentile(rc.CONFERENCE_WEIGHTS["rpi"] * pr + rc.CONFERENCE_WEIGHTS["bids"] * pb)
    cp[ind.values] = 0.5                     # an independent: no conference, the neutral middle (graded NEUTRAL below)
    pct["conference_prestige"] = cp

    # Omaha Contender (reference world)
    card["sim_strength_o_plus_d"] = card.index.map(omaha(s))
    pct["omaha_contender"] = rc.percentile(card.sim_strength_o_plus_d)

    # Academic Prestige
    gr, adm, ef = ipeds("DRVGR2023"), ipeds("DRVADM2023"), ipeds("DRVEF2023")
    hdz = zipfile.ZipFile(IPEDS / "HD2024.zip")
    hd = pd.read_csv(hdz.open([n for n in hdz.namelist() if n.lower().endswith(".csv")][0]), encoding="latin-1", low_memory=False).set_index("UNITID")
    uid = s.set_index("school").unitid
    card["grad_rate_6yr"] = card.index.map(lambda t: pd.to_numeric(gr.GBA6RTT.get(uid[t]), errors="coerce"))
    card["admit_rate"] = card.index.map(lambda t: pd.to_numeric(adm.DVADM01.get(uid[t]), errors="coerce"))
    card["admit_rate_reported"] = card.admit_rate.notna()
    card["admit_rate"] = card.admit_rate.fillna(100.0)
    g_fill = card.grad_rate_6yr.fillna(card.grad_rate_6yr.median())
    a = pd.DataFrame({"grad_rate": rc.percentile(g_fill), "selectivity": rc.percentile(100 - card.admit_rate)}, index=card.index)
    pct["academic_prestige"] = rc.percentile(blend(a, rc.ACADEMIC_WEIGHTS))

    # Campus Life
    card["enrollment"] = card.index.map(lambda t: ef.ENRTOT.get(uid[t]))
    card["locale_code"] = card.index.map(lambda t: hd.LOCALE.get(uid[t]))
    c = pd.DataFrame({"enrollment": rc.percentile(np.log(card.enrollment.astype(float))),
                      "locale": card.locale_code.map(rc.LOCALE_SCORE).fillna(0.5).values}, index=card.index)
    pct["campus_life"] = rc.percentile(blend(c, rc.CAMPUS_WEIGHTS))
    pct["enrollment"] = c.enrollment.values

    # Climate
    cl = pd.read_csv(NOAA).set_index("team")
    card["tavg_feb_may_f"] = card.index.map(cl.tavg_feb_may)
    card["precip_days_feb_may"] = card.index.map(cl.precip_days_feb_may)
    card["climate_station"] = card.index.map(cl.station)
    card["climate_station_miles"] = card.index.map(cl.miles)
    k = pd.DataFrame({"temperature": rc.percentile(card.tavg_feb_may_f.fillna(card.tavg_feb_may_f.median())),
                      "dry_days": rc.percentile(-card.precip_days_feb_may.fillna(card.precip_days_feb_may.median()))}, index=card.index)
    pct["climate"] = rc.percentile(blend(k, rc.CLIMATE_WEIGHTS))

    # Money
    ea = pd.read_csv(EADA).set_index("unitid")
    card["baseball_expenses_2024_25"] = card.index.map(lambda t: ea.baseball_total_expenses.get(uid[t]))
    card["money_imputed"] = card.baseball_expenses_2024_25.isna()
    med = card.groupby("tier").baseball_expenses_2024_25.median()
    card["baseball_expenses_2024_25"] = card.baseball_expenses_2024_25.fillna(card.tier.map(med))
    pct["money"] = rc.percentile(card.baseball_expenses_2024_25)

    # GUESS proxies
    pp = pct.rename(columns={"conference_prestige": "conference", "program_tradition": "tradition", "omaha_hist": "omaha"})
    pct["facilities"] = rc.percentile(blend(pp, rc.FACILITIES_WEIGHTS))
    pct["ballpark_atmosphere"] = rc.percentile(blend(pp, rc.ATMOSPHERE_WEIGHTS))
    pct["brand_exposure"] = rc.percentile(blend(pp, rc.EXPOSURE_WEIGHTS))
    pct["draft_development"] = rc.percentile(blend(pp, rc.DRAFT_WEIGHTS))

    src = {"program_tradition": ("NCAA tournament brackets 2015-2025 (Wikipedia pages, data/ncaa_brackets) + D1 win pct 2021-2025 (data.ncaa.com scoreboards)", "B"),
           "conference_prestige": ("RPI computed from data.ncaa.com scoreboards 2021-2025 (engine/rpi.py) + bids from the brackets, 2025 conference map", "B"),
           "omaha_contender": (f"the sim's drawn team strength o + d, reference world seed {REFERENCE_SEED}; a dynasty regrades it from its own draw", "A"),
           "academic_prestige": ("IPEDS 2023 DRVGR (GBA6RTT) and DRVADM (DVADM01), NCES", "A"),
           "campus_life": ("IPEDS 2023 DRVEF (ENRTOT) and HD2024 (LOCALE), NCES; weighting GUESS", "C"),
           "climate": ("NOAA NCEI 1991-2020 monthly normals, nearest station with temperature and precipitation days", "A"),
           "money": ("EADA 2024-25, baseball total expenses (U.S. Department of Education)", "A"),
           "facilities": ("GUESS proxy: baseball expenses, regional hosting, conference", "D"),
           "ballpark_atmosphere": ("GUESS proxy: regional hosting, enrollment, conference", "D"),
           "brand_exposure": ("GUESS proxy: conference, Omaha and super regional history", "D"),
           "draft_development": ("GUESS proxy: program tradition, baseball expenses, conference", "D"),
           "coach_prestige": ("neutral baseline for a new coach", "D"),
           "coach_stability": ("neutral baseline for a new coach", "D")}
    for cat in rc.CATEGORIES:
        if cat in ("coach_prestige", "coach_stability"):
            card[f"{cat}_grade"] = rc.NEUTRAL
            card[f"{cat}_score"] = np.nan
        else:
            card[f"{cat}_score"] = pct[cat].round(4).values
            card[f"{cat}_grade"] = [rc.grade_of(p) for p in pct[cat].values]
        card[f"{cat}_source"] = src[cat][0]
        card[f"{cat}_confidence"] = src[cat][1]
    # rows whose input was imputed carry a lower confidence
    card.loc[card.money_imputed, "money_confidence"] = "D"
    card.loc[~card.admit_rate_reported, "academic_prestige_confidence"] = "B"
    card.loc[card.tavg_feb_may_f.isna(), "climate_confidence"] = "D"
    card.loc[ind, "conference_prestige_grade"] = rc.NEUTRAL
    card.loc[ind, "conference_prestige_confidence"] = "D"
    card.loc[ind, "conference_prestige_source"] = "independent (no conference): neutral baseline"

    raw = ["tradition_points", "hosting_points", "n_field_2015_2025", "n_host_2015_2025", "n_super_2015_2025", "n_omaha_2015_2025",
           "n_title_2015_2025", "d1_winpct_2021_2025", "program_tradition_score", "conf_rpi_mean", "conf_bids_per_member",
           "sim_strength_o_plus_d", "grad_rate_6yr", "admit_rate", "admit_rate_reported", "enrollment", "locale_code", "tavg_feb_may_f",
           "precip_days_feb_may", "climate_station", "climate_station_miles", "baseball_expenses_2024_25", "money_imputed"]
    cols = ["tid", "ncaa_team_id", "school", "conference", "tier"]
    for cat in rc.CATEGORIES:
        cols += [f"{cat}_grade", f"{cat}_score", f"{cat}_confidence"]
    cols += raw + [f"{cat}_source" for cat in rc.CATEGORIES]
    out = card.reset_index(drop=True)[cols].sort_values("tid")
    for c_ in ("tradition_points", "hosting_points", "program_tradition_score", "d1_winpct_2021_2025", "conf_rpi_mean",
               "conf_bids_per_member", "sim_strength_o_plus_d"):
        out[c_] = out[c_].astype(float).round(4)
    out.to_csv(OUT / "report_cards.csv", index=False)
    report(out, tr.attrs["unmatched"])


def report(out: pd.DataFrame, unmatched: list) -> None:
    lines = ["# School report cards: distribution and examples", "",
             "Built by `scripts/build_report_cards.py` (Phase 9 prep, owner request 2026-10-08). Data only: grades never feed the engine's "
             "team strength or any gated row. Grading: percentile across the 307 D1 programs, cutoffs in `config/report_cards.py` "
             f"(top shares {', '.join(f'{g} {s:.0%}' for g, s in zip(rc.GRADES, rc.TOP_SHARE))}).", "",
             "## Grade distribution (programs per grade)", "",
             "| Category | " + " | ".join(rc.GRADES) + " | Confidence |", "|---|" + "---|" * (len(rc.GRADES) + 1)]
    for cat in rc.CATEGORIES:
        vc = out[f"{cat}_grade"].value_counts()
        conf = out[f"{cat}_confidence"].value_counts()
        lines.append(f"| {cat.replace('_', ' ').title()} | " + " | ".join(str(int(vc.get(g, 0))) for g in rc.GRADES) + " | "
                     + ", ".join(f"{k} {v}" for k, v in conf.sort_index().items()) + " |")
    lines += ["", "Grades by tier (share of the tier's programs at B- or better):", "", "| Category | P4 | Mid | Low |", "|---|---|---|---|"]
    good = set(rc.GRADES[:6])
    for cat in rc.CATEGORIES[:11]:
        lines.append(f"| {cat.replace('_', ' ').title()} | " + " | ".join(f"{out[out.tier == t][f'{cat}_grade'].isin(good).mean():.2f}" for t in ("p4", "mid", "low")) + " |")
    if unmatched:
        lines += ["", f"Bracket teams not among the 307 programs (left D1 or not matched): {', '.join(unmatched)}."]
    (ROOT / "reports/report_cards.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
