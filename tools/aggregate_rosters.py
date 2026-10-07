#!/usr/bin/env python3
"""Aggregate a roster fetch into the only roster tables the project commits.

Owner decision 2026-10-07: the game never uses real players. Rosters feed aggregate
distributions only: handedness shares by position and pitcher role, hometown regions by
school (recruiting pipelines), JUCO / D2 / transfer origins, and the Phase 3 platoon tables,
which join roster hands to the committed WMT play-by-play. Player names are used inside
this script for that join and are never written out: every output is a count or a share by
school, conference, tier, region, position, class or hand, and the script ends by scanning
every file it wrote for roster names (it fails if it finds one).

    python tools/aggregate_rosters.py --in <fetch dir>     # the fetcher's --out directory
    python tools/aggregate_rosters.py --selftest           # synthetic rosters built from the
                                                           # play-by-play names; runs everything

Input (the fetcher's output, never committed): rosters_2025.csv, state.json, failures.csv.
Repository data read: data/ncaa_2025/pbp/teams_2025.csv (conference, tier; joined on
team_ncaa_id = ncaa_team_id), data/ncaa_2025/ncaa_d1_teams_2025.csv (D1 names),
tools/roster_teams.csv (the teams the fetcher tries), and
data/ncaa_2025/pbp/parsed/pa_events_2025.csv.gz (the play-by-play).

Output (default data/ncaa_2025/roster_aggregates/; tables and rules in data/README.md):
    coverage.csv                 teams attempted / parsed / failed by reason class, fields filled, by tier
    failures.csv                 team, reason class, reason (URLs removed); no player data
    handedness_by_position.csv   bats x throws by position group, by scope (all / tier / conference)
    linkage.csv                  roster-to-play-by-play name match rates, by side and tier
    pitcher_throws_by_role.csv   throws x role (starter / reliever / unmatched), by scope
    batter_bats_matched.csv      bats of roster batters matched to the play-by-play, with PA
    platoon_league.csv           PA outcome counts by batter side x pitcher throws, by tier
    platoon_spread.csv           individual platoon-split spread (method of moments), no individual rows
    hometown_by_school.csv       hometown state / province / country and Census region by school
    hometown_by_conference.csv   conference x Census division
    origins_by_school.csv        class x origin category (high school, JUCO, D1 transfer, other) by school
    origins_rules.csv            which classification rule fired, by origin and tier (for grading the rules)

Linkage: the play-by-play's batter_id and pitcher_id are WMT game_player_id values, unique
to one game (checked: every id appears in exactly one game), so they cannot equal the
roster's wmt_person_id. Players are therefore matched by name within team: the play-by-play
check name ("Gholston, J.", "J. Jones", "Herrera lll", "Justin Heffl", truncated at 12
characters) is parsed into a last name and a first-name prefix and matched to the roster's
full names on last name plus first initial (or the longer prefix when one is given).
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import shutil
import sys
import tempfile
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.phase1 import RESULTS  # noqa: E402  the outcome classes of the engine's table
from scripts.build_engine_tables import RES_MAP  # noqa: E402  raw result -> RESULTS class

TEAMS = ROOT / "data/ncaa_2025/pbp/teams_2025.csv"
D1_TEAMS = ROOT / "data/ncaa_2025/ncaa_d1_teams_2025.csv"
ROSTER_TEAMS = ROOT / "tools/roster_teams.csv"
PA_EVENTS = ROOT / "data/ncaa_2025/pbp/parsed/pa_events_2025.csv.gz"
OUT = ROOT / "data/ncaa_2025/roster_aggregates"

MIN_SPLIT_PA = 50          # GUESS: PA (BF for pitchers) needed against each hand to enter platoon_spread
MIN_CELL_PLAYERS = 5       # GUESS: platoon_spread cells with fewer players print counts only (no moments)
STARTER_SHARE = 0.5        # GUESS: a pitcher is a starter when at least this share of his appearances are starts
TRUNCATED_LEN = 12         # WMT check names are cut at 12 characters (2026-10-07: 99.9% of names are <= 12)
LEAK_MIN_LAST = 6          # last names this long or longer are searched for in the outputs (owner spec)

HIT = ("1B", "2B", "3B")
BIP_NOROE = ("1B", "2B", "3B", "FO", "GO", "GIDP", "DP", "SF", "SH", "FC")   # scripts/build_phase2_benchmarks.py
ON_BASE = ("1B", "2B", "3B", "HR", "BB", "IBB", "HBP")
SPLIT_RATES = {   # rate: (successes, trials or None for every PA)
    "K": (("K",), None),
    "BB": (("BB", "IBB"), None),
    "HR": (("HR",), None),
    "OB": (ON_BASE, None),
    "BABIP": (HIT, BIP_NOROE),
}

# ------------------------------------------------------------------ text helpers
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v", "lll", "ll", "2nd", "3rd"}
BLANKS = {"", "-", "--", "—", "n/a", "na", "none", "tbd", "tba", "null", "nan"}


def fold(s) -> str:
    """Lower case, accents removed, whitespace collapsed."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def letters(s: str) -> str:
    return re.sub(r"[^a-z]", "", fold(s))


def is_blank(v) -> bool:
    return fold(v) in BLANKS


# ------------------------------------------------------------------ position groups
# Each '/', '-', ',' or '&' separated token maps to a group; a pitcher token together with a
# non-pitcher token is two-way; otherwise the first listed non-pitcher token decides
# (C/OF -> C, INF/OF -> IF, OF/1B -> OF). Unrecognised or blank -> unknown.
POS_TOKENS = {
    "P": {"p", "rhp", "lhp", "pitcher", "sp", "rp", "hp", "rhsp", "lhsp", "rhrp", "lhrp", "rh", "lh", "pit",
          "righthandedpitcher", "lefthandedpitcher"},
    "C": {"c", "catcher"},
    "1B": {"1b", "firstbase", "firstbaseman"},
    "IF": {"2b", "ss", "3b", "inf", "if", "mif", "mi", "ci", "infield", "infielder", "secondbase", "thirdbase",
           "shortstop"},
    "OF": {"of", "lf", "cf", "rf", "outfield", "outfielder", "leftfield", "centerfield", "rightfield"},
    "UT/DH": {"ut", "utl", "util", "utility", "dh", "designatedhitter", "ph", "pr"},
}
POS_GROUPS = ("P", "C", "1B", "IF", "OF", "UT/DH", "two-way", "unknown")
_POS_OF = {t: g for g, ts in POS_TOKENS.items() for t in ts}


def position_group(pos) -> str:
    toks = [re.sub(r"[^a-z0-9]", "", t) for t in re.split(r"[/\-,&+]|\s+or\s+", fold(pos))]
    groups = [_POS_OF[t] for t in toks if t in _POS_OF]
    if not groups:
        joined = re.sub(r"[^a-z0-9]", "", fold(pos))
        groups = [_POS_OF[joined]] if joined in _POS_OF else []
    if not groups:
        return "unknown"
    other = [g for g in groups if g != "P"]
    if "P" in groups:
        return "two-way" if other else "P"
    return other[0]


# ------------------------------------------------------------------ class
def class_year(v) -> str:
    """Fr / So / Jr / Sr / Gr / unknown. Redshirt markers (R-, RS, Redshirt) are dropped:
    'R-Fr.' is a freshman by academic class. 5th/6th year, graduate and super senior -> Gr."""
    s = fold(v)
    s = re.sub(r"^(redshirt|red-shirt|rs|r)[\s\-\.]*(?=[a-z0-9])", "", s)
    s = re.sub(r"[^a-z0-9 ]", "", s).strip()
    if not s:
        return "unknown"
    if re.match(r"^(gr|grad|graduate|gs|5th|6th|fifth|sixth|super|5y|5 ?yr)", s):
        return "Gr"
    for lab, pat in (("Fr", r"^(fr|freshman|first|1st|fy)"), ("So", r"^(so|soph|sophomore|second|2nd)"),
                     ("Jr", r"^(jr|junior|third|3rd)"), ("Sr", r"^(sr|senior|fourth|4th)")):
        if re.match(pat, s):
            return lab
    return "unknown"


# ------------------------------------------------------------------ hometowns
# postal | names and abbreviations (AP style and others) | Census region | Census division
STATES = """AL|Alabama;Ala|South|East South Central
AK|Alaska|West|Pacific
AZ|Arizona;Ariz|West|Mountain
AR|Arkansas;Ark|South|West South Central
CA|California;Calif;Cal;Cali|West|Pacific
CO|Colorado;Colo|West|Mountain
CT|Connecticut;Conn|Northeast|New England
DE|Delaware;Del|South|South Atlantic
DC|District of Columbia;Washington DC;D.C.|South|South Atlantic
FL|Florida;Fla|South|South Atlantic
GA|Georgia;Ga|South|South Atlantic
HI|Hawaii;Hawai'i|West|Pacific
ID|Idaho|West|Mountain
IL|Illinois;Ill|Midwest|East North Central
IN|Indiana;Ind|Midwest|East North Central
IA|Iowa|Midwest|West North Central
KS|Kansas;Kan;Kans|Midwest|West North Central
KY|Kentucky;Ky|South|East South Central
LA|Louisiana;La|South|West South Central
ME|Maine|Northeast|New England
MD|Maryland;Md|South|South Atlantic
MA|Massachusetts;Mass|Northeast|New England
MI|Michigan;Mich|Midwest|East North Central
MN|Minnesota;Minn|Midwest|West North Central
MS|Mississippi;Miss|South|East South Central
MO|Missouri;Mo|Midwest|West North Central
MT|Montana;Mont|West|Mountain
NE|Nebraska;Neb;Nebr|Midwest|West North Central
NV|Nevada;Nev|West|Mountain
NH|New Hampshire;N.H.|Northeast|New England
NJ|New Jersey;N.J.|Northeast|Middle Atlantic
NM|New Mexico;N.M.;N.Mex|West|Mountain
NY|New York;N.Y.|Northeast|Middle Atlantic
NC|North Carolina;N.C.|South|South Atlantic
ND|North Dakota;N.D.;N.Dak|Midwest|West North Central
OH|Ohio|Midwest|East North Central
OK|Oklahoma;Okla|South|West South Central
OR|Oregon;Ore;Oreg|West|Pacific
PA|Pennsylvania;Pa;Penn|Northeast|Middle Atlantic
RI|Rhode Island;R.I.|Northeast|New England
SC|South Carolina;S.C.|South|South Atlantic
SD|South Dakota;S.D.;S.Dak|Midwest|West North Central
TN|Tennessee;Tenn|South|East South Central
TX|Texas;Tex|South|West South Central
UT|Utah|West|Mountain
VT|Vermont;Vt|Northeast|New England
VA|Virginia;Va|South|South Atlantic
WA|Washington;Wash|West|Pacific
WV|West Virginia;W.Va;W.V.|South|South Atlantic
WI|Wisconsin;Wis;Wisc|Midwest|East North Central
WY|Wyoming;Wyo|West|Mountain"""
TERRITORIES = {"Puerto Rico": "puerto rico;pr;p.r.", "U.S. Virgin Islands": "us virgin islands;usvi;virgin islands",
               "Guam": "guam", "Northern Mariana Islands": "northern mariana islands;cnmi", "American Samoa": "american samoa"}
