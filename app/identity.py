"""School colors and home ballparks for display (owner request 2026-10-10): `app/school_identity.csv` (built by
`scripts/build_school_identity.py` from Wikipedia; colors, ballpark, capacity, city, source, fetch date, confidence per
row) and `app/conference_tournaments.csv` (the 2025 conference tournament sites confirmed from Wikipedia).

Display only. The engine never reads these: its park factors are still its own draw, not tied to these ballparks
(matching real parks is a future engine change).

The color rules (app/README.md, "School colors"):
  * school colors are accents (chips, stripes, header bands, the user's own-team highlight), never large backgrounds;
    the app's accent (#F2A900) stays for buttons and actions;
  * text on a school color is white or near-black, whichever reaches 4.5:1 (`text_on`);
  * a color too dark to see on the #12151C background gets a thin light border (`border`), and where a visible color
    is needed as ink (a stripe, a highlight tint) the first visible one of primary, alt, secondary is used (`ink`);
  * when two teams with similar colors meet on the scoreboard, the away team's chip uses its secondary color (`pair`).
"""
from __future__ import annotations

import csv
import math
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = ROOT / "app/school_identity.csv"
TOURNAMENTS = ROOT / "app/conference_tournaments.csv"
BACKGROUND = "12151C"                 # the app's page background (system.css --bg)
WHITE, NEAR_BLACK = "FFFFFF", "0B0D12"
MIN_TEXT_CONTRAST = 4.5               # WCAG AA for normal text
MIN_VISIBLE = 1.45                    # a chip below this contrast against the background (navy, black, dark maroon) gets a border
MIN_INK = 2.6                         # a stripe or highlight color needs at least this against the background
SIMILAR_DE = 22.0                     # CIE76 distance below which two primaries read as the same color
OMAHA = {"name": "Charles Schwab Field Omaha", "city": "Omaha, NE"}


