#!/usr/bin/env python3
"""Fetch 2025 college baseball rosters with bats/throws for the teams in the WMT
play-by-play sample. Runs on your own machine or in GitHub Actions
(.github/workflows/fetch_rosters.yml); many athletics sites block cloud IPs, and blocked sites
are logged and skipped.

    pip install requests
    python tools/fetch_rosters.py                 # all teams in tools/roster_teams.csv
    python tools/fetch_rosters.py --only 596583   # one team (LSU) to try it out
    python tools/fetch_rosters.py --selftest      # check the parsers offline
    python tools/fetch_rosters.py --reparse       # rebuild the CSV from saved pages (no fetching)
    python tools/fetch_rosters.py --probe 5       # try 5 teams across Sidearm, WMT and Presto; report blocks

Writes to data/ncaa_2025/rosters/ (change with --out):
    rosters_2025.csv     team_ncaa_id, team, name, jersey, position, class, bats, throws,
                         hometown_city, hometown_state, high_school, previous_school, source_url, wmt_person_id
                         (origin columns where the roster page lists them, blank otherwise;
                         wmt_person_id: WMT stats person id, filled on WMT Digital sites only)
    raw/<id>.html.gz     every roster page fetched, so parsing can be redone without refetching
    failures.csv         teams that could not be fetched or parsed, with the reason
    fetch_rosters.log    one line per request
    state.json           progress; rerunning skips teams already done (resumable)

None of this is committed (owner decision 2026-10-07; the folder is git-ignored): it holds
player names. tools/aggregate_rosters.py turns it into count and share tables in
data/ncaa_2025/roster_aggregates/, the only roster data the repository keeps.

Politeness: robots.txt is read for every domain and obeyed (including Crawl-delay);
at least 3 seconds between requests to any site (--delay, never below 3); one
request at a time; a descriptive User-Agent. Standard library plus requests only.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import html
import json
import logging
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib import robotparser

import requests

HERE = Path(__file__).resolve().parent
UA = "CollegeBaseballSim-roster-fetcher/1.0 (personal research project; one request every few seconds)"
MIN_DELAY = 3.0
PROBE_MAX_TRIES = 25      # teams the probe may try while looking for each platform
MAX_CRAWL_DELAY = 60.0    # a host whose robots.txt asks for a longer Crawl-delay is skipped (logged), not fetched faster
RESPONSE_DEADLINE = 90.0  # seconds for a whole response; a server that trickles bytes past it is treated as a block
MIN_PLAYERS = 10          # a parsed page with fewer players carrying bats/throws is treated as a miss
ORIGIN = ["hometown_city", "hometown_state", "high_school", "previous_school"]
FIELDS = ["team_ncaa_id", "team", "name", "jersey", "position", "class", "bats", "throws", *ORIGIN, "source_url", "wmt_person_id"]
# 2025 season roster URLs, most common platform first (Sidearm, WMT Digital, PrestoSports, old Sidearm)
PATHS = ["/sports/baseball/roster/2025", "/sports/bsb/roster/season/2025", "/sports/baseball/roster/season/2025",
         "/sports/baseball/roster/2024-25", "/sports/bsb/2024-25/roster", "/roster.aspx?path=baseball&year=2025"]
BOT_MARKERS = ("_Incapsula_Resource", "Incapsula incident", "cf-chl-", "Attention Required! | Cloudflare",
               "<TITLE>Loading</TITLE>", "Request blocked")
NUXT_TAGS = ("ShallowReactive", "Reactive", "Ref", "ShallowRef", "EmptyRef", "EmptyShallowRef")


# ---------------------------------------------------------------- normalisation
def norm_bats(v: str) -> str:
    v = (v or "").strip().upper()
    if v in ("L", "LEFT"):
        return "L"
    if v in ("R", "RIGHT"):
        return "R"
    if v in ("S", "B", "SWITCH", "BOTH"):
        return "S"
    return ""


def norm_throws(v: str) -> str:
    v = (v or "").strip().upper()
    return {"L": "L", "LEFT": "L", "R": "R", "RIGHT": "R"}.get(v, "")


BT_RE = re.compile(r"\b(L|R|S|B|Left|Right|Switch|Both)\s*[/\-]\s*(L|R|Left|Right)\b", re.I)


def split_bt(v: str) -> tuple[str, str]:
    m = BT_RE.search(v or "")
    return (norm_bats(m.group(1)), norm_throws(m.group(2))) if m else ("", "")


def clean(s) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(s or ""))).strip()


# ---------------------------------------------------------------- origin: hometown, high school, previous school
def split_hometown(v: str) -> tuple[str, str]:
    """'Baton Rouge, La.' -> ('Baton Rouge', 'La.'); 'Toronto, Ontario, Canada' -> ('Toronto', 'Ontario, Canada')."""
    v = clean(v).strip(" ,/")
    if not v:
        return "", ""
    city, _, state = v.partition(",")
    return city.strip(), state.strip()


def origin(hometown: str = "", high_school: str = "", previous: str = "", combined: str = "", order: tuple = ()) -> dict:
    """Origin columns from separate values or from one combined cell. Combined cells list the parts
    in the header's order separated by '/', and a previous school often sits in parentheses:
    'Dallas, Texas / Jesuit (Texas Tech)'."""
    hometown, high_school, previous = clean(hometown), clean(high_school), clean(previous)
    if combined:
        text = clean(combined)
        m = re.search(r"\(([^()]+)\)\s*$", text)
        if m:   # a trailing parenthetical fills the part the header names last, or the one it leaves out
            if order and order[-1] in ("previous_school", "high_school") and len(order) > 1:
                paren = order[-1]
            elif "high_school" not in order:
                paren = "high_school"
            else:
                paren = "previous_school"
            if paren == "previous_school":
                previous = previous or m.group(1).strip()
            else:
                high_school = high_school or m.group(1).strip()
            text = text[:m.start()].strip()
            order = tuple(k for k in order if k != paren)
        parts = [x.strip() for x in re.split(r"\s+/\s+|\s*/\s*(?=[A-Z])", text) if x.strip()]
        for kind, val in zip(order, parts):
            if kind == "hometown" and not hometown:
                hometown = val
            elif kind == "high_school" and not high_school:
                high_school = val
            elif kind == "previous_school" and not previous:
                previous = val
    city, state = split_hometown(hometown)
    return {"hometown_city": city, "hometown_state": state, "high_school": high_school, "previous_school": previous}


ORIGIN_KEYS = {  # normalised header / JSON key / label -> origin part
    "hometown": "hometown", "home town": "hometown", "hometowncity": "hometown",
    "highschool": "high_school", "high school": "high_school", "hs": "high_school", "highschoolname": "high_school",
    "previousschool": "previous_school", "previous school": "previous_school", "lastschool": "previous_school",
    "last school": "previous_school", "prevschool": "previous_school", "previouscollege": "previous_school",
    "transfer": "previous_school", "formerschool": "previous_school", "previous": "previous_school",
}


def origin_kinds(label: str) -> tuple:
    """Parts named in a header or label, in order: 'Hometown/High School (Previous School)' ->
    ('hometown', 'high_school', 'previous_school')."""
    lab = re.sub(r"[^a-z/() ]", "", label.lower())
    found = []
    for piece in re.split(r"[/()]", lab):
        key = ORIGIN_KEYS.get(piece.strip()) or ORIGIN_KEYS.get(piece.replace(" ", ""))
        if key and key not in found:
            found.append(key)
    return tuple(found)


# ---------------------------------------------------------------- parser 1: HTML tables
class _Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self._stack = [], []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._stack.append([])
        elif tag == "tr" and self._stack:
            self._stack[-1].append([])
        elif tag in ("td", "th") and self._stack and self._stack[-1]:
            self._stack[-1][-1].append("")

    def handle_endtag(self, tag):
        if tag == "table" and self._stack:
            self.tables.append(self._stack.pop())

    def handle_data(self, data):
        if self._stack and self._stack[-1] and self._stack[-1][-1]:
            self._stack[-1][-1][-1] += data


def _col(header: list[str], *keys: str) -> int | None:
    h = [re.sub(r"[^a-z/#.]", "", c.lower()) for c in header]
    for k in keys:
        for i, c in enumerate(h):
            if c == k:
                return i
    return None


def parse_tables(page: str) -> list[dict]:
    p = _Tables()
    p.feed(page)
    out = []
    for rows in p.tables:
        rows = [[clean(c) for c in r] for r in rows if r]
        for hi, header in enumerate(rows[:3]):
            bt = _col(header, "b/t", "bats/throws", "b-t", "bt")
            bats, throws = _col(header, "bats", "b"), _col(header, "throws", "t")
            if bt is None and (bats is None or throws is None):
                continue
            name = _col(header, "name", "player", "fullname", "playername")
            first, last = _col(header, "firstname", "first"), _col(header, "lastname", "last")
            num = _col(header, "#", "no.", "no", "number", "jersey")
            pos = _col(header, "pos.", "pos", "position")
            cls = _col(header, "yr.", "yr", "cl.", "cl", "class", "year", "academicyear", "eligibility")
            ocols = [(i, origin_kinds(c)) for i, c in enumerate(header) if origin_kinds(c)]
            for r in rows[hi + 1:]:
                get = lambda i: r[i] if i is not None and i < len(r) else ""
                b, t = split_bt(get(bt)) if bt is not None else (norm_bats(get(bats)), norm_throws(get(throws)))
                nm = get(name) or f"{get(first)} {get(last)}".strip()
                if nm and b and t:
                    o = {k: "" for k in ORIGIN}
                    for i, kinds in ocols:
                        part = origin(combined=get(i), order=kinds)
                        o.update({k: v for k, v in part.items() if v and not o[k]})
                    out.append({"name": nm, "jersey": get(num), "position": get(pos), "class": get(cls), "bats": b, "throws": t, **o})
            if out:
                return out
    return out


# ---------------------------------------------------------------- parser 2: embedded JSON (Nuxt, Next, ld+json)
def _hydrate(raw):
    """Nuxt 3 payloads are flat arrays where values point at other indices."""
    memo: dict = {}

    def hy(i):
        if not isinstance(i, int) or i < 0 or i >= len(raw):
            return None
        if i in memo:
            return memo[i]
        v = raw[i]
        memo[i] = None
        if isinstance(v, list):
            if len(v) == 2 and isinstance(v[0], str) and v[0] in NUXT_TAGS and isinstance(v[1], int):
                out = hy(v[1])
            elif v and isinstance(v[0], str) and v[0] in ("Date", "BigInt", "RegExp"):
                out = v[1] if len(v) > 1 else None
            elif v and isinstance(v[0], str) and v[0] in ("Set", "Map"):
                out = [hy(x) for x in v[1:] if isinstance(x, int)]
            else:
                out = [hy(x) for x in v]
        elif isinstance(v, dict):
            out = {k: hy(x) for k, x in v.items()}
        else:
            out = v
        memo[i] = out
        return out
    return hy(0)


SCRIPT_RE = re.compile(r"<script([^>]*)>(.*?)</script>", re.S | re.I)
NAME_KEYS = ("fullName", "full_name", "playerName", "displayName", "name", "title")


def _wmt_player(d: dict) -> dict | None:
    """WMT Digital roster entry: custom fields in profile_field_values ({profile_field: {name}, value})."""
    pl = d.get("player") if isinstance(d.get("player"), dict) else {}
    fields = [v for v in (d.get("profile_field_values") or []) + (pl.get("profile_field_values") or []) if isinstance(v, dict)]
    named = {re.sub(r"[^a-z/ ]", "", str(v["profile_field"].get("name", "")).lower()).strip(): clean(v.get("value") or "")
             for v in fields if isinstance(v.get("profile_field"), dict)}
    bt = next((v for k, v in named.items() if k.replace(" ", "") in ("b/t", "bats/throws", "bt")), "")
    o = {k: "" for k in ORIGIN}
    for k, v in list(named.items()) + [(k, clean(pl.get(k2) or d.get(k2) or "")) for k, k2 in (("hometown", "hometown"), ("high school", "high_school"),
                                                                                              ("previous school", "previous_school"))]:
        kinds = origin_kinds(k)
        if kinds and v:
            part = origin(combined=v, order=kinds)
            o.update({kk: vv for kk, vv in part.items() if vv and not o[kk]})
    b, t = split_bt(bt)
    nm = pl.get("full_name") or f"{pl.get('first_name', '')} {pl.get('last_name', '')}".strip()
    if not (b and t and nm):
        return None
    pos = d.get("player_position") or pl.get("player_position") or {}
    cls = d.get("class_level") or pl.get("class_level") or {}
    return {"name": clean(nm), "jersey": clean(d.get("jersey_number_label") or d.get("jersey_number") or pl.get("jersey_number_label") or ""),
            "position": clean(pos.get("abbreviation") or pos.get("name") or "") if isinstance(pos, dict) else clean(pos),
            "class": clean(cls.get("abbreviation") or cls.get("name") or "") if isinstance(cls, dict) else clean(cls),
            "bats": b, "throws": t, **o, "wmt_person_id": str(pl.get("wmt_stats2_person_id") or "")}


def _player_from(d: dict) -> dict | None:
    if not isinstance(d, dict):
        return None
    if "profile_field_values" in d and isinstance(d.get("player"), dict):
        return _wmt_player(d)
    lower = {k.lower(): k for k in d}
    b = t = ""
    for k, v in d.items():
        if not isinstance(v, str):
            continue
        kl = k.lower()
        if kl in ("bats", "bat", "batshand", "battinghand", "bats_hand"):
            b = norm_bats(v)
        elif kl in ("throws", "throw", "throwshand", "throwinghand", "throws_hand"):
            t = norm_throws(v)
        elif (("bat" in kl and "throw" in kl) or kl in ("bt", "b_t") or kl.startswith("custom")) and BT_RE.fullmatch(v.strip() or "x"):
            b, t = split_bt(v)
    if not (b and t):
        return None
    nm = ""
    for k in NAME_KEYS:
        if isinstance(d.get(k), str) and d[k].strip():
            nm = d[k]
            break
    if not nm:
        fn = next((d[lower[k]] for k in ("firstname", "first_name") if k in lower and isinstance(d[lower[k]], str)), "")
        ln = next((d[lower[k]] for k in ("lastname", "last_name") if k in lower and isinstance(d[lower[k]], str)), "")
        nm = f"{fn} {ln}".strip()
    if not nm and isinstance(d.get("player"), dict):
        inner = d["player"]
        nm = inner.get("fullName") or f"{inner.get('firstName', '')} {inner.get('lastName', '')}".strip()
    if not nm:
        return None
    pick = lambda *ks: next((clean(d[lower[k]]) for k in ks if k in lower and isinstance(d[lower[k]], (str, int)) and d[lower[k]] != ""), "")
    o = origin(hometown=pick("hometown", "home_town", "hometowncity"),
               high_school=pick("highschool", "high_school", "highschoolname"),
               previous=pick("previousschool", "previous_school", "lastschool", "last_school", "previouscollege", "formerschool"))
    return {"name": clean(nm), "jersey": pick("jerseynumber", "jersey", "number", "uniform", "jersey_number", "uni"),
            "position": pick("positionshort", "position_short", "position", "positionlong", "pos"),
            "class": pick("academicyearshort", "academicyear", "class", "classshort", "year", "eligibility", "academic_year"),
            "bats": b, "throws": t, **o}


def _walk(o, out):
    if isinstance(o, dict):
        p = _player_from(o)
        if p:
            out.append(p)
        for v in o.values():
            _walk(v, out)
    elif isinstance(o, list):
        for v in o:
            _walk(v, out)


def parse_json(page: str) -> list[dict]:
    out: list = []
    for attrs, body in SCRIPT_RE.findall(page):
        body = body.strip()
        if not body or body[0] not in "[{":
            continue
        try:
            data = json.loads(body)
        except ValueError:
            continue
        nuxt = "__NUXT_DATA__" in attrs or any(isinstance(x, list) and x[:1] in (["ShallowReactive"], ["Reactive"]) for x in data[:3]) \
            if isinstance(data, list) else False
        if nuxt:
            data = _hydrate(data)
        _walk(data, out)
    seen, uniq = set(), []
    for p in out:
        key = (p["name"].lower(), p["jersey"])
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq


# ---------------------------------------------------------------- parser 3: roster cards (text)
CARD_RE = re.compile(r'<(?:li|div|article)[^>]*class="[^"]*(?:sidearm-roster-player(?!-)|s-person-card(?!_)|roster-card|roster-player-card)[^"]*"[^>]*>',
                     re.I)
TAG_RE = re.compile(r"<[^>]+>")


ORIGIN_SPAN_RE = re.compile(r'class="[^"]*(hometown|highschool|high-school|previous-school|previousschool|last-school)[^"]*"[^>]*>(.*?)</', re.I | re.S)
LABEL_RE = re.compile(r"(Hometown|High School|Previous School|Last School|Hometown\s*/\s*High School)\s*:?\s*\|\s*([^|]+)", re.I)


def _card_origin(block: str, text: str) -> dict:
    """Sidearm card spans (class *hometown*, *highschool*, *previous-school*) or 'Label | value' text."""
    o = {k: "" for k in ORIGIN}
    found = []
    for cls_, val in ORIGIN_SPAN_RE.findall(block):
        key = {"hometown": "hometown", "highschool": "high_school", "high-school": "high_school"}.get(cls_.lower(), "previous_school")
        found.append(((key,), clean(TAG_RE.sub(" ", val))))
    for lab, val in LABEL_RE.findall(text):
        found.append((origin_kinds(lab), clean(val)))
    for kinds, val in found:
        if kinds and val:
            part = origin(combined=val, order=kinds)
            o.update({k: v for k, v in part.items() if v and not o[k]})
    return o


def parse_cards(page: str) -> list[dict]:
    starts = [m.start() for m in CARD_RE.finditer(page)]
    out = []
    for i, s in enumerate(starts):
        block = page[s: starts[i + 1] if i + 1 < len(starts) else s + 8000]
        text = clean(TAG_RE.sub(" | ", block))
        m = re.search(r"(?:B/T|Bats/Throws|B-T)\s*:?\s*\|?\s*([LRSB])\s*/\s*([LR])", text, re.I) or BT_RE.search(text)
        if not m:
            continue
        b, t = norm_bats(m.group(1)), norm_throws(m.group(2))
        nm = ""
        hm = re.search(r"<(?:h[1-6]|a)[^>]*>\s*(?:<[^>]+>\s*)*([^<]{3,60}?)\s*<", block[block.find(">") + 1:], re.S)
        for cand in re.findall(r'(?:aria-label|title|alt)="([^"]{3,60})"', block) + ([hm.group(1)] if hm else []):
            cand = clean(cand)
            if re.fullmatch(r"[A-Za-z][A-Za-z .'\-]+", cand) and not re.search(r"(?i)roster|photo|image|headshot|view|full bio", cand):
                nm = cand
                break
        jm = re.search(r"(?:#|Jersey Number|No\.)\s*\|?\s*(\d{1,2})\b", text)
        pm = re.search(r"\b(RHP|LHP|INF|OF|C|1B|2B|3B|SS|UT|IF|P|DH|C/INF|INF/OF|OF/INF|C/1B|1B/OF|RHP/INF|LHP/OF)\b", text)
        cm = re.search(r"\b(R-)?(Freshman|Sophomore|Junior|Senior|Graduate|Fr|So|Jr|Sr|Gr|5th)(\.|\b)", text)
        if nm and b and t:
            out.append({"name": nm, "jersey": jm.group(1) if jm else "", "position": pm.group(1) if pm else "",
                        "class": cm.group(0) if cm else "", "bats": b, "throws": t, **_card_origin(block, text)})
    return out


def parse_page(page: str) -> tuple[list[dict], str]:
    best, how = [], ""
    for fn, label in ((parse_tables, "table"), (parse_json, "json"), (parse_cards, "cards")):
        try:
            got = fn(page)
        except Exception as e:  # a parser bug on one layout must not stop the run
            logging.warning("parser %s raised %r", label, e)
            got = []
        if len(got) > len(best):
            best, how = got, label
    return best, how


# ---------------------------------------------------------------- fetching
class Fetcher:
    def __init__(self, delay: float):
        self.delay = max(delay, MIN_DELAY)
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
        self.robots: dict = {}
        self.last: dict = {}

    def _wait(self, host: str, extra: float = 0.0):
        gap = max(self.delay, extra)
        since = time.monotonic() - self.last.get(host, 0)
        if since < gap:
            time.sleep(gap - since)
        self.last[host] = time.monotonic()

    def robot(self, host: str):
        """robots.txt per RFC 9309: 2xx parsed, 4xx means no rules, 5xx or unreachable means do not crawl.
        Network errors and 5xx are retried twice before giving up on the host."""
        if host not in self.robots:
            rp, note = robotparser.RobotFileParser(), ""
            for attempt in range(3):
                self._wait(host, MIN_DELAY * (attempt + 1))
                try:
                    r = self._fetch(f"https://{host}/robots.txt", 30)
                except (requests.RequestException, TimeoutError) as e:
                    note = f"robots.txt unreachable ({e.__class__.__name__})"
                    continue
                if r.status_code >= 500:
                    note = f"robots.txt unreachable (HTTP {r.status_code})"
                    continue
                if r.status_code >= 400:
                    rp.allow_all = True
                else:
                    rp.parse(r.text.splitlines())
                note = ""
                break
            if note:
                rp.disallow_all = True
            logging.info("robots %s: %s", host, note or "ok")
            self.robots[host] = (rp, note)
        return self.robots[host]

    def _fetch(self, url: str, timeout: float):
        """GET with a per-read timeout and a deadline on the whole response (streamed, so a slow drip is cut off)."""
        start = time.monotonic()
        r = self.s.get(url, timeout=timeout, allow_redirects=True, stream=True)
        chunks = []
        try:
            for chunk in r.iter_content(65536):
                chunks.append(chunk)
                if time.monotonic() - start > RESPONSE_DEADLINE:
                    raise TimeoutError(url)
        finally:
            r.close()
        r._content = b"".join(chunks)
        r._content_consumed = True
        return r

    def get(self, host: str, path: str):
        rp, note = self.robot(host)
        url = f"https://{host}{path}"
        if note:
            return url, None, note
        if not rp.can_fetch(UA, url):
            return url, None, "disallowed by robots.txt"
        cd = float(rp.crawl_delay(UA) or 0)
        if cd > MAX_CRAWL_DELAY:
            return url, None, f"robots.txt Crawl-delay {cd:.0f} s (over {MAX_CRAWL_DELAY:.0f} s): skipped"
        r = None
        for attempt in range(3):  # network errors and 5xx retried with a growing pause
            self._wait(host, max(cd, MIN_DELAY * (attempt + 1)))
            try:
                r = self._fetch(url, 45)
            except TimeoutError:
                return url, None, f"response not complete in {RESPONSE_DEADLINE:.0f} s (treated as a block, not retried)"
            except requests.RequestException as e:
                err = f"request error: {e.__class__.__name__}"
                r = None
                continue
            if r.status_code < 500:
                break
        if r is None:
            return url, None, err
        logging.info("%s %s %d bytes", r.status_code, url, len(r.content))
        if r.status_code != 200:
            return url, None, f"HTTP {r.status_code}"
        if any(m in r.text[:5000] for m in BOT_MARKERS) and len(r.text) < 20000:
            return r.url, r.text, "bot challenge page"
        return r.url, r.text, ""


# ---------------------------------------------------------------- one team
def team_host(t: dict) -> str:
    return (t.get("domain") or "").strip().lower().removeprefix("https://").removeprefix("http://").strip("/")


def fetch_team(fetcher: "Fetcher", t: dict, out: Path) -> tuple[list[dict], str, str, str, list]:
    """Try the roster URLs of one team in turn. Returns (rows, parser, failure reason, last URL,
    [(url, page, error)] for every URL tried). The last page fetched is saved to raw/."""
    tid, host = t["team_ncaa_id"], team_host(t)
    if not host:
        return [], "", "no domain in roster_teams.csv (add one and rerun)", "", []
    reasons, tried, rows, how, last_url = [], [], [], "", ""
    for path in PATHS:
        url, page, err = fetcher.get(host, path)
        last_url = url
        err = err or (off_target(url) if page else "")
        tried.append((url, page, err))
        if page:
            with gzip.open(out / "raw" / f"{tid}.html.gz", "wt", encoding="utf-8") as g:
                g.write(f"<!-- source: {url} fetched {time.strftime('%Y-%m-%d')} -->\n" + page)
        if err:
            reasons.append(f"{path}: {err}")
            continue
        rows, how = parse_page(page)
        if len(rows) >= MIN_PLAYERS:
            return rows, how, "", last_url, tried
        reasons.append(f"{path}: parsed {len(rows)} players with bats/throws")
        rows = []
    return [], "", "; ".join(reasons), last_url, tried


def platform_of(tried: list) -> str:
    """Which site platform served the roster pages, from the pages themselves (Sidearm Sports,
    WMT Digital, PrestoSports), or 'unknown'."""
    for _, page, _ in reversed(tried):          # the last page fetched is the one that parsed, if any
        low = (page or "").lower()
        if not low:
            continue
        if "wmt_stats2" in low or "wmt.games" in low or "wmt.digital" in low:
            return "WMT"
        if "prestosports" in low:
            return "Presto"
        if "sidearmsports" in low or "sidearm-roster" in low or "sidearm_" in low:
            return "Sidearm"
    return "unknown"


def off_target(url: str) -> str:
    """A roster URL can redirect to another season's roster or away from baseball (seen: a 2025
    URL served the 2006 roster; another a soccer player page). Such a page is not used."""
    path = url.split("://", 1)[-1].split("/", 1)[-1].lower()
    if "baseball" not in path and "/bsb/" not in "/" + path and "path=baseball" not in path:
        return f"redirected away from the baseball roster ({url})"
    for y in re.findall(r"(?<!\d)((?:19|20)\d\d)(?:-\d\d)?(?!\d)", path):
        if y not in ("2024", "2025"):
            return f"redirected to another season ({url})"
    return ""


def blocked_by(tried: list) -> str:
    """The bot protection a page came back with, if any."""
    for _, page, err in tried:
        low = (page or "")[:5000]
        if "Incapsula" in low:
            return "Imperva Incapsula"
        if "cf-chl-" in low or "Cloudflare" in low:
            return "Cloudflare"
        if err in ("HTTP 403", "HTTP 429"):
            return err
    return ""


def probe(fetcher: "Fetcher", teams: list[dict], out: Path, n: int, max_tries: int) -> int:
    """Fetch a handful of teams' roster pages to see which platforms answer and which block.
    Goes down the team list until it has n pages and at least one Sidearm, WMT and Presto
    site (or max_tries teams). Writes probe.md and probe.json in out; never fails the run."""
    results, seen = [], set()
    for t in teams:
        if len(results) >= max_tries or (len(results) >= n and {"Sidearm", "WMT", "Presto"} <= seen):
            break
        if not team_host(t):
            continue
        rows, how, reason, last_url, tried = fetch_team(fetcher, t, out)
        plat = platform_of(tried)
        block = blocked_by(tried)
        if plat in seen and len(results) >= n:
            continue      # enough of this platform; keep looking for the missing ones
        seen.add(plat)
        results.append({"team_ncaa_id": t["team_ncaa_id"], "team": t["team"], "domain": team_host(t), "platform": plat,
                        "status": f"ok: {len(rows)} players ({how})" if rows else ("blocked: " + block if block else "failed"),
                        "detail": reason, "url": last_url})
        print(f"probe {t['team']} ({team_host(t)}): {plat}, {results[-1]['status']}", flush=True)
    lines = ["# Roster probe", "", f"{time.strftime('%Y-%m-%d %H:%M')} UTC. Platforms seen: {', '.join(sorted(seen)) or 'none'}.", "",
             "| Team | Domain | Platform | Status | Detail |", "|---|---|---|---|---|"]
    lines += [f"| {r['team']} | {r['domain']} | {r['platform']} | {r['status']} | {r['detail'][:200]} |" for r in results]
    blocked = [r for r in results if r["status"].startswith("blocked")]
    lines += ["", f"Blocked: {len(blocked)} of {len(results)}" + (" (" + ", ".join(f"{r['domain']} [{r['status'][9:]}]" for r in blocked) + ")" if blocked else "") + ".",
              "Blocked sites are logged and skipped; nothing tries to get around bot protection."]
    (out / "probe.md").write_text("\n".join(lines) + "\n")
    (out / "probe.json").write_text(json.dumps(results, indent=1) + "\n")
    print("\n".join(lines))
    return 0


# ---------------------------------------------------------------- main
def load_state(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {"done": {}, "failed": {}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--teams", default=str(HERE / "roster_teams.csv"))
    ap.add_argument("--out", default=str(HERE.parent / "data/ncaa_2025/rosters"))
    ap.add_argument("--delay", type=float, default=MIN_DELAY, help="seconds between requests (minimum 3)")
    ap.add_argument("--only", action="append", help="team_ncaa_id to fetch (repeatable)")
    ap.add_argument("--limit", type=int, help="stop after this many teams")
    ap.add_argument("--retry-failed", action="store_true", help="retry teams that failed on an earlier run")
    ap.add_argument("--selftest", action="store_true", help="run the offline parser checks and exit")
    ap.add_argument("--reparse", action="store_true", help="rebuild rosters_2025.csv from the saved raw/ pages without fetching")
    ap.add_argument("--probe", type=int, metavar="N", help="fetch N teams' roster pages (covering Sidearm, WMT and Presto) and report which are blocked")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    out = Path(a.out)
    if a.reparse:
        return reparse(out, a.teams)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=out / "fetch_rosters.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.WARNING)
    logging.getLogger().addHandler(console)
    state_path = out / "state.json"
    state = load_state(state_path)
    teams = list(csv.DictReader(open(a.teams, newline="")))
    if a.only:
        teams = [t for t in teams if t["team_ncaa_id"] in set(a.only)]
    if a.probe:
        return probe(Fetcher(a.delay), teams, out, a.probe, PROBE_MAX_TRIES)
    csv_path, fail_path = out / "rosters_2025.csv", out / "failures.csv"
    new_csv = not csv_path.exists()
    if not new_csv:
        with open(csv_path, newline="") as fh:
            header = next(csv.reader(fh), [])
        if header != FIELDS:
            print(f"{csv_path} has the columns of an older version of this script.\n"
                  "Run once with --reparse to rebuild it from the saved raw/ pages (no fetching), then rerun.")
            return 1
    fetcher = Fetcher(a.delay)
    done_now = 0
    with open(csv_path, "a", newline="") as fh, open(fail_path, "a", newline="") as ff:
        w, wf = csv.DictWriter(fh, FIELDS), csv.writer(ff)
        if new_csv:
            w.writeheader()
        if ff.tell() == 0:
            wf.writerow(["team_ncaa_id", "team", "domain", "reason", "last_url", "when"])
        for i, t in enumerate(teams):
            tid = t["team_ncaa_id"]
            if tid in state["done"] or (tid in state["failed"] and not a.retry_failed and not a.only):
                continue
            if a.limit is not None and done_now >= a.limit:
                break
            done_now += 1
            host = team_host(t)
            print(f"[{i + 1}/{len(teams)}] {t['team']} ({host or 'no domain'})", flush=True)
            rows, how, reason, last_url, _ = fetch_team(fetcher, t, out)
            if rows:
                for r in rows:
                    w.writerow({"team_ncaa_id": tid, "team": t["team"], "wmt_person_id": "", **r, "source_url": last_url})
                fh.flush()
                state["done"][tid] = {"players": len(rows), "parser": how, "url": last_url, "when": time.strftime("%Y-%m-%d %H:%M")}
                state["failed"].pop(tid, None)
                logging.info("OK %s %s: %d players via %s", tid, t["team"], len(rows), how)
            else:
                state["failed"][tid] = {"reason": reason, "url": last_url, "when": time.strftime("%Y-%m-%d %H:%M")}
                wf.writerow([tid, t["team"], host, reason, last_url, time.strftime("%Y-%m-%d %H:%M")])
                ff.flush()
                logging.warning("FAILED %s %s: %s", tid, t["team"], reason)
            state_path.write_text(json.dumps(state, indent=1))
    print(f"done: {len(state['done'])} teams parsed, {len(state['failed'])} failed (see {fail_path})")
    return 0


def reparse(out: Path, teams_csv: str) -> int:
    """Rebuild rosters_2025.csv from raw/<id>.html.gz for every team marked done in state.json
    (the saved page is the one that parsed). The previous CSV is kept as rosters_2025.old.csv."""
    state = load_state(out / "state.json")
    names = {t["team_ncaa_id"]: t["team"] for t in csv.DictReader(open(teams_csv, newline=""))}
    csv_path = out / "rosters_2025.csv"
    if csv_path.exists():
        csv_path.replace(out / "rosters_2025.old.csv")
    n_teams = n_players = 0
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        for tid, info in state["done"].items():
            raw = out / "raw" / f"{tid}.html.gz"
            if not raw.exists():
                print(f"{tid}: no saved page, skipped")
                continue
            page = gzip.open(raw, "rt", encoding="utf-8").read()
            m = re.match(r"<!-- source: (\S+)", page)
            rows, how = parse_page(page)
            for r in rows:
                w.writerow({"team_ncaa_id": tid, "team": names.get(tid, ""), "wmt_person_id": "", **r, "source_url": m.group(1) if m else info.get("url", "")})
            n_teams += 1
            n_players += len(rows)
    print(f"reparsed {n_teams} teams, {n_players} players -> {csv_path}")
    return 0


# ---------------------------------------------------------------- offline checks
def selftest() -> int:
    table = """<table><thead><tr><th>#</th><th>Name</th><th>Pos.</th><th>B/T</th><th>Ht.</th><th>Yr.</th></tr></thead>
      <tbody><tr><td>7</td><td>Jake Smith</td><td>SS</td><td>R/R</td><td>6-1</td><td>Jr.</td></tr>
      <tr><td>22</td><td>Tom Lee</td><td>LHP</td><td>L/L</td><td>6-3</td><td>Fr.</td></tr>
      <tr><td>4</td><td>Ray Diaz</td><td>OF</td><td>S/R</td><td>5-11</td><td>So.</td></tr></tbody></table>"""
    presto = """<table><tr><th>No.</th><th>Name</th><th>Pos</th><th>Cl.</th><th>B/T</th></tr>
      <tr><td>12</td><td>Ben Ortiz</td><td>C</td><td>Sr.</td><td>B/R</td></tr></table>"""
    nuxt = json.dumps([["ShallowReactive", 1], {"players": 2}, [3, 4],
                       {"firstName": 5, "lastName": 6, "jerseyNumber": 7, "positionShort": 8, "academicYearShort": 9, "custom1": 10},
                       {"firstName": 11, "lastName": 12, "jerseyNumber": 13, "positionShort": 14, "academicYearShort": 9, "custom1": 15},
                       "Cole", "Ward", "18", "RHP", "So.", "R/R", "Max", "Hill", "3", "OF", "L/L"])
    nuxt_page = f'<script type="application/json" id="__NUXT_DATA__" data-ssr="true">{nuxt}</script>'
    nxt = '<script id="__NEXT_DATA__" type="application/json">' + json.dumps(
        {"props": {"roster": [{"name": "Al Gore", "jersey": "9", "position": "1B", "class": "Gr.", "bats": "Left", "throws": "Right"}]}}) + "</script>"
    cards = """<li class="sidearm-roster-player"><div class="sidearm-roster-player-name"><h3><a href="/x">Luke Bell</a></h3></div>
      <span class="sidearm-roster-player-position">INF</span><span>Jr.</span><span>B/T: R/R</span><span>#14</span></li>
      <li class="sidearm-roster-player"><h3><a href="/y">Nate Cruz</a></h3><span>RHP</span><span>So.</span><span>B/T: L/R</span></li>"""
    checks = [
        (parse_tables(table), [("Jake Smith", "R", "R", "7", "SS", "Jr."), ("Tom Lee", "L", "L", "22", "LHP", "Fr."), ("Ray Diaz", "S", "R", "4", "OF", "So.")]),
        (parse_tables(presto), [("Ben Ortiz", "S", "R", "12", "C", "Sr.")]),
        (parse_json(nuxt_page), [("Cole Ward", "R", "R", "18", "RHP", "So."), ("Max Hill", "L", "L", "3", "OF", "So.")]),
        (parse_json(nxt), [("Al Gore", "L", "R", "9", "1B", "Gr.")]),
        (parse_json('<script type="application/json" id="__NUXT_DATA__">' + json.dumps(
            [{"data": 1}, {"roster-1-players-list": 2}, [3], {"jersey_number_label": 4, "player_position": 5, "class_level": 6, "profile_field_values": 7, "player": 8},
             "23", {"abbreviation": 9}, {"name": 10}, [], {"full_name": 11, "profile_field_values": 12, "wmt_stats2_person_id": 13},
             "RHP", "Junior", "Jacob Mayers", [14], 2828463, {"profile_field": 15, "value": 16}, {"name": 17}, "R-R", "B/T"]) + "</script>"),
         [("Jacob Mayers", "R", "R", "23", "RHP", "Junior")]),
        (parse_cards(cards), [("Luke Bell", "R", "R", "14", "INF", "Jr."), ("Nate Cruz", "L", "R", "", "RHP", "So.")]),
    ]
    # origin columns: (hometown_city, hometown_state, high_school, previous_school)
    o_table = """<table><tr><th>#</th><th>Name</th><th>Pos.</th><th>B/T</th><th>Yr.</th><th>Hometown / High School</th><th>Previous School</th></tr>
      <tr><td>7</td><td>Jake Smith</td><td>SS</td><td>R/R</td><td>Jr.</td><td>Baton Rouge, La. / Catholic</td><td>LSU Eunice</td></tr>
      <tr><td>9</td><td>Tom Lee</td><td>C</td><td>L/R</td><td>Fr.</td><td>Toronto, Ontario, Canada / St. Mike's</td><td></td></tr></table>"""
    o_combo = """<table><tr><th>No.</th><th>Name</th><th>B/T</th><th>Hometown/High School (Previous School)</th></tr>
      <tr><td>3</td><td>Ben Ortiz</td><td>S/R</td><td>Dallas, Texas / Jesuit (Texas Tech)</td></tr></table>"""
    o_cards = """<li class="sidearm-roster-player"><h3><a href="/x">Luke Bell</a></h3><span>INF</span><span>B/T: R/R</span>
      <span class="sidearm-roster-player-hometown">Mobile, Ala.</span><span class="sidearm-roster-player-highschool">McGill-Toolen</span>
      <span class="sidearm-roster-player-previous-school">Wallace State CC</span></li>"""
    o_json = '<script id="__NEXT_DATA__" type="application/json">' + json.dumps({"props": {"roster": [
        {"name": "Al Gore", "jersey": "9", "position": "1B", "class": "Gr.", "bats": "Left", "throws": "Right",
         "hometown": "Carthage, Tenn.", "highSchool": "St. Albans", "previousSchool": "Harvard"}]}}) + "</script>"
    o_wmt = ('<script type="application/json" id="__NUXT_DATA__">' + json.dumps(
        [{"data": 1}, {"roster": 2}, [3], {"jersey_number_label": 4, "profile_field_values": 5, "player": 6},
         "23", [7, 8, 9], {"full_name": 10}, {"profile_field": 11, "value": 12}, {"profile_field": 13, "value": 14},
         {"profile_field": 15, "value": 16}, "Jacob Mayers", {"name": 17}, "R-R", {"name": 18}, "Tulsa, Okla.", {"name": 19}, "Jenks HS / Connors State College",
         "B/T", "Hometown", "High School/Previous School"]) + "</script>")
    ocheck = [
        (parse_tables(o_table), [("Jake Smith", "Baton Rouge", "La.", "Catholic", "LSU Eunice"), ("Tom Lee", "Toronto", "Ontario, Canada", "St. Mike's", "")]),
        (parse_tables(o_combo), [("Ben Ortiz", "Dallas", "Texas", "Jesuit", "Texas Tech")]),
        (parse_tables(o_combo.replace("Hometown/High School (Previous School)", "Hometown").replace("Dallas, Texas / Jesuit (Texas Tech)", "Dallas, Texas (Jesuit)")),
         [("Ben Ortiz", "Dallas", "Texas", "Jesuit", "")]),
        (parse_cards(o_cards), [("Luke Bell", "Mobile", "Ala.", "McGill-Toolen", "Wallace State CC")]),
        (parse_json(o_json), [("Al Gore", "Carthage", "Tenn.", "St. Albans", "Harvard")]),
        (parse_json(o_wmt), [("Jacob Mayers", "Tulsa", "Okla.", "Jenks HS", "Connors State College")]),
    ]
    ok = True
    for url, want in (("https://lsusports.net/sports/bsb/roster/season/2025", ""), ("https://x.com/sports/baseball/roster/2024-25", ""),
                      ("https://x.com/roster.aspx?path=baseball&year=2025", ""),
                      ("https://goutsa.com/sports/baseball/roster/season/2006", "season"), ("https://m.com/sports/soc/roster/player/emma", "away")):
        if want not in off_target(url) or (not want and off_target(url)):
            ok = False
            print("OFF-TARGET MISMATCH", url, repr(off_target(url)))
    for page, want in (('<script>{"wmt_stats2_person_id":1}</script>', "WMT"), ('<li class="sidearm-roster-player">', "Sidearm"),
                       ('<a href="https://www.prestosports.com">', "Presto"), ("<html></html>", "unknown")):
        if platform_of([("u", page, "")]) != want:
            ok = False
            print("PLATFORM MISMATCH", want, platform_of([("u", page, "")]))
    for got, want in ocheck:
        g = [(r["name"], r.get("hometown_city", ""), r.get("hometown_state", ""), r.get("high_school", ""), r.get("previous_school", "")) for r in got]
        if g != want:
            ok = False
            print("ORIGIN MISMATCH\n  got ", g, "\n  want", want)
    for got, want in checks:
        g = [(r["name"], r["bats"], r["throws"], r["jersey"], r["position"], r["class"]) for r in got]
        if g != want:
            ok = False
            print("MISMATCH\n  got ", g, "\n  want", want)
    print("selftest", "passed" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