PROVINCES = {   # -> country
    "Canada": "ontario;ont;on;quebec;que;qc;british columbia;b.c.;bc;alberta;alta;ab;manitoba;man;mb;saskatchewan;"
              "sask;sk;nova scotia;n.s.;ns;new brunswick;n.b.;nb;newfoundland;newfoundland and labrador;nl;nfld;"
              "prince edward island;pei;p.e.i.;pe;yukon;northwest territories;nwt;nunavut;canada;can",
    "Australia": "australia;new south wales;nsw;victoria;queensland;qld;western australia;south australia;tasmania;aus",
    "Mexico": "mexico;mex;baja california;sonora;chihuahua;nuevo leon;jalisco;sinaloa",
    "Dominican Republic": "dominican republic;d.r.;dr;dom. rep.;rep. dom.;republica dominicana",
    "Venezuela": "venezuela", "Cuba": "cuba", "Panama": "panama", "Colombia": "colombia", "Nicaragua": "nicaragua",
    "Bahamas": "bahamas;the bahamas", "Aruba": "aruba", "Curacao": "curacao", "Netherlands": "netherlands;holland;the netherlands",
    "Germany": "germany", "Italy": "italy", "Spain": "spain", "France": "france",
    "United Kingdom": "england;scotland;wales;united kingdom;uk;u.k.;great britain;northern ireland",
    "Ireland": "ireland", "Czech Republic": "czech republic;czechia", "New Zealand": "new zealand;nz",
    "Japan": "japan", "South Korea": "south korea;korea;republic of korea", "Taiwan": "taiwan", "China": "china",
    "Philippines": "philippines", "South Africa": "south africa", "Brazil": "brazil", "Israel": "israel",
    "Sweden": "sweden", "Norway": "norway", "Denmark": "denmark", "Austria": "austria", "Switzerland": "switzerland",
    "Belgium": "belgium", "Lithuania": "lithuania", "Croatia": "croatia", "Russia": "russia", "Ukraine": "ukraine",
    "Poland": "poland", "Greece": "greece", "Jamaica": "jamaica", "Honduras": "honduras", "Guatemala": "guatemala",
    "El Salvador": "el salvador", "Costa Rica": "costa rica", "Peru": "peru", "Argentina": "argentina", "Chile": "chile",
    "Ecuador": "ecuador", "Haiti": "haiti", "Trinidad and Tobago": "trinidad and tobago;trinidad", "Bermuda": "bermuda",
    "Cayman Islands": "cayman islands", "Finland": "finland", "Uganda": "uganda", "Nigeria": "nigeria", "Ghana": "ghana",
    "Hong Kong": "hong kong", "Singapore": "singapore", "India": "india", "Portugal": "portugal",
}
USA = {"usa", "us", "u.s.", "u.s.a.", "united states", "united states of america", "america"}


def _key(s: str) -> str:
    return re.sub(r"[^a-z]", "", fold(s))


STATE_OF: dict = {}
STATE_INFO: dict = {}
for _line in STATES.splitlines():
    _post, _names, _reg, _div = _line.split("|")
    STATE_INFO[_post] = (_reg, _div)
    for _n in [_post] + _names.split(";"):
        STATE_OF[_key(_n)] = _post
TERRITORY_OF = {_key(n): t for t, ns in TERRITORIES.items() for n in ns.split(";")}
COUNTRY_OF = {_key(n): c for c, ns in PROVINCES.items() for n in ns.split(";")}
COUNTRY_OF.update({_key(c): c for c in PROVINCES})
GEO_LABELS = {"unknown", "unrecognized", "international", "US territory"}


def _place(part: str):
    k = _key(part)
    if not k or fold(part) in USA or k in {_key(u) for u in USA}:
        return None
    if k in STATE_OF:
        post = STATE_OF[k]
        reg, div = STATE_INFO[post]
        return post, "us_state", reg, div
    if k in TERRITORY_OF:
        return TERRITORY_OF[k], "us_territory", "US territory", "US territory"
    if k in COUNTRY_OF:
        return COUNTRY_OF[k], "international", "international", "international"
    return None


def locate(city, state) -> tuple[str, str, str, str]:
    """(area, area_type, Census region, Census division). The area is a US state's postal code,
    a US territory, or a country (Canadian provinces and other countries' states -> the country).
    The state field is read right to left ('Ontario, Canada' -> Canada, 'Texas, USA' -> TX); if it
    is blank, a city field that is itself a state or country is used ('Venezuela'). Anything else
    is 'unrecognized'; blank is 'unknown'. Only these canonical labels are ever written."""
    parts = [p for p in re.split(r",", str(state or "")) if p.strip()]
    for p in reversed(parts):
        got = _place(p)
        if got:
            return got
    if not parts:
        cparts = [p for p in re.split(r",", str(city or "")) if p.strip()]
        for p in reversed(cparts):
            got = _place(p)
            if got:
                return got
        if not cparts:
            return "unknown", "unknown", "unknown", "unknown"
    return "unrecognized", "unrecognized", "unknown", "unknown"


# ------------------------------------------------------------------ previous-school origin
JUCO_MARKERS = re.compile(r"\b(community college|junior college|jr\.? college|juco|city college|technical college|"
                          r"cc|jc|c\.\s?c\.|j\.\s?c\.)(?![a-z])")
JUCO_COLLEGE_OF_THE = re.compile(r"^college of the\b")
JUCO_NAMES = [   # well-known junior colleges whose names carry none of the markers above (constant list)
    "Chipola", "San Jacinto", "Walters State", "McLennan", "Blinn", "Iowa Western", "Wabash Valley", "Central Arizona",
    "Seminole State", "Northwest Florida State", "Cowley", "Cowley County", "Crowder", "Grayson", "Howard", "Weatherford",
    "Navarro", "LSU Eunice", "LSU-Eunice", "Shelton State", "Jefferson College", "Wallace State", "Florida SouthWestern",
    "Chattahoochee Valley", "State College of Florida", "Polk State", "Eastern Florida State", "Santa Fe", "Tallahassee",
    "Pensacola State", "Hill College", "Odessa", "Temple College", "Paris JC", "Western Oklahoma State",
    "Connors State", "Seward County", "Butler", "Hutchinson", "Neosho County", "Johnson County", "Iowa Central",
    "Kirkwood", "Indian Hills", "Des Moines Area", "John A. Logan", "Lake Land", "Heartland", "Parkland",
    "State Fair", "Mineral Area", "Three Rivers", "Meridian", "Pearl River", "Jones College", "Jones County", "Hinds",
    "Itawamba", "Northwest Mississippi", "Southwest Mississippi", "Gulf Coast", "Mississippi Gulf Coast",
    "Gulf Coast State", "Delgado", "Bossier Parish", "Northeast Texas", "Panola", "Tyler", "Trinity Valley", "Angelina",
    "Kilgore", "Yavapai", "Arizona Western", "Cochise", "Pima", "South Mountain", "Mesa", "Glendale", "Salt Lake",
    "Southern Nevada", "Colorado Northwestern", "Lamar CC", "Otero", "Trinidad State", "Northeastern JC",
    "Western Nevada", "Murray State College", "Northeastern Oklahoma A&M", "Carl Albert State",
    "Eastern Oklahoma State", "Northern Oklahoma", "Barton County", "Dodge City", "Garden City", "Pratt", "Fort Scott",
    "Coffeyville", "Allen County", "Labette", "Cloud County", "Rend Lake", "Kaskaskia",
    "Southwestern Illinois", "Olney Central", "Lincoln Land", "Illinois Central", "Moberly Area",
    "East Central", "Holmes", "Copiah-Lincoln", "Co-Lin", "East Mississippi", "Northeast Mississippi",
    "Baton Rouge", "Chattanooga State", "Columbia State", "Cleveland State", "Roane State", "Motlow State",
    "Dyersburg State", "Volunteer State", "Calhoun", "Snead State", "Bevill State", "Southern Union", "Enterprise State",
    "Lawson State", "Gadsden State", "Coastal Alabama", "Northwest Shoals", "Jefferson State", "Wallace",
    "George C. Wallace", "Indian River State", "St. Johns River State", "Daytona State", "Broward", "Miami Dade",
    "Palm Beach State", "Hillsborough", "South Florida State", "Lake-Sumter", "St. Petersburg College",
    "Florida State College at Jacksonville", "College of Central Florida", "Georgia Highlands", "South Georgia State",
    "East Georgia State", "Andrew College", "Spartanburg Methodist", "USC Salkehatchie", "USC Sumter", "USC Lancaster",
    "Louisburg", "Alvin", "Wharton", "Galveston", "Lee College", "Ranger", "Clarendon", "Frank Phillips",
    "Western Texas", "Midland", "New Mexico JC", "Cisco", "Vernon", "Lone Star", "Eastern Arizona",
    "Chandler-Gilbert", "GateWay", "Paradise Valley", "Scottsdale", "Phoenix College", "Snow College",
    "College of Southern Idaho", "North Idaho", "Western Nebraska", "McCook", "Orange Coast", "Saddleback", "Cypress",
    "Fullerton College", "Riverside City", "Golden West", "Santa Ana", "Mt. San Antonio", "Mt. SAC", "Citrus",
    "Cerritos", "El Camino", "Ventura", "Moorpark", "Fresno City", "Sacramento City", "Cosumnes River",
    "San Joaquin Delta", "Diablo Valley", "Chabot", "Ohlone", "Cabrillo", "Santa Rosa", "Sierra College", "Butte",
    "Feather River", "Yuba", "Shasta", "Palomar", "Grossmont", "San Diego Mesa", "Cuyamaca",
    "Irvine Valley", "Long Beach City", "Pasadena City", "Antelope Valley", "Bakersfield College", "Taft College",
    "Porterville", "Edmonds", "Bellevue College", "Lower Columbia", "Clark College", "Centralia", "Linn-Benton",
    "Mt. Hood", "Chemeketa", "Umpqua", "Clackamas", "Treasure Valley", "Columbia Basin", "Big Bend",
    "Wenatchee Valley", "Walla Walla", "Yakima Valley", "Spokane Falls", "Shoreline", "Skagit Valley", "Grays Harbor",
    "Olympic College", "Rowan College", "Lackawanna", "Iowa Lakes", "Ellsworth", "Marshalltown", "Muscatine",
    "Joliet", "Triton", "Morton", "Moraine Valley", "Harper", "College of DuPage", "Waubonsee", "Kishwaukee",
    "Sauk Valley", "Black Hawk", "Spoon River", "Lincoln Trail", "Southeastern Illinois", "John Wood",
]
JUCO_TAIL = {"college", "community", "junior", "jr", "cc", "jc", "the", "campus", "north", "south", "east", "west",
             "central", "northwest", "northeast", "southwest", "southeast", "county", "district", "area", "of", "state",
             "florida", "texas", "california", "kansas", "iowa", "illinois", "mississippi", "at"}
