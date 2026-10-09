"""School locations of the D1 baseball programs, from the IPEDS institutional directory (public domain, U.S. Department of
Education, NCES; owner approval 2026-10-08), for the Proximity test of the Phase 9 spec (design/phase9_recruiting.md).

Input:  data/ipeds/HD2024.zip (IPEDS HD2024, https://nces.ed.gov/ipeds/datacenter/data/HD2024.zip, fetched 2026-10-08;
        robots.txt allows the path) and data/ncaa_2025/ncaa_d1_teams_2025.csv (NCAA team names).
Output: data/ncaa_2025/school_locations_2025.csv: ncaa_team_id, team, unitid, instnm, city, state, latitude, longitude, match.

Matching: the NCAA short name is expanded (St. -> State, Ark. -> Arkansas, ...) and matched to the closest four-year
degree-granting institution name or alias. Short names that match the wrong school (a flagship campus, a same-name school
in another state, an academy) are resolved by OVERRIDES: a name fragment plus the state, which must identify exactly one
institution. Every match is then checked against the school's most common hometown state in the roster aggregates; the
script fails on any disagreement not listed in STATE_CHECK_EXCEPTIONS (border schools whose rosters lean to a neighbour).
    python3 scripts/build_school_locations.py
"""
from __future__ import annotations

import difflib
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HD = ROOT / "data/ipeds/HD2024.zip"
TEAMS = ROOT / "data/ncaa_2025/ncaa_d1_teams_2025.csv"
HOMETOWN = ROOT / "data/ncaa_2025/roster_aggregates/hometown_by_school.csv"
OUT = ROOT / "data/ncaa_2025/school_locations_2025.csv"

EXPAND = [(r"\bSt\.", "State"), (r"\bSo\.", "Southern"), (r"\bMich\.", "Michigan"), (r"\bConn\.", "Connecticut"), (r"\bArk\.", "Arkansas"),
          (r"\bFla\.", "Florida"), (r"\bGa\.", "Georgia"), (r"\bKy\.", "Kentucky"), (r"\bIll\.", "Illinois"), (r"\bCol\.", "College"),
          (r"\bU\.", "University"), (r"\bTenn\.", "Tennessee"), (r"\bMiss\.", "Mississippi"), (r"\bLa\.", "Louisiana"), (r"\bAla\.", "Alabama"),
          (r"\bWash\.", "Washington"), (r"\bCaro\.", "Carolina"), (r"\bN\.C\.", "North Carolina"), (r"\bOkla\.", "Oklahoma"), (r"\bTex\.", "Texas"),
          (r"\bMo\.", "Missouri"), (r"\bColo\.", "Colorado"), (r"\bInd\.", "Indiana"), (r"\bVal\.", "Valley")]

