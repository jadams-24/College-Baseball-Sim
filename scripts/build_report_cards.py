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
                       none reported: open admission, 100%); selectivity weighted 3:1 over graduation (owner calibration 2026-10-09)
  Campus Life          IPEDS DRVEF2023 (ENRTOT, total enrollment) and HD2024 (LOCALE)
  Climate              NOAA 1991-2020 monthly normals at the nearest normals station (data/noaa/climate_normals_by_school.csv):
                       Feb-May daily highs against a comfortable band (cold and heat both penalized) and precipitation days
                       (owner calibration 2026-10-09)
  Money                EADA 2024-25 (data/eada/baseball_eada_2024_25.csv): baseball total expenses
  Facilities, Ballpark Atmosphere, Brand Exposure, Draft Development: GUESS proxies (confidence D, marked for replacement); Brand
                       Exposure from the conference's media footprint, NCAA tournament appearances and Omaha / super history
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
EXAMPLES = ("LSU", "Vanderbilt", "Stanford", "Oregon St.", "Nebraska", "Coastal Carolina", "DBU", "Murray St.", "Wright St.",
            "Army West Point", "Alabama A&M")
LAST = 2025
RPI_SEASONS = (2021, 2022, 2023, 2024, 2025)
# one shared name-alias table for every source (owner audit 2026-10-09): a spelling in a source file -> our 2025 school name
ALIASES = dict(pd.read_csv(ROOT / "data/schools/name_aliases.csv")[["alias", "school"]].values)
MIN_CONF_ENTRIES = 50       # a feed conference with this many team-game entries is Division I (non-D1 opponents appear rarely)


def w(season: int) -> float:
    return 0.5 ** ((LAST - season) / rc.TRADITION_HALF_LIFE)