HS_MARKERS = re.compile(r"\b(high school|high|h\.?\s?s\.?|academy|prep|preparatory|secondary|school|catholic|jesuit|bishop|"
                        r"country day|mater dei)\b")
COLLEGE_WORD = re.compile(r"\b(university|univ|college)\b")
FOUR_YEAR_KEYWORD = re.compile(r"\b(university|univ|college|state|institute|tech|polytechnic|poly|a&m)\b")
D1_ALIASES = [   # other names of 2025 D1 programs, used only to say "this previous school is D1"
    "Louisiana State", "Texas Christian", "Brigham Young", "Central Florida", "Virginia Commonwealth",
    "Florida Gulf Coast", "Florida International", "East Tennessee State", "Dallas Baptist", "Stephen F. Austin",
    "SIU Edwardsville", "Southern Illinois Edwardsville", "Incarnate Word", "Louisiana-Monroe", "UL Monroe",
    "Maryland Baltimore County", "Maryland Eastern Shore", "UNC Wilmington", "North Carolina Wilmington",
    "Nevada Las Vegas", "UT Rio Grande Valley", "Texas Rio Grande Valley", "UT San Antonio", "Texas San Antonio",
    "Alabama Birmingham", "Illinois Chicago", "Northern Illinois", "New Jersey Institute of Technology",
    "Fairleigh Dickinson", "Long Island", "LIU Brooklyn", "Loyola Marymount", "LMU", "Appalachian State",
    "Mississippi", "Army", "West Point", "Nebraska Omaha", "Arkansas Little Rock", "Louisiana Lafayette",
    "UL Lafayette", "USC", "Miami", "Miami Ohio", "Miami University", "Pennsylvania", "UPenn", "Pitt",
    "Connecticut", "Albany", "Seattle", "Saint Mary's", "St. John's", "St. Thomas", "Queens",
    "Queens University of Charlotte", "Lamar", "McNeese State", "Nicholls State", "Sam Houston State",
    "Alcorn State", "Grambling State", "Prairie View A&M", "North Carolina A&T", "North Carolina State",
    "California Davis", "UCSB", "UCSD", "UCI", "UCR", "Cal State Northridge", "Cal State Bakersfield",
    "Cal State Fullerton", "CSU Fullerton", "Cal State Long Beach", "UMass", "Massachusetts Lowell",
    "Charleston", "College of Charleston", "Citadel", "Fort Wayne", "IPFW", "Houston Baptist", "Dixie State",
    "Charleston Southern", "Mount Saint Mary's", "South Carolina Upstate", "Southern", "Southern University",
    "Texas A&M Corpus Christi", "Texas A&M-Corpus Christi", "Corpus Christi", "Texas Arlington", "UTA",
    "Tennessee Martin", "New Orleans", "UNO", "Tarleton", "Middle Tennessee State", "MTSU", "Southeast Missouri",
    "SEMO", "Southern Miss", "Southern Mississippi", "Mississippi Valley State", "Central Connecticut", "CCSU",
    "USF", "FAU", "Bethune Cookman", "Kennesaw", "ODU", "UNCG", "UNCA", "UNC", "Wisconsin-Milwaukee",
    "UW-Milwaukee", "Saint Joseph's", "St. Joseph's", "St. Peter's", "SLU", "Naval Academy", "Air Force Academy",
    "Virginia Military Institute", "William and Mary", "College of William & Mary", "GW", "GWU",
    "College of the Holy Cross", "Holy Cross", "Ohio State", "Penn State", "Hawai'i", "UH", "Arkansas-Pine Bluff",
    "Mississippi Valley", "Northern Colorado", "Long Beach State", "Purdue Fort Wayne", "Omaha",
    "University of North Florida", "UNF", "Sacramento State", "Sac State", "Fresno State", "San Jose State",
    "Utah Tech", "Utah Valley", "UVU", "Texas State", "UTRGV", "Abilene Christian", "ACU", "Houston Christian",
    "Tennessee Tech", "Georgia Tech", "Virginia Tech", "Louisiana Tech", "Texas Tech", "UIW", "Saint Louis",
    "Cal Baptist", "CBU", "Grand Canyon", "GCU", "Gardner Webb", "Kennesaw State", "Little Rock", "UALR",
]
ORIGINS = ("high_school_only", "juco", "d1_transfer", "other_four_year", "unknown")
ABBR = {"st": ("state", "saint"), "ark": ("arkansas",), "conn": ("connecticut",), "fla": ("florida",),
        "ga": ("georgia",), "tenn": ("tennessee",), "ala": ("alabama",), "colo": ("colorado",), "mo": ("missouri",),
        "la": ("louisiana",), "caro": ("carolina",), "val": ("valley",), "miss": ("mississippi",),
        "mich": ("michigan",), "ill": ("illinois",), "ky": ("kentucky",), "ind": ("indiana",), "u": ("university",),
        "col": ("college",), "so": ("southern",), "mt": ("mount",), "ft": ("fort",), "univ": ("university",),
        "saint": ("saint", "state"), "state": ("state", "saint")}
D1_STOP = {"the", "university", "of", "at", "in"}


def _school_tokens(s: str) -> list[str]:
    s = fold(s).replace("&", " and ").replace("'", "").replace("’", "")
    s = re.sub(r"\(([^)]*)\)", r" \1 ", s)
    return [t for t in re.split(r"[^a-z0-9]+", s) if t]


def school_keys(s: str) -> set[str]:
    """Spelling variants of a school name with filler words dropped: 'Kent St.' -> {'kentstate',
    'kentsaint'}; 'University of Florida' -> {'florida'}; 'Texas A&M' -> {'texasandm'}."""
    toks = _school_tokens(s)
    if not toks:
        return set()
    alts = [ABBR.get(t, (t,)) for t in toks]
    keys = set()
    for combo in itertools.islice(itertools.product(*alts), 64):
        words = " ".join(combo).split()
        keys.add("".join(w for w in words if w not in D1_STOP))
    return keys - {""}


def d1_keyset(names) -> set[str]:
    out: set = set()
    for n in list(names) + D1_ALIASES:
        out |= school_keys(n)
        out |= school_keys(re.sub(r"\([^)]*\)", "", n))
    return out


_JUCO_TOKS = [tuple(_school_tokens(n)) for n in JUCO_NAMES]


def _juco_listed(toks: list[str]) -> bool:
    for lead in ((), ("college", "of", "the"), ("college", "of")):
        if tuple(toks[:len(lead)]) != lead:
            continue
        rest = toks[len(lead):]
        for e in _JUCO_TOKS:
            if e and tuple(rest[:len(e)]) == e and all(t in JUCO_TAIL for t in rest[len(e):]):
                return True
    return False


def classify_school(name: str, high_school: str, d1keys: set) -> tuple[str, str]:
    """(category, rule) for one previous-school string. Rules in order:
    1. JUCO marker (Community College, CC, C.C., JC, J.C., Junior College, City College) -> juco
    2. a 2025 D1 program name or alias (St./State/Saint, abbreviations, 'University of') -> d1_transfer
    3. 'College of the ...' or a name on the JUCO list (with College/CC/campus words after it) -> juco
    4. the high school itself, or High School / HS / Academy / Prep / School / Catholic / Jesuit /
       Bishop / Country Day without University or College -> high_school_only
    5. anything else -> other_four_year (rule four_year_keyword when it says University, College,
       State, Institute or Tech; residual_unclassified otherwise)."""
    f = fold(name)
    if JUCO_MARKERS.search(f):
        return "juco", "juco_marker"
    if school_keys(name) & d1keys:
        return "d1_transfer", "d1_name"
    toks = _school_tokens(name)
    if JUCO_COLLEGE_OF_THE.search(f) or _juco_listed(toks):
        return "juco", "juco_list"
    if (high_school and letters(high_school) == letters(name)) or (HS_MARKERS.search(f) and not COLLEGE_WORD.search(f)):
        return "high_school_only", "previous_is_high_school"
    if FOUR_YEAR_KEYWORD.search(f):
        return "other_four_year", "four_year_keyword"
    return "other_four_year", "residual_unclassified"


ORIGIN_RANK = {"d1_transfer": 0, "juco": 1, "other_four_year": 2, "high_school_only": 3}


def classify_origin(previous: str, high_school: str, team_lists_previous: bool, d1keys: set,
                    year: str = "unknown") -> tuple[str, str]:
    """Origin of one player. A page that lists no previous school for anyone on the team gives
    'unknown' (the column is missing, not empty). Several schools ('Texas Tech / San Jacinto')
    are each classified and the most informative kept: D1 > JUCO > other four-year > high school.
    A freshman whose previous school matched no rule (residual_unclassified) is taken to come from
    high school (rule freshman_residual_as_high_school): some pages put the high school in the
    previous-school column."""
    if not team_lists_previous:
        return "unknown", "no_previous_school_field_on_page"
    if is_blank(previous):
        return "high_school_only", "blank_previous_school"
    parts = [p for p in re.split(r"\s*(?:/|;|\|)\s*|,\s+(?=[A-Z])", str(previous)) if not is_blank(p)]
    got = [classify_school(p, high_school, d1keys) for p in parts] or [("high_school_only", "blank_previous_school")]
    best = min(got, key=lambda cr: ORIGIN_RANK[cr[0]])
    if best[1] == "residual_unclassified" and year == "Fr":
        return "high_school_only", "freshman_residual_as_high_school"
    return best


# ------------------------------------------------------------------ failure reasons
REASONS = ("bot_protection", "http_403", "no_page", "parse_failure", "other")


def reason_class(reason: str) -> str:
    """bot_protection > http_403 > parse_failure > no_page > other, over every URL the fetcher tried."""
    r = fold(reason)
    if "bot challenge" in r or "incapsula" in r or "cloudflare" in r:
        return "bot_protection"
    if "http 403" in r:
        return "http_403"
    if re.search(r"parsed \d+ players", r):
        return "parse_failure"
    if re.search(r"http 40[04]|http 410|redirected", r):
        return "no_page"
    return "other"


def scrub_reason(reason: str) -> str:
    """The fetcher's reason text with URLs (which can carry page slugs) removed."""
    r = re.sub(r"\(?https?://\S+\)?", "<url>", str(reason or ""))
    return r[:400]


# ------------------------------------------------------------------ names and linkage
def _strip_suffix(tokens: list[str]) -> list[str]:
    while len(tokens) > 1 and letters(tokens[-1]) in SUFFIXES:
        tokens = tokens[:-1]
    return tokens


