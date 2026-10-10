#!/usr/bin/env python3
"""Recruit rankings -> outcomes, from the MLB Stats API draft feeds.

Sources (all fetched 2026-10-10 with curl, browser UA):
  https://statsapi.mlb.com/api/v1/draft/prospects/<year>   MLB Pipeline's draft prospect
        registry for that draft: every draft-eligible player MLB tracked, with the
        Pipeline rank (1-200; 1-250 from 2025) on the ranked ones, school, schoolClass
        ("HS SR", "4YR JR", ...; absent in 2019) and the Pipeline scouting blurb, which
        for high schoolers names the college commitment.
  https://statsapi.mlb.com/api/v1/draft/<year>             the draft itself: every pick with
        person.id, school, schoolClass (absent in 2019), pickRound, pickNumber,
        signingBonus (missing or "0" when unsigned).

What the ranking is: MLB Pipeline's DRAFT ranking in the player's HS senior year, HS and
college prospects on one list.  It is not a recruiting ranking made two years earlier,
and it ignores signability ("When we do our Draft rankings, we do it based only on
perceived talent and upside. Signability ... doesn't enter into the equation", Jonathan
Mayo, MLB Pipeline Inbox, 2025-04-25).

Matching: by MLB person.id between the prospect registry and later draft feeds (the id
is the player's permanent MLB id; checked on known cases), with a normalized-name
fallback.  Names are used only inside this script; the CSV carries counts only.

Usage (repo tool, Phase 9 yardstick, 2026-10-10):
    python tools/build_recruit_outcomes.py --work /path/outside/the/repo            # fetch the feeds, then build
    python tools/build_recruit_outcomes.py --work /path/outside/the/repo --no-fetch
Writes data/recruiting/recruit_outcomes.csv (counts only; HS classes 2019-2024 by MLB Pipeline rank band:
commitment tier, drafted and signed out of high school by round band, reached campus, drafted from
college two to four years later). The raw feeds (names, blurbs) stay in the working directory. An optional
hand-saved text of Baseball America's 2018 HS Top 100 (raw/ba_hs100_2018.txt) adds a recruiting-style list
when present. Research notes: PHASE8_NOTES.md section 11; reports/phase8_11_yardstick.md section 12.
"""
import csv, json, re, sys, unicodedata
from collections import Counter, defaultdict

import argparse, os, time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ap = argparse.ArgumentParser(description="recruit rankings -> outcomes from the MLB Stats API feeds")
_ap.add_argument("--work", required=True, help="working directory for the raw feeds (outside the repository)")
_ap.add_argument("--schools", default=str(_ROOT / "data/schools/schools.csv"))
_ap.add_argument("--out", default=str(_ROOT / "data/recruiting/recruit_outcomes.csv"))
_ap.add_argument("--no-fetch", action="store_true")
_args = _ap.parse_args()
_work = Path(_args.work).resolve()
if _ROOT in _work.parents or _work == _ROOT:
    _ap.error("--work must be outside the repository (the feeds carry names)")
RAW = str(_work / "raw")
os.makedirs(RAW, exist_ok=True)
Path(_args.out).parent.mkdir(parents=True, exist_ok=True)
if not _args.no_fetch:
    import requests
    _H = {"User-Agent": "Mozilla/5.0 (compatible; college-baseball-sim data pull; github.com/jadams-24/College-Baseball-Sim)"}
    for _y in range(2018, 2027):
        for _name, _url in ((f"draft_{_y}.json", f"https://statsapi.mlb.com/api/v1/draft/{_y}"),
                            (f"prospects_api_{_y}.json", f"https://statsapi.mlb.com/api/v1/draft/prospects/{_y}")):
            _p = Path(RAW) / _name
            if _p.exists():
                continue
            _r = requests.get(_url, headers=_H, timeout=120)
            _r.raise_for_status()
            _p.write_text(_r.text)
            print(f"fetched {_name} ({len(_r.text)} bytes)", file=sys.stderr)
            time.sleep(1)
SCHOOLS_CSV, OUT_CSV = _args.schools, _args.out
CLASSES = range(2019, 2025)          # HS classes 2019-2024 (draft year = class year)
DRAFTS = range(2018, 2027)            # draft feeds on disk (2018 for the BA list below)
OVERALL_BANDS = [(1, 25, "top25"), (26, 100, "26-100"), (101, 200, "101-200")]
HS_BANDS = [(1, 10, "hs1-10"), (11, 25, "hs11-25"), (26, 50, "hs26-50"), (51, 999, "hs51+")]

# ---------------------------------------------------------------- schools / tiers
def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ").replace("st.", "state").replace("saint", "st")
    s = re.sub(r"\b(the|university|univ|of|college|at)\b", " ", s)
    return re.sub(r"[^a-z]", "", s)