# NCAA team name -> (fragment of the IPEDS institution name, or "=" + the exact name, state): must identify exactly one institution
OVERRIDES = {
    # 2026-10-08: two name matches found wrong against EADA's Division I list (Florida College, North Florida College)
    "Florida": ("=University of Florida", "FL"), "North Florida": ("=University of North Florida", "FL"),
    "Alcorn": ("Alcorn State", "MS"), "Missouri": ("University of Missouri-Columbia", "MO"), "Air Force": ("Air Force Academy", "CO"),
    "Hawaii": ("University of Hawaii at Manoa", "HI"), "The Citadel": ("Citadel", "SC"), "LMU (CA)": ("Loyola Marymount", "CA"),
    "Milwaukee": ("=University of Wisconsin-Milwaukee", "WI"), "Pittsburgh": ("University of Pittsburgh-Pittsburgh", "PA"),
    "Nebraska": ("University of Nebraska-Lincoln", "NE"), "Indiana": ("Indiana University-Bloomington", "IN"),
    "Minnesota": ("University of Minnesota-Twin Cities", "MN"), "St. Thomas (MN)": ("University of St Thomas", "MN"),
    "St. John's (NY)": ("St. John's University-New York", "NY"), "LIU": ("Long Island University", "NY"),
    "Fresno St.": ("California State University-Fresno", "CA"), "UConn": ("=University of Connecticut", "CT"),
    "Missouri St.": ("Missouri State University-Springfield", "MO"), "Louisiana": ("University of Louisiana at Lafayette", "LA"),
    "USC Upstate": ("University of South Carolina-Upstate", "SC"), "Tennessee": ("The University of Tennessee-Knoxville", "TN"),
    "Massachusetts": ("University of Massachusetts-Amherst", "MA"), "North Carolina": ("University of North Carolina at Chapel Hill", "NC"),
    "Queens (NC)": ("Queens University of Charlotte", "NC"), "Southern U.": ("Southern University and A & M College", "LA"),
    "Penn St.": ("Pennsylvania State University-Main Campus", "PA"), "Arizona St.": ("Arizona State University Campus Immersion", "AZ"),
    "Long Beach St.": ("California State University-Long Beach", "CA"), "Bowling Green": ("Bowling Green State University-Main Campus", "OH"),
    "Sam Houston": ("Sam Houston State University", "TX"), "South Carolina": ("University of South Carolina-Columbia", "SC"),
    "UNC Greensboro": ("University of North Carolina at Greensboro", "NC"), "Mississippi Val.": ("Mississippi Valley State", "MS"),
    "NIU": ("Northern Illinois University", "IL"), "FGCU": ("Florida Gulf Coast University", "FL"), "Kent St.": ("Kent State University at Kent", "OH"),
    "UC San Diego": ("University of California-San Diego", "CA"), "App State": ("Appalachian State University", "NC"),
    "Southern Ill.": ("Southern Illinois University-Carbondale", "IL"), "Saint Mary's (CA)": ("Saint Mary's College of California", "CA"),
    "Nicholls": ("Nicholls State University", "LA"), "Boston College": ("Boston College", "MA"),
    "Illinois": ("University of Illinois Urbana-Champaign", "IL"), "Georgetown": ("Georgetown University", "DC"),
    "Northwestern": ("Northwestern University", "IL"), "Notre Dame": ("University of Notre Dame", "IN"), "Murray St.": ("Murray State University", "KY"),
    "Pacific": ("University of the Pacific", "CA"), "Rutgers": ("Rutgers University-New Brunswick", "NJ"),
    "Saint Joseph's": ("=Saint Joseph's University - Philadelphia", "PA"), "Texas": ("The University of Texas at Austin", "TX"),
    "Col. of Charleston": ("College of Charleston", "SC"), "Columbia": ("Columbia University in the City of New York", "NY"),
    "California": ("University of California-Berkeley", "CA"), "Washington": ("University of Washington-Seattle", "WA"),
    "Nevada": ("University of Nevada-Reno", "NV"), "UMass Lowell": ("University of Massachusetts-Lowell", "MA"),
    "Maryland": ("University of Maryland-College Park", "MD"), "Miami (FL)": ("University of Miami", "FL"),
    "LSU New Orleans": ("University of New Orleans", "LA"), "Prairie View": ("Prairie View A & M University", "TX"),
    "A&M-Corpus Christi": ("Texas A & M University-Corpus Christi", "TX"), "Army West Point": ("United States Military Academy", "NY"),
    "Austin Peay": ("Austin Peay State University", "TN"), "Charlotte": ("University of North Carolina at Charlotte", "NC"),
    "Little Rock": ("University of Arkansas at Little Rock", "AR"), "Miami (OH)": ("Miami University-Oxford", "OH"),
    "Michigan": ("University of Michigan-Ann Arbor", "MI"), "Middle Tenn.": ("Middle Tennessee State University", "TN"),
    "N.C. A&T": ("North Carolina A & T State University", "NC"), "Omaha": ("University of Nebraska at Omaha", "NE"),
    "UC Irvine": ("University of California-Irvine", "CA"), "UC Santa Barbara": ("University of California-Santa Barbara", "CA"),
    "Cornell": ("=Cornell University", "NY"), "San Francisco": ("=University of San Francisco", "CA"),
    "Holy Cross": ("College of the Holy Cross", "MA"), "Monmouth": ("Monmouth University", "NJ"), "Washington St.": ("Washington State University", "WA"),
}
# schools whose most common roster hometown state is not their own: each institution checked by hand (2026-10-08) and right;
# their rosters lean to a neighbour or recruit nationally (academies, Ivies, border schools). Listed so the check stays strict.
STATE_CHECK_EXCEPTIONS = ('Air Force', 'Alabama St.', 'Alcorn', 'Army West Point', 'Charleston So.', 'Coastal Carolina', 'Columbia', 'Coppin St.', 'Dartmouth', 'Dayton', 'East Carolina', 'Eastern Mich.', 'Elon', 'Evansville', 'Fairfield', 'Fordham', 'Gardner-Webb', 'Georgetown', 'Grambling', 'Harvard', 'Hawaii', 'Jackson St.', 'Kansas', 'Kansas St.', 'Lafayette', 'Louisville', 'Manhattan', 'Marshall', 'Murray St.', 'Navy', 'Nevada', 'New Mexico St.', 'North Dakota St.', 'Northern Ky.', 'Oklahoma', 'Oregon', 'Penn', 'Portland', 'Presbyterian', 'Princeton', 'Richmond', 'South Dakota St.', 'Tulane', 'USC Upstate', 'Utah', 'Utah Valley', 'Valparaiso', 'Villanova', 'West Virginia', 'Wichita St.', 'Wofford')