def roster_name_keys(name: str) -> tuple[set[str], set[str]]:
    """(last-name keys, first-name keys) of a roster full name. Last keys are every trailing run
    of tokens ('Juan De La Cruz' -> delacruz, lacruz, cruz) and each part of a hyphenated last
    name; first keys are the first token and a quoted or parenthesised nickname."""
    raw = str(name or "")
    nick = re.findall(r"[\"“(']([A-Za-z]+)[\"”)']", raw)
    raw = re.sub(r"[\"“(][^\"”)]*[\"”)]", " ", raw)
    s = fold(raw)
    if "," in s:   # 'Smith, Jake' (but not 'Jake Smith, Jr.')
        a, b = s.split(",", 1)
        if letters(b) not in SUFFIXES and b.strip():
            s = f"{b} {a}"
        else:
            s = a
    toks = _strip_suffix([t for t in s.split() if letters(t)])
    if not toks:
        return set(), set()
    if len(toks) == 1:
        return {letters(toks[0])}, set()
    last = {letters(" ".join(toks[i:])) for i in range(1, len(toks))}
    last |= {letters(p) for p in toks[-1].split("-") if len(letters(p)) >= 2}
    first = {letters(toks[0])} | {letters(n) for n in nick}
    return {k for k in last if k}, {k for k in first if k}


def pbp_name_options(check: str) -> list[tuple[str, str]]:
    """Readings of a play-by-play check name as (last-name key, first-name prefix), most likely first.
    'Gholston, J.' -> [(gholston, j)]; 'J. Jones' -> [(jones, j)]; 'T Head' -> [(head, t)];
    'PBrzustewicz' -> [(brzustewicz, p)]; 'Herrera lll' -> [(herrera, '')];
    'Justin Heffl' -> [(justinheffl, ''), (heffl, justin)]."""
    raw = str(check or "").strip()
    s = fold(raw)
    if not s:
        return []
    if "," in s:
        last, first = s.split(",", 1)
        ltoks = _strip_suffix(last.split())
        ftoks = [t for t in first.split() if letters(t) not in SUFFIXES]
        return [(letters(" ".join(ltoks)), letters(ftoks[0]) if ftoks else "")]
    m = re.match(r"^([a-z]{1,3})\.\s*(.+)$", s)
    if m:
        return [(letters(" ".join(_strip_suffix(m.group(2).split()))), m.group(1))]
    m = re.match(r"^([a-z])\s+(.+)$", s)
    if m:
        return [(letters(" ".join(_strip_suffix(m.group(2).split()))), m.group(1))]
    m = re.match(r"^([A-Z])([A-Z][a-z].*)$", raw)
    if m:
        return [(letters(m.group(2)), m.group(1).lower())]
    toks = _strip_suffix(s.split())
    opts = [(letters(" ".join(toks)), "")]
    if len(toks) >= 2:
        opts.append((letters(" ".join(toks[1:])), letters(toks[0])))
    return opts


def build_name_index(roster: pd.DataFrame) -> dict:
    """team id -> list of (pid, last keys, first keys)."""
    idx: dict = {}
    for pid, tid, nm in zip(roster.pid, roster.team_ncaa_id, roster.name):
        lk, fk = roster_name_keys(nm)
        if lk:
            idx.setdefault(tid, []).append((pid, lk, fk))
    return idx


def match_name(check: str, players: list) -> tuple[str, int]:
    """('matched', pid) | ('ambiguous', -1) | ('no_candidate', -1) for one check name against one
    team's roster. Last name must match one of the roster's last keys exactly, or as a prefix
    when the check name is 12+ characters (WMT truncates); the first-name prefix, when given,
    must start the roster first name (or a nickname). An exact last-name match beats a prefix one."""
    truncated = len(str(check)) >= TRUNCATED_LEN
    ambiguous = False
    for lk, fp in pbp_name_options(check):
        if not lk:
            continue
        exact = [p for p in players if lk in p[1]]
        cands = exact or ([p for p in players if any(k.startswith(lk) for k in p[1])] if truncated and len(lk) >= 3 else [])
        if fp:
            cands = [p for p in cands if any(f.startswith(fp) or (len(f) >= 2 and fp.startswith(f)) for f in p[2])]
        if len(cands) == 1:
            return "matched", cands[0][0]
        if len(cands) > 1:
            ambiguous = True
    return ("ambiguous", -1) if ambiguous else ("no_candidate", -1)


# ------------------------------------------------------------------ loading
def load_teams() -> pd.DataFrame:
    rt = pd.read_csv(ROSTER_TEAMS, dtype={"team_ncaa_id": "int64"})
    t = pd.read_csv(TEAMS).rename(columns={"ncaa_team_id": "team_ncaa_id", "team": "team_d1"})
    m = rt.merge(t[["team_ncaa_id", "team_d1", "conference", "tier"]], on="team_ncaa_id", how="left")
    m["team"] = m.team_d1.fillna(m.team)
    m["conference"] = m.conference.fillna("non-D1")
    m["tier"] = m.tier.fillna("non_d1")
    return m[["team_ncaa_id", "team", "conference", "tier", "domain"]]


def load_fetch(fetch_dir: Path) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    state_p, csv_p, fail_p = fetch_dir / "state.json", fetch_dir / "rosters_2025.csv", fetch_dir / "failures.csv"
    state = json.loads(state_p.read_text()) if state_p.exists() else {"done": {}, "failed": {}}
    if csv_p.exists():
        r = pd.read_csv(csv_p, dtype=str, keep_default_na=False)
    else:
        r = pd.DataFrame(columns=["team_ncaa_id", "team", "name", "jersey", "position", "class", "bats", "throws",
                                  "hometown_city", "hometown_state", "high_school", "previous_school",
                                  "source_url", "wmt_person_id"])
    for c in ("hometown_city", "hometown_state", "high_school", "previous_school", "wmt_person_id"):
        if c not in r:
            r[c] = ""
    r = r[r.team_ncaa_id.str.fullmatch(r"\d+")].copy()
    r["team_ncaa_id"] = r.team_ncaa_id.astype("int64")
    if state["done"]:   # rows of a team interrupted mid-write are not used
        r = r[r.team_ncaa_id.astype(str).isin(set(state["done"]))]
    r = r.drop_duplicates(subset=["team_ncaa_id", "name", "jersey", "position"]).reset_index(drop=True)
    fails = pd.read_csv(fail_p, dtype=str, keep_default_na=False) if fail_p.exists() else pd.DataFrame(
        columns=["team_ncaa_id", "team", "domain", "reason", "last_url", "when"])
    return r, state, fails


def load_pa() -> pd.DataFrame:
    cols = ["game_id", "group_id", "bat_team_id", "pit_team_id", "batter", "pitcher", "result"]
    pa = pd.read_csv(PA_EVENTS, usecols=cols, dtype={"batter": str, "pitcher": str}, low_memory=False)
    pa = pa.sort_values(["game_id", "group_id"]).reset_index(drop=True)
    pa["res"] = pa.result.map(lambda r: RES_MAP.get(r, r))
    return pa


# ------------------------------------------------------------------ tables
def scopes(df: pd.DataFrame, cols=("tier", "conference")):
    yield "all", "all", df
    for c in cols:
        for v, g in df.groupby(c, sort=True):
            yield c, v, g


def team_status(teams: pd.DataFrame, state: dict, fails: pd.DataFrame, roster: pd.DataFrame) -> pd.DataFrame:
    T = teams.copy()
    done = {int(k) for k in state.get("done", {})}
    failed = {int(k): v.get("reason", "") for k, v in state.get("failed", {}).items()}
    if not done and not failed:   # no state.json: fall back to the CSVs
        done = set(roster.team_ncaa_id)
        for _, f in fails.iterrows():
            if str(f.team_ncaa_id).isdigit() and int(f.team_ncaa_id) not in done:
                failed[int(f.team_ncaa_id)] = f.reason
    T["status"] = np.where(T.team_ncaa_id.isin(done), "parsed",
                           np.where(T.team_ncaa_id.isin(set(failed)), "failed", "not_attempted"))
    T["reason"] = T.team_ncaa_id.map(failed).fillna("")
    T["reason_class"] = np.where(T.status == "failed", T.reason.map(reason_class), "")
    T["players"] = T.team_ncaa_id.map(roster.groupby("team_ncaa_id").size()).fillna(0).astype(int)
    return T


def fetch_dates(state: dict) -> list:
    """First and last fetch date (YYYY-MM-DD, UTC as the fetcher logs it) over the teams in state.json."""
    when = sorted(str(v.get("when", ""))[:10] for part in ("done", "failed") for v in state.get(part, {}).values()
                  if re.match(r"\d{4}-\d\d-\d\d", str(v.get("when", ""))))
    return [("all", "all", "fetch_first_date", when[0]), ("all", "all", "fetch_last_date", when[-1])] if when else []


def coverage_table(T: pd.DataFrame, R: pd.DataFrame, extra: list) -> pd.DataFrame:
    rows = []
    for sc, val, t in scopes(T, ("tier",)):
        r = R if sc == "all" else R[R.tier == val]
        add = lambda m, v: rows.append({"scope": sc, "scope_value": val, "metric": m, "value": v})
        add("teams_listed", len(t))
        add("teams_attempted", int((t.status != "not_attempted").sum()))
        add("teams_parsed", int((t.status == "parsed").sum()))
        add("teams_failed", int((t.status == "failed").sum()))
        for rc in REASONS:
            add(f"teams_failed_{rc}", int(((t.status == "failed") & (t.reason_class == rc)).sum()))
        add("teams_not_attempted", int((t.status == "not_attempted").sum()))
        add("players_parsed", len(r))
        n = max(len(r), 1)
        add("share_bats_filled", round(r.bats_n.isin(["L", "R", "S"]).sum() / n, 4))
        add("share_throws_filled", round(r.throws_n.isin(["L", "R"]).sum() / n, 4))
        add("share_position_filled", round((r.pos_group != "unknown").sum() / n, 4))
        add("share_class_filled", round((r.class_n != "unknown").sum() / n, 4))
        add("share_hometown_filled", round((~(r.hometown_city.map(is_blank).astype(bool) & r.hometown_state.map(is_blank).astype(bool))).sum() / n, 4))
        add("share_hometown_located", round((~r.area.isin(["unknown", "unrecognized"])).sum() / n, 4))
        add("share_high_school_filled", round((~r.high_school.map(is_blank).astype(bool)).sum() / n, 4))
        add("share_previous_school_filled", round((~r.previous_school.map(is_blank).astype(bool)).sum() / n, 4))
        add("share_origin_classified", round((r.origin != "unknown").sum() / n, 4))
        add("share_wmt_person_id_filled", round((~r.wmt_person_id.map(is_blank).astype(bool)).sum() / n, 4))
        add("teams_listing_previous_school", int(r[~r.previous_school.map(is_blank).astype(bool)].team_ncaa_id.nunique()))
    for sc, val, m, v in extra:
        rows.append({"scope": sc, "scope_value": val, "metric": m, "value": v})
    df = pd.DataFrame(rows)
    df["value"] = pd.Series([int(v) if isinstance(v, (int, float, np.integer, np.floating)) and float(v).is_integer()
                             and not str(m).startswith("share") else v
                             for v, m in zip(df.value, df.metric)], index=df.index, dtype=object)
    return df