def ipeds(name: str) -> pd.DataFrame:
    z = zipfile.ZipFile(IPEDS / f"{name}.zip")
    d = pd.read_csv(z.open([n for n in z.namelist() if n.lower().endswith(".csv")][0]), encoding="latin-1", low_memory=False)
    d.columns = [c.replace("ï»¿", "").replace("\ufeff", "").strip() for c in d.columns]   # HD2024 starts with a byte-order mark
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
    for c in dict.fromkeys((team, ALIASES.get(team), m.get(team), team.replace("–", "-"), (m.get(team) or team).replace(" State", " St."),
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
    """Per season 2021-2025: RPI, D1 win pct and fitted strength (the scoreboard fit's o + d, log runs, no parks) of every
    current program. Names: the 2025 feed's seo slug names a program in older feeds; other spellings go through the shared
    alias table (data/schools/name_aliases.csv)."""
    from build_phase2_teams import fit
    from engine.rpi import rpi
    f25 = pd.read_csv(ROOT / "data/ncaa_2025/scoreboard/games_2025.csv")
    seo = dict(zip(f25.home, f25.home_seo)); seo.update(dict(zip(f25.away, f25.away_seo)))
    by_seo = {seo[n]: n for n in s.school if n in seo}
    R, WP, S = {}, {}, {}
    for y in RPI_SEASONS:
        d = pd.read_csv(ROOT / f"data/ncaa_{y}/scoreboard/games_{y}.csv")
        d = d[(d.state == "final") & d.home_score.notna() & d.away_score.notna() & (d.home_score != d.away_score)]
        if "url" in d:
            d = d.drop_duplicates("url")
        conf_n = pd.concat([d.away_conf, d.home_conf]).value_counts()
        d1c = set(conf_n[conf_n >= MIN_CONF_ENTRIES].index)
        d = d[d.home_conf.isin(d1c) & d.away_conf.isin(d1c)]
        key = lambda name, slug: by_seo.get(slug, ALIASES.get(name, name))
        g = [(key(h, hs), key(a, as_), hsc > asc, False) for h, hs, a, as_, hsc, asc in
             zip(d.home, d.home_seo, d.away, d.away_seo, d.home_score, d.away_score)]
        r = rpi(g)
        R[y] = {t: v["rpi"] for t, v in r.items()}
        WP[y] = {t: v["w"] / max(v["w"] + v["l"], 1) for t, v in r.items()}
        sb = pd.DataFrame(g, columns=["home", "away", "hw", "nt"])
        sb["home_score"], sb["away_score"] = d.home_score.values, d.away_score.values
        names = sorted(set(sb.home) | set(sb.away))
        f = fit(sb, names, parks=False)
        S[y] = {t: float(o + dd) for t, o, dd in zip(names, f["o"], f["d"])}
    return R, WP, S


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


def postseason_recent(s: pd.DataFrame) -> pd.DataFrame:
    """Per program, Omaha and super regional appearances in config OMAHA_POST_SEASONS: raw counts and recency-weighted counts."""
    ours, m = set(s.school), name_map()
    ww = lambda y: 0.5 ** ((LAST - y) / rc.OMAHA_HALF_LIFE)          # noqa: E731
    rows = {k: [0, 0, 0.0, 0.0] for k in ours}
    for y, b in brackets().items():
        y = int(y)
        if y not in rc.OMAHA_POST_SEASONS:
            continue
        for k, teams in ((0, set(b["cws"])), (1, {t for sp in b["supers"] for t in sp["teams"]})):
            for team in teams:
                n = our_name(team, ours, m)
                if n is not None:
                    rows[n][k] += 1; rows[n][k + 2] += ww(y)
    return pd.DataFrame.from_dict(rows, orient="index", columns=["n_omaha_recent", "n_super_recent", "omaha_recent_w", "super_recent_w"])


def omaha(s: pd.DataFrame) -> pd.Series:
    """The reference world's drawn team strength (the pre-2026-10-09 Omaha Contender input; kept for the audit's before/after)."""
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
    R, WP, S = seasons_rpi(s)
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

    # Omaha Contender (owner audit 2026-10-09): real current strength, recency weighted over the seasons a program has, plus
    # recent Omaha / super regional appearances; a program with no strength season is left out of the ranking and graded with
    # confidence D on its postseason alone (none in the 307 today)
    card["sim_strength_o_plus_d"] = card.index.map(omaha(s))
    ws = {y: 0.5 ** ((LAST - y) / rc.OMAHA_HALF_LIFE) for y in rc.OMAHA_STRENGTH_SEASONS}
    card["strength_seasons"] = card.index.map(lambda t: sum(t in S[y] for y in rc.OMAHA_STRENGTH_SEASONS))
    card["strength_recent"] = card.index.map(lambda t: sum(ws[y] * S[y][t] for y in rc.OMAHA_STRENGTH_SEASONS if t in S[y])
                                             / sum(ws[y] for y in rc.OMAHA_STRENGTH_SEASONS if t in S[y]) if any(t in S[y] for y in rc.OMAHA_STRENGTH_SEASONS) else np.nan)
    card = card.join(postseason_recent(s))
    om = [rc.omaha_score(st if not np.isnan(st) else np.nanmedian(card.strength_recent), o, sp)
          for st, o, sp in zip(card.strength_recent, card.omaha_recent_w, card.super_recent_w)]
    card["omaha_contender_raw"] = np.round(om, 4)
    pct["omaha_contender"] = rc.percentile(om)

    # Academic Prestige
    gr, adm, ef = ipeds("DRVGR2023"), ipeds("DRVADM2023"), ipeds("DRVEF2023")
    hd = ipeds("HD2024")
    uid = s.set_index("school").unitid
    card["grad_rate_6yr"] = card.index.map(lambda t: pd.to_numeric(gr.GBA6RTT.get(uid[t]), errors="coerce"))
    card["admit_rate"] = card.index.map(lambda t: pd.to_numeric(adm.DVADM01.get(uid[t]), errors="coerce"))
    card["admit_rate_reported"] = card.admit_rate.notna()
    card["admit_rate"] = card.admit_rate.fillna(100.0)
    pct["academic_prestige"] = rc.percentile(100 - card.admit_rate)        # placeholder: graded on the absolute scale below

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
    card["tmax_feb_may_f"] = card.index.map(cl.tmax_feb_may)
    pct["climate"] = rc.percentile(card.tmax_feb_may_f.fillna(card.tmax_feb_may_f.median()))   # placeholder: absolute scale below

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
    be = pd.DataFrame({"media": card.conference.map(rc.MEDIA_FOOTPRINT).fillna(rc.MEDIA_DEFAULT).values,
                       "field": rc.percentile(card.n_field_2015_2025), "omaha": pct["omaha_hist"].values}, index=card.index)
    pct["brand_exposure"] = rc.percentile(blend(be, rc.EXPOSURE_WEIGHTS))
    pct["draft_development"] = rc.percentile(blend(pp, rc.DRAFT_WEIGHTS))

    src = {"program_tradition": ("NCAA tournament brackets 2015-2025 (Wikipedia pages, data/ncaa_brackets) + D1 win pct 2021-2025 (data.ncaa.com scoreboards)", "B"),
           "conference_prestige": ("RPI computed from data.ncaa.com scoreboards 2021-2025 (engine/rpi.py) + bids from the brackets, 2025 conference map", "B"),
           "omaha_contender": ("current real strength: the data.ncaa.com scoreboard fit's o + d per season 2021-2025 (recency weighted, seasons "
                               "without data skipped) plus recent Omaha and super regional appearances 2021-2025 (brackets); a dynasty regrades "
                               "it from its own teams with config.report_cards.omaha_score", "B"),
           "academic_prestige": ("IPEDS 2023 DRVGR (GBA6RTT) and DRVADM (DVADM01), NCES; absolute cutoffs (config ACADEMIC_*)", "A"),
           "campus_life": ("IPEDS 2023 DRVEF (ENRTOT) and HD2024 (LOCALE), NCES; weighting GUESS", "C"),
           "climate": ("NOAA NCEI 1991-2020 monthly normals, nearest station: Feb-May daily highs (warmth capped) and precipitation "
                       "days, absolute cutoffs (config CLIMATE_*)", "A"),
           "money": ("EADA 2024-25, baseball total expenses (U.S. Department of Education)", "A"),
           "facilities": ("GUESS proxy: baseball expenses, regional hosting, conference", "D"),
           "ballpark_atmosphere": ("GUESS proxy: regional hosting, enrollment, conference", "D"),
           "brand_exposure": ("GUESS proxy, to be replaced by TV and streaming appearance counts: conference media footprint "
                              "(config MEDIA_FOOTPRINT), NCAA tournament appearances, Omaha and super regional history", "D"),
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
    card.loc[card.tmax_feb_may_f.isna(), "climate_confidence"] = "D"
    # absolute scales (owner decision 2026-10-09): Climate and Academic Prestige graded on fixed cutoffs, score = the raw score
    card["climate_score"] = [round(rc.climate_score(t, r), 3) for t, r in zip(card.tmax_feb_may_f.fillna(card.tmax_feb_may_f.median()),
                                                                             card.precip_days_feb_may.fillna(card.precip_days_feb_may.median()))]
    card["climate_grade"] = card.climate_score.map(rc.climate_grade)
    card["academic_prestige_score"] = 100 - card.admit_rate
    card["academic_prestige_grade"] = [rc.academic_grade(a, g) for a, g in zip(card.admit_rate, card.grad_rate_6yr.fillna(card.grad_rate_6yr.median()))]
    card["omaha_contender_confidence"] = np.where(card.strength_seasons >= 3, "B", np.where(card.strength_seasons >= 1, "C", "D"))
    card.loc[ind, "conference_prestige_grade"] = rc.NEUTRAL
    card.loc[ind, "conference_prestige_confidence"] = "D"
    card.loc[ind, "conference_prestige_source"] = "independent (no conference): neutral baseline"

    raw = ["tradition_points", "hosting_points", "n_field_2015_2025", "n_host_2015_2025", "n_super_2015_2025", "n_omaha_2015_2025",
           "n_title_2015_2025", "d1_winpct_2021_2025", "program_tradition_score", "conf_rpi_mean", "conf_bids_per_member",
           "sim_strength_o_plus_d", "strength_recent", "strength_seasons", "n_omaha_recent", "n_super_recent", "omaha_contender_raw", "grad_rate_6yr", "admit_rate", "admit_rate_reported", "enrollment", "locale_code", "tavg_feb_may_f",
           "precip_days_feb_may", "tmax_feb_may_f", "climate_station", "climate_station_miles", "baseball_expenses_2024_25", "money_imputed"]
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
    audit(out, R, S)


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
    short = {"program_tradition": "Trad", "conference_prestige": "Conf", "omaha_contender": "Omaha", "academic_prestige": "Acad",
             "campus_life": "Campus", "climate": "Climate", "money": "Money", "facilities": "Facil", "ballpark_atmosphere": "Atmos",
             "brand_exposure": "Brand", "draft_development": "Draft", "coach_prestige": "Coach", "coach_stability": "Stab"}
    ex = out.set_index("school").loc[[e for e in EXAMPLES if e in set(out.school)]]
    lines += ["", "## Example report cards", "", "Omaha Contender is real current strength plus recent Omaha history (a dynasty regrades it from its own teams). "
              "Climate and Academic Prestige are absolute scales; the other categories are percentiles. Money for the "
              "service academies is imputed (no EADA filing; confidence D). Oregon St. is an independent: Conference Prestige neutral.", "",
              "| School | Conf | Tier | " + " | ".join(short.values()) + " |", "|---|---|---|" + "---|" * len(short)]
    for sch, r in ex.iterrows():
        lines.append(f"| {sch} | {r.conference} | {r.tier} | " + " | ".join(r[f"{k}_grade"] for k in short) + " |")
    lines += ["", "| School | Field / hosts / Omaha / titles 2015-25 | Conf. RPI | Real o+d 2021-25 | Grad rate | Admit rate | Enrollment | Locale | "
              "Feb-May high °F | Precip days | Baseball expenses |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for sch, r in ex.iterrows():
        lines.append(f"| {sch} | {r.n_field_2015_2025} / {r.n_host_2015_2025} / {r.n_omaha_2015_2025} / {r.n_title_2015_2025} | "
                     f"{'—' if pd.isna(r.conf_rpi_mean) else f'{r.conf_rpi_mean:.3f}'} | {r.strength_recent:+.2f} | {r.grad_rate_6yr:.0f}% | "
                     f"{r.admit_rate:.0f}% | {int(r.enrollment):,} | {r.locale_code} | {r.tmax_feb_may_f:.1f} | {r.precip_days_feb_may:.1f} | "
                     f"${r.baseball_expenses_2024_25 / 1e6:.2f}M{' (imputed)' if r.money_imputed else ''} |")
    if unmatched:
        lines += ["", f"Bracket teams not among the 307 programs (left D1 or not matched): {', '.join(unmatched)}."]
    (ROOT / "reports/report_cards.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))




def audit(out: pd.DataFrame, R: dict, S: dict) -> None:
    """Omaha Contender input audit (owner request 2026-10-09): inputs and sources, coverage per school, name joins, the
    missing-data rule, Coastal Carolina and LSU before and after, the recent-Omaha anchor; plus the A+ lists of the two absolute
    categories. Writes reports/report_cards_audit.md."""
    o = out.set_index("school")
    yrs = rc.OMAHA_STRENGTH_SEASONS
    cov = pd.DataFrame({"strength_seasons": [sum(t in S[y] for y in yrs) for t in o.index],
                        "rpi_seasons": [sum(t in R[y] for y in RPI_SEASONS) for t in o.index]}, index=o.index)
    status = lambda n, full: "present" if n == full else ("missing" if n == 0 else "partial")  # noqa: E731
    before = pd.Series(rc.percentile(o.sim_strength_o_plus_d.values), index=o.index).map(rc.grade_of)
    L = ["# Report cards: Omaha Contender input audit, absolute Climate and Academic Prestige", "",
         "Owner request 2026-10-09. Built by `scripts/build_report_cards.py`.", "",
         "## Omaha Contender: what the formula used, and what it uses now", "",
         "**Before:** one input, the reference world's drawn team strength (o + d) for the sim team that carries the school's identity "
         f"(`engine/league.py`, seed {REFERENCE_SEED}). The league draws each team's strength from its tier and conference distribution "
         "(tiers and conferences are distributions of team strength), not from the school's own results, so the grade had no link to the "
         "real program. Nothing was missing and no join failed: the input was simply not about the school.", "",
         "**Now:**", "", "| Input | Source file | Seasons | Missing data |", "|---|---|---|---|",
         f"| Current strength: the scoreboard fit's o + d per season (log runs; `scripts/build_phase2_teams.fit`, no parks), recency half-life {rc.OMAHA_HALF_LIFE} seasons | "
         "`data/ncaa_<year>/scoreboard/games_<year>.csv` (data.ncaa.com) | 2021-2025 | seasons without data skipped (not zero); confidence B with 3+ seasons, C with 1-2, D with none |",
         f"| Recent Omaha appearances (+ {rc.OMAHA_POST_WEIGHT} per weighted appearance) and super regionals (half that) | `data/ncaa_brackets/` | 2021-2025 | a year a school is absent is a year it did not make it |", "",
         "The dynasty regrades with the same function: `config.report_cards.omaha_score(strength, omaha_recent, super_recent)` and `grade_values` "
         "(the UI passes its dynasty's own team strength and postseason history).", "",
         "## Name joins", "",
         "One shared alias table for every source: `data/schools/name_aliases.csv`. Joins fixed on 2026-10-09 (they had silently dropped data):", "",
         "| Spelling in the source | School | Effect before the fix |", "|---|---|---|",
         "| New Orleans (scoreboards) | LSU New Orleans | every season 2021-2025 missing (win pct imputed at the median, out of its conference's RPI) |",
         "| Fairleigh Dickinson (scoreboards) | FDU | 2021-2022 missing |", "| Houston Baptist (scoreboards) | Houston Christian | 2021-2022 missing |",
         "| Dixie St. (scoreboards) | Utah Tech | 2021-2022 missing |", "",
         "Bracket spellings already handled by the old alias list (Lamar, Long Island, Northern Illinois, Saint Mary's) moved into the same table. "
         "Bracket teams not among the 307 programs: Hartford (left D1).", "",
         "## Coverage (strength and RPI seasons found, of 5)", "",
         "| School | Strength seasons | RPI seasons | Status | Omaha / supers 2021-25 | Confidence |", "|---|---|---|---|---|---|"]
    row = lambda t: (f"| {t} | {cov.strength_seasons[t]} | {cov.rpi_seasons[t]} | {status(cov.strength_seasons[t], len(yrs))} | "  # noqa: E731
                     f"{int(o.n_omaha_recent[t])} / {int(o.n_super_recent[t])} | {o.omaha_contender_confidence[t]} |")
    ex = [e for e in EXAMPLES if e in o.index]
    L += [row(t) for t in ex]
    part = [t for t in o.index if t not in ex and cov.strength_seasons[t] < len(yrs)]
    L += ["", f"Every other school with any missing or partial season ({len(part)}; the rest of the 307 have all five):", "",
          "| School | Strength seasons | RPI seasons | Status | Omaha / supers 2021-25 | Confidence |", "|---|---|---|---|---|---|"]
    L += [row(t) for t in sorted(part)]
    L += ["", "Why they are partial: the Ivy League and Bethune-Cookman did not play in 2021; the others joined Division I after 2021 "
          "(their earlier seasons were not D1 games). LSU New Orleans now has all five.", "",
          "## Coastal Carolina and LSU, before and after", "",
          "| School | Before: sim draw o + d | Before grade | Real strength 2021-25 (per season) | Weighted | Omaha / supers 2021-25 | Score | After grade |",
          "|---|---|---|---|---|---|---|---|"]
    for t in ("Coastal Carolina", "LSU"):
        per = ", ".join(f"{y}: {S[y][t]:+.2f}" for y in yrs if t in S[y])
        L.append(f"| {t} | {o.sim_strength_o_plus_d[t]:+.2f} | {before[t]} | {per} | {o.strength_recent[t]:+.3f} | {int(o.n_omaha_recent[t])} / "
                 f"{int(o.n_super_recent[t])} | {o.omaha_contender_raw[t]:+.3f} | {o.omaha_contender_grade[t]} |")
    om = o[o.n_omaha_recent > 0].sort_values("omaha_contender_raw", ascending=False)
    L += ["", f"Sanity anchor: every 2021-2025 Omaha team ({len(om)}), its grade (target B+ or better unless its strength collapsed):", "",
          ", ".join(f"{t} {o.omaha_contender_grade[t]}" for t in om.index) + ".", "",
          "## Climate and Academic Prestige: absolute scales", "",
          "| Category | " + " | ".join(rc.GRADES) + " |", "|---|" + "---|" * len(rc.GRADES)]
    for cat in ("climate", "academic_prestige"):
        vc = o[f"{cat}_grade"].value_counts()
        L.append(f"| {cat.replace('_', ' ').title()} | " + " | ".join(str(int(vc.get(g, 0))) for g in rc.GRADES) + " |")
    for cat, lab in (("academic_prestige", "Academic Prestige"), ("climate", "Climate")):
        a = o[o[f"{cat}_grade"] == "A+"].sort_values(f"{cat}_score", ascending=False)
        L += ["", f"A+ in {lab} ({len(a)}): " + ", ".join(a.index) + "."]
    L += ["", f"Climate score = min(Feb-May mean daily high, {rc.CLIMATE_WARM_CAP_F:.0f} °F) - {rc.CLIMATE_RAIN_F_PER_DAY} °F x rain days; cutoffs "
          + ", ".join(f"{g} ≥ {c}" for c, g in rc.CLIMATE_CUTOFFS) + ", else F.",
          "Academic: admission rate sets the grade (" + ", ".join(f"≤{c}% {g}" for c, g in rc.ACADEMIC_ADMIT_CUTOFFS) + "), graduation rate caps it ("
          + ", ".join(f"below {c}%: at most {g}" for c, g in rc.ACADEMIC_GRAD_CAPS if c) + "). The service academies report admission and "
          "graduation to IPEDS like any school (Navy 9% / 92%, Army 14% / 85%, Air Force 14% / 88%): no override needed."]
    (ROOT / "reports/report_cards_audit.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
