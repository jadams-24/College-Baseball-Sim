"""Build app/school_identity.csv: each sim team's official athletics colors, home ballpark, capacity and city, with a
source URL, fetch date and confidence per row (owner request 2026-10-10). Display only: the engine never reads it.

Sources (Wikipedia only; www.ncaa.com blocks agents and is never fetched):
  * colors: Wikipedia's `Module:College color/data`, the table every college sports infobox draws its colors from.
    Each entry cites the school's brand guide; that citation URL is recorded as `color_source`. Confidence B
    (fetched from Wikipedia, not from the school's own site).
  * ballpark, capacity, city: the infobox of the program's `<School Nickname> baseball` article, found through
    Wikipedia's `List of NCAA Division I baseball programs`. Confidence B; D when the article or the field is missing.
  * recent renames: the ballpark's own article lead, flagged when it says "renamed" / "formerly" with a year 2023 or later.
  * conference tournaments: the `2025 <Conference> baseball tournament` infobox (Ballpark, City); blank when absent.

Usage: python scripts/build_school_identity.py [--cache DIR] [--offline]
The raw pages are cached under --cache (default: scratch/wiki_cache, not committed) so a rerun fetches nothing.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHOOLS = ROOT / "data/schools/schools.csv"
NAMES = ROOT / "app/school_names.csv"
OUT = ROOT / "app/school_identity.csv"
TOURN_OUT = ROOT / "app/conference_tournaments.csv"
REPORT = ROOT / "reports/school_identity.md"
UA = "CollegeBaseballSim/0.1 (https://github.com/jadams-24/College-Baseball-Sim; adams.jordan24@gmail.com)"
RAW = "https://en.wikipedia.org/w/index.php?title={}&action=raw"
PAGE = "https://en.wikipedia.org/wiki/{}"
TODAY = dt.date.today().isoformat()
SLEEP = 0.35

# schools.csv name -> the Wikipedia baseball article (the ones the automatic match on the D1 list misses or gets wrong)
TITLE_FIX = {"Central Conn. St.": "Central Connecticut Blue Devils baseball", "Massachusetts": "UMass Minutemen baseball",
             "Miami (OH)": "Miami RedHawks baseball", "Miami (FL)": "Miami Hurricanes baseball", "Col. of Charleston": "Charleston Cougars baseball", "Delaware": "Delaware Fightin' Blue Hens baseball",
             "Southern California": "USC Trojans baseball", "Southern U.": "Southern Jaguars baseball", "Purdue Fort Wayne": "Purdue Fort Wayne Mastodons baseball",
             "Tarleton St.": "Tarleton State Texans baseball", "UTRGV": "UT Rio Grande Valley Vaqueros baseball", "West Ga.": "West Georgia Wolves baseball",
             "Mercyhurst": "Mercyhurst Lakers baseball", "Ole Miss": "Ole Miss Rebels baseball", "Penn": "Penn Quakers baseball",
             "LMU (CA)": "Loyola Marymount Lions baseball", "Saint Mary's (CA)": "Saint Mary's Gaels baseball", "St. John's (NY)": "St. John's Red Storm baseball",
             "Queens (NC)": "Queens Royals baseball", "St. Thomas (MN)": "St. Thomas (Minnesota) Tommies baseball"}


# ---------------------------------------------------------------- fetching
class Wiki:
    def __init__(self, cache: Path, offline: bool):
        self.cache, self.offline, self.misses = cache, offline, []
        cache.mkdir(parents=True, exist_ok=True)

    def raw(self, title: str, follow: bool = True) -> str | None:
        """The wikitext of a page (redirects followed), None when missing or unreachable."""
        key = re.sub(r"[^A-Za-z0-9._-]", "_", title)[:150]
        f = self.cache / (key + ".txt")
        if f.exists():
            txt = f.read_text(encoding="utf-8")
        elif self.offline:
            self.misses.append(title)
            return None
        else:
            url = RAW.format(urllib.parse.quote(title.replace(" ", "_")))
            txt = None
            for attempt in range(3):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": UA})
                    with urllib.request.urlopen(req, timeout=40) as r:
                        txt = r.read().decode("utf-8")
                    break
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        txt = ""
                        break
                    time.sleep(3 * (attempt + 1))
                except Exception:
                    time.sleep(3 * (attempt + 1))
            if txt is None:
                self.misses.append(title)
                return None
            f.write_text(txt, encoding="utf-8")
            time.sleep(SLEEP)
        if not txt.strip():
            return None
        m = re.match(r"\s*#REDIRECT\s*\[\[([^\]|#]+)", txt, re.I)
        if m and follow:
            return self.raw(m.group(1).strip(), follow=False)
        return txt


# ---------------------------------------------------------------- wikitext helpers
def infobox(txt: str, name: str) -> dict:
    """The fields of the first {{Infobox <name>...}} as a dict (nested templates kept intact)."""
    m = re.search(r"\{\{\s*Infobox\s+" + name, txt, re.I)
    if not m:
        return {}
    i, depth, start = m.start(), 0, m.start()
    while i < len(txt):
        if txt.startswith("{{", i):
            depth += 1
            i += 2
        elif txt.startswith("}}", i):
            depth -= 1
            i += 2
            if depth == 0:
                break
        else:
            i += 1
    body = txt[start + 2:i - 2]
    fields, depth, cur, parts = {}, 0, [], []
    j = 0
    while j < len(body):
        c = body[j]
        if body.startswith("{{", j) or body.startswith("[[", j):
            depth += 1
            cur.append(body[j:j + 2])
            j += 2
            continue
        if body.startswith("}}", j) or body.startswith("]]", j):
            depth -= 1
            cur.append(body[j:j + 2])
            j += 2
            continue
        if c == "|" and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        j += 1
    parts.append("".join(cur))
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            fields[k.strip().lower()] = v.strip()
    return fields


def plain(v: str) -> str:
    """Wikitext to plain text: links to their display text, templates stripped, refs and comments removed."""
    v = re.sub(r"<!--.*?-->", "", v, flags=re.S)
    v = re.sub(r"<ref[^>]*/>", "", v)
    v = re.sub(r"<ref[^>]*>.*?</ref>", "", v, flags=re.S)
    v = re.sub(r"\{\{\s*nowrap\s*\|(.*?)\}\}", r"\1", v, flags=re.S | re.I)
    v = re.sub(r"\{\{\s*(?:small|smaller)\s*\|(.*?)\}\}", r"\1", v, flags=re.S | re.I)
    v = re.sub(r"\{\{[^{}]*\}\}", "", v)
    v = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", v)
    v = re.sub(r"'''?", "", v)
    v = re.sub(r"<br\s*/?>", "; ", v)
    v = re.sub(r"<[^>]+>", "", v)
    return re.sub(r"\s+", " ", v).strip(" ;,")


def link_target(v: str) -> str | None:
    m = re.search(r"\[\[([^\]|#]+)", v)
    return m.group(1).strip() if m else None


def capacity(v: str) -> str:
    """The first capacity listed (a program with two parks lists the main one first)."""
    v = plain(v)
    m = re.search(r"\d[\d,]{2,}", v)
    return m.group(0).replace(",", "") if m else ""


def first_venue(v: str) -> tuple:
    """The main ballpark from a stadium field that may list two ("A (Capacity: 2,000) or B", "A ; B", "A (2002–present)"):
    the first one, parentheticals stripped; a capacity found inside the parenthetical is returned too."""
    v = re.split(r"<br\s*/?>|\n", v.strip(), flags=re.I)[0]     # a second park on its own line is a second park
    v = plain(v)
    cap = ""
    m = re.search(r"\(\s*capacity:?\s*([\d,]+)", v, re.I)
    if m:
        cap = m.group(1).replace(",", "")
    v = re.split(r"\s*;\s*|\s+or\s+", v)[0]
    v = re.sub(r"\s*\([^)]*\)", "", v)
    return v.strip(" ,/"), cap


def city_of(v: str) -> str:
    """The city alone ("Baton Rouge" from "[[Baton Rouge, Louisiana]]"); the app adds the state from the school file."""
    v = plain(v)
    v = v.split(";")[0].split("(")[0]
    return v.split(",")[0].strip(" ,")


# ---------------------------------------------------------------- the D1 programs list
def programs(w: Wiki) -> list:
    txt = w.raw("List of NCAA Division I baseball programs")
    rows = []
    if not txt:
        return rows
    for block in txt.split("|-")[1:]:
        cells = [c.strip() for c in re.split(r"\n\|", "\n" + block.strip()) if c.strip()]
        if len(cells) < 5:
            continue
        link = re.search(r"\[\[([^\]|]+ baseball)\|", cells[1])
        if not link:
            continue
        rows.append({"school_cell": plain(cells[0]), "school_link": link_target(cells[0]) or "", "title": link.group(1).strip(),
                     "field": plain(cells[3]), "conference": plain(cells[4])})
    return rows


def norm(s: str) -> str:
    s = s.lower().replace("&", " and ").replace("–", "-").replace("—", "-")
    s = re.sub(r"\bst\.", "state", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def match_programs(schools: dict, progs: list, names: dict) -> dict:
    """tid -> program row. A baseball article is titled "<School> <Nickname> baseball"; the school matches when the
    title minus its last k nickname words (k = 1, 2, 3) equals the app's full or short name, the smallest k winning
    (so "Florida" is the Gators, not Florida Atlantic). TITLE_FIX covers the names Wikipedia spells differently."""
    out = {}
    by_prefix = {re.sub(r" baseball$", "", p["title"]): p for p in progs}
    for tid, s in schools.items():
        full = names.get(tid, {}).get("full") or s["school"]
        short = s["school"]
        if short in TITLE_FIX:
            t = TITLE_FIX[short]
            out[tid] = by_prefix.get(re.sub(r" baseball$", "", t)) or {"title": t, "field": "", "school_cell": "", "school_link": "", "conference": ""}
            continue
        best = None
        for prefix, p in by_prefix.items():
            words = norm(prefix).split()
            for k in (1, 2, 3):
                if len(words) <= k:
                    break
                stem = " ".join(words[:-k])
                if stem in (norm(full), norm(short)):
                    if best is None or k < best[0]:
                        best = (k, p)
                    break
        if best:
            out[tid] = best[1]
    return out


# ---------------------------------------------------------------- colors
def color_table(w: Wiki) -> dict:
    txt = w.raw("Module:College color/data")
    table, alias = {}, {}
    if not txt:
        return table
    for m in re.finditer(r'^\s*\["([^"]+)"\]\s*=\s*(\{.*?\}|"[^"]*"),?\s*(?:--.*)?$', txt, re.M):
        key, val = m.group(1), m.group(2)
        if val.startswith('"'):
            alias[key] = val.strip('"')
            continue
        hexes = re.findall(r'^\s*"([0-9A-Fa-f]{6})"|,\s*"([0-9A-Fa-f]{6})"', val)
        hexes = [a or b for a, b in re.findall(r'(?:\{|,)\s*"([0-9A-Fa-f]{6})"()', val)] or []
        hexes = [h.upper() for h in re.findall(r'"([0-9A-Fa-f]{6})"', val.split("name1")[0] if "name1" in val else val.split("cite")[0])]
        names = dict(re.findall(r'name(\d)="([^"]*)"', val))
        cite = re.search(r"\|url=([^ |}]+)", val)
        table[key] = {"hex": hexes, "names": names, "cite": cite.group(1) if cite else ""}
    for a, k in alias.items():
        if k in table:
            table[a] = table[k]
    return table


NEUTRAL = {"FFFFFF", "000000"}


def pick_colors(entry: dict) -> tuple:
    """primary, secondary (the official first two), and alt: the first listed non-neutral color after the primary."""
    h = entry["hex"]
    if not h:
        return "", "", ""
    primary = h[0]
    secondary = h[1] if len(h) > 1 else ""
    alt = next((x for x in h[1:] if x not in NEUTRAL and x != primary), "")
    return primary, secondary, alt


# ---------------------------------------------------------------- stadium rename check
def rename_note(w: Wiki, stadium_title: str | None) -> str:
    if not stadium_title:
        return ""
    txt = w.raw(stadium_title)
    if not txt:
        return ""
    lead = txt.split("\n==", 1)[0]
    lead = plain(re.sub(r"\{\{Infobox.*?\n\}\}", "", lead, flags=re.S | re.I))
    for m in re.finditer(r"[^.]*\b(renamed|formerly|previously (?:known|named)|known as|name(?:d)? (?:was )?changed)\b[^.]*\.", lead, re.I):
        sent = m.group(0)
        years = [int(y) for y in re.findall(r"\b(20[2-9]\d)\b", sent)]
        if any(y >= 2023 for y in years):
            return sent.strip()[:240]
    return ""


# ---------------------------------------------------------------- conference tournaments
CONF_TITLES = {"ACC": "Atlantic Coast Conference", "ASUN": "ASUN Conference", "America East": "America East Conference",
               "Atlantic 10": "Atlantic 10 Conference", "Big 12": "Big 12 Conference", "Big East": "Big East Conference",
               "Big South": "Big South Conference", "Big Ten": "Big Ten Conference", "Big West": "Big West Conference",
               "CAA": "Coastal Athletic Association", "CUSA": "Conference USA", "Horizon": "Horizon League",
               "Ivy League": "Ivy League", "MAAC": "Metro Atlantic Athletic Conference", "MAC": "Mid-American Conference",
               "MVC": "Missouri Valley Conference", "Mountain West": "Mountain West Conference", "NEC": "Northeast Conference",
               "OVC": "Ohio Valley Conference", "Patriot": "Patriot League", "SEC": "Southeastern Conference",
               "SWAC": "Southwestern Athletic Conference", "SoCon": "Southern Conference", "Southland": "Southland Conference",
               "Summit League": "Summit League", "Sun Belt": "Sun Belt Conference", "The American": "American Athletic Conference",
               "WAC": "Western Athletic Conference", "WCC": "West Coast Conference"}


def tournaments(w: Wiki) -> list:
    rows = []
    for short, full in CONF_TITLES.items():
        title = f"2025 {full} baseball tournament"
        txt = w.raw(title)
        box = infobox(txt, r"NCAA Baseball Conference Tournament") if txt else {}
        park, city = plain(box.get("ballpark", "")), plain(box.get("city", ""))
        rows.append({"conference": short, "year": 2025, "venue": park, "city": city,
                     "source": PAGE.format(urllib.parse.quote(title.replace(" ", "_"))) if txt else "",
                     "fetch_date": TODAY, "confidence": "B" if park else "D"})
    rows.append({"conference": "DI Independent", "year": 2025, "venue": "", "city": "", "source": "", "fetch_date": TODAY, "confidence": "D"})
    return rows


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(ROOT / "scratch/wiki_cache"))
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    w = Wiki(Path(a.cache), a.offline)
    with SCHOOLS.open() as f:
        schools = {int(r["tid"]): r for r in csv.DictReader(f)}
    names = {}
    if NAMES.exists():
        with NAMES.open() as f:
            names = {int(r["tid"]): r for r in csv.DictReader(f)}
    progs = programs(w)
    matched = match_programs(schools, progs, names)
    colors = color_table(w)
    rows, unmatched, d_rows, renames, color_misses = [], [], [], [], []
    for tid, s in sorted(schools.items()):
        p = matched.get(tid)
        row = {"tid": tid, "school": names.get(tid, {}).get("full") or s["school"], "primary": "", "secondary": "", "alt": "",
               "color_names": "", "color_source": "", "color_confidence": "D", "stadium": "", "capacity": "", "city": "",
               "stadium_source": "", "stadium_confidence": "D", "wiki_title": "", "fetch_date": TODAY, "note": ""}
        if p is None:
            unmatched.append(s["school"])
            row["note"] = "no Wikipedia program row matched"
            rows.append(row)
            continue
        title = p["title"]
        row["wiki_title"] = title
        key = re.sub(r" baseball$", "", title)
        entry = colors.get(key)
        if entry is None:
            # the athletics key sometimes differs from the baseball title's prefix: try the school link's nickname variants
            for k in colors:
                if norm(k) == norm(key):
                    entry = colors[k]
                    break
        if entry and entry["hex"]:
            pr, se, alt = pick_colors(entry)
            row.update(primary=pr, secondary=se, alt=alt, color_names="; ".join(f"{k}={v}" for k, v in sorted(entry["names"].items())),
                       color_source=entry["cite"] or PAGE.format("Module:College_color/data"), color_confidence="B")
        else:
            color_misses.append(s["school"])
        txt = w.raw(title)
        if txt:
            box = infobox(txt, r"college baseball team")
            stad = box.get("stadium", "") or box.get("ballpark", "") or box.get("field", "")
            stadium, cap_in_name = first_venue(stad)
            if not stadium and p["field"]:
                stadium = p["field"].split(";")[0].strip()
            row.update(stadium=stadium, capacity=cap_in_name or capacity(box.get("capacity", "")), city=city_of(box.get("location", "")) or s["city"],
                       stadium_source=PAGE.format(urllib.parse.quote(title.replace(" ", "_"))), stadium_confidence="B" if stadium else "D")
            note = rename_note(w, link_target(stad))
            if note:
                row["note"] = note
                renames.append((row["school"], stadium, note))
        else:
            if p["field"]:
                row.update(stadium=p["field"], city=s["city"], stadium_source=PAGE.format("List_of_NCAA_Division_I_baseball_programs"), stadium_confidence="B")
            else:
                row["note"] = f"article '{title}' unreachable or missing"
        if row["color_confidence"] == "D" or row["stadium_confidence"] == "D":
            d_rows.append(row)
        rows.append(row)
    cols = list(rows[0].keys())
    with OUT.open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=cols)
        wr.writeheader()
        wr.writerows(rows)
    tourn = tournaments(w)
    with TOURN_OUT.open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(tourn[0].keys()))
        wr.writeheader()
        wr.writerows(tourn)
    write_report(rows, d_rows, renames, tourn, unmatched, color_misses, w.misses)
    print(f"{len(rows)} rows; D rows {len(d_rows)}; unmatched {len(unmatched)}; color misses {len(color_misses)}; renames {len(renames)}; fetch misses {len(w.misses)}")


def write_report(rows, d_rows, renames, tourn, unmatched, color_misses, misses):
    L = ["# School identity: colors and ballparks", "",
         f"Built {TODAY} by `scripts/build_school_identity.py` into `app/school_identity.csv` (display only: the engine never reads it; "
         "its park factors are still the engine's own draw, not these ballparks).", "",
         "Sources: colors from Wikipedia's `Module:College color/data` (the table every college sports infobox draws from; each row cites "
         "the school's brand guide, recorded as `color_source`), confidence B; ballpark, capacity and city from the program's Wikipedia "
         "baseball article infobox, confidence B; D when missing. www.ncaa.com was not used.", "",
         f"Rows: {len(rows)}; both colors and a ballpark: {sum(1 for r in rows if r['color_confidence'] != 'D' and r['stadium_confidence'] != 'D')}; "
         f"D rows: {len(d_rows)}.", "",
         "## D rows (check these)", ""]
    if d_rows:
        L += ["| tid | School | Colors | Ballpark | Why |", "|---|---|---|---|---|"]
        for r in d_rows:
            L.append(f"| {r['tid']} | {r['school']} | {r['color_confidence']} {r['primary']} {r['secondary']} | {r['stadium_confidence']} {r['stadium']} | {r['note']} |")
    else:
        L.append("None.")
    L += ["", "## Ballparks renamed recently (2023 or later)", "",
          "Found by reading each ballpark's own Wikipedia article lead for \"renamed\" / \"formerly\" with a year of 2023 or later; a rename the "
          "article does not state in its lead is not caught, so the list is a lead, not a proof.", ""]
    if renames:
        L += ["| School | Ballpark | Note |", "|---|---|---|"]
        for s, st, n in renames:
            L.append(f"| {s} | {st} | {n.replace('|', '/')} |")
    else:
        L.append("None found.")
    L += ["", "## 2025 conference tournament venues (`app/conference_tournaments.csv`)", "",
          "Shown only when the 2025 tournament article confirms the site; otherwise the app says \"Conference tournament\" with no venue.", "",
          "| Conference | Venue | City | Confidence |", "|---|---|---|---|"]
    for t in tourn:
        L.append(f"| {t['conference']} | {t['venue']} | {t['city']} | {t['confidence']} |")
    if unmatched:
        L += ["", "## Schools with no Wikipedia program row matched", ""] + [f"- {u}" for u in unmatched]
    if color_misses:
        L += ["", "## Schools with no entry in the college color table", ""] + [f"- {u}" for u in color_misses]
    if misses:
        L += ["", "## Pages that could not be fetched", ""] + [f"- {u}" for u in misses]
    L += ["", "## Secondary colors", "",
          "`primary` and `secondary` are the first two official colors as the brand guide lists them (white or black is often the official "
          "second color). `alt` is the first non-white, non-black color after the primary, which the app uses where a visible second "
          "color is needed (a dark primary on the dark background; two similar primaries on one scoreboard).", ""]
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