def handedness_table(R: pd.DataFrame) -> pd.DataFrame:
    out = []
    for sc, val, g in scopes(R):
        c = g.groupby(["pos_group", "bats_n", "throws_n"]).size().rename("count").reset_index()
        c["share"] = (c["count"] / c.groupby("pos_group")["count"].transform("sum")).round(4)
        c.insert(0, "scope_value", val)
        c.insert(0, "scope", sc)
        out.append(c)
    df = pd.concat(out, ignore_index=True) if out else pd.DataFrame()
    df = df.rename(columns={"pos_group": "position_group", "bats_n": "bats", "throws_n": "throws"})
    df["position_group"] = pd.Categorical(df.position_group, POS_GROUPS, ordered=True)
    return df.sort_values(["scope", "scope_value", "position_group", "bats", "throws"]).reset_index(drop=True)


def link(pa: pd.DataFrame, R: pd.DataFrame, parsed_teams: set) -> tuple[dict, dict]:
    """Name-match every play-by-play batter and pitcher of a team with a parsed roster.
    Returns {(team, check name): (status, pid)} for batters and for pitchers."""
    idx = build_name_index(R)
    out = {}
    for side, tcol, ncol in (("batter", "bat_team_id", "batter"), ("pitcher", "pit_team_id", "pitcher")):
        ids = pa[[tcol, ncol]].drop_duplicates()
        res = {}
        for tid, nm in zip(ids[tcol], ids[ncol]):
            if tid not in parsed_teams:
                res[(tid, nm)] = ("no_roster", -1)
            else:
                res[(tid, nm)] = match_name(nm, idx.get(tid, []))
        out[side] = res
    return out["batter"], out["pitcher"]


def linkage_table(pa, R, bat_map, pit_map, tier_of) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    stats = {}
    for side, tcol, ncol, mp in (("batter", "bat_team_id", "batter", bat_map), ("pitcher", "pit_team_id", "pitcher", pit_map)):
        ident = pa.groupby([tcol, ncol]).size().rename("pa").reset_index()
        ident["status"] = [mp[(t, n)][0] for t, n in zip(ident[tcol], ident[ncol])]
        ident["pid"] = [mp[(t, n)][1] for t, n in zip(ident[tcol], ident[ncol])]
        ident["tier"] = ident[tcol].map(tier_of).fillna("non_d1")
        stats[side] = ident
        for sc, val, g in scopes(ident, ("tier",)):
            on = g[g.status != "no_roster"]
            rr = R if sc == "all" else R[R.tier == val]
            matched_pids = set(on.pid[on.status == "matched"])
            pool = rr[rr.pos_group != "P"] if side == "batter" else rr[rr.pos_group.isin(["P", "two-way"])]
            rows.append({"scope": sc, "scope_value": val, "side": side,
                         "pbp_names": len(on), "matched": int((on.status == "matched").sum()),
                         "ambiguous": int((on.status == "ambiguous").sum()),
                         "no_candidate": int((on.status == "no_candidate").sum()),
                         "pbp_names_team_not_parsed": int((g.status == "no_roster").sum()),
                         "pa_or_bf": int(on.pa.sum()), "pa_or_bf_matched": int(on.pa[on.status == "matched"].sum()),
                         "share_pa_or_bf_matched": round(on.pa[on.status == "matched"].sum() / max(on.pa.sum(), 1), 4),
                         "share_names_matched": round((on.status == "matched").mean(), 4) if len(on) else np.nan,
                         "roster_players": len(pool),
                         "roster_players_matched": int(pool.pid.isin(matched_pids).sum()),
                         "share_roster_matched": round(pool.pid.isin(matched_pids).mean(), 4) if len(pool) else np.nan})
    return pd.DataFrame(rows), stats


def pitcher_role_table(pa, R, pit_map, stats) -> tuple[pd.DataFrame, pd.DataFrame]:
    first = pa.groupby(["game_id", "pit_team_id"], sort=False).head(1)
    st = first.groupby(["pit_team_id", "pitcher"]).size()
    apps = pa.groupby(["pit_team_id", "pitcher"]).game_id.nunique()
    bf = pa.groupby(["pit_team_id", "pitcher"]).size()
    ident = pd.DataFrame({"apps": apps, "starts": st, "bf": bf}).fillna(0).reset_index()
    ident["pid"] = [pit_map[(t, n)][1] if pit_map[(t, n)][0] == "matched" else -1 for t, n in zip(ident.pit_team_id, ident.pitcher)]
    per = ident[ident.pid >= 0].groupby("pid")[["apps", "starts", "bf"]].sum()
    P = R.set_index("pid")
    pit = P.loc[P.index.isin(per.index) | P.pos_group.isin(["P", "two-way"]).values].copy()
    pit = pit.join(per, how="left")
    pit[["apps", "starts", "bf"]] = pit[["apps", "starts", "bf"]].fillna(0)
    pit["role"] = np.where(pit.apps == 0, "unmatched", np.where(pit.starts / pit.apps.clip(lower=1) >= STARTER_SHARE, "starter", "reliever"))
    out = []
    for sc, val, g in scopes(pit.reset_index()):
        c = g.groupby(["role", "throws_n"]).agg(pitchers=("pid", "size"), appearances=("apps", "sum"),
                                                 starts=("starts", "sum"), batters_faced=("bf", "sum")).reset_index()
        c["share_pitchers"] = (c.pitchers / c.groupby("role").pitchers.transform("sum")).round(4)
        c["share_bf"] = (c.batters_faced / c.groupby("role").batters_faced.transform("sum").clip(lower=1)).round(4)
        c.insert(0, "scope_value", val)
        c.insert(0, "scope", sc)
        out.append(c)
    df = pd.concat(out, ignore_index=True).rename(columns={"throws_n": "throws"})
    for c in ("appearances", "starts", "batters_faced"):
        df[c] = df[c].astype(int)
    # batters: bats of roster batters matched to the play-by-play, with their PA
    b = stats["batter"]
    per_b = b[b.status == "matched"].groupby("pid").pa.sum()
    B = R.set_index("pid")
    bat = B.loc[B.index.isin(per_b.index) | (~B.pos_group.isin(["P"])).values].copy()
    bat["pa"] = per_b.reindex(bat.index).fillna(0).astype(int)
    bat["status"] = np.where(bat.pa > 0, "matched", "roster_unmatched")
    out = []
    for sc, val, g in scopes(bat.reset_index()):
        c = g.groupby(["status", "bats_n"]).agg(batters=("pid", "size"), pa=("pa", "sum")).reset_index()
        c["share_batters"] = (c.batters / c.groupby("status").batters.transform("sum")).round(4)
        c["share_pa"] = (c.pa / c.groupby("status").pa.transform("sum").clip(lower=1)).round(4)
        c.insert(0, "scope_value", val)
        c.insert(0, "scope", sc)
        out.append(c)
    bdf = pd.concat(out, ignore_index=True).rename(columns={"bats_n": "bats"})
    return df, bdf


def hands_on_pa(pa, R, bat_map, pit_map, tier_of) -> pd.DataFrame:
    bats = R.set_index("pid").bats_n
    throws = R.set_index("pid").throws_n
    bkey = [bat_map[(t, n)] for t, n in zip(pa.bat_team_id, pa.batter)]
    pkey = [pit_map[(t, n)] for t, n in zip(pa.pit_team_id, pa.pitcher)]
    h = pa.copy()
    h["bpid"] = [k[1] if k[0] == "matched" else -1 for k in bkey]
    h["ppid"] = [k[1] if k[0] == "matched" else -1 for k in pkey]
    h["bats"] = h.bpid.map(bats).fillna("unknown")
    h["throws"] = h.ppid.map(throws).fillna("unknown")
    opp = {"L": "R", "R": "L"}
    h["side"] = np.where(h.bats.isin(["L", "R"]), h.bats,
                         np.where((h.bats == "S") & h.throws.isin(["L", "R"]), h.throws.map(opp).fillna("unknown"), "unknown"))
    h["bat_tier"] = h.bat_team_id.map(tier_of).fillna("non_d1")
    h["pit_tier"] = h.pit_team_id.map(tier_of).fillna("non_d1")
    h["known"] = h.bats.isin(["L", "R", "S"]) & h.throws.isin(["L", "R"])
    return h


def platoon_league_table(h: pd.DataFrame) -> pd.DataFrame:
    k = h[h.known]
    cats = list(RESULTS) + sorted(set(k.res) - set(RESULTS))
    out = []
    for sc, val, g in scopes(k, ("bat_tier", "pit_tier")):
        for basis, col in (("side_used", "side"), ("listed", "bats")):
            c = pd.crosstab([g[col], g.throws], g.res).reindex(columns=cats, fill_value=0)
            c.insert(0, "pa", c.sum(axis=1))
            c = c.reset_index().rename(columns={col: "bat_hand", "throws": "pit_throws"})
            c.insert(0, "basis", basis)
            c.insert(0, "scope_value", val)
            c.insert(0, "scope", sc)
            out.append(c)
    return pd.concat(out, ignore_index=True)


def _logit(p):
    return np.log(p / (1 - p))


_LGF = np.array([math.lgamma(i + 1) for i in range(5001)])


def smoothed_logit_var(n: int, p: float) -> float:
    """Exact variance of logit((X + .5) / (n + 1)) for X ~ Binomial(n, p)."""
    n = int(n)
    x = np.arange(n + 1)
    p = min(max(p, 1e-9), 1 - 1e-9)
    pmf = np.exp(_LGF[n] - _LGF[x] - _LGF[n - x] + x * math.log(p) + (n - x) * math.log(1 - p))
    v = _logit((x + .5) / (n + 1))
    m = (pmf * v).sum()
    return float((pmf * (v - m) ** 2).sum())


SPREAD_SIDES = (("batter", "bpid", "throws", "bats", ("L", "R", "S")),    # side, player, opponent hand, own hand
                ("pitcher", "ppid", "side", "throws", ("L", "R")))


def _split_moments(kk: pd.DataFrame, pid_col: str, opp_col: str, hand_of: pd.Series, rate: str, exact_noise: bool) -> dict:
    """{listed hand: moments} of the logit split (vs L minus vs R) of one rate, for the players in hand_of."""
    succ, trials = SPLIT_RATES[rate]
    n = pd.Series(1, index=kk.index) if trials is None else kk.result.isin(trials).astype(int)
    x = (kk.result.isin(succ) & (n > 0)).astype(int)
    agg = pd.DataFrame({"n": n, "x": x, "pid": kk[pid_col], "opp": kk[opp_col]}).groupby(["pid", "opp"])[["n", "x"]].sum()
    agg = agg.unstack(fill_value=0)
    out = {}
    for hand in ("all",) + tuple(sorted(set(hand_of))):
        ids = hand_of.index if hand == "all" else hand_of.index[hand_of == hand]
        a = agg.reindex(ids).fillna(0)
        if not len(a) or ("n", "L") not in a or ("n", "R") not in a:
            out[hand] = {"players": 0}
            continue
        nL, nR, xL, xR = a["n"]["L"], a["n"]["R"], a["x"]["L"], a["x"]["R"]
        ok = (nL > 0) & (nR > 0)
        nL, nR, xL, xR = nL[ok], nR[ok], xL[ok], xR[ok]
        m = {"players": int(ok.sum())}
        if m["players"] >= MIN_CELL_PLAYERS:
            split = _logit((xL + .5) / (nL + 1)) - _logit((xR + .5) / (nR + 1))
            m["obs_var"] = float(split.var(ddof=1))
            if exact_noise:
                p_i = (xL + xR + .5) / (nL + nR + 1)          # the player's own rate, both hands
                m.update({"mean_trials_vs_L": float(nL.mean()), "mean_trials_vs_R": float(nR.mean()),
                          "pooled_rate_vs_L": float(xL.sum() / nL.sum()), "pooled_rate_vs_R": float(xR.sum() / nR.sum()),
                          "mean_split": float(split.mean()),
                          "mean_noise_var_delta": float(((1 / nL + 1 / nR) / (p_i * (1 - p_i))).mean()),
                          "mean_noise_var": float(np.mean([smoothed_logit_var(u, p) + smoothed_logit_var(v, p)
                                                           for u, v, p in zip(nL, nR, p_i)]))})
        out[hand] = m
    return out


