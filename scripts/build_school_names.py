"""Display names for the 307 D1 programs (owner request 2026-10-09): app-side, display only.

Writes app/school_names.csv, one row per school in data/schools/schools.csv (the engine PR #17 identity file):
  tid, ncaa_team_id, short (the identity file's NCAA-style name, e.g. "Central Mich."), full (the common full name,
  "Central Michigan"), abbr (a 2-5 letter abbreviation for tight spaces, "CMU"), abbr_source ("common": the
  abbreviation the school and the press use; "guess": a ticker-style abbreviation chosen here, for the owner to check).

The full name expands the NCAA short name (St. -> State, Mich. -> Michigan, ...) with overrides for the names
that are not a simple expansion. Nothing here reaches the engine: the engine keeps its own team ids and names.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/schools/schools.csv"
OUT = ROOT / "app/school_names.csv"

EXPAND = {"St.": "State", "Mich.": "Michigan", "Ill.": "Illinois", "Fla.": "Florida", "Ga.": "Georgia", "Ky.": "Kentucky",
          "Tenn.": "Tennessee", "Ala.": "Alabama", "Ark.": "Arkansas", "Miss.": "Mississippi", "La.": "Louisiana", "Caro.": "Carolina",
          "Conn.": "Connecticut", "Mo.": "Missouri", "Colo.": "Colorado", "Ind.": "Indiana", "So.": "Southern", "Val.": "Valley",
          "Col.": "College", "U.": "University"}
FULL = {"A&M-Corpus Christi": "Texas A&M-Corpus Christi", "Alcorn": "Alcorn State", "App State": "Appalachian State",
        "Ark.-Pine Bluff": "Arkansas-Pine Bluff", "Army West Point": "Army", "CSU Bakersfield": "Cal State Bakersfield",
        "CSUN": "Cal State Northridge", "Cal St. Fullerton": "Cal State Fullerton", "Central Conn. St.": "Central Connecticut State",
        "Charleston So.": "Charleston Southern", "Col. of Charleston": "College of Charleston", "DBU": "Dallas Baptist",
        "ETSU": "East Tennessee State", "FDU": "Fairleigh Dickinson", "FGCU": "Florida Gulf Coast", "FIU": "Florida International",
        "LIU": "Long Island", "LMU (CA)": "Loyola Marymount", "LSU New Orleans": "New Orleans", "Lamar University": "Lamar",
        "Miami (FL)": "Miami", "Mississippi Val.": "Mississippi Valley State", "N.C. A&T": "North Carolina A&T", "NIU": "Northern Illinois",
        "Prairie View": "Prairie View A&M", "Queens (NC)": "Queens", "SFA": "Stephen F. Austin", "SIUE": "SIU Edwardsville",
        "Saint Mary's (CA)": "Saint Mary's", "Seattle U": "Seattle", "Southern California": "USC", "Southern Miss.": "Southern Miss",
        "Southern U.": "Southern", "St. John's (NY)": "St. John's", "St. Thomas (MN)": "St. Thomas", "UAlbany": "Albany",
        "UIW": "Incarnate Word", "ULM": "Louisiana-Monroe", "UMES": "Maryland Eastern Shore", "UNCW": "UNC Wilmington",
        "Penn": "Penn", "Ole Miss": "Ole Miss", "BYU": "BYU", "LSU": "LSU", "TCU": "TCU", "UAB": "UAB", "UCF": "UCF", "UCLA": "UCLA",
        "UConn": "UConn", "UIC": "UIC", "UMBC": "UMBC", "UNLV": "UNLV", "UTRGV": "UTRGV", "UTSA": "UTSA", "VCU": "VCU", "VMI": "VMI",
        "NJIT": "NJIT", "NC State": "NC State", "The Citadel": "The Citadel", "Texas A&M": "Texas A&M", "Miami (OH)": "Miami (OH)",
        "Omaha": "Omaha", "Louisiana": "Louisiana", "McNeese": "McNeese", "Little Rock": "Little Rock", "Milwaukee": "Milwaukee",
        "Mount St. Mary's": "Mount St. Mary's", "Saint Joseph's": "Saint Joseph's", "Saint Louis": "Saint Louis",
        "Saint Peter's": "Saint Peter's", "St. Bonaventure": "St. Bonaventure", "Purdue Fort Wayne": "Purdue Fort Wayne",
        "Southeast Mo. St.": "Southeast Missouri State", "UMass Lowell": "UMass Lowell", "Sam Houston": "Sam Houston",
        "UT Arlington": "UT Arlington", "UT Martin": "UT Martin", "USC Upstate": "USC Upstate", "UC San Diego": "UC San Diego"}

# every school's abbreviation (unique across the 307; a clash is resolved with the school's own alternate form)
ABBR = {"A&M-Corpus Christi": "AMCC", "Abilene Christian": "ACU", "Air Force": "AF", "Akron": "AKR", "Alabama": "ALA", "Alabama A&M": "AAMU",
        "Alabama St.": "ALST", "Alcorn": "ALCN", "App State": "APP", "Arizona": "ARIZ", "Arizona St.": "ASU", "Ark.-Pine Bluff": "UAPB",
        "Arkansas": "ARK", "Arkansas St.": "ARST", "Army West Point": "ARMY", "Auburn": "AUB", "Austin Peay": "APSU", "BYU": "BYU",
        "Ball St.": "BALL", "Baylor": "BAY", "Bellarmine": "BELL", "Belmont": "BEL", "Bethune-Cookman": "BCU", "Binghamton": "BING",
        "Boston College": "BC", "Bowling Green": "BGSU", "Bradley": "BRAD", "Brown": "BRWN", "Bryant": "BRY", "Bucknell": "BUCK",
        "Butler": "BUT", "CSU Bakersfield": "CSUB", "CSUN": "CSUN", "Cal Poly": "CP", "Cal St. Fullerton": "CSUF", "California": "CAL",
        "California Baptist": "CBU", "Campbell": "CAMP", "Canisius": "CAN", "Central Ark.": "UCA", "Central Conn. St.": "CCSU",
        "Central Mich.": "CMU", "Charleston So.": "CHSO", "Charlotte": "CLT", "Cincinnati": "CIN", "Clemson": "CLEM", "Coastal Carolina": "CCU",
        "Col. of Charleston": "CofC", "Columbia": "COLU", "Coppin St.": "COPP", "Cornell": "COR", "Creighton": "CREI", "DBU": "DBU",
        "Dartmouth": "DART", "Davidson": "DAV", "Dayton": "DAY", "Delaware": "DEL", "Delaware St.": "DSU", "Duke": "DUKE", "ETSU": "ETSU",
        "East Carolina": "ECU", "Eastern Ill.": "EIU", "Eastern Ky.": "EKU", "Eastern Mich.": "EMU", "Elon": "ELON", "Evansville": "EVAN",
        "FDU": "FDU", "FGCU": "FGCU", "FIU": "FIU", "Fairfield": "FAIR", "Fla. Atlantic": "FAU", "Florida": "FLA", "Florida A&M": "FAMU",
        "Florida St.": "FSU", "Fordham": "FOR", "Fresno St.": "FRES", "Ga. Southern": "GASO", "Gardner-Webb": "GWU", "George Mason": "GMU",
        "George Washington": "GW", "Georgetown": "GTWN", "Georgia": "UGA", "Georgia St.": "GSU", "Georgia Tech": "GT", "Gonzaga": "GONZ",
        "Grambling": "GRAM", "Grand Canyon": "GCU", "Harvard": "HARV", "Hawaii": "HAW", "High Point": "HPU", "Hofstra": "HOF",
        "Holy Cross": "HC", "Houston": "HOU", "Houston Christian": "HCU", "Illinois": "ILL", "Illinois St.": "ILST", "Indiana": "IU",
        "Indiana St.": "INST", "Iona": "IONA", "Iowa": "IOWA", "Jackson St.": "JKST", "Jacksonville": "JAX", "Jacksonville St.": "JVST",
        "James Madison": "JMU", "Kansas": "KU", "Kansas St.": "KSU", "Kennesaw St.": "KENN", "Kent St.": "KENT", "Kentucky": "UK",
        "LIU": "LIU", "LMU (CA)": "LMU", "LSU": "LSU", "LSU New Orleans": "UNO", "Lafayette": "LAF", "Lamar University": "LAM",
        "Le Moyne": "LEM", "Lehigh": "LEH", "Liberty": "LIB", "Lindenwood": "LIN", "Lipscomb": "LIP", "Little Rock": "UALR",
        "Long Beach St.": "LBSU", "Longwood": "LONG", "Louisiana": "ULL", "Louisiana Tech": "LT", "Louisville": "LOU", "Maine": "ME",
        "Manhattan": "MAN", "Marist": "MRST", "Marshall": "MRSH", "Maryland": "UMD", "Massachusetts": "UMASS", "McNeese": "MCN",
        "Memphis": "MEM", "Mercer": "MER", "Mercyhurst": "MERC", "Merrimack": "MRMK", "Miami (FL)": "MIA", "Miami (OH)": "M-OH",
        "Michigan": "MICH", "Michigan St.": "MSU", "Middle Tenn.": "MTSU", "Milwaukee": "MILW", "Minnesota": "MINN", "Mississippi St.": "MSST",
        "Mississippi Val.": "MVSU", "Missouri": "MIZ", "Missouri St.": "MOST", "Monmouth": "MONM", "Morehead St.": "MORE",
        "Mount St. Mary's": "MSM", "Murray St.": "MUR", "N.C. A&T": "NCAT", "NC State": "NCSU", "NIU": "NIU", "NJIT": "NJIT", "Navy": "NAVY",
        "Nebraska": "NEB", "Nevada": "NEV", "New Mexico": "UNM", "New Mexico St.": "NMSU", "Niagara": "NIAG", "Nicholls": "NICH",
        "Norfolk St.": "NSU", "North Ala.": "UNA", "North Carolina": "UNC", "North Dakota St.": "NDSU", "North Florida": "UNF",
        "Northeastern": "NE", "Northern Colo.": "UNCO", "Northern Ky.": "NKU", "Northwestern": "NW", "Northwestern St.": "NWST",
        "Notre Dame": "ND", "Oakland": "OAK", "Ohio": "OHIO", "Ohio St.": "OSU", "Oklahoma": "OU", "Oklahoma St.": "OKST",
        "Old Dominion": "ODU", "Ole Miss": "MISS", "Omaha": "OMA", "Oral Roberts": "ORU", "Oregon": "ORE", "Oregon St.": "ORST",
        "Pacific": "PAC", "Penn": "PENN", "Penn St.": "PSU", "Pepperdine": "PEPP", "Pittsburgh": "PITT", "Portland": "PORT",
        "Prairie View": "PVAM", "Presbyterian": "PRES", "Princeton": "PRIN", "Purdue": "PUR", "Purdue Fort Wayne": "PFW", "Queens (NC)": "QUNC",
        "Quinnipiac": "QUIN", "Radford": "RAD", "Rhode Island": "URI", "Rice": "RICE", "Richmond": "RICH", "Rider": "RID", "Rutgers": "RUT",
        "SFA": "SFA", "SIUE": "SIUE", "Sacramento St.": "SAC", "Sacred Heart": "SHU", "Saint Joseph's": "SJOE", "Saint Louis": "SLU",
        "Saint Mary's (CA)": "SMC", "Saint Peter's": "SPU", "Sam Houston": "SHSU", "Samford": "SAM", "San Diego": "USD", "San Diego St.": "SDSU",
        "San Francisco": "SF", "San Jose St.": "SJSU", "Santa Clara": "SCU", "Seattle U": "SEA", "Seton Hall": "HALL", "Siena": "SIE",
        "South Alabama": "USA", "South Carolina": "SC", "South Dakota St.": "SDST", "South Fla.": "USF", "Southeast Mo. St.": "SEMO",
        "Southeastern La.": "SELA", "Southern California": "USC", "Southern Ill.": "SIU", "Southern Ind.": "USI", "Southern Miss.": "USM",
        "Southern U.": "SOU", "St. Bonaventure": "BONA", "St. John's (NY)": "SJU", "St. Thomas (MN)": "UST", "Stanford": "STAN",
        "Stetson": "STET", "Stonehill": "STON", "Stony Brook": "SBU", "TCU": "TCU", "Tarleton St.": "TAR", "Tennessee": "TENN",
        "Tennessee Tech": "TNTC", "Texas": "TEX", "Texas A&M": "TAMU", "Texas Southern": "TXSO", "Texas St.": "TXST", "Texas Tech": "TTU",
        "The Citadel": "CIT", "Toledo": "TOL", "Towson": "TOW", "Troy": "TROY", "Tulane": "TUL", "UAB": "UAB", "UAlbany": "ALB",
        "UC Davis": "UCD", "UC Irvine": "UCI", "UC Riverside": "UCR", "UC San Diego": "UCSD", "UC Santa Barbara": "UCSB", "UCF": "UCF",
        "UCLA": "UCLA", "UConn": "CONN", "UIC": "UIC", "UIW": "UIW", "ULM": "ULM", "UMBC": "UMBC", "UMES": "UMES", "UMass Lowell": "UML",
        "UNC Asheville": "UNCA", "UNC Greensboro": "UNCG", "UNCW": "UNCW", "UNLV": "UNLV", "USC Upstate": "UPST", "UT Arlington": "UTA",
        "UT Martin": "UTM", "UTRGV": "UTRGV", "UTSA": "UTSA", "Utah": "UTAH", "Utah Tech": "UTU", "Utah Valley": "UVU", "VCU": "VCU",
        "VMI": "VMI", "Valparaiso": "VALP", "Vanderbilt": "VAN", "Villanova": "NOVA", "Virginia": "UVA", "Virginia Tech": "VT",
        "Wagner": "WAG", "Wake Forest": "WAKE", "Washington": "WASH", "Washington St.": "WSU", "West Ga.": "UWG", "West Virginia": "WVU",
        "Western Caro.": "WCU", "Western Ill.": "WIU", "Western Ky.": "WKU", "Western Mich.": "WMU", "Wichita St.": "WICH",
        "William & Mary": "W&M", "Winthrop": "WIN", "Wofford": "WOF", "Wright St.": "WRST", "Xavier": "XAV", "Yale": "YALE",
        "Youngstown St.": "YSU"}
# the abbreviations known to be the school's own or the press's standard form; every other entry of ABBR is a guess for the owner to check
CONFIDENT = {"AMCC", "ACU", "ALA", "AAMU", "APP", "ARIZ", "ASU", "UAPB", "ARK", "ARMY", "AUB", "APSU", "BYU", "BAY", "BCU", "BC", "BGSU", "CSUB",
             "CSUN", "CSUF", "CAL", "CBU", "UCA", "CCSU", "CMU", "CLT", "CIN", "CLEM", "CCU", "CofC", "CREI", "DBU", "DSU", "DUKE", "ETSU", "ECU",
             "EIU", "EKU", "EMU", "FDU", "FGCU", "FIU", "FAU", "FLA", "FAMU", "FSU", "GASO", "GWU", "GMU", "GW", "UGA", "GSU", "GT", "GONZ",
             "GCU", "HPU", "HOU", "HCU", "ILL", "IU", "IOWA", "JMU", "KU", "KSU", "UK", "LIU", "LMU", "LSU", "UNO", "LBSU", "ULL", "LOU", "UMD",
             "UMASS", "MCN", "MIA", "MICH", "MSU", "MTSU", "MINN", "MSST", "MVSU", "MIZ", "NCAT", "NCSU", "NIU", "NJIT", "NAVY", "NEB", "UNM",
             "NMSU", "UNA", "UNC", "NDSU", "UNF", "NKU", "NW", "NWST", "ND", "OSU", "OU", "OKST", "ODU", "ORU", "ORE", "ORST", "PENN", "PSU",
             "PITT", "PVAM", "PUR", "PFW", "URI", "RUT", "SFA", "SIUE", "SLU", "SMC", "SHSU", "USD", "SDSU", "SJSU", "SCU", "USA", "SC",
             "USF", "SEMO", "SELA", "USC", "SIU", "USI", "USM", "SJU", "STAN", "SBU", "TCU", "TENN", "TEX", "TAMU", "TXSO", "TXST", "TTU",
             "TROY", "UAB", "UCD", "UCI", "UCR", "UCSD", "UCSB", "UCF", "UCLA", "CONN", "UIC", "UIW", "ULM", "UMBC", "UMES", "UML", "UNCA",
             "UNCG", "UNCW", "UNLV", "UTA", "UTM", "UTRGV", "UTSA", "UTAH", "UVU", "VCU", "VMI", "VAN", "NOVA", "UVA", "VT", "WAKE", "WASH",
             "WSU", "WVU", "WCU", "WIU", "WKU", "WMU", "XAV", "YSU", "JKST", "GRAM", "ALST", "ELON", "LIB", "MEM", "RICE", "TUL", "JAX",
             "STET", "LIP", "UALR", "UVU", "SAC", "HAW", "NEV", "FRES", "OMA", "NE", "W&M", "UST", "YALE", "HARV", "PRIN", "BONA", "UWG"}


def full_name(short: str) -> str:
    if short in FULL:
        return FULL[short]
    words = [EXPAND.get(w, w) for w in short.split(" ")]
    return " ".join(words)


def abbr_of(short: str) -> tuple[str, str]:
    a = ABBR[short]
    return a, "common" if a in CONFIDENT else "guess"


def main() -> None:
    with SRC.open() as f:
        rows = list(csv.DictReader(f))
    out = []
    seen = {}
    for r in rows:
        short = r["school"]
        full = full_name(short)
        abbr, src = abbr_of(short)
        assert abbr not in seen, (abbr, short, seen.get(abbr))
        seen[abbr] = short
        out.append({"tid": r["tid"], "ncaa_team_id": r["ncaa_team_id"], "short": short, "full": full, "abbr": abbr, "abbr_source": src})
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["tid", "ncaa_team_id", "short", "full", "abbr", "abbr_source"])
        w.writeheader(); w.writerows(out)
    assert all(2 <= len(o["abbr"]) <= 5 for o in out), [o for o in out if not 2 <= len(o["abbr"]) <= 5]
    print(f"{len(out)} schools; {sum(o['abbr_source'] == 'guess' for o in out)} guessed abbreviations")


if __name__ == "__main__":
    main()