def norm_name(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", s)
    return re.sub(r"[^a-z]", "", s)

schools = {}            # norm -> (school, tier)
tier_of = {}
for r in csv.DictReader(open(SCHOOLS_CSV)):
    schools[norm(r["school"])] = (r["school"], r["tier"])
    tier_of[r["school"]] = r["tier"]

# Blurb / draft-feed spellings -> schools.csv spelling.  Hand-built from the unmatched list.
ALIASES = {
    "Louisiana State": "LSU", "Louisiana-Lafayette": "Louisiana", "Louisiana Lafayette": "Louisiana",
    "Southern Cal": "Southern California", "USC": "Southern California", "UNC": "North Carolina",
    "Mississippi": "Ole Miss", "Miami": "Miami (FL)", "Miami (Fla.)": "Miami (FL)",
    "Florida State": "Florida St.", "Oregon State": "Oregon St.", "Oklahoma State": "Oklahoma St.",
    "Mississippi State": "Mississippi St.", "Arizona State": "Arizona St.", "Ohio State": "Ohio St.",
    "Kansas State": "Kansas St.", "Michigan State": "Michigan St.", "Penn State": "Penn St.",
    "Washington State": "Washington St.", "Texas State": "Texas St.", "Georgia State": "Georgia St.",
    "Fresno State": "Fresno St.", "San Diego State": "San Diego St.", "Long Beach State": "Long Beach St.",
    "Wichita State": "Wichita St.", "Missouri State": "Missouri St.", "Illinois State": "Illinois St.",
    "Indiana State": "Indiana St.", "Arkansas State": "Arkansas St.", "Ball State": "Ball St.",
    "Boise State": "Boise State", "Kennesaw State": "Kennesaw St.", "Jacksonville State": "Jacksonville St.",
    "New Mexico State": "New Mexico St.", "Sacramento State": "Sacramento St.", "San Jose State": "San Jose St.",
    "Tarleton State": "Tarleton St.", "Utah State": "Utah State", "Sam Houston State": "Sam Houston",
    "Cal State Fullerton": "Cal St. Fullerton", "Cal State Northridge": "CSUN",
    "Dallas Baptist": "DBU", "Central Florida": "UCF", "UCF": "UCF", "South Florida": "South Fla.",
    "Florida Atlantic": "Fla. Atlantic", "Florida Gulf Coast": "FGCU", "Florida International": "FIU",
    "North Carolina State": "NC State", "N.C. State": "NC State", "Appalachian State": "App State",
    "Southern Miss": "Southern Miss.", "Southern Mississippi": "Southern Miss.",
    "Middle Tennessee": "Middle Tenn.", "Middle Tennessee State": "Middle Tenn.",
    "Western Kentucky": "Western Ky.", "Eastern Kentucky": "Eastern Ky.", "Northern Kentucky": "Northern Ky.",
    "Georgia Southern": "Ga. Southern", "East Tennessee State": "ETSU", "Tennessee-Martin": "UT Martin",
    "Connecticut": "UConn", "UNC Wilmington": "UNCW", "UNC-Wilmington": "UNCW", "Charleston": "Col. of Charleston",
    "College of Charleston": "Col. of Charleston", "Texas-Arlington": "UT Arlington", "UT-Arlington": "UT Arlington",
    "Texas-San Antonio": "UTSA", "Alabama-Birmingham": "UAB", "Stephen F. Austin": "SFA",
    "Loyola Marymount": "LMU (CA)", "Saint Mary's": "Saint Mary's (CA)", "St. Mary's": "Saint Mary's (CA)",
    "St. John's": "St. John's (NY)", "Cal State Bakersfield": "CSU Bakersfield", "Seattle": "Seattle U",
    "Army": "Army West Point", "Texas A&M-Corpus Christi": "A&M-Corpus Christi",
    "Nebraska-Omaha": "Omaha", "Albany": "UAlbany", "Long Island": "LIU", "Northern Illinois": "NIU",
    "Lamar": "Lamar University", "Houston Baptist": "Houston Christian", "Dixie State": "Utah Tech",
    "Incarnate Word": "UIW", "Louisiana-Monroe": "ULM", "Southeastern Louisiana": "Southeastern La.",
    "Northwestern State": "Northwestern St.", "Central Arkansas": "Central Ark.", "Southern Illinois": "Southern Ill.",
    "Western Carolina": "Western Caro.", "Virginia Commonwealth": "VCU", "Massachusetts-Lowell": "UMass Lowell",
    "UC-Irvine": "UC Irvine", "UC-Santa Barbara": "UC Santa Barbara", "UC-San Diego": "UC San Diego",
    "UC-Davis": "UC Davis", "UC-Riverside": "UC Riverside", "Georgia Tech": "Georgia Tech",
    "Pitt": "Pittsburgh", "Michigan St": "Michigan St.", "Texas Christian": "TCU", "Brigham Young": "BYU",
    "Texas A&M": "Texas A&M", "Texas A & M": "Texas A&M", "Texas AandM": "Texas A&M",
    "Virginia Military Institute": "VMI", "Nevada-Las Vegas": "UNLV", "The Citadel": "The Citadel",
    "Cal Poly San Luis Obispo": "Cal Poly", "Cal Poly-San Luis Obispo": "Cal Poly",
    "North Carolina-Charlotte": "Charlotte", "Mount St. Mary's": "Mount St. Mary's",
    "Southeast Missouri State": "Southeast Mo. St.", "Southeast Missouri": "Southeast Mo. St.",
    "Eastern Illinois": "Eastern Ill.", "Western Illinois": "Western Ill.", "Central Michigan": "Central Mich.",
    "Eastern Michigan": "Eastern Mich.", "Western Michigan": "Western Mich.", "Northern Colorado": "Northern Colo.",
    "Texas Rio Grande Valley": "UTRGV", "Maryland-Baltimore County": "UMBC", "Maryland Eastern Shore": "UMES",
    "North Carolina A&T": "N.C. A&T", "Southern": "Southern U.", "Southern University": "Southern U.",
    "Mississippi Valley State": "Mississippi Val.", "Alabama State": "Alabama St.", "Jackson State": "Jackson St.",
    "Prairie View A&M": "Prairie View", "Purdue-Fort Wayne": "Purdue Fort Wayne", "SIU-Edwardsville": "SIUE",
    "Southern Indiana": "Southern Ind.", "North Alabama": "North Ala.", "West Georgia": "West Ga.",
    "Charleston Southern": "Charleston So.", "Fairleigh Dickinson": "FDU", "New Orleans": "LSU New Orleans",
    "Grand Canyon": "Grand Canyon", "Cal Baptist": "California Baptist", "UMass": "Massachusetts",
    "Southeastern": "Southeastern La.", "North Dakota State": "North Dakota St.", "South Dakota State": "South Dakota St.",
    "Youngstown State": "Youngstown St.", "Wright State": "Wright St.", "Morehead State": "Morehead St.",
    "Murray State": "Murray St.", "Delaware State": "Delaware St.", "Coppin State": "Coppin St.",
    "Norfolk State": "Norfolk St.", "Alcorn State": "Alcorn", "Texas-Rio Grande Valley": "UTRGV",
    "St. Thomas": "St. Thomas (MN)", "Loyola Marymount University": "LMU (CA)", "Queens": "Queens (NC)",
    "Hawaii": "Hawaii", "Central Connecticut State": "Central Conn. St.", "Central Connecticut": "Central Conn. St.",
    # nicknames and places the blurbs use for a commitment ("away from the Rebels", "heading to Baton Rouge")
    "Miss. State": "Mississippi St.", "FSU": "Florida St.", "Rebels": "Ole Miss", "Commodores": "Vanderbilt", "Gators": "Florida", "Florida Gators": "Florida",
    "Longhorns": "Texas", "Seminoles": "Florida St.", "Volunteers": "Tennessee", "Vols": "Tennessee",
    "Razorbacks": "Arkansas", "Sooners": "Oklahoma", "Beavers": "Oregon St.", "Ducks": "Oregon", "Bruins": "UCLA",
    "Trojans": "Southern California", "Hurricanes": "Miami (FL)", "Gamecocks": "South Carolina",
    "Tar Heels": "North Carolina", "Wolfpack": "NC State", "Blue Devils": "Duke", "Cavaliers": "Virginia",
    "Hokies": "Virginia Tech", "Hoosiers": "Indiana", "Wolverines": "Michigan", "Buckeyes": "Ohio St.",
    "Horned Frogs": "TCU", "Red Raiders": "Texas Tech", "Sun Devils": "Arizona St.", "Jayhawks": "Kansas",
    "Cornhuskers": "Nebraska", "Huskers": "Nebraska", "Fighting Irish": "Notre Dame", "Crimson Tide": "Alabama",
    "Yellow Jackets": "Georgia Tech", "Demon Deacons": "Wake Forest", "Mountaineers": "West Virginia",
    "Boilermakers": "Purdue", "Baton Rouge": "LSU", "Starkville": "Mississippi St.", "Oxford": "Ole Miss",
    "Chapel Hill": "North Carolina", "Tuscaloosa": "Alabama", "Fayetteville": "Arkansas", "Knoxville": "Tennessee",
    "Gainesville": "Florida", "Tallahassee": "Florida St.", "Westwood": "UCLA", "Corvallis": "Oregon St.",
    "Golden Bears": "California", "Cardinal": "Stanford", "Dons": "San Francisco", "Owls": "Rice",
    "Shockers": "Wichita St.", "Cougars": "Houston", "Zags": "Gonzaga", "Pirates": "East Carolina",
}
# Non-D1 destinations named in blurbs (D2, NAIA, JUCO), kept out of the D1 join.
NON_D1 = ["juco", "junior college", "community college", "cc", "jc", "state college of florida",
          "san jacinto", "chipola", "mclennan", "wabash valley", "iowa western", "cowley", "blinn",
          "cisco", "grayson", "weatherford", "walters state", "navarro", "northwest florida",
          "crowder", "johnson county", "tampa", "nova southeastern", "point loma", "azusa pacific",
          "central missouri", "west florida", "colorado mesa", "lubbock christian", "boise state",
          "utah state", "colorado state", "wyoming", "idaho", "montana"]

ALIAS_N = {norm(k): v for k, v in ALIASES.items()}

def school_lookup(name):
    """Return (schools.csv name, tier) or (None, 'other') for a D1-looking name, or (None, None) if unknown."""
    if not name:
        return None, None
    n = norm(name)
    if n in ALIAS_N:
        s = ALIAS_N[n]
        return s, tier_of.get(s, "other")
    if n in schools:
        return schools[n]
    # draft-feed forms like "University of Memphis", "Vanderbilt University", "Florida International University"
    n2 = norm(re.sub(r"(?i)\b(university|college)\b", " ", name))
    if n2 in ALIAS_N:
        s = ALIAS_N[n2]
        return s, tier_of.get(s, "other")
    if n2 in schools:
        return schools[n2]
    return None, None

# ---------------------------------------------------------------- blurb commitment
# Vocabulary: every schools.csv name, every alias key, "University of X" forms, and non-D1 forms
# (junior colleges, D2) so that "South Florida State College" is not read as "Florida State".
NON_D1_VOCAB = ["San Jacinto Junior College", "San Jacinto College", "San Jacinto", "South Florida State College",
                "State College of Florida", "Gulf Coast State", "Chipola", "McLennan", "Wabash Valley", "Iowa Western",
                "Cowley", "Blinn", "Cisco", "Grayson", "Weatherford", "Walters State", "Navarro", "Northwest Florida State",
                "Crowder", "Johnson County", "Meridian", "Central Arizona", "Yavapai", "Hutchinson", "Seminole State",
                "Santa Fe College", "Florida SouthWestern", "Polk State", "Odessa", "Howard College",
                "Pearl River", "Jones College", "Hinds", "Tallahassee CC", "Tallahassee Community College", "Northwest Mississippi", "Shelton State", "Wallace State",
                "Tampa", "Nova Southeastern", "Point Loma", "Azusa Pacific", "Central Missouri", "West Florida",
                "Colorado Mesa", "Lubbock Christian", "Boise State", "Utah State", "Colorado State", "Wyoming",
                "Division II", "D-II", "NAIA", "junior college", "Junior College", "Community College", "JC", "CC", "J.C."]
VOCAB = sorted(set(list(ALIASES) + [s for s, _ in schools.values()]
                   + ["University of " + s for s, _ in schools.values()] + NON_D1_VOCAB), key=len, reverse=True)
BAD = {"Pacific", "Southern", "Charleston", "Portland", "Richmond", "Maine", "Liberty", "Rice", "Brown", "Navy", "Army",
       "Ohio", "Houston", "Memphis", "Omaha", "Dayton", "Akron", "Toledo", "Troy", "Butler", "Mercer", "Elon", "Siena",
       "Iona", "Rider", "Wagner", "Oakland", "Hawaii", "Nevada", "Utah", "Delaware", "Louisiana"}
# ambiguous city/state words stay in only when followed by a recruiting word (handled by the strong patterns)
VOCAB = [v for v in VOCAB if (len(v) >= 4 or v.isupper())]
ALT = "|".join(re.escape(v) for v in VOCAB)
V = r"(?<![A-Za-z])(" + ALT + r")(?![a-z])"
JUCO_STRONG = re.compile(r"(?i)(?:committed to|commitment to|headed to|heading to|head to|signed with|commit to|attend|enroll at) "
                         r"((?:[A-Z][\w.'-]+ ){1,4}(?:Junior College|Community College|State College|JC|CC|J\.C\.))")
STRONG = [re.compile(x) for x in (
    r"(?i:(?:flipp\w*|switch\w*|chang\w*|re-?commit\w*|decommit\w*)[^.]{0,70}?\bto (?:the )?(?:University of )?)" + V,
    r"(?i:(?:committed|commitment|commits|commit|pledged|pledge|signee|signed|ticket|ticketed|headed|heading|head|go|going|bound|enroll|enrolling|attend|attending|play|playing|pitch|pitching|suit up|verbal|verbally|home|scholarship|offer) (?:early |on )?(?:to |with |for |at |in )(?:the |a |an )?(?:University of )?)" + V,
    V + r"(?:'s)? (?i:commit|commitment|recruit|signee|pledge|verbal|scholarship|signing|recruiting class)",
    r"(?i:(?:away|him|them|player|prospect|loose|free) from (?:his |a |the |an |that )?(?:strong |firm )?(?:commitment to |scholarship to |playing for |playing at |pitching for |pitching at |a spot at |heading to |going to )?(?:the )?(?:University of )?)" + V,
    r"(?i:(?:recruiting class|incoming class|signing class|haul) (?:for|at|of) (?:the )?)" + V,
    V + r"(?i:(?:'s)? (?:recruiting class|incoming class|signing class|haul|coaching staff|program|campus))",
)]
VOCAB_RE = re.compile(V)
KEY_RE = re.compile(r"(?i)(commit\w*|recruit\w*|signee|pledge\w*|scholarship|away from|headed to|heading to|bound for|"
                    r"signed with|letter of intent|ticket to|ticketed|verbal\w*|flipp\w*|switched to|decommit\w*|"
                    r"(?:lure|pry|steer|divert|sign|buy|keep)\w* (?:him|them)? ?(?:out|away|off)|from his)")
UNCOMMITTED_RE = re.compile(r"(?i)\b(uncommitted|not committed|no college commitment|without a college|"
                            r"hasn't committed|has not committed|yet to commit|no commitment|doesn't have a college|"
                            r"no school|without a commitment)")
NON_D1_RE = re.compile(r"(?i)\b(junior college|community college|JC|CC|J\.C\.|JUCO|Division II|D-II|NAIA)\b")

def _classify(sch):
    return "non-D1" if (sch in NON_D1_VOCAB or NON_D1_RE.search(sch)) else "D1"

def extract_commit(blurb):
    """-> (school string as written, status); status in {'strong','weak','uncommitted','none'}"""
    if not blurb:
        return None, "none"
    if UNCOMMITTED_RE.search(blurb):
        return None, "uncommitted"
    m = JUCO_STRONG.search(blurb)
    if m:
        return m.group(1), "strong"
    for pat in STRONG:
        hits = [m for m in pat.finditer(blurb)]
        if hits:
            # a pattern that catches a flip returns the new school; otherwise the first hit
            sch = hits[0].group(1)
            # a bare ambiguous word only counts in the strong patterns (it did), but skip pure state names
            return sch, "strong"
    keys = [m for m in KEY_RE.finditer(blurb)]
    mentions = [(m.start(), m.group(1)) for m in VOCAB_RE.finditer(blurb) if m.group(1) not in BAD]
    if not mentions or not keys:
        return None, "none"
    cands = sorted((min(abs(pos - k.start()) for k in keys), pos, sch) for pos, sch in mentions)
    if cands and cands[0][0] <= 60:
        return cands[0][2], "weak"
    return None, "none"

# ---------------------------------------------------------------- HS flag
HS_NAME_RE = re.compile(r"(?i)\b(HS|High School|High|School|Academy|Prep|Preparatory|Institute|Christian|"
                        r"Catholic|Jesuit|Country Day|Charter|Secondary|Collegiate|Latin|Episcopal|Lutheran|"
                        r"Baptist Academy|Classical|Magnet|Regional|Memorial|Central|Senior|Township|Area|Consolidated)\b")
COLLEGE_NAME_RE = re.compile(r"(?i)\b(College|CC|University|Univ\.?|JC|Community|State)\b")

def age_at_draft(p, year):
    bd = (p.get("person") or {}).get("birthDate")
    if not bd:
        return None
    y, m, d = map(int, bd.split("-"))
    return (year + 6 / 12) - (y + (m - 1) / 12 + (d - 1) / 365)

def is_hs(p, year):
    cls = (p.get("school") or {}).get("schoolClass")
    if cls:
        return cls == "HS SR"
    name = (p.get("school") or {}).get("name", "")
    a = age_at_draft(p, year)
    if HS_NAME_RE.search(name) and not COLLEGE_NAME_RE.search(name):
        return True
    if a is not None and a < 19.9 and not COLLEGE_NAME_RE.search(name):
        return True
    return False

def round_band(pick):
    r = str(pick.get("pickRound", ""))
    if r in ("1", "1C", "PPI", "CB-A"):
        return "R1"
    if r in ("2", "2C", "CB-B"):
        return "R2"
    try:
        n = int(r)
    except ValueError:
        return "R3-10"
    if n == 3:
        return "R3"
    if n <= 5:
        return "R4-5"
    if n <= 10:
        return "R6-10"
    return "R11+"

def signed(pick):
    b = pick.get("signingBonus")
    return bool(b) and str(b) not in ("0", "")

# ---------------------------------------------------------------- load
def load_prospects(year):
    d = json.load(open(f"{RAW}/prospects_api_{year}.json"))["prospects"]
    out = {}
    for p in d:
        pid = p["person"]["id"]
        if pid in out:          # the 2019-2024 feeds carry exact duplicates
            if (p.get("rank") or 999) < (out[pid].get("rank") or 999):
                out[pid] = p
            continue
        out[pid] = p
    return out

def load_draft(year):
    out, by_name = {}, {}
    for r in json.load(open(f"{RAW}/draft_{year}.json"))["drafts"]["rounds"]:
        for p in r["picks"]:
            out[p["person"]["id"]] = p
            by_name.setdefault(norm_name(p["person"]["fullName"]), []).append(p)
    return out, by_name

drafts = {y: load_draft(y) for y in DRAFTS}

def find_pick(pid, name, year):
    by_id, by_name = drafts[year]
    if pid in by_id:
        return by_id[pid], "id"
    c = by_name.get(norm_name(name), [])
    if len(c) == 1:
        return c[0], "name"
    return None, None

# ---------------------------------------------------------------- main
rows = []            # per-player records (never written out with names)
unmatched_commits = Counter()
diag = defaultdict(Counter)

for Y in CLASSES:
    pros = load_prospects(Y)
    ranked = [p for p in pros.values() if p.get("rank")]
    hs = sorted([p for p in ranked if is_hs(p, Y)], key=lambda p: p["rank"])
    diag[Y]["ranked_all"] = len(ranked)
    diag[Y]["ranked_hs"] = len(hs)
    # heuristic check where schoolClass exists
    if Y >= 2020:
        agree = sum(1 for p in ranked if (p["school"].get("schoolClass") == "HS SR") ==
                    (bool(HS_NAME_RE.search(p["school"].get("name", ""))) and not COLLEGE_NAME_RE.search(p["school"].get("name", ""))
                     or ((age_at_draft(p, Y) or 99) < 19.9 and not COLLEGE_NAME_RE.search(p["school"].get("name", "")))))
        diag[Y]["hs_heuristic_agree"] = agree
    for i, p in enumerate(hs, 1):
        pid, name = p["person"]["id"], p["person"]["fullName"]
        commit_raw, cstatus = extract_commit(p.get("blurb", ""))
        cschool, ctier = school_lookup(commit_raw)
        if commit_raw and _classify(commit_raw) == "non-D1":
            cschool, ctier = None, "non-D1"
        elif commit_raw and not cschool:
            unmatched_commits[commit_raw] += 1
            ctier = "unmatched"
        if cstatus == "uncommitted":
            ctier = "uncommitted"
        elif cstatus == "none":
            ctier = "not stated"
        # HS draft
        pick, how = find_pick(pid, name, Y)
        hs_drafted = pick is not None
        hs_signed = hs_drafted and signed(pick)
        hs_round = round_band(pick) if hs_drafted else None
        campus = not hs_signed
        # college draft, k = 2,3,4 years later
        col = {}
        if campus:
            for k in (2, 3, 4):
                yk = Y + k
                if yk in drafts:
                    cp, chow = find_pick(pid, name, yk)
                    if cp is not None:
                        cs, ct = school_lookup((cp.get("school") or {}).get("name"))
                        col[k] = dict(round=round_band(cp), signed=signed(cp), school_tier=ct or "other",
                                      cls=(cp.get("school") or {}).get("schoolClass"), how=chow)
        diag[Y]["commit_" + cstatus] += 1
        rows.append(dict(Y=Y, rank=p["rank"], hs_ord=i, ctier=ctier, cstatus=cstatus, hs_drafted=hs_drafted, hs_signed=hs_signed,
                         hs_round=hs_round, how=how, campus=campus, col=col))

# ---------------------------------------------------------------- aggregate
def band_of(v, bands):
    for lo, hi, lab in bands:
        if lo <= v <= hi:
            return lab
    return None

out = []
def emit(Y, scheme, band, group, outcome, count, denom, note=""):
    out.append(dict(class_year=Y, rank_scheme=scheme, rank_band=band, outcome_group=group,
                    outcome=outcome, count=count, denominator=denom, note=note))

TIERS = ["p4", "mid", "low", "non-D1", "uncommitted", "not stated", "unmatched"]
RB = ["R1", "R2", "R3", "R4-5", "R6-10", "R11+"]

for scheme, bands, key in (("pipeline_overall_rank", OVERALL_BANDS, "rank"), ("hs_ordinal_rank", HS_BANDS, "hs_ord")):
    for Y in list(CLASSES) + ["2019-2024", "2019-2022"]:
        if Y == "2019-2024":
            sel = rows
        elif Y == "2019-2022":
            sel = [r for r in rows if r["Y"] <= 2022]
        else:
            sel = [r for r in rows if r["Y"] == Y]
        for lo, hi, band in bands:
            g = [r for r in sel if band_of(r[key], bands) == band]
            n = len(g)
            if n == 0:
                continue
            emit(Y, scheme, band, "sample", "ranked_hs_prospects", n, n)
            # (a) commitment tier
            for t in TIERS:
                emit(Y, scheme, band, "a_commitment", t, sum(1 for r in g if r["ctier"] == t), n)
            # (b) drafted out of HS and signed, by round band
            emit(Y, scheme, band, "b_hs_draft", "drafted", sum(1 for r in g if r["hs_drafted"]), n)
            emit(Y, scheme, band, "b_hs_draft", "drafted_signed", sum(1 for r in g if r["hs_signed"]), n)
            emit(Y, scheme, band, "b_hs_draft", "drafted_unsigned", sum(1 for r in g if r["hs_drafted"] and not r["hs_signed"]), n)
            emit(Y, scheme, band, "b_hs_draft", "undrafted", sum(1 for r in g if not r["hs_drafted"]), n)
            for rb in RB:
                emit(Y, scheme, band, "b_hs_draft_signed_by_round", rb, sum(1 for r in g if r["hs_signed"] and r["hs_round"] == rb), n)
                emit(Y, scheme, band, "b_hs_draft_unsigned_by_round", rb, sum(1 for r in g if r["hs_drafted"] and not r["hs_signed"] and r["hs_round"] == rb), n)
            # (c) reached campus by commitment tier
            camp = [r for r in g if r["campus"]]
            emit(Y, scheme, band, "c_campus", "reached_campus", len(camp), n, "unsigned or undrafted; commitment tier from the Pipeline blurb")
            for t in TIERS:
                emit(Y, scheme, band, "c_campus_by_commit_tier", t, sum(1 for r in camp if r["ctier"] == t), len(camp))
            # (d) drafted from college k years later
            if isinstance(Y, int):
                ks = [k for k in (2, 3, 4) if Y + k in drafts]
            else:
                ks = [2, 3, 4] if Y == "2019-2022" else []
            for k in ks:
                nk = len(camp) if isinstance(Y, int) else sum(1 for r in camp if r["Y"] + k in drafts)
                dk = [r for r in camp if k in r["col"] and (isinstance(Y, int) or r["Y"] + k in drafts)]
                emit(Y, scheme, band, f"d_college_draft_y+{k}", "drafted", len(dk), nk)
                emit(Y, scheme, band, f"d_college_draft_y+{k}", "drafted_signed", sum(1 for r in dk if r["col"][k]["signed"]), nk)
                for rb in RB:
                    emit(Y, scheme, band, f"d_college_draft_y+{k}_by_round", rb, sum(1 for r in dk if r["col"][k]["round"] == rb), nk)
                for t in ["p4", "mid", "low", "other"]:
                    emit(Y, scheme, band, f"d_college_draft_y+{k}_by_college_tier", t, sum(1 for r in dk if r["col"][k]["school_tier"] == t), nk)
            if ks and (isinstance(Y, int) and Y + 4 in drafts or Y == "2019-2022"):
                any34 = [r for r in camp if 3 in r["col"] or 4 in r["col"]]
                emit(Y, scheme, band, "d_college_draft_y+3or4", "drafted", len(any34), len(camp))
                emit(Y, scheme, band, "d_college_draft_y+3or4", "drafted_signed", sum(1 for r in any34 if any(r["col"][k]["signed"] for k in (3, 4) if k in r["col"])), len(camp))
                any234 = [r for r in camp if r["col"]]
                emit(Y, scheme, band, "d_college_draft_y+2to4", "drafted", len(any234), len(camp))
                first = Counter(r["col"][min(r["col"])]["round"] for r in any234)
                for rb in RB:
                    emit(Y, scheme, band, "d_college_draft_y+2to4_first_by_round", rb, first[rb], len(camp))
                # commitment tier x drafted later (did the committed tier matter)
                for t in ["p4", "mid", "low"]:
                    ct = [r for r in camp if r["ctier"] == t]
                    emit(Y, scheme, band, "d_college_draft_y+2to4_by_commit_tier", t, sum(1 for r in ct if r["col"]), len(ct))
                # commitment vs where actually drafted from (flip / transfer rate)
                same = sum(1 for r in any234 if r["col"][min(r["col"])]["school_tier"] == r["ctier"])
                emit(Y, scheme, band, "d_college_tier_equals_commit_tier", "same_tier", same, len(any234))

# background: every HS senior drafted, by draft year (schoolClass from the feed; 2019 by school-name/age heuristic)
for y in DRAFTS:
    by_id, _ = drafts[y]
    hs_picks = [p for p in by_id.values() if is_hs(p, y)]
    emit(y, "all_hs_picks_in_draft", "all", "background", "picks_total", len(by_id), len(by_id),
         "every pick in the draft feed")
    emit(y, "all_hs_picks_in_draft", "all", "background", "hs_sr_picks", len(hs_picks), len(by_id),
         "2019: no schoolClass in the feed, HS inferred from school name and age")
    emit(y, "all_hs_picks_in_draft", "all", "background", "hs_sr_signed", sum(1 for p in hs_picks if signed(p)), len(hs_picks))
    for rb in RB:
        g = [p for p in hs_picks if round_band(p) == rb]
        emit(y, "all_hs_picks_in_draft", rb, "background", "hs_sr_picks", len(g), len(hs_picks))
        emit(y, "all_hs_picks_in_draft", rb, "background", "hs_sr_signed", sum(1 for p in g if signed(p)), len(g))

# ---------------------------------------------------------------- Baseball America HS Top 100 for the 2018 draft
# https://www.baseballamerica.com/stories/2018-top-100-mlb-draft-prospects-in-high-school/ (Carlos Collazo,
# published 2017-11-17, after the early signing period: a recruiting-style ranking 199 days before the draft).
# Page text saved in raw/ba_hs100_2018.txt.  Entry form: "1. RHP Ethan Hankins | 6-6 | 215 | (HS, City, St.) | Commitment".
import os
BA_TXT = f"{RAW}/ba_hs100_2018.txt"
if os.path.exists(BA_TXT):
    lines = open(BA_TXT, encoding="utf-8", errors="ignore").read().split("\n")
    ba = []
    for i, l in enumerate(lines):
        m = re.match(r"^(\d{1,3})\. ([A-Z0-9/]+) (.+)$", l)
        if m and int(m.group(1)) <= 100:
            commit = None
            for j in range(i + 1, min(i + 10, len(lines))):
                if lines[j].startswith("(") and j + 2 < len(lines):
                    commit = lines[j + 2].strip()
                    break
            ba.append((int(m.group(1)), m.group(3).strip(), commit))
    pros18 = load_prospects(2018)
    by_name18 = defaultdict(list)
    for p in pros18.values():
        by_name18[norm_name(p["person"]["fullName"])].append(p)
    BA_BANDS = [(1, 10, "ba1-10"), (11, 25, "ba11-25"), (26, 50, "ba26-50"), (51, 100, "ba51-100")]
    barows = []
    for rank, name, commit in ba:
        cands = by_name18.get(norm_name(name), [])
        cands = [c for c in cands if is_hs(c, 2018)] or cands
        reg = cands[0] if len(cands) >= 1 else None
        pid = reg["person"]["id"] if reg else None
        cschool, ctier = school_lookup(commit)
        if commit and not cschool:
            ctier = "non-D1" if _classify(commit) == "non-D1" else "unmatched"
            if ctier == "unmatched":
                unmatched_commits["BA:" + commit] += 1
        if not commit or commit.lower() in ("uncommitted", "undecided", "none"):
            ctier = "uncommitted"
        pick, how = find_pick(pid, name, 2018) if pid else (None, None)
        if pick is None:
            c = drafts[2018][1].get(norm_name(name), [])
            if len(c) == 1:
                pick, how = c[0], "name"
        hs_drafted = pick is not None
        hs_signed = hs_drafted and signed(pick)
        col = {}
        if not hs_signed:
            for k in (2, 3, 4, 5):
                cp, chow = find_pick(pid, name, 2018 + k) if pid else (None, None)
                if cp is None:
                    c = drafts[2018 + k][1].get(norm_name(name), [])
                    if len(c) == 1:
                        cp, chow = c[0], "name"
                if cp is not None:
                    cs, ct = school_lookup((cp.get("school") or {}).get("name"))
                    col[k] = dict(round=round_band(cp), signed=signed(cp), school_tier=ct or "other", how=chow)
        barows.append(dict(rank=rank, ctier=ctier, in_registry=reg is not None, pipeline_rank=(reg or {}).get("rank"),
                           hs_drafted=hs_drafted, hs_signed=hs_signed, hs_round=round_band(pick) if pick else None,
                           campus=not hs_signed, col=col))
    SCH = "ba_hs_top100_2017-11"
    for lo, hi, band in BA_BANDS:
        g = [r for r in barows if lo <= r["rank"] <= hi]
        n = len(g)
        emit(2018, SCH, band, "sample", "ranked_hs_prospects", n, n, "BA HS Top 100 for the 2018 draft, published 2017-11-17")
        emit(2018, SCH, band, "sample", "found_in_mlb_registry", sum(1 for r in g if r["in_registry"]), n)
        emit(2018, SCH, band, "sample", "on_pipeline_top200_at_draft", sum(1 for r in g if r["pipeline_rank"]), n)
        for t in TIERS + ["uncommitted"]:
            emit(2018, SCH, band, "a_commitment", t, sum(1 for r in g if r["ctier"] == t), n)
        emit(2018, SCH, band, "b_hs_draft", "drafted", sum(1 for r in g if r["hs_drafted"]), n)
        emit(2018, SCH, band, "b_hs_draft", "drafted_signed", sum(1 for r in g if r["hs_signed"]), n)
        emit(2018, SCH, band, "b_hs_draft", "drafted_unsigned", sum(1 for r in g if r["hs_drafted"] and not r["hs_signed"]), n)
        emit(2018, SCH, band, "b_hs_draft", "undrafted", sum(1 for r in g if not r["hs_drafted"]), n)
        for rb in RB:
            emit(2018, SCH, band, "b_hs_draft_signed_by_round", rb, sum(1 for r in g if r["hs_signed"] and r["hs_round"] == rb), n)
        camp = [r for r in g if r["campus"]]
        emit(2018, SCH, band, "c_campus", "reached_campus", len(camp), n)
        for t in TIERS + ["uncommitted"]:
            emit(2018, SCH, band, "c_campus_by_commit_tier", t, sum(1 for r in camp if r["ctier"] == t), len(camp))
        for k in (2, 3, 4, 5):
            dk = [r for r in camp if k in r["col"]]
            emit(2018, SCH, band, f"d_college_draft_y+{k}", "drafted", len(dk), len(camp))
            for rb in RB:
                emit(2018, SCH, band, f"d_college_draft_y+{k}_by_round", rb, sum(1 for r in dk if r["col"][k]["round"] == rb), len(camp))
            for t in ["p4", "mid", "low", "other"]:
                emit(2018, SCH, band, f"d_college_draft_y+{k}_by_college_tier", t, sum(1 for r in dk if r["col"][k]["school_tier"] == t), len(camp))
        any34 = [r for r in camp if 3 in r["col"] or 4 in r["col"]]
        emit(2018, SCH, band, "d_college_draft_y+3or4", "drafted", len(any34), len(camp))
        any234 = [r for r in camp if any(k in r["col"] for k in (2, 3, 4))]
        emit(2018, SCH, band, "d_college_draft_y+2to4", "drafted", len(any234), len(camp))
        emit(2018, SCH, band, "d_college_draft_y+2to5", "drafted", sum(1 for r in camp if r["col"]), len(camp))
        first = Counter(r["col"][min(r["col"])]["round"] for r in any234)
        for rb in RB:
            emit(2018, SCH, band, "d_college_draft_y+2to4_first_by_round", rb, first[rb], len(camp))
        for t in ["p4", "mid", "low"]:
            ct = [r for r in camp if r["ctier"] == t]
            emit(2018, SCH, band, "d_college_draft_y+2to4_by_commit_tier", t, sum(1 for r in ct if r["col"]), len(ct))
    print("== BA 2018 list:", len(ba), "entries; in registry", sum(r["in_registry"] for r in barows),
          "; on Pipeline top 200 at draft", sum(1 for r in barows if r["pipeline_rank"]),
          "; commit tiers", Counter(r["ctier"] for r in barows), file=sys.stderr)

with open(OUT_CSV, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
    w.writeheader(); w.writerows(out)

# ---------------------------------------------------------------- diagnostics (names only to stderr, never to the CSV)
print("== per class", file=sys.stderr)
for Y in CLASSES:
    g = [r for r in rows if r["Y"] == Y]
    c = Counter(r["ctier"] for r in g)
    print(Y, dict(diag[Y]), "hs ranked", len(g), "commit tiers", dict(c),
          "hs drafted", sum(r["hs_drafted"] for r in g), "signed", sum(r["hs_signed"] for r in g),
          "matched by name only", sum(1 for r in g if r["how"] == "name"), file=sys.stderr)
print("== unmatched commitment strings", unmatched_commits.most_common(60), file=sys.stderr)
print("== college-draft school names not in schools.csv:",
      Counter(r["col"][k]["school_tier"] for r in rows for k in r["col"]).most_common(), file=sys.stderr)