def platoon_spread_table(h: pd.DataFrame, null_draws: int = 20, seed: int = 20261007) -> pd.DataFrame:
    """Individual platoon-split spread, by side, rate and the player's listed hand; no individual rows.
    Players: >= MIN_SPLIT_PA PA (BF) against each hand. Split = logit(rate vs L) - logit(rate vs R)
    on (x + .5) / (n + 1); for batters the hand is the pitcher's, for pitchers the batter's side used.
    Noise: the exact variance of that smoothed logit under Binomial(n, p) at the player's own rate
    over both hands (mean_noise_var; the delta-method value (1/n_L + 1/n_R) / (p (1-p)) is kept as
    mean_noise_var_delta, it overstates rare rates such as HR). true_sd = sqrt(max(0, obs_var -
    mean_noise_var)). Opponent mix: the split also varies because each player faces a different
    set of left- and right-handed opponents; null_obs_var is the observed variance with the
    opponents' hands permuted among opponents (same players, same games, null_draws draws), so
    true_sd_net = sqrt(max(0, obs_var - null_obs_var)) removes noise and opponent mix together.
    Cells under MIN_CELL_PLAYERS players print the count only."""
    k = h[h.known]
    rng = np.random.default_rng(seed)
    rows = []
    for side, pid_col, opp_col, hand_col, _hands in SPREAD_SIDES:
        kk = k[k[opp_col].isin(["L", "R"])]
        pa_n = kk.groupby([pid_col, opp_col]).size().unstack(fill_value=0).reindex(columns=["L", "R"], fill_value=0)
        qual = pa_n[(pa_n.L >= MIN_SPLIT_PA) & (pa_n.R >= MIN_SPLIT_PA)].index
        q = kk[kk[pid_col].isin(qual)]
        hand_of = q.groupby(pid_col)[hand_col].first()
        nulls = []
        for _ in range(null_draws):   # permute the opponents' own hands, then rebuild the opponent hand
            if side == "batter":
                opp_ids = q.ppid.unique()
                perm = dict(zip(opp_ids, rng.permutation(q.groupby("ppid").throws.first().reindex(opp_ids).values)))
                qq = q.assign(throws=q.ppid.map(perm))
            else:
                opp_ids = q.bpid.unique()
                perm = dict(zip(opp_ids, rng.permutation(q.groupby("bpid").bats.first().reindex(opp_ids).values)))
                b = q.bpid.map(perm)
                qq = q.assign(side=np.where(b == "S", q.throws.map({"L": "R", "R": "L"}), b))
            nulls.append(qq)
        for rate in SPLIT_RATES:
            real = _split_moments(q, pid_col, opp_col, hand_of, rate, True)
            null = [_split_moments(qq, pid_col, opp_col, hand_of, rate, False) for qq in nulls]
            for hand, m in real.items():
                row = {"side": side, "rate": rate, "listed_hand": hand, "min_pa_each_hand": MIN_SPLIT_PA, **m}
                if "obs_var" in m:
                    nv = [d[hand]["obs_var"] for d in null if "obs_var" in d.get(hand, {})]
                    row["null_obs_var"] = float(np.mean(nv)) if nv else np.nan
                    row["true_sd"] = math.sqrt(max(0.0, m["obs_var"] - m["mean_noise_var"]))
                    row["true_sd_net"] = math.sqrt(max(0.0, m["obs_var"] - row["null_obs_var"])) if nv else np.nan
                    row["obs_var_se"] = m["obs_var"] * math.sqrt(2 / max(m["players"] - 1, 1))   # normal approximation
                rows.append(row)
    cols = ["side", "rate", "listed_hand", "min_pa_each_hand", "players", "mean_trials_vs_L", "mean_trials_vs_R",
            "pooled_rate_vs_L", "pooled_rate_vs_R", "mean_split", "obs_var", "obs_var_se", "mean_noise_var_delta",
            "mean_noise_var", "true_sd", "null_obs_var", "true_sd_net"]
    return pd.DataFrame(rows).reindex(columns=cols).round(5)


