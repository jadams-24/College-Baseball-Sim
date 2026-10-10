"""MLB draft aggregates from the MLB Stats API, 2021-2026 (Phase 8-9 yardstick, 2026-10-10).

    python tools/fetch_mlb_draft.py --work /path/outside/the/repo          # fetch and aggregate
    python tools/fetch_mlb_draft.py --work /path/outside/the/repo --aggregate

Source: https://statsapi.mlb.com/api/v1/draft/<year> (the feed behind mlb.com/draft/tracker): every pick
with round code, pick number, school name and class (HS SR; 4YR JR/SO/SR/5S/GR; JC J1-J3; NS), the slot
value (rounds 1-10) and the signing bonus when one is on file. One request per year. The raw JSON (with
names) stays in the working directory; data/mlb_draft/ holds counts only: picks by year x round x source
(HS, JC, D1 by Phase 0 tier, D2, D3, NAIA), the unsigned proxy (no bonus on file; equal to MLB.com's
deadline counts in the top 10 rounds for 2021-2025 and to Baseball America's 576 of 615 for 2025), the
class of four-year picks, P4 picks by conference, picks per D1 program, and the slot values. Four-year
schools are matched to the 307 D1 programs (data/schools/schools.csv, name_aliases.csv and the alias
table below; the current conference map, so Stanford, Cal and SMU count as P4 in every year and
Oregon St. and Washington St. as mid); the D2 / D3 / NAIA split of the rest is a hand list (grade C).
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/mlb_draft"
API = "https://statsapi.mlb.com/api/v1/draft/{year}"
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]
ABBR = {"St.": "State", "Ky.": "Kentucky", "Tenn.": "Tennessee", "Fla.": "Florida", "Ill.": "Illinois", "Mich.": "Michigan",
        "La.": "Louisiana", "Ark.": "Arkansas", "Caro.": "Carolina", "Ga.": "Georgia", "Ala.": "Alabama", "Miss.": "Mississippi",
        "Conn.": "Connecticut", "Colo.": "Colorado", "Mo.": "Missouri", "Ind.": "Indiana", "Val.": "Valley", "So.": "Southern",
        "Col.": "College", "Okla.": "Oklahoma"}
SRCS = ["HS", "JC", "D1 p4", "D1 mid", "D1 low", "D2", "D3", "NAIA", "4YR unclassified", "other/none"]
BANDS = ["R1+", "R2-5", "R6-10", "R11-20"]

# hand alias table (Stats API spelling -> schools.csv spelling; None = not D1; JC/HS/other = mis-tagged)
MANUAL={'Dallas Baptist':'DBU','Southern Mississippi':'Southern Miss.','U Southern Mississippi':'Southern Miss.','USC':'Southern California','Miami':'Miami (FL)','Mississippi':'Ole Miss','U Mississippi':'Ole Miss',
 'Central Florida':'UCF','Connecticut':'UConn','UNC Charlotte':'Charlotte','UNC Wilmington':'UNCW','South Florida':'South Fla.','Loyola Marymount University':'LMU (CA)',"St. Mary's College":"Saint Mary's (CA)","Saint Mary's":"Saint Mary's (CA)",
 'Florida Gulf Coast University':'FGCU','Florida Gulf Coast':'FGCU','Florida International':'FIU','Florida Atlantic':'Fla. Atlantic','University of Illinois at Chicago':'UIC','Illinois-Chicago':'UIC','Southern Illinois University Edwardsville':'SIUE',
 'University of Texas - San Antonio':'UTSA','Texas-San Antonio':'UTSA','University of Texas - Arlington':'UT Arlington','Southern Illinois University Carbondale':'Southern Ill.','Southern Illinois U Carbondale':'Southern Ill.','Southern Illinois':'Southern Ill.',
 'Virginia Military Institute':'VMI','East Tennessee State':'ETSU','East Tennessee St U':'ETSU','SUNY Binghamton':'Binghamton','Binghamton University':'Binghamton','Pennsylvania':'Penn','Brigham Young':'BYU','Brigham Young U':'BYU','Virginia Commonwealth':'VCU','Virginia Commonwealth U':'VCU',
 'U Nevada Las Vegas':'UNLV','Nevada-Las Vegas':'UNLV','Wisconsin-Milwaukee':'Milwaukee','Nebraska-Omaha':'Omaha','U Nebraska Omaha':'Omaha','U Alabama Birmingham':'UAB','Alabama-Birmingham':'UAB','Long Island University':'LIU','University of New Orleans':'LSU New Orleans',
 'University of Maryland-Baltimore County':'UMBC','U Tennessee Martin':'UT Martin','Tennesse-Martin':'UT Martin','University of Louisiana - Monroe':'ULM','Arkansas-Little Rock':'Little Rock','Central Arkansas':'Central Ark.','U Central Arkansas':'Central Ark.',
 'Cal State Fullerton':'Cal St. Fullerton','Cal St Fullerton':'Cal St. Fullerton','Cal State Northridge':'CSUN','Cal State Bakersfield':'CSU Bakersfield','Cal Poly San Luis Obispo':'Cal Poly','Lamar':'Lamar University','Lamar U':'Lamar University','Seattle':'Seattle U','Seattle University':'Seattle U','Southern':'Southern U.',
 'Queens University of Charlotte':'Queens (NC)','Charleston Southern':'Charleston So.','College of Charleston':'Col. of Charleston','University of Louisiana at Lafayette':'Louisiana','U Louisiana Lafayette':'Louisiana','Louisana-Lafayette':'Louisiana',
 'Miami University':'Miami (OH)','Appalachian State':'App State','Sam Houston State':'Sam Houston','New Jersey Institute of Technology':'NJIT','Texas A&M - Corpus Christi':'A&M-Corpus Christi','St. Louis University':'Saint Louis','St Johns U':"St. John's (NY)","St. John's":"St. John's (NY)",
 'Houston Christian U':'Houston Christian','Washington U':None,'U Georgia':'Georgia','Villanova U':'Villanova','North Carolina A&T':'N.C. A&T','University of British Columbia':None,'U British Columbia':None,'Bowling Green State':'Bowling Green','Southeast Missouri St U':'Southeast Mo. St.','Southeast Missouri State':'Southeast Mo. St.',
 'University of San Diego':'San Diego','San Diego St U':'San Diego St.','Grand Canyon University':'Grand Canyon','Liberty University':'Liberty','Campbell University':'Campbell','Campbell U':'Campbell','University of South Alabama':'South Alabama','U South Alabama':'South Alabama','University of Portland':'Portland','Troy University':'Troy',
 'Western Kentucky':'Western Ky.','Middle Tennessee State':'Middle Tenn.','California Baptist University':'California Baptist','California Baptist U':'California Baptist','Western Carolina':'Western Caro.','Western Carolina U':'Western Caro.','Samford University':'Samford','Georgia Southern':'Ga. Southern','James Madison University':'James Madison','James Madison U':'James Madison','Elon University':'Elon',
 'Bryant University':'Bryant','University of Memphis':'Memphis','University of Maine':'Maine','McNeese State':'McNeese','Western Michigan':'Western Mich.','Central Michigan':'Central Mich.','Eastern Michigan':'Eastern Mich.','Eastern Illinois':'Eastern Ill.','Eastern Illinois U':'Eastern Ill.','Lipscomb University':'Lipscomb','Wright State University':'Wright St.',
 'Bradley University':'Bradley','University of South Carolina Upstate':'USC Upstate','U South Carolina Upstate':'USC Upstate','Southeastern Louisiana University':'Southeastern La.','Southeastern Louisiana U':'Southeastern La.','University of San Francisco':'San Francisco','Jacksonville University':'Jacksonville','Murray State University':'Murray St.',
 'Monmouth University':'Monmouth','Belmont University':'Belmont','Oral Roberts U':'Oral Roberts','U Hawaii':'Hawaii','Canisius College':'Canisius','Abilene Christian U':'Abilene Christian','University of Rhode Island':'Rhode Island','Mercer U':'Mercer','Presbyterian College':'Presbyterian','Alabama St U':'Alabama St.','Alabama State University':'Alabama St.','High Point University':'High Point','Niagara U':'Niagara',
 'Ohio University':'Ohio','Gardner-Webb University':'Gardner-Webb','Quinnipiac University':'Quinnipiac','Hofstra U':'Hofstra','Penn St U':'Penn St.','Marist College':'Marist','Fairfield U':'Fairfield','Louisiana Tech U':'Louisiana Tech','Eastern Kentucky':'Eastern Ky.','Eastern Kentucky U':'Eastern Ky.','George Washington University':'George Washington','Lehigh U':'Lehigh','U South Carolina':'South Carolina',
 'Tarleton St U':'Tarleton St.','U Missouri':'Missouri','Boston Col':'Boston College','U Washington':'Washington','Xavier U':'Xavier','U Richmond':'Richmond','Texas Southern U':'Texas Southern','Grambling State':'Grambling','Bethune-Cookman University':'Bethune-Cookman','Morehead State':'Morehead St.','University of California - Davis':'UC Davis','University of California - Irvine':'UC Irvine','University of California - Riverside':'UC Riverside',
 'Sacred Heart University':'Sacred Heart','Delaware State University':'Delaware St.','Delaware State':'Delaware St.','Arizona St U':'Arizona St.','Nicholls State':'Nicholls','Nicholls St U':'Nicholls','Northern Kentucky':'Northern Ky.','Creighton U':'Creighton','U Alabama':'Alabama','U Arizona':'Arizona','U Oklahoma':'Oklahoma','U Oregon':'Oregon','U Iowa':'Iowa','U Houston':'Houston','U Dayton':'Dayton',
 'SUNY Stony Brook':'Stony Brook','Austin Peay State':'Austin Peay','Lafayette Col':'Lafayette','Oakland University':'Oakland','Longwood University':'Longwood','North Dakota St U':'North Dakota St.','South Dakota State':'South Dakota St.','Georgia St U':'Georgia St.','Wayne St U':None,'Jacksonville State':'Jacksonville St.','North Carolina State':'NC State','Youngstown State':'Youngstown St.','Arkansas State':'Arkansas St.',
 'Florida SouthWestern State College':'JC','Ivy Tech':'JC','Farragut HS':'HS','Ankeny Centennial HS':'HS','Marjory Stoneman Douglas HS':'HS','Puerto Rico Baseball Academy':'other','No School':'other','University of Olivet':None,'Park University-Gilbert':None,'LSU Shreveport':None,'University of Mobile':None,'Houston-Victoria':None,
}
D2={'Florida Southern','University of Central Missouri','U Central Missouri','Central Missouri','Wingate','Wingate U','Angelo State','Angelo St U','UNC Pembroke','Saint Leo University','St Leo U','Colorado Mesa University','Colorado Mesa U','Nova Southeastern University','Nova Southeastern','North Greenville University','North Greenville U','University of West Florida','Lander University','Minnesota St U Mankato','Minnesota State - Mankato','Quincy University','Quincy U','Lee University','Azusa Pacific University','Azusa Pacific U','University of Pittsburgh - Johnstown','Shepherd University','University of Tampa',"St. Edwards University",'St. Cloud State','University of Central Oklahoma','Northeastern St U','Notre Dame Col','Cal Poly Pomona','Assumption Col','University of Illinois Springfield','Pittsburg State University','Point Loma Nazarene University','Missouri Southern St Col','East Stroudsburg U','Seton Hill University','Seton Hill U','Seton Hill','Hillsdale College','Washburn University','Regis U','University of Montevallo','Lenoir-Rhyne U','Maryville U','Northwood University','Fresno Pacific','Wayne St U','Lynn U','Felician Col','Shippensburg University','Ashland University','Lewis U','Saginaw Valley State','University of New Haven','Augustana U','Grand Valley St U','Francis Marion','Catawba','Biola University','Missouri-St. Louis','Purdue University Northwest','Westmont College','Columbia College','Benedictine U Mesa','North Carolina Central University'}
D3={'Adrian College','St John Fisher College','Pomona-Pitzer Col','Salve Regina U','Rowan University','Skidmore Col','Randolph-Macon College','Transylvania University','University of Rochester','Whitworth University','MIT','Kean University','University of Olivet','Washington U'}
NAIA={'University of British Columbia','U British Columbia','Southeastern University','William Carey University','University of Mobile','Hope International U','Hope International University','Hope International','Lewis-Clark State','Lewis-Clark State College','Lindsey Wilson Col',"The Master's University",'Taylor University','University of the Cumberlands','Webber International University','Reinhardt University','Park University-Gilbert','LSU Shreveport','Houston-Victoria'}


def load_teams() -> tuple[dict, dict, dict]:
    teams = {r["school"]: (r["conference"], r["tier"]) for r in csv.DictReader(open(ROOT / "data/schools/schools.csv")) if r["tier"]}
    alias = {r["alias"]: r["school"] for r in csv.DictReader(open(ROOT / "data/schools/name_aliases.csv"))}
    normmap = {}
    for t in teams:
        normmap.setdefault(norm(t), t)
    return teams, alias, normmap


def norm(n: str) -> str:
    n = n.replace("&", "and")
    for a, b in ABBR.items():
        n = re.sub(r"(?<!\w)" + re.escape(a) + r"(?!\w)", b, n)
    n = re.sub(r"\(.*?\)", "", n)
    n = n.lower().replace("-", " ").replace("\u2013", " ")
    n = re.sub(r"[^a-z0-9 ]", "", n)
    n = re.sub(r"\b(university|univ|college|col|u|the|of|at|st|saint)\b", " ", n)
    n = re.sub(r"\bstate\b", "st", n)
    return " ".join(n.split())


def canon(n: str, teams: dict, alias: dict, normmap: dict):
    if n in MANUAL:
        return MANUAL[n]
    for c in (n, alias.get(n)):
        if c in teams:
            return c
    return normmap.get(norm(n))


def source(p: dict, teams, alias, normmap) -> tuple[str, str | None]:
    s = p.get("school") or {}
    sc, name = s.get("schoolClass", "NONE") or "NONE", s.get("name", "") or ""
    if sc.startswith("HS"):
        return "HS", None
    if sc.startswith("JC"):
        return "JC", None
    if sc.startswith("4YR") or sc == "5S":
        c = canon(name, teams, alias, normmap)
        if c in ("JC", "HS"):
            return c, None
        if c == "other":
            return "other/none", None
        if c and c in teams:
            return "D1 " + teams[c][1], c
        if name in D2:
            return "D2", None
        if name in D3:
            return "D3", None
        if name in NAIA:
            return "NAIA", None
        return "4YR unclassified", None
    return "other/none", None


def band(rd: str) -> str:
    if rd in ("1", "PPI", "1C", "CB-A"):
        return "R1+"
    if rd in ("2", "CB-B", "SUP-2", "2C", "3", "SUP-3", "4", "4C", "5"):
        return "R2-5"
    if rd in ("6", "7", "8", "9", "10"):
        return "R6-10"
    return "R11-20"


def rnum(rd: str) -> int:
    m = re.match(r"^(\d+)$", rd)
    if m:
        return int(m.group(1))
    return {"PPI": 1, "1C": 1, "CB-A": 1, "CB-B": 2, "SUP-2": 2, "2C": 2, "SUP-3": 3, "4C": 4}.get(rd, 99)


def fetch(work: Path, years: list[int]) -> None:
    import requests
    (work / "raw").mkdir(parents=True, exist_ok=True)
    for y in years:
        p = work / "raw" / f"draft_{y}.json"
        if p.exists():
            continue
        r = requests.get(API.format(year=y), headers={"User-Agent": "college-baseball-sim data pull (github.com/jadams-24/College-Baseball-Sim)"}, timeout=120)
        r.raise_for_status()
        p.write_text(r.text)
        print(f"{y}: {sum(len(x['picks']) for x in r.json()['drafts']['rounds'])} picks", flush=True)
        time.sleep(1)


def aggregate(work: Path, out: Path = OUT) -> dict:
    teams, alias, normmap = load_teams()
    rows, cls_rows, conf_rows, prog_rows, slot_rows, uncl, names = [], [], [], [], [], collections.Counter(), set()
    summary = {}
    for p in sorted((work / "raw").glob("draft_*.json")):
        y = int(p.stem.split("_")[1])
        d = json.loads(p.read_text())
        picks = [pk for r in d["drafts"]["rounds"] for pk in r["picks"]]
        tab, uns = collections.Counter(), collections.Counter()
        cls, confs, progs = collections.Counter(), collections.Counter(), collections.Counter()
        for pk in picks:
            nm = (pk.get("person") or {}).get("fullName") or ""
            if nm:
                names.add(nm)
            s, c = source(pk, teams, alias, normmap)
            r, b = rnum(pk["pickRound"]), band(pk["pickRound"])
            unsigned = "signingBonus" not in pk
            tab[(r, b, s)] += 1
            if unsigned:
                uns[(r, b, s)] += 1
            if s == "4YR unclassified":
                uncl[(y, pk["school"]["name"])] += 1
            if s.startswith("D1") or s in ("D2", "D3", "NAIA", "4YR unclassified"):
                cls[(s, pk["school"].get("schoolClass", ""))] += 1
            if s == "JC":
                cls[("JC", pk["school"].get("schoolClass", ""))] += 1
            if c:
                confs[teams[c][0]] += 1
                progs[(c, teams[c][0], teams[c][1])] += 1
            if int(float(pk.get("pickValue") or 0)) > 0:
                slot_rows.append({"year": y, "pick": pk["pickNumber"], "round": pk["pickRound"], "mlb_team": pk["team"]["name"],
                                  "slot_value": int(float(pk["pickValue"])), "source": s.split(" ")[0]})
        for (r, b, s), n in sorted(tab.items()):
            rows.append({"year": y, "round": r, "band": b, "source": s, "picks": n, "unsigned_proxy": uns[(r, b, s)]})
        for (s, sc), n in sorted(cls.items()):
            cls_rows.append({"year": y, "source": s, "school_class": sc, "picks": n})
        for cf, n in sorted(confs.items()):
            conf_rows.append({"year": y, "conference": cf, "picks": n})
        for (c, cf, t), n in sorted(progs.items()):
            prog_rows.append({"year": y, "school": c, "conference": cf, "tier": t, "picks": n})
        d1 = sum(n for (r, b, s), n in tab.items() if s.startswith("D1"))
        summary[y] = {"picks": len(picks), "hs": sum(n for (r, b, s), n in tab.items() if s == "HS"),
                      "jc": sum(n for (r, b, s), n in tab.items() if s == "JC"), "d1": d1,
                      "d1_per_program": round(d1 / 307, 3), "d1_programs_with_a_pick": len(progs),
                      "top10_rounds_picks": sum(n for (r, b, s), n in tab.items() if b != "R11-20"),
                      "unsigned_proxy_all": sum(uns.values()),
                      "unsigned_proxy_top10": sum(n for (r, b, s), n in uns.items() if b != "R11-20"),
                      "bonus_total_on_file": sum(int(float(pk["signingBonus"])) for pk in picks if "signingBonus" in pk),
                      "unclassified_4yr": sum(n for (yy, nm), n in uncl.items() if yy == y)}
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "picks_by_round_source.csv", index=False)
    pd.DataFrame(cls_rows).to_csv(out / "picks_by_class.csv", index=False)
    pd.DataFrame(conf_rows).to_csv(out / "picks_by_conference.csv", index=False)
    pd.DataFrame(prog_rows).to_csv(out / "picks_by_d1_program.csv", index=False)
    pd.DataFrame(slot_rows).to_csv(out / "slot_values.csv", index=False)
    pd.DataFrame([{"year": y, **v} for y, v in summary.items()]).to_csv(out / "summary.csv", index=False)
    pd.DataFrame([{"year": y, "school_name": nm, "picks": n} for (y, nm), n in sorted(uncl.items())],
                 columns=["year", "school_name", "picks"]).to_csv(out / "unclassified_schools.csv", index=False)
    (out / "README.md").write_text(README)
    # leak check: no drafted player's name in any output cell
    keys = {nm.lower() for nm in names}
    for f in out.glob("*.csv"):
        df = pd.read_csv(f, dtype=str, keep_default_na=False)
        for col in df.columns:
            for v in df[col].unique():
                if str(v).lower() in keys:
                    for g in out.glob("*.csv"):
                        g.unlink()
                    raise SystemExit(f"name leak in {f.name}:{col}; output deleted")
    return summary


README = """# data/mlb_draft/ — MLB draft aggregates, 2021–2026 (MLB Stats API)