def norm(s: str) -> str:
    s = s.lower().replace("&", " and ").replace("-", " ")
    s = re.sub(r"[^a-z ]", " ", s)
    for w in ("the", "of", "university", "college", "main campus", "campus", "at"):
        s = re.sub(rf"\b{w}\b", " ", s)
    return " ".join(s.split())


def load_hd() -> pd.DataFrame:
    with zipfile.ZipFile(HD) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(name) as fh:
            d = pd.read_csv(fh, encoding="latin1", low_memory=False)
    d.columns = [c.replace("﻿", "").replace("ï»¿", "") for c in d.columns]
    return d[(d.ICLEVEL == 1) & (d.DEGGRANT == 1)].copy()


def main() -> None:
    d = load_hd()
    teams = pd.read_csv(TEAMS)
    names = {}
    for i, n, a in zip(d.index, d.INSTNM, d.IALIAS.fillna("")):
        names.setdefault(norm(n), i)
        for part in re.split(r"[|,;]", a):
            if part.strip():
                names.setdefault(norm(part), i)
    keys = list(names)
    rows, bad = [], []
    for tid, team in zip(teams.ncaa_team_id, teams.team):
        if team in OVERRIDES:
            frag, st = OVERRIDES[team]
            exact = frag.startswith("=")
            m = d[((d.INSTNM == frag[1:]) if exact else d.INSTNM.str.contains(frag, regex=False)) & (d.STABBR == st)]
            if len(m) != 1:
                bad.append(f"{team}: override '{frag}' ({st}) matches {len(m)} institutions: {list(m.INSTNM)[:4]}")
                continue
            r, how = m.iloc[0], "override"
        else:
            s = team
            for pat, rep in EXPAND:
                s = re.sub(pat, rep, s)
            n = norm(s)
            best = difflib.get_close_matches(n, keys, n=1, cutoff=0.0)[0]
            score = difflib.SequenceMatcher(None, n, best).ratio()
            if score < 0.9:
                bad.append(f"{team}: best automatic match '{d.loc[names[best]].INSTNM}' scores {score:.2f}; add an override")
                continue
            r, how = d.loc[names[best]], "name"
        rows.append({"ncaa_team_id": tid, "team": team, "unitid": int(r.UNITID), "instnm": r.INSTNM, "city": r.CITY, "state": r.STABBR,
                     "latitude": float(r.LATITUDE), "longitude": float(r.LONGITUD), "match": how})
    if bad:
        sys.exit("unmatched:\n  " + "\n  ".join(bad))
    out = pd.DataFrame(rows)
    # check: the school's state against its most common roster hometown state
    h = pd.read_csv(HOMETOWN)
    us = h[h.area_type == "us_state"]
    modal = us.sort_values("count", ascending=False).groupby("team_ncaa_id").head(1).set_index("team_ncaa_id").hometown_area
    chk = out.assign(modal=out.ncaa_team_id.map(modal))
    off = chk[chk.modal.notna() & (chk.modal != chk.state) & ~chk.team.isin(STATE_CHECK_EXCEPTIONS)]
    print(f"{len(out)} teams located ({(out.match == 'override').sum()} by override); state check on {chk.modal.notna().sum()} with roster data: "
          f"{len(off)} disagree")
    if len(off):
        print(off[["team", "instnm", "state", "modal"]].to_string())
    if out.unitid.duplicated().any():
        sys.exit(f"one institution matched twice: {list(out[out.unitid.duplicated(keep=False)].team)}")
    out.to_csv(OUT, index=False)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
