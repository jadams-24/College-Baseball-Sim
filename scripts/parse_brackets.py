"""Rebuild data/ncaa_brackets/brackets_2015_2025.json from the saved Wikipedia pages.

Source: English Wikipedia, "<YEAR> NCAA Division I baseball tournament", one page per
season, fetched once and saved gzipped in data/ncaa_brackets/raw/wikipedia_<YEAR>.html.gz.
This script never touches the network. Standard library only (html.parser): lxml, bs4 and
html5lib are not installed, so pandas.read_html is not usable here.

What is extracted per season (seeds, hosts and winners only, no game scores):
  * teams: the 64 teams from the regional brackets, with conference (bids tables, else the
    "By conference" table), bid type and national seed;
  * regionals: site, host, the four teams with regional seeds 1-4, winner;
  * supers: the two teams, host, winner;
  * cws: the eight Omaha teams, champion and runner-up.

How each fact is read (and where a fact is inferred rather than stated, the JSON says so):
  * Regional teams and seeds: the "<City> Super Regional" bracket tables. Each holds two
    double-elimination regional brackets (seed cell, team cell, score cells) captioned
    "<Name> Regional - <Stadium>", the regional finals, and the best-of-three super regional.
  * Regional winner: the one of the regional's four teams that appears in the super
    regional column (it must also appear in the regional final column).
  * Super winner: games won from the super regional score cells; must be a CWS participant.
  * Super host: the "Hosted by X at Y" line under the super regional heading; else the
    "Schedule and venues" super regional line whose city is the heading's city; else the
    regional site whose city is the heading's city when that regional's host won it.
  * Regional host: the "Schedule and venues" regional line whose stadium or city matches
    the bracket caption, matched to one of the regional's four teams. Pages before 2019
    have no such list; then the host is recorded as the regional 1 seed and the source is
    marked "inferred: regional 1 seed". (2018: the page states the 16 national seeds hosted.)
  * National seeds: the "National seeds" section, in published order (ordered list or
    "N. Team" lines).
  * Bid: "Automatic bids" / "At-large" / combined "Bids" (Berth column) tables. When the page
    has only the automatic-bid table, a team not in it is recorded at-large and the season's
    "bid_source" says so (the 64-team field is automatic bids plus at-large bids).
  * CWS: the "Participants" table. Champion and runner-up: the "Final standings" table
    (1st and 2nd), cross-checked against the infobox.

Usage:  python scripts/parse_brackets.py [--check]
  --check: rebuild in memory and compare with the committed JSON (exit 1 on a difference).
"""

from __future__ import annotations

import gzip
import json
import re
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "ncaa_brackets" / "raw"
OUT = ROOT / "data" / "ncaa_brackets" / "brackets_2015_2025.json"
SEASONS = [2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025, 2026]
URL = "https://en.wikipedia.org/wiki/{y}_NCAA_Division_I_baseball_tournament"
FETCHED_ON = "2026-10-05"