# ---------------------------------------------------------------- color math
def _rgb(hexcode: str) -> tuple:
    h = hexcode.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def luminance(hexcode: str) -> float:
    """WCAG relative luminance."""
    def lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in _rgb(hexcode))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio, 1 to 21."""
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def text_on(hexcode: str) -> str:
    """White or near-black text on a school color: the first that reaches 4.5:1, else the higher (every real color
    reaches it with one of them; pure black is the last resort)."""
    for t in (WHITE, NEAR_BLACK, "000000"):
        if contrast(t, hexcode) >= MIN_TEXT_CONTRAST:
            return "#" + t
    return "#" + max((WHITE, NEAR_BLACK, "000000"), key=lambda t: contrast(t, hexcode))


def _lab(hexcode: str) -> tuple:
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in _rgb(hexcode))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 1.0
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def distance(a: str, b: str) -> float:
    """CIE76 color distance (Lab)."""
    la, lb = _lab(a), _lab(b)
    return math.sqrt(sum((p - q) ** 2 for p, q in zip(la, lb)))


def similar(a: str, b: str) -> bool:
    return distance(a, b) < SIMILAR_DE


# ---------------------------------------------------------------- the table
@lru_cache(maxsize=1)
def _load() -> dict:
    if not IDENTITY.exists():
        return {}
    with IDENTITY.open() as f:
        return {int(r["tid"]): r for r in csv.DictReader(f)}


@lru_cache(maxsize=1)
def _tournaments() -> dict:
    if not TOURNAMENTS.exists():
        return {}
    with TOURNAMENTS.open() as f:
        return {r["conference"]: r for r in csv.DictReader(f)}


def available() -> bool:
    return IDENTITY.exists()


def row(tid: int) -> dict | None:
    return _load().get(int(tid))


def _visible(hexcode: str) -> bool:
    return bool(hexcode) and contrast(hexcode, BACKGROUND) >= MIN_VISIBLE


def colors(tid: int) -> dict | None:
    """The display colors of a school: primary, secondary and alt as the file has them (None when the row is D), plus
    chip (the color drawn beside the name: the primary), text (white or near-black on the chip), border (the chip is
    too dark for the background), ink (a visible color for stripes and tints) and ink_text."""
    r = row(tid)
    if r is None or r["color_confidence"] == "D" or not r["primary"]:
        return None
    pr, se, alt = r["primary"], r["secondary"], r["alt"]
    ink = next((c for c in (pr, alt, se) if c and contrast(c, BACKGROUND) >= MIN_INK), pr)
    return {"primary": "#" + pr, "secondary": "#" + se if se else None, "alt": "#" + alt if alt else None,
            "chip": "#" + pr, "text": text_on(pr), "border": not _visible(pr),
            "ink": "#" + ink, "ink_text": text_on(ink), "confidence": r["color_confidence"]}


def pair(home_tid: int, away_tid: int) -> tuple:
    """Both teams' colors for one scoreboard: when the two primaries read the same, the away team's chip uses its
    secondary (the alt when the secondary is a neutral white or black and an alt exists)."""
    h, a = colors(home_tid), colors(away_tid)
    if h and a and similar(h["primary"], a["primary"]):
        a = dict(a)
        swap = a["alt"] if (a["secondary"] or "").upper() in ("#FFFFFF", "#000000") and a["alt"] else a["secondary"]
        if swap:
            a["chip"] = swap
            a["text"] = text_on(swap.lstrip("#"))
            a["border"] = not _visible(swap.lstrip("#"))
            a["swapped"] = True
    return h, a


def venue(tid: int) -> dict | None:
    """The home ballpark: name, capacity (int or None), city ("Baton Rouge, LA" style when the row has it) and a one-line
    text "Alex Box Stadium, Skip Bertman Field · Baton Rouge, LA". None when the row is D."""
    r = row(tid)
    if r is None or r["stadium_confidence"] == "D" or not r["stadium"]:
        return None
    city = _city_state(r)
    return {"name": r["stadium"], "capacity": int(r["capacity"]) if r["capacity"].isdigit() else None, "city": city,
            "text": r["stadium"] + (f" · {city}" if city else ""), "confidence": r["stadium_confidence"]}


@lru_cache(maxsize=1)
def _states() -> dict:
    """tid -> (city, state) from the school file (read here, not through app.schools, which reads this module)."""
    f = ROOT / "data/schools/schools.csv"
    if not f.exists():
        return {}
    with f.open() as fh:
        return {int(r["tid"]): (r["city"], r["state"]) for r in csv.DictReader(fh)}


def _city_state(r: dict) -> str:
    """'Baton Rouge, LA' from the row's city and the school file's state."""
    sc, st = _states().get(int(r["tid"]), ("", ""))
    city = (r.get("city") or "").split(",")[0].strip() or sc
    if not city:
        return ""
    return f"{city}, {st}" if st else city


def venue_text(v: dict | None) -> str | None:
    return v["text"] if v else None


def game_venue(stage: str, home_tid: int, neutral: bool, host_tid: int | None = None, conference: str | None = None,
               site_detail: str | None = None) -> dict | None:
    """The ballpark of one game by stage: Omaha for the CWS; the host's park in regionals and supers; the confirmed
    2025 site for a conference tournament at a neutral site, the host's park when the tournament is on campus,
    nothing (the screens say "Conference tournament") when the site is unconfirmed; the home park otherwise.
    Returns {name, city, text, kind} or None (never a guess)."""
    if stage == "cws":
        return dict(OMAHA, text=f"{OMAHA['name']} · {OMAHA['city']}", kind="cws")
    if stage in ("regional", "super"):
        v = venue(host_tid if host_tid is not None else home_tid)
        return dict(v, kind=stage) if v else None
    if stage == "conf":
        t = _tournaments().get(conference or "")
        if t and t["confidence"] != "D" and t["venue"] and (site_detail or "").startswith("neutral"):
            return {"name": t["venue"], "city": t["city"], "text": t["venue"] + (f" · {t['city']}" if t["city"] else ""), "kind": "conf"}
        if site_detail and site_detail.startswith("campus"):
            v = venue(host_tid if host_tid is not None else home_tid) if (host_tid is not None or not neutral) else None
            return dict(v, kind="conf") if v else None
        return None
    if neutral:
        return None
    v = venue(home_tid)
    return dict(v, kind="home") if v else None


def tournament_site(conference: str) -> dict | None:
    """The confirmed 2025 site of a conference tournament, or None."""
    t = _tournaments().get(conference)
    if not t or t["confidence"] == "D" or not t["venue"]:
        return None
    return {"venue": t["venue"], "city": t["city"], "source": t["source"], "confidence": t["confidence"]}


def all_json() -> dict:
    """Every school's display colors and ballpark for the screens (one load per page)."""
    out = {}
    for tid in sorted(_load()):
        out[tid] = {"colors": colors(tid), "venue": venue(tid)}
    return out


def d_rows() -> list:
    return [r for r in _load().values() if r["color_confidence"] == "D" or r["stadium_confidence"] == "D"]