def hometown_tables(R: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    keys = ["team_ncaa_id", "team", "conference", "tier", "area", "area_type", "census_region", "census_division"]
    by_school = R.groupby(keys).size().rename("count").reset_index().rename(columns={"area": "hometown_area"})
    by_conf = R.groupby(["conference", "census_region", "census_division"]).size().rename("count").reset_index()
    by_conf["share"] = (by_conf["count"] / by_conf.groupby("conference")["count"].transform("sum")).round(4)
    return by_school, by_conf


def origin_tables(R: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    keys = ["team_ncaa_id", "team", "conference", "tier", "class_n", "origin"]
    by_school = R.groupby(keys).size().rename("count").reset_index().rename(columns={"class_n": "class"})
    rules = []
    for sc, val, g in scopes(R, ("tier",)):
        c = g.groupby(["origin", "origin_rule"]).size().rename("count").reset_index()
        c["share"] = (c["count"] / max(len(g), 1)).round(4)
        c.insert(0, "scope_value", val)
        c.insert(0, "scope", sc)
        rules.append(c)
    return by_school, pd.concat(rules, ignore_index=True)


# ------------------------------------------------------------------ the name-leak check
OUTPUT_LABELS = {   # fixed labels the tables write (some are surnames too: Pitcher, Starter)
    "all", "tier", "conference", "bat_tier", "pit_tier", "batter", "pitcher", "starter", "reliever", "unmatched",
    "matched", "roster_unmatched", "side_used", "listed", "us_state", "us_territory", "international", "unknown",
    "unrecognized", "p4", "mid", "low", "non_d1", "non-D1", "Fr", "So", "Jr", "Sr", "Gr", "L", "R", "S",
    "blank_previous_school", "no_previous_school_field_on_page", "previous_is_high_school", "juco_marker",
    "juco_list", "d1_name", "four_year_keyword", "residual_unclassified", "freshman_residual_as_high_school", "Northeast", "Midwest", "South", "West",
    "New England", "Middle Atlantic", "East North Central", "West North Central", "South Atlantic",
    "East South Central", "West South Central", "Mountain", "Pacific", "US territory"}
def allowed_vocabulary(teams: pd.DataFrame) -> set[str]:
    """Strings the outputs may legitimately hold: team, conference and place names, labels."""
    words = set(teams.team) | set(teams.conference) | set(pd.read_csv(D1_TEAMS).team) | set(pd.read_csv(TEAMS).team)
    words |= set(STATE_OF.values()) | set(TERRITORY_OF.values()) | set(COUNTRY_OF.values()) | GEO_LABELS
    words |= {n for line in STATES.splitlines() for n in line.split("|")[1].split(";")}
    words |= {r for line in STATES.splitlines() for r in line.split("|")[2:]}
    words |= set(POS_GROUPS) | set(ORIGINS) | set(REASONS) | set(RESULTS) | set(SPLIT_RATES) | OUTPUT_LABELS
    out = set()
    for w in words:
        out |= {fold(w), letters(w)}
    return out


def leak_check(out_dir: Path, roster: pd.DataFrame, allowed: set[str]) -> list[tuple[str, str]]:
    """Every cell of every file written: no roster full name, last name of LEAK_MIN_LAST+ letters,
    hometown city, high school or previous-school name as a whole cell, and no full name inside
    a cell (word n-grams). Strings that are also team, conference or place names are skipped."""
    full, last, other = set(), set(), set()
    for nm in roster.name:
        toks = _strip_suffix([t for t in fold(re.sub(r"[\"“(][^\"”)]*[\"”)]", " ", str(nm))).split() if letters(t)])
        if len(toks) >= 2:
            full.add(" ".join(letters(t) for t in toks))
            ln = letters(toks[-1])
            if len(ln) >= LEAK_MIN_LAST:
                last.add(ln)
    for col in ("hometown_city", "high_school", "previous_school"):
        for v in roster[col]:
            if not is_blank(v) and len(letters(v)) >= 4:
                other.add(letters(v))
    full -= allowed
    last -= allowed
    other -= allowed
    full_keys = {f.replace(" ", "") for f in full}
    hits = []
    for f in sorted(out_dir.rglob("*")):
        if not f.is_file():
            continue
        text = f.read_text(errors="replace")
        cells = re.split(r"[,\n\t|]", text)
        for cell in cells:
            c = letters(cell)
            if not c or c in allowed:
                continue
            if c in full_keys or c in last or c in other:
                hits.append((f.name, cell.strip()))
                continue
            words = [letters(w) for w in fold(cell).split() if letters(w)]
            for n in (2, 3, 4):
                for i in range(len(words) - n + 1):
                    if " ".join(words[i:i + n]) in full:
                        hits.append((f.name, cell.strip()))
    return hits


# ------------------------------------------------------------------ main pipeline
def prepare_players(roster: pd.DataFrame, teams: pd.DataFrame, d1keys: set) -> pd.DataFrame:
    R = roster.merge(teams[["team_ncaa_id", "conference", "tier"]], on="team_ncaa_id", how="left")
    R["team"] = R.team_ncaa_id.map(dict(zip(teams.team_ncaa_id, teams.team))).fillna(R.team)
    R["conference"] = R.conference.fillna("non-D1")
    R["tier"] = R.tier.fillna("non_d1")
    R["pid"] = np.arange(len(R))
    R["pos_group"] = R.position.map(position_group)
    R["bats_n"] = R.bats.map(lambda v: v if v in ("L", "R", "S") else "unknown")
    R["throws_n"] = R.throws.map(lambda v: v if v in ("L", "R") else "unknown")
    R["class_n"] = R["class"].map(class_year)
    loc = [locate(c, s) for c, s in zip(R.hometown_city, R.hometown_state)]
    R["area"], R["area_type"], R["census_region"], R["census_division"] = (list(x) for x in zip(*loc)) if loc else ([], [], [], [])
    lists_prev = R.groupby("team_ncaa_id").previous_school.agg(lambda s: bool((~s.map(is_blank).astype(bool)).any()))
    og = [classify_origin(p, hs, bool(lists_prev.get(t, False)), d1keys, y)
          for p, hs, t, y in zip(R.previous_school, R.high_school, R.team_ncaa_id, R.class_n)]
    R["origin"], R["origin_rule"] = (list(x) for x in zip(*og)) if og else ([], [])
    return R


def aggregate(fetch_dir: Path, out_dir: Path, pa: pd.DataFrame | None = None, quiet: bool = False) -> dict:
    teams = load_teams()
    roster, state, fails = load_fetch(fetch_dir)
    d1keys = d1_keyset(pd.read_csv(D1_TEAMS).team.tolist() + pd.read_csv(TEAMS).team.tolist())
    R = prepare_players(roster, teams, d1keys)
    T = team_status(teams, state, fails, R)
    failures = T[T.status == "failed"].assign(reason=lambda d: d.reason.map(scrub_reason))[
        ["team_ncaa_id", "team", "tier", "conference", "reason_class", "reason"]]
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("*.csv"):
        f.unlink()
    if R.empty:   # nothing parsed: coverage and failures only
        tables = {"coverage.csv": coverage_table(T, R, fetch_dates(state)), "failures.csv": failures}
        for name, df in tables.items():
            df.to_csv(out_dir / name, index=False)
        if not quiet:
            print(f"no players parsed ({len(failures)} teams failed); wrote coverage.csv and failures.csv only")
        return {"teams_parsed": 0, "teams_failed": len(failures), "players": 0, "tables": {k: len(v) for k, v in tables.items()}}
    pa = load_pa() if pa is None else pa
    tier_of = dict(zip(pd.read_csv(TEAMS).ncaa_team_id, pd.read_csv(TEAMS).tier))
    parsed = set(T.team_ncaa_id[T.status == "parsed"])
    bat_map, pit_map = link(pa, R, parsed)
    linkage, stats = linkage_table(pa, R, bat_map, pit_map, tier_of)
    roles, batters = pitcher_role_table(pa, R, pit_map, stats)
    h = hands_on_pa(pa, R, bat_map, pit_map, tier_of)
    extra = fetch_dates(state) + [("all", "all", "pbp_pa_total", len(h)), ("all", "all", "pbp_pa_both_hands_known", int(h.known.sum())),
             ("all", "all", "pbp_pa_both_hands_share", round(float(h.known.mean()), 4))]
    for t, g in h.groupby("bat_tier"):
        extra += [("tier", t, "pbp_pa_total", len(g)), ("tier", t, "pbp_pa_both_hands_share", round(float(g.known.mean()), 4))]
    tables = {
        "coverage.csv": coverage_table(T, R, extra),
        "failures.csv": failures,
        "handedness_by_position.csv": handedness_table(R),
        "linkage.csv": linkage,
        "pitcher_throws_by_role.csv": roles,
        "batter_bats_matched.csv": batters,
        "platoon_league.csv": platoon_league_table(h),
        "platoon_spread.csv": platoon_spread_table(h),
    }
    tables["hometown_by_school.csv"], tables["hometown_by_conference.csv"] = hometown_tables(R)
    tables["origins_by_school.csv"], tables["origins_rules.csv"] = origin_tables(R)
    for name, df in tables.items():
        df.to_csv(out_dir / name, index=False)
    hits = leak_check(out_dir, R, allowed_vocabulary(teams))
    if hits:   # remove what was written, and name only the files (never the cells) in the message
        for f in out_dir.glob("*.csv"):
            f.unlink()
        raise AssertionError(f"roster names found in {len(hits)} output cells, e.g. in {sorted({h[0] for h in hits})}; "
                             "nothing may be committed")
    summary = {"teams_parsed": int((T.status == "parsed").sum()), "teams_failed": int((T.status == "failed").sum()),
               "players": len(R), "tables": {k: len(v) for k, v in tables.items()},
               "batter_pa_matched": float(linkage.query("scope == 'all' and side == 'batter'").share_pa_or_bf_matched.iloc[0]),
               "pitcher_bf_matched": float(linkage.query("scope == 'all' and side == 'pitcher'").share_pa_or_bf_matched.iloc[0]),
               "pa_both_hands_share": round(float(h.known.mean()), 4)}
    if not quiet:   # counts only; never a name
        print(json.dumps(summary, indent=1))
        print(f"leak check passed: no roster name in {len(tables)} files ({out_dir})")
    return summary


# ------------------------------------------------------------------ self-test
FIRSTS = ["Aaron", "Blake", "Cole", "Drew", "Evan", "Finn", "Grant", "Hunter", "Isaac", "Jake", "Kyle", "Luke",
          "Mason", "Nate", "Owen", "Parker", "Quinn", "Ryan", "Seth", "Tyler", "Uriel", "Victor", "Wyatt", "Xavier",
          "Yusuf", "Zach"]
FAKE_STATES = ["La.", "Texas", "TX", "Calif.", "Fla.", "Ga.", "N.C.", "Ontario, Canada", "Dominican Republic", "",
               "Okla.", "Puerto Rico", "Ariz.", "Tenn.", "Miss.", "Ala.", "Ill.", "Ohio", "Wash.", "Venezuela",
               "New South Wales, Australia", "Mo.", "Kan.", "Ark.", "Penn.", "Md.", "Va.", "S.C.", "Nowhere Land"]
FAKE_PREV = ["", "", "", "", "", "", "San Jacinto College", "Chipola", "Walters State CC", "Iowa Western",
             "McLennan Community College", "Texas Tech", "Kent St.", "University of Florida", "LSU", "Miss. State",
             "Florida Southern", "Tampa", "Lubbock Christian", "IMG Academy", "Wallace State", "Jesuit HS",
             "Seminole State College", "College of the Canyons", "Georgia Southern", "Howard College", "Howard Payne",
             "Texas Tech / San Jacinto", "Mesa State", "Butler CC"]
FAKE_CLASS = ["Fr.", "R-Fr.", "So.", "Redshirt Sophomore", "Jr.", "RS-Jr.", "Sr.", "Senior", "Gr.", "5th", "Graduate", ""]
FAKE_POS_BAT = ["C", "INF", "OF", "1B", "UT", "C/OF", "IF", "SS", "2B", "OF/INF", "", "3B", "DH", "C/1B"]


def synthetic_rosters(pa: pd.DataFrame, teams: pd.DataFrame, out: Path, seed: int = 20261007) -> None:
    """Fake rosters for the teams in the play-by-play: one player per (team, last name, initial)
    read from the check names, with invented first names, hands, hometowns, classes and origins;
    8% of them left off, 6 invented extras per team, ~7% of teams 'failed'."""
    rng = np.random.default_rng(seed)
    ids = pd.concat([pa[["bat_team_id", "batter"]].set_axis(["tid", "nm"], axis=1).assign(pit=0),
                     pa[["pit_team_id", "pitcher"]].set_axis(["tid", "nm"], axis=1).assign(pit=1)])
    ids = ids.groupby(["tid", "nm"]).pit.max().reset_index()
    ids = ids[ids.tid.isin(set(teams.team_ncaa_id))]
    tids = sorted(int(t) for t in ids.tid.unique())
    failed = set(rng.choice(tids, size=max(1, len(tids) // 15), replace=False).tolist())
    reasons = ["/sports/baseball/roster/2025: bot challenge page", "/sports/baseball/roster/2025: HTTP 403",
               "/sports/baseball/roster/2025: HTTP 404; /sports/bsb/roster/season/2025: HTTP 404",
               "/sports/baseball/roster/2025: parsed 3 players with bats/throws",
               "no domain in roster_teams.csv (add one and rerun)",
               "/sports/baseball/roster/2025: redirected away from the baseball roster (https://x.edu/sports/soc/roster/player/someone)"]
    rows, state = [], {"done": {}, "failed": {}}
    no_prev_teams = set(rng.choice(tids, size=len(tids) // 5, replace=False).tolist())
    name_of = dict(zip(teams.team_ncaa_id, teams.team))
    for tid in tids:
        if tid in failed:
            state["failed"][str(tid)] = {"reason": str(rng.choice(reasons)), "url": "", "when": "2026-10-07 00:00"}
            continue
        seen = {}
        for nm, pit in zip(ids.nm[ids.tid == tid], ids.pit[ids.tid == tid]):
            opts = pbp_name_options(nm)
            if not opts or not opts[0][0]:
                continue
            lk, fp = opts[0]
            key = (lk, fp[:1])
            seen[key] = (max(pit, seen.get(key, (0, ""))[0]), nm, fp)
        for (lk, ini), (pit, nm, fp) in seen.items():
            if rng.random() < 0.08:
                continue
            cands = [f for f in FIRSTS if fp and f.lower().startswith(fp)]
            first = cands[0] if cands else ((fp.capitalize() + "son") if fp else str(rng.choice(FIRSTS)))
            last = lk.capitalize() + ("er" if len(nm) >= TRUNCATED_LEN else "")
            if rng.random() < 0.03:
                last += " III"
            rows.append(_fake_player(rng, tid, name_of, f"{first} {last}", bool(pit), tid in no_prev_teams))
        for j in range(6):
            rows.append(_fake_player(rng, tid, name_of, f"{rng.choice(FIRSTS)} Zzextra{tid % 1000}x{j}",
                                     bool(rng.random() < .5), tid in no_prev_teams))
        state["done"][str(tid)] = {"players": int(sum(r["team_ncaa_id"] == tid for r in rows)), "parser": "json",
                                   "when": "2026-10-07 00:00"}
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "rosters_2025.csv", index=False)
    (out / "state.json").write_text(json.dumps(state))
    pd.DataFrame([{"team_ncaa_id": k, "team": name_of.get(int(k), ""), "domain": "x.edu", "reason": v["reason"],
                   "last_url": "", "when": v["when"]} for k, v in state["failed"].items()]).to_csv(out / "failures.csv", index=False)


def _fake_player(rng, tid, name_of, name, pitcher, no_prev) -> dict:
    if pitcher:
        throws = "L" if rng.random() < .28 else "R"
        pos = ("LHP" if throws == "L" else "RHP") if rng.random() < .93 else f"1B/{'LHP' if throws == 'L' else 'RHP'}"
        bats = throws if rng.random() < .85 else ("S" if rng.random() < .3 else "R")
    else:
        throws = "L" if rng.random() < .15 else "R"
        u = rng.random()
        bats = "L" if u < .33 else ("S" if u < .38 else "R")
        pos = str(rng.choice(FAKE_POS_BAT))
    if rng.random() < .02:
        bats = ""
    st = str(rng.choice(FAKE_STATES))
    return {"team_ncaa_id": tid, "team": name_of.get(tid, ""), "name": name, "jersey": str(int(rng.integers(0, 60))),
            "position": pos, "class": str(rng.choice(FAKE_CLASS)), "bats": bats, "throws": throws,
            "hometown_city": "" if not st else f"Faketown{int(rng.integers(0, 500))}", "hometown_state": st,
            "high_school": f"Fake Central HS {int(rng.integers(0, 900))}",
            "previous_school": "" if no_prev else str(rng.choice(FAKE_PREV)), "source_url": "https://x.edu/roster",
            "wmt_person_id": ""}


def _unit_checks(d1keys: set) -> list[str]:
    bad = []
    expect = [
        (position_group, "RHP", "P"), (position_group, "LHP", "P"), (position_group, "INF", "IF"),
        (position_group, "C/OF", "C"), (position_group, "UT", "UT/DH"), (position_group, "1B/RHP", "two-way"),
        (position_group, "OF", "OF"), (position_group, "", "unknown"), (position_group, "Infielder", "IF"),
        (position_group, "RHP/OF", "two-way"), (position_group, "SS/2B", "IF"),
        (class_year, "R-Fr.", "Fr"), (class_year, "Redshirt Sophomore", "So"), (class_year, "RS-Jr.", "Jr"),
        (class_year, "5th", "Gr"), (class_year, "Gr.", "Gr"), (class_year, "Senior", "Sr"), (class_year, "", "unknown"),
        (class_year, "r-So.", "So"), (class_year, "Graduate Student", "Gr"),
        (lambda s: locate("Baton Rouge", s)[0], "La.", "LA"), (lambda s: locate("Toronto", s)[0], "Ontario, Canada", "Canada"),
        (lambda s: locate("x", s)[0], "Texas, USA", "TX"), (lambda s: locate("Venezuela", s)[0], "", "Venezuela"),
        (lambda s: locate("", s)[0], "", "unknown"), (lambda s: locate("Paris", s)[0], "Somewhere", "unrecognized"),
        (lambda s: locate("Washington", s)[0], "D.C.", "DC"), (lambda s: locate("San Juan", s)[1], "P.R.", "us_territory"),
        (lambda s: locate("x", s)[3], "W.Va.", "South Atlantic"),
    ]
    for fn, arg, want in expect:
        if fn(arg) != want:
            bad.append(f"{arg!r} -> {fn(arg)!r}, want {want!r}")
    for school, want in [("San Jacinto College", "juco"), ("Walters State CC", "juco"), ("Chipola", "juco"),
                         ("Kent St.", "d1_transfer"), ("University of Florida", "d1_transfer"), ("LSU", "d1_transfer"),
                         ("Miss. State", "d1_transfer"), ("Florida Southern", "other_four_year"),
                         ("IMG Academy", "high_school_only"), ("Howard College", "juco"), ("Howard Payne", "other_four_year"),
                         ("College of the Canyons", "juco"), ("Texas A&M", "d1_transfer"), ("Southern Miss", "d1_transfer"),
                         ("Seminole State College of Florida", "juco"), ("LSU Eunice", "juco"), ("Butler CC", "juco"),
                         ("College of Charleston", "d1_transfer"), ("St. John's", "d1_transfer"), ("Jesuit HS", "high_school_only"),
                         ("Northeastern JC", "juco"), ("Northeastern", "d1_transfer"), ("Iowa Western", "juco"),
                         ("Lamar CC", "juco"), ("Lamar University", "d1_transfer"), ("Cal Baptist", "d1_transfer"),
                         ("Mater Dei", "high_school_only"), ("Catholic University", "other_four_year"),
                         ("Bishop Gorman HS", "high_school_only"), ("Tampa", "other_four_year")]:
        got = classify_school(school, "", d1keys)[0]
        if got != want:
            bad.append(f"origin {school!r} -> {got}, want {want}")
    for check, roster, want in [("Gholston, J.", ["Jake Gholston", "Tom Gholston"], 0), ("J. Jones", ["Jake Jones"], 0),
                                ("Herrera lll", ["Luis Herrera III"], 0), ("T Head", ["Tim Head"], 0),
                                ("PBrzustewicz", ["Paul Brzustewicz"], 0), ("Van Valkenbu", ["Joe Van Valkenburg"], 0),
                                ("Justin Heffl", ["Justin Hefflinger"], 0), ("Harris, Das.", ["Dasan Harris", "Dante Harris"], 0),
                                ("Smith", ["Jake Smith", "Tom Smith"], -1), ("De La Cruz, J.", ["Juan De La Cruz"], 0),
                                ("Cruz, J.", ["Juan De La Cruz"], 0), ("Smith-Jones, K.", ["Kyle Smith-Jones"], 0),
                                ("Jones, K.", ["Kyle Smith-Jones"], 0), ("BURDETTE, C.", ["Cole Burdette"], 0),
                                ("Saum,C", ["Cole Saum"], 0), ("Martinez, An", ["Andres Martinez", "Alex Martinez"], 0),
                                ("O'SHAUGHNESS", ["Pat O'Shaughnessy"], 0), ("Zed, Q.", ["Jake Smith"], -1)]:
        players = [(i, *roster_name_keys(n)) for i, n in enumerate(roster)]
        st, pid = match_name(check, players)
        if pid != want:
            bad.append(f"match {check!r} -> {st} {pid}, want {want}")
    return bad


def selftest(keep: str | None = None) -> int:
    ok = True
    teams = load_teams()
    d1keys = d1_keyset(pd.read_csv(D1_TEAMS).team.tolist() + pd.read_csv(TEAMS).team.tolist())
    bad = _unit_checks(d1keys)
    for b in bad:
        print("UNIT", b)
    print("unit checks (positions, classes, hometowns, origins, name matching):", "passed" if not bad else f"{len(bad)} FAILED")
    ok &= not bad
    pa = load_pa()
    tmp = Path(tempfile.mkdtemp(prefix="roster_selftest_"))
    try:
        fetch, out = tmp / "fetch", tmp / "aggregates"
        synthetic_rosters(pa, teams, fetch)
        s = aggregate(fetch, out, pa=pa, quiet=True)
        print("selftest tables (rows):", ", ".join(f"{k} {v}" for k, v in s["tables"].items()))
        print(f"selftest: {s['teams_parsed']} teams parsed, {s['teams_failed']} failed, {s['players']} synthetic players")
        lk = pd.read_csv(out / "linkage.csv")
        for _, r in lk[lk.scope_value.isin(["all", "p4", "mid", "low"])].iterrows():
            print(f"  linkage {r.scope_value:4} {r.side:7}: {r.matched}/{r.pbp_names} names matched "
                  f"({r.ambiguous} ambiguous, {r.no_candidate} no candidate), PA/BF matched {r.share_pa_or_bf_matched:.3f}, "
                  f"roster matched {r.share_roster_matched:.3f}")
        print(f"  PA with both hands known: {s['pa_both_hands_share']:.3f}")
        if s["batter_pa_matched"] < .85 or s["pitcher_bf_matched"] < .85:
            ok = False
            print("FAIL: match rate below .85 on synthetic rosters built from the play-by-play names")
        # the synthetic hands must come back out: L share of matched pitchers ~ .28
        roles = pd.read_csv(out / "pitcher_throws_by_role.csv", keep_default_na=False)
        a = roles[(roles.scope == "all") & roles.role.isin(["starter", "reliever"])]
        l_share = a[a.throws == "L"].pitchers.sum() / a.pitchers.sum()
        print(f"  matched pitchers throwing L: {l_share:.3f} (synthetic .28); roles: "
              + ", ".join(f"{r} {a[a.role == r].pitchers.sum()}" for r in ("starter", "reliever")))
        ok &= abs(l_share - .28) < .03
        pl = pd.read_csv(out / "platoon_league.csv", keep_default_na=False)
        pa_all = pl[pl.scope == "all"]
        cov = pd.read_csv(out / "coverage.csv", keep_default_na=False)
        known = int(cov[(cov.scope == "all") & (cov.metric == "pbp_pa_both_hands_known")].value.iloc[0])
        sums = {b: int(pa_all[pa_all.basis == b].pa.sum()) for b in ("side_used", "listed")}
        print(f"  platoon_league PA: side_used {sums['side_used']}, listed {sums['listed']}, both hands known {known}")
        ok &= sums["side_used"] == sums["listed"] == known
        sp = pd.read_csv(out / "platoon_spread.csv")
        print("  platoon_spread (fake hands are independent of outcomes, so noise/observed should be near 1):")
        for _, r in sp[sp.listed_hand == "all"].iterrows():
            ratio = r.mean_noise_var / r.obs_var if r.obs_var > 0 else float("nan")
            print(f"    {r.side:7} {r.rate:5} n={int(r.players):4}  mean split {r.mean_split:+.3f}  obs var {r.obs_var:.4f}  "
                  f"noise {r.mean_noise_var:.4f} (delta {r.mean_noise_var_delta:.4f})  ratio {ratio:.2f}  true SD {r.true_sd:.3f}  "
                  f"null {r.null_obs_var:.4f}  net SD {r.true_sd_net:.3f}")
            if r.rate in ("K", "BB", "OB") and not (.7 < ratio < 1.3):
                ok = False
                print("FAIL: binomial noise does not match the observed split variance on fake hands")
        dev = (sp.obs_var - sp.null_obs_var).abs() / sp.obs_var_se
        print(f"  |observed - permutation null| / SE on fake hands, max over all cells: {dev.max():.2f} (should be < 3)")
        ok &= bool(dev.max() < 3)
        oc = pd.read_csv(out / "origins_rules.csv", keep_default_na=False)
        print("  origins (all):", ", ".join(f"{o} {oc[(oc.scope == 'all') & (oc.origin == o)]['count'].sum()}" for o in ORIGINS))
        hb = pd.read_csv(out / "hometown_by_school.csv", keep_default_na=False)
        print("  hometown area types:", hb.groupby("area_type")["count"].sum().to_dict())
        fl = pd.read_csv(out / "failures.csv", keep_default_na=False)
        ok &= not fl.reason.str.contains("://").any()
        print("  failures by class:", fl.reason_class.value_counts().to_dict())
        # the leak check itself must catch a name (negative tests)
        roster = pd.read_csv(fetch / "rosters_2025.csv", dtype=str, keep_default_na=False)
        R = roster.assign(team_ncaa_id=roster.team_ncaa_id.astype(int))
        allowed = allowed_vocabulary(teams)
        probe = tmp / "leakprobe"
        for label, cell in (("full name", R.name.iloc[0]),
                            ("last name", next(n.split()[-1] for n in R.name if len(letters(n.split()[-1])) >= LEAK_MIN_LAST
                                               and letters(n.split()[-1]) not in allowed)),
                            ("previous school", "Lubbock Christian"),
                            ("name inside a cell", f"note: {R.name.iloc[5]} (3)")):
            shutil.rmtree(probe, ignore_errors=True)
            shutil.copytree(out, probe)
            with open(probe / "coverage.csv", "a") as fh:
                fh.write(f'all,all,"{cell}",1\n')
            caught = bool(leak_check(probe, R, allowed))
            print(f"  leak check catches an injected {label}: {caught}")
            ok &= caught
        print("  leak check on the real selftest outputs:", "clean" if not leak_check(out, R, allowed) else "LEAK")
        if keep:
            shutil.copytree(tmp, keep, dirs_exist_ok=True, ignore=shutil.ignore_patterns("leakprobe"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("selftest", "passed" if ok else "FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="fetch_dir", default=str(ROOT / "data/ncaa_2025/rosters"),
                    help="the fetcher's output directory (rosters_2025.csv, state.json, failures.csv)")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--keep", help="selftest: also copy the synthetic fetch and the aggregates to this directory")
    a = ap.parse_args()
    if a.selftest:
        return selftest(a.keep)
    aggregate(Path(a.fetch_dir), Path(a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