# --------------------------------------------------------------------------------------
# HTML -> headings, tables, list items, paragraphs (stdlib html.parser)
# --------------------------------------------------------------------------------------
class Page(HTMLParser):
    VOID = {"br", "img", "hr", "meta", "link", "input", "wbr", "col", "source"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.h2 = None  # current h2 id
        self.h3 = None  # current h3 id
        self._hd = None  # heading tag being read
        self._hid = None
        self.tables: list[dict] = []
        self._tstack: list[dict] = []
        self.items: list[dict] = []  # li / p / dt / dd blocks: {h2, h3, tag, parent, text, links}
        self._blocks: list[dict] = []
        self._lists: list[str] = []
        self._skip = 0
        self._skipstack: list[str] = []
        self._fmt = {"b": 0, "i": 0}

    # text sinks -----------------------------------------------------------------------
    def _cell(self):
        if self._tstack:
            t = self._tstack[-1]
            if t["rows"] and t["rows"][-1]:
                return t["rows"][-1][-1]
        return None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class") or ""
        if self._skip:
            if tag not in self.VOID:
                self._skipstack.append(tag)
            return
        # every <sup> is dropped: footnote markers, and extra-inning counts that the bracket
        # templates attach to scores ("2<sup>10</sup>" = 2 runs in 10 innings)
        if tag in ("style", "script", "sup") or (
            tag == "span" and "mw-editsection" in cls
        ):
            self._skip = 1
            self._skipstack = [tag]
            return
        if tag in ("h2", "h3"):
            self._hd, self._hid = tag, a.get("id")
            return
        if tag in ("b", "i"):
            self._fmt[tag] += 1
            c = self._cell()
            if c is not None:
                c["bold" if tag == "b" else "ital"] = True
            if self._blocks:
                self._blocks[-1]["bold" if tag == "b" else "ital"] = True
        if tag == "table":
            t = {"h2": self.h2, "h3": self.h3, "class": cls, "rows": []}
            self.tables.append(t)
            self._tstack.append(t)
            return
        if tag in ("ol", "ul"):
            self._lists.append(tag)
        if tag in ("li", "p", "dt", "dd") and not self._tstack:
            self._blocks.append(
                {"h2": self.h2, "h3": self.h3, "tag": tag,
                 "parent": self._lists[-1] if self._lists else None,
                 "text": "", "links": [], "bold": False, "ital": False}
            )
        if self._tstack:
            t = self._tstack[-1]
            if tag == "tr":
                t["rows"].append([])
            elif tag in ("td", "th"):
                if not t["rows"]:
                    t["rows"].append([])
                t["rows"][-1].append(
                    {"text": "", "links": [], "bold": False, "ital": False,
                     "rowspan": int(re.sub(r"\D", "", a.get("rowspan") or "") or 1),
                     "colspan": int(re.sub(r"\D", "", a.get("colspan") or "") or 1)}
                )
            elif tag == "a":
                c = self._cell()
                if c is not None:
                    c["links"].append(a.get("title") or "")
            elif tag == "br":
                c = self._cell()
                if c is not None:
                    c["text"] += "\n"
        else:
            if tag == "a" and self._blocks:
                self._blocks[-1]["links"].append(a.get("title") or "")

    def handle_endtag(self, tag):
        if self._skip:
            if self._skipstack and self._skipstack[-1] == tag:
                self._skipstack.pop()
            if not self._skipstack:
                self._skip = 0
            return
        if tag == self._hd:
            if tag == "h2":
                self.h2, self.h3 = self._hid, None
            else:
                self.h3 = self._hid
            self._hd = None
            return
        if tag in ("b", "i"):
            self._fmt[tag] = max(0, self._fmt[tag] - 1)
        if tag == "table" and self._tstack:
            self._tstack.pop()
        if tag in ("ol", "ul") and self._lists:
            self._lists.pop()
        if tag in ("li", "p", "dt", "dd") and self._blocks and not self._tstack:
            b = self._blocks.pop()
            b["text"] = norm_space(b["text"])
            self.items.append(b)
            if self._blocks:  # nested block: let the outer one see the text too
                self._blocks[-1]["text"] += " " + b["text"]

    def handle_data(self, d):
        if self._skip or self._hd:
            return
        c = self._cell()
        if c is not None:
            c["text"] += d
        elif self._blocks:
            self._blocks[-1]["text"] += d


def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def load(year: int) -> Page:
    p = Page()
    with gzip.open(RAW / f"wikipedia_{year}.html.gz", "rt", encoding="utf-8") as fh:
        p.feed(fh.read())
    return p


def grid(table: dict) -> list[tuple[int, int, dict]]:
    """Cells with their absolute (row, col), resolving rowspan/colspan."""
    occ: set[tuple[int, int]] = set()
    out = []
    for ri, row in enumerate(table["rows"]):
        c = 0
        for cell in row:
            while (ri, c) in occ:
                c += 1
            for a in range(cell["rowspan"]):
                for b in range(cell["colspan"]):
                    occ.add((ri + a, c + b))
            out.append((ri, c, cell))
            c += cell["colspan"]
    return out


# --------------------------------------------------------------------------------------
# Team names
# --------------------------------------------------------------------------------------
MARKS = "†‡*#§^"
# Variant spellings seen across tables of the same page -> one key.
ALIASES = {
    "mississippi": "ole miss",
    "miami": "miami (fl)",
    "miami (florida)": "miami (fl)",
    "southern california": "usc",
    "louisiana-lafayette": "louisiana",
    "ul lafayette": "louisiana",
    "louisiana lafayette": "louisiana",
    "north carolina state": "nc state",
    "uconn": "connecticut",
    "army west point": "army",
    "unc wilmington": "uncw",
    "unc-wilmington": "uncw",
    "texas a&m-corpus christi": "texas a&m–corpus christi",
    "central connecticut state": "central connecticut",
    "southeast missouri": "southeast missouri state",
    "semo": "southeast missouri state",
    "cal state fullerton": "cal state fullerton",
    "uc irvine": "uc irvine",
    "saint mary's": "saint mary's (ca)",
    "st. mary's": "saint mary's (ca)",
    "liu brooklyn": "liu",
    "long island": "liu",
    "southern miss": "southern miss",
    "southern mississippi": "southern miss",
    "ut arlington": "texas-arlington",
    "ut-arlington": "texas-arlington",
    "utsa": "utsa",
    "fiu": "fiu",
    "florida international": "fiu",
    "mcneese": "mcneese state",
    "nicholls": "nicholls state",
    "sam houston": "sam houston state",
    "ucf": "ucf",
    "central florida": "ucf",
    "vcu": "vcu",
    "virginia commonwealth": "vcu",
}


def clean_name(s: str) -> str:
    s = norm_space(s)
    s = re.sub(r"^No\.\s*\d+\s+", "", s)
    s = s.strip(MARKS + " ")
    s = re.sub(r"\s*\((?:\d+|\d+-\d+)\)$", "", s)
    return s.strip()


def key(name: str) -> str:
    s = unicodedata.normalize("NFKC", clean_name(name)).lower()
    s = s.replace("—", "-").replace("’", "'")
    s = re.sub(r"\s+", " ", s).strip()
    s2 = s.replace("–", "-")
    if s in ALIASES:
        return ALIASES[s]
    if s2 in ALIASES:
        return ALIASES[s2]
    return s2.replace("-", "–") if "a&m" in s2 else s2


STOP = {"university", "of", "the", "at", "college", "institute", "and", "in", "main", "campus"}
EXPAND = {
    "nc": "north carolina", "unc": "north carolina", "uc": "california", "lsu": "louisiana state",
    "ole": "mississippi", "miss": "mississippi", "tcu": "texas christian", "ucla": "california los angeles",
    "usc": "southern california", "ecu": "east carolina", "byu": "brigham young", "dbu": "dallas baptist",
    "ucf": "central florida", "fau": "florida atlantic", "fiu": "florida international",
    "unlv": "nevada las vegas", "vcu": "virginia commonwealth", "smu": "southern methodist",
    "utsa": "texas san antonio", "uconn": "connecticut", "unf": "north florida", "uab": "alabama birmingham",
    "fl": "", "a&m": "a&m", "st": "state", "liu": "long island", "csun": "california state northridge",
    "ul": "louisiana", "uncw": "north carolina wilmington", "ttu": "texas tech",
    "virginia tech": "virginia polytechnic state",
}


def tokens(s: str) -> set[str]:
    s = unicodedata.normalize("NFKC", s).lower().replace("–", " ").replace("-", " ")
    s = re.sub(r"[().,']", " ", s)
    if s.strip() == "virginia tech":
        s = "virginia polytechnic state"
    out: list[str] = []
    for w in s.split():
        out.extend(EXPAND.get(w, w).split())
    return {w for w in out if w and w not in STOP}


def match_institution(inst: str, candidates: list[str]) -> str | None:
    """Pick the candidate team whose name best matches an institution name (unique best)."""
    it = tokens(inst)
    scored = []
    for c in candidates:
        ct = tokens(c)
        if not ct or not it:
            continue
        j = len(it & ct) / len(it | ct)
        scored.append((j, c))
    scored.sort(reverse=True)
    if not scored or scored[0][0] == 0:
        return None
    if len(scored) > 1 and scored[1][0] == scored[0][0]:
        return None
    return scored[0][1]


# --------------------------------------------------------------------------------------
# Season extraction
# --------------------------------------------------------------------------------------
NUM = re.compile(r"^\d+$")


def is_team_text(s: str) -> bool:
    return bool(re.search(r"[A-Za-z]", s))


def parse_bracket(table: dict) -> dict:
    """One "<City> Super Regional" table -> two regionals and one super regional."""
    cells = grid(table)
    at = {(r, c): cell for r, c, cell in cells}
    header = [(c, cell) for r, c, cell in cells if r == 0 and norm_space(cell["text"])]
    starts = {}
    for c, cell in header:
        t = norm_space(cell["text"])
        if t.startswith("Super Regional"):
            starts["super"] = c
        elif t.startswith("Regional Final"):
            starts["final"] = c
    if set(starts) != {"super", "final"}:
        raise ValueError(f"bracket header not recognised: {[norm_space(x['text']) for _, x in header]}")
    captions = [(r, norm_space(cell["text"]), cell["links"]) for r, c, cell in cells
                if r > 0 and cell["colspan"] >= 5 and "Regional" in cell["text"]]
    if len(captions) != 2:
        raise ValueError(f"expected 2 regional captions, got {captions}")
    mid = (captions[0][0] + captions[1][0]) / 2.0

    regs = [{"caption": cap, "caption_links": links, "teams": {}, "final": set()} for _, cap, links in captions]
    sup = []
    for r, c, cell in cells:
        txt = norm_space(cell["text"])
        if r == 0 or cell["colspan"] >= 5 or not is_team_text(txt) or txt in ("–", "-"):
            continue
        name = clean_name(txt)
        left = at.get((r, c - 1))
        seed_txt = norm_space(left["text"]) if left else ""
        seed = int(seed_txt) if NUM.match(seed_txt) else None
        if c >= starts["super"]:
            scores = []
            for k in range(1, 4):
                sc = at.get((r, c + k))
                st = norm_space(sc["text"]) if sc else ""
                m = re.match(r"^(\d+)", st)
                scores.append(int(m.group(1)) if m else None)
            sup.append({"team": name, "national_seed": seed, "scores": scores, "bold": cell["bold"], "row": r})
            continue
        reg = regs[0] if r < mid else regs[1]
        if c >= starts["final"]:
            reg["final"].add(key(name))
            continue
        k = key(name)
        if k in reg["teams"] and reg["teams"][k]["seed"] != seed:
            raise ValueError(f"{name}: seeds {reg['teams'][k]['seed']} and {seed} in {reg['caption']}")
        reg["teams"].setdefault(k, {"team": name, "seed": seed})
    return {"regionals": regs, "super": sup}


def section_items(page: Page, h2_prefix: str) -> list[dict]:
    return [it for it in page.items if it["h2"] and it["h2"].startswith(h2_prefix)]


def national_seeds(page: Page) -> list[str]:
    items = [it for it in section_items(page, "National_seeds") if it["tag"] == "li" and it["text"]]
    if any(it["parent"] == "ol" for it in items):
        items = [it for it in items if it["parent"] == "ol"]
    if items:
        return [clean_name(it["text"]) for it in items]
    # 2018/2019: "N. Team" lines inside a column table
    found = {}
    for t in page.tables:
        if t["h2"] == "National_seeds":
            for row in t["rows"]:
                for cell in row:
                    for line in cell["text"].split("\n"):
                        m = re.match(r"^\s*(\d+)\.\s*(.+?)\s*$", line.replace("\xa0", " "))
                        if m:
                            found[int(m.group(1))] = clean_name(m.group(2))
    return [found[i] for i in sorted(found)]


def schedule(page: Page) -> dict[str, list[dict]]:
    """Schedule-and-venues lines: {"regional": [...], "super": [...]}, each {venue, city, inst}."""
    out = {"regional": [], "super": []}
    label = None
    for it in section_items(page, "Schedule_and_venues"):
        t = it["text"]
        if it["tag"] in ("dt", "p") or (it["tag"] == "li" and "Host" not in t):
            low = t.lower()
            if low.startswith("super regional"):
                label = "super"
            elif low.startswith("regional"):
                label = "regional"
            elif "world series" in low:
                label = "cws"
            continue
        if it["tag"] in ("li", "dd") and "Host" in t and label in out:
            m = re.match(r"^(?P<venue>.+?),\s*(?P<city>[^,]+),\s*(?P<state>[^,(]+?),?\s*\(\s*Host:\s*(?P<inst>[^)]+?)\s*\)?$", t)
            if not m:
                raise ValueError(f"schedule line not parsed: {t}")
            out[label].append({k: norm_space(v) for k, v in m.groupdict().items()})
    return out


def hosted_by(page: Page) -> dict[str, str]:
    out = {}
    for it in page.items:
        if it["h2"] == "Regionals_and_Super_Regionals" and it["h3"] and it["tag"] == "p":
            m = re.match(r"^Hosted by (.+?) at ", it["text"])
            if m:
                out[it["h3"]] = clean_name(m.group(1))
    return out


def bids(page: Page) -> tuple[dict, str]:
    """{key: {"team", "conference", "bid"}} from the bid tables, and a description of the source."""
    out = {}
    kinds = []
    for t in page.tables:
        if t["h2"] != "Bids" or "wikitable" not in t["class"] or not t["rows"]:
            continue
        head = [norm_space(c["text"]).lower() for c in t["rows"][0]]
        h3 = (t["h3"] or "").lower().replace("–", "-")
        if "automatic" in h3:
            kind = "auto"
        elif "at-large" in h3:
            kind = "at-large"
        elif h3.startswith("by_conference") or "schools" in head:
            continue
        else:
            kind = "berth"
        kinds.append(kind)
        ci = head.index("conference")
        bi = head.index("berth") if "berth" in head else None
        rows: dict[int, dict[int, dict]] = {}
        for r, c, cell in grid(t):  # conference cells may span rows
            for k in range(cell["rowspan"]):
                rows.setdefault(r + k, {})[c] = cell
        for r in sorted(rows):
            row = rows[r]
            if r == 0 or 0 not in row or ci not in row:
                continue
            team = clean_name(row[0]["text"])
            conf = norm_space(row[ci]["text"])
            if kind == "berth":
                b = norm_space(row[bi]["text"]).lower()
                bid = "at-large" if b.startswith("at") else "auto"
            else:
                bid = kind
            out[key(team)] = {"team": team, "conference": conf, "bid": bid}
    if "berth" in kinds:
        src = "combined Bids table (Berth column)"
    elif "auto" in kinds and "at-large" in kinds:
        src = "Automatic bids and At-large tables"
    elif kinds == ["auto"]:
        src = "Automatic bids table only; teams not in it recorded at-large (64 = automatic + at-large)"
    else:
        src = f"unrecognised bid tables: {kinds}"
    return out, src


def by_conference(page: Page) -> dict[str, str]:
    out = {}
    for t in page.tables:
        if t["h2"] != "Bids" or not t["rows"]:
            continue
        head = [norm_space(c["text"]).lower() for c in t["rows"][0]]
        if "schools" not in head:
            continue
        si = head.index("schools")
        for row in t["rows"][1:]:
            if len(row) <= si:
                continue
            conf = norm_space(row[0]["text"])
            for s in re.split(r",\s*|\n", row[si]["text"]):
                s = clean_name(s)
                if s:
                    out[key(s)] = conf
    return out


def cws_participants(page: Page) -> list[str]:
    for t in page.tables:
        if t["h3"] == "Participants" and t["rows"]:
            return [clean_name(r[0]["text"]) for r in t["rows"][1:] if r and norm_space(r[0]["text"])]
    raise ValueError("no Participants table")


def final_places(page: Page) -> dict[str, str]:
    """Final standings: team -> place for the 1st and 2nd rows (place cells may span rows)."""
    for t in page.tables:
        if t["h2"] == "Final_standings" and "wikitable" in t["class"]:
            out = {}
            cells = grid(t)
            place_at = {}
            for r, c, cell in cells:
                if c == 0 and r > 0:
                    for k in range(cell["rowspan"]):
                        place_at[r + k] = norm_space(cell["text"])
            for r, c, cell in cells:
                if c == 1 and r > 0:
                    out[clean_name(cell["text"])] = place_at.get(r)
            return out
    return {}


def infobox(page: Page) -> dict[str, str]:
    for t in page.tables:
        if "infobox" in t["class"]:
            return {norm_space(r[0]["text"]): norm_space(r[1]["text"]) for r in t["rows"] if len(r) == 2}
    return {}


def city_of(caption: str) -> str:
    return re.sub(r"\s+Regional$", "", caption.split(" – ")[0].split(" - ")[0]).strip()


def season(year: int) -> tuple[dict, list[str]]:
    page = load(year)
    notes: list[str] = []
    sched = schedule(page)
    hb = hosted_by(page)
    sup_tables = [t for t in page.tables if t["h2"] == "Regionals_and_Super_Regionals"
                  and (t["h3"] or "").endswith("Super_Regional") and not t["class"].strip()]
    regionals, supers = [], []
    for t in sup_tables:
        b = parse_bracket(t)
        sup_city = t["h3"].replace("_Super_Regional", "").replace("_", " ")
        reg_out = []
        for reg in b["regionals"]:
            teams = sorted(reg["teams"].values(), key=lambda x: (x["seed"] is None, x["seed"]))
            sup_keys = {key(s["team"]) for s in b["super"]}
            winners = [x["team"] for x in teams if key(x["team"]) in sup_keys]
            winner = winners[0] if len(winners) == 1 else None
            if winner is None:
                notes.append(f"{reg['caption']}: regional winner not identified ({winners})")
            elif key(winner) not in reg["final"]:
                notes.append(f"{reg['caption']}: winner {winner} not in the regional final column")
            cap = reg["caption"]
            name = cap.split(" – ")[0].strip().strip(MARKS + " ")
            stadium = cap.split(" – ", 1)[1].strip() if " – " in cap else None
            city = city_of(cap)
            host, host_src = None, None
            line = None
            for s in sched["regional"]:
                if stadium and (norm_space(s["venue"]).lower() == stadium.lower()
                                or stadium.lower() in s["venue"].lower()
                                or s["venue"].lower().endswith(stadium.lower())):
                    line = s
                    break
            if line is None:
                for s in sched["regional"]:
                    if s["city"].lower() == city.lower():
                        line = s
                        break
            if line is not None:
                host = match_institution(line["inst"], [x["team"] for x in teams])
                host_src = f"Schedule and venues: {line['venue']}, {line['city']} (Host: {line['inst']})"
                if host is None:
                    notes.append(f"{cap}: host institution '{line['inst']}' not matched to a team")
            elif sched["regional"]:
                notes.append(f"{cap}: no schedule line for this regional")
            if host is None and not sched["regional"]:
                host = next((x["team"] for x in teams if x["seed"] == 1), None)
                host_src = "inferred: regional 1 seed (page lists no regional hosts)"
            if host is not None and next((x["seed"] for x in teams if x["team"] == host), None) != 1:
                notes.append(f"{name}: host {host} is not the regional 1 seed ({host_src})")
            reg_out.append({
                "name": name,
                "site": stadium,
                "city": city,
                "host": host,
                "host_source": host_src,
                "teams": [{"team": x["team"], "seed": x["seed"]} for x in teams],
                "winner": winner,
            })
        regionals.extend(reg_out)

        # super regional ------------------------------------------------------------
        s = b["super"]
        if len(s) != 2:
            raise ValueError(f"{year} {t['h3']}: {len(s)} super regional team cells")
        wins = [0, 0]
        for g in range(3):
            a, c = s[0]["scores"][g], s[1]["scores"][g]
            if a is not None and c is not None and a != c:
                wins[0 if a > c else 1] += 1
        sw = s[0]["team"] if wins[0] >= 2 else s[1]["team"] if wins[1] >= 2 else None
        if sw is None:
            notes.append(f"{t['h3']}: super winner not readable from scores {wins}")
        names = [x["team"] for x in s]
        host, host_src = None, None
        if t["h3"] in hb:
            host = next((n for n in names if key(n) == key(hb[t["h3"]])), None) or match_institution(hb[t["h3"]], names)
            host_src = f"page: 'Hosted by {hb[t['h3']]}'"
        if host is None:
            for line in sched["super"]:
                if line["city"].lower() == sup_city.lower() or sup_city.lower() in line["city"].lower():
                    host = match_institution(line["inst"], names)
                    host_src = f"Schedule and venues: {line['venue']}, {line['city']} (Host: {line['inst']})"
                    break
        if host is None:
            for r in reg_out:
                if r["city"].lower() == sup_city.lower() and r["winner"] and r["host"] and key(r["winner"]) == key(r["host"]):
                    host = r["winner"]
                    host_src = f"inferred: super held in {sup_city}, site of the {r['name']} won by its host"
        page_note = " ".join(it["text"] for it in page.items
                             if it["h3"] == t["h3"] and it["tag"] == "p" and it["text"]) or None
        if host is None:
            notes.append(f"{t['h3']}: super host not identified (page note: {page_note})")
            host_src = ("none: the listed host is neither team; " + (host_src or "no host statement")
                        + ("; see page_note" if page_note else ""))
        if sw is not None:
            bold = [x["team"] for x in s if x["bold"]]
            if len(bold) == 1 and key(bold[0]) != key(sw):
                notes.append(f"{t['h3']}: bold team {bold[0]} differs from score winner {sw}")
        supers.append({
            "name": f"{sup_city} Super Regional",
            "teams": names,
            "national_seeds_shown": {x["team"]: x["national_seed"] for x in s if x["national_seed"]},
            "host": host,
            "host_source": host_src,
            "page_note": page_note,
            "winner": sw,
        })

    # teams ---------------------------------------------------------------------------
    bid_map, bid_src = bids(page)
    conf_map = by_conference(page)
    seeds = national_seeds(page)
    seed_of = {key(n): i + 1 for i, n in enumerate(seeds)}
    hosts = {key(r["host"]) for r in regionals if r["host"]}
    teams = []
    for r in regionals:
        for x in r["teams"]:
            k = key(x["team"])
            b = bid_map.get(k)
            # "By conference" covers all 64 with one naming style per page; the bids tables
            # spell some conferences out ("Southeastern" vs "SEC"), kept as conference_bids_table.
            conf = conf_map.get(k) or (b["conference"] if b else None)
            if b is None and bid_src.startswith("Automatic bids table only"):
                bid = "at-large"
            else:
                bid = b["bid"] if b else None
            if conf is None:
                notes.append(f"{x['team']}: conference not found")
            if k not in conf_map:
                notes.append(f"{x['team']}: not in the By conference table; conference from the bids table")
            teams.append({"team": x["team"], "conference": conf,
                          "conference_bids_table": b["conference"] if b else None, "bid": bid,
                          "national_seed": seed_of.get(k), "host": k in hosts})
    team_keys = {key(t["team"]) for t in teams}
    for n in seeds:
        if key(n) not in team_keys:
            notes.append(f"national seed '{n}' not found among bracket teams")
    for k, b in bid_map.items():
        if k not in team_keys:
            notes.append(f"bids-table team '{b['team']}' not found among bracket teams")
    for k in conf_map:
        if k not in team_keys:
            notes.append(f"by-conference team '{k}' not found among bracket teams")
    # super column national seeds must agree with the published list
    for sp in supers:
        for n, sd in sp["national_seeds_shown"].items():
            if seed_of.get(key(n)) != sd:
                notes.append(f"{sp['name']}: bracket shows {n} as national seed {sd}, list says {seed_of.get(key(n))}")

    cws = cws_participants(page)
    places = final_places(page)
    champ = next((n for n, p in places.items() if p == "1st"), None)
    runner = next((n for n, p in places.items() if p == "2nd"), None)
    ib = infobox(page)
    if champ and "Champions" in ib and key(champ) not in key(ib["Champions"]) and not ib["Champions"].lower().startswith(champ.lower()):
        notes.append(f"infobox champion '{ib['Champions']}' vs final standings '{champ}'")
    if runner and "Runner-up" in ib and not ib["Runner-up"].lower().startswith(runner.lower()):
        notes.append(f"infobox runner-up '{ib['Runner-up']}' vs final standings '{runner}'")

    # use bracket spellings for CWS / champion where they differ only by alias
    spell = {key(t["team"]): t["team"] for t in teams}
    cws = [spell.get(key(n), n) for n in cws]
    champ = spell.get(key(champ), champ) if champ else None
    runner = spell.get(key(runner), runner) if runner else None

    out = {
        "url": URL.format(y=year),
        "raw_file": f"data/ncaa_brackets/raw/wikipedia_{year}.html.gz",
        "national_seeds_published": len(seeds),
        "national_seeds": seeds,
        "bid_source": bid_src,
        "teams": teams,
        "regionals": regionals,
        "supers": supers,
        "cws": cws,
        "champion": champ,
        "runner_up": runner,
    }
    return out, notes


# --------------------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------------------
def validate(year: int, s: dict) -> list[str]:
    err = []
    teams = s["teams"]
    keys = [key(t["team"]) for t in teams]
    if len(teams) != 64:
        err.append(f"{len(teams)} teams, expected 64")
    if len(set(keys)) != len(keys):
        err.append("duplicate teams")
    if len(s["regionals"]) != 16:
        err.append(f"{len(s['regionals'])} regionals, expected 16")
    winners = []
    for r in s["regionals"]:
        if len(r["teams"]) != 4:
            err.append(f"{r['name']}: {len(r['teams'])} teams")
        if sorted(x["seed"] or 0 for x in r["teams"]) != [1, 2, 3, 4]:
            err.append(f"{r['name']}: seeds {[x['seed'] for x in r['teams']]}")
        tk = {key(x["team"]) for x in r["teams"]}
        if not r["winner"] or key(r["winner"]) not in tk:
            err.append(f"{r['name']}: winner {r['winner']} not one of its teams")
        else:
            winners.append(key(r["winner"]))
        if not r["host"] or key(r["host"]) not in tk:
            err.append(f"{r['name']}: host {r['host']} not one of its teams")
    if len(s["supers"]) != 8:
        err.append(f"{len(s['supers'])} supers, expected 8")
    sw = []
    sup_teams = []
    for sp in s["supers"]:
        tk = [key(x) for x in sp["teams"]]
        sup_teams += tk
        for k in tk:
            if k not in winners:
                err.append(f"{sp['name']}: {k} is not a regional winner")
        if not sp["winner"] or key(sp["winner"]) not in tk:
            err.append(f"{sp['name']}: winner {sp['winner']} not one of its teams")
        else:
            sw.append(key(sp["winner"]))
        if sp["host"] is not None and key(sp["host"]) not in tk:
            err.append(f"{sp['name']}: host {sp['host']} not one of its teams")
    if sorted(sup_teams) != sorted(winners):
        err.append("super regional teams are not exactly the 16 regional winners")
    cws = [key(x) for x in s["cws"]]
    if len(cws) != 8 or sorted(cws) != sorted(sw):
        err.append(f"CWS teams {sorted(cws)} != super winners {sorted(sw)}")
    if not s["champion"] or key(s["champion"]) not in cws:
        err.append(f"champion {s['champion']} not a CWS team")
    if not s["runner_up"] or key(s["runner_up"]) not in cws or s["runner_up"] == s["champion"]:
        err.append(f"runner-up {s['runner_up']} not a CWS team")
    if s["national_seeds_published"] not in (8, 16):
        err.append(f"{s['national_seeds_published']} national seeds published")
    if sum(1 for t in teams if t["national_seed"]) != s["national_seeds_published"]:
        err.append("national seeds not all matched to teams")
    if sum(t["host"] for t in teams) != 16:
        err.append(f"{sum(t['host'] for t in teams)} regional hosts, expected 16")
    nb = sum(1 for t in teams if t["bid"] is None)
    if nb:
        err.append(f"{nb} teams without bid type")
    nc = sum(1 for t in teams if not t["conference"])
    if nc:
        err.append(f"{nc} teams without conference")
    return err


def build() -> tuple[dict, dict]:
    seasons, report = {}, {}
    for y in SEASONS:
        s, notes = season(y)
        errs = validate(y, s)
        s["validation"] = {"passed": not errs, "errors": errs, "notes": notes}
        seasons[str(y)] = s
        report[y] = (errs, notes)
    doc = {
        "source": "English Wikipedia, '<YEAR> NCAA Division I baseball tournament' pages "
                  "(bids tables, National seeds, Schedule and venues, regional/super regional "
                  "brackets, CWS Participants and Final standings). Secondary source; not NCAA official.",
        "fetched_on": FETCHED_ON,
        "parser": "scripts/parse_brackets.py",
        "seasons": seasons,
    }
    return doc, report


def main(argv: list[str]) -> int:
    doc, report = build()
    for y, (errs, notes) in report.items():
        s = doc["seasons"][str(y)]
        nb = {"auto": 0, "at-large": 0, None: 0}
        for t in s["teams"]:
            nb[t["bid"]] += 1
        print(f"{y}: teams {len(s['teams'])}, regionals {len(s['regionals'])}, supers {len(s['supers'])}, "
              f"national seeds {s['national_seeds_published']}, auto {nb['auto']}, at-large {nb['at-large']}, "
              f"champion {s['champion']} | {'OK' if not errs else 'FAIL'}")
        for e in errs:
            print("   ERROR", e)
        for n in notes:
            print("   note ", n)
    text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    if "--check" in argv:
        old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if old != text:
            print("JSON differs from the committed file")
            return 1
        print("JSON reproduces the committed file")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