Built by `tools/fetch_mlb_draft.py` from `https://statsapi.mlb.com/api/v1/draft/<year>` (fetched
2026-10-10). Counts only; the raw feed (names, blurbs) stays outside the repository.

| File | Content |
|---|---|
| `picks_by_round_source.csv` | `year, round (1–20; supplemental and compensation picks folded into the round they follow), band (R1+, R2-5, R6-10, R11-20), source (HS, JC, D1 p4/mid/low on the current conference map, D2, D3, NAIA, 4YR unclassified, other/none), picks, unsigned_proxy` (picks with no signing bonus on file: equals MLB.com's deadline-day unsigned counts in the top 10 rounds 2021–2025 and Baseball America's 39 of 615 for all of 2025; an upper bound in rounds 11–20 and for 2026) |
| `picks_by_class.csv` | four-year and JC picks by the feed's school class (4YR JR/SO/SR/5S/GR; JC J1/J2/J3) |
| `picks_by_conference.csv` | D1 picks by conference (current map) |
| `picks_by_d1_program.csv` | D1 picks per program and year (the Draft Development input) |
| `slot_values.csv` | every pick with a slot value (rounds 1–10): year, overall pick, round code, MLB team, value, source type |
| `summary.csv` | per year: picks, HS, JC, D1, D1 per program (÷307), programs with a pick, top-10-round picks, unsigned proxy (all, top 10), bonuses on file, unclassified four-year picks |
| `unclassified_schools.csv` | four-year school names the matcher could not place, with counts (to extend the alias table) |

Grades: picks, round, class, slot value A (MLB's own feed); D1 and tier assignment B (name match to the
307 programs, validated against the NCAA's D1 counts: 428 = 428 in 2023, 432 vs 431 in 2025); D2 / D3 /
NAIA split C (hand list); unsigned proxy B in rounds 1–10, C in 11–20.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True, help="working directory for the raw feed (outside the repository)")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--years", default=",".join(map(str, YEARS)))
    ap.add_argument("--aggregate", action="store_true")
    a = ap.parse_args()
    work = Path(a.work).resolve()
    if ROOT in work.parents or work == ROOT:
        ap.error("--work must be outside the repository")
    if not a.aggregate:
        fetch(work, [int(y) for y in a.years.split(",")])
    s = aggregate(work, Path(a.out))
    print(json.dumps(s, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
