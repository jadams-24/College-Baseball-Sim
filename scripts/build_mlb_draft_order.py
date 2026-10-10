"""Build app/mlb_draft_order_2025.csv: the real 2025 MLB draft order through Competitive Balance Round A (the first
round, the Prospect Promotion Incentive pick, the compensatory picks and Competitive Balance Round A), from the
Wikipedia article "2025 Major League Baseball draft". Real MLB team names only, no logos. Display only: the app's
mock draft (app/prospects.py) fills these slots from its board. Usage: python scripts/build_mlb_draft_order.py [--cache DIR]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_school_identity import Wiki, plain                      # noqa: E402  (the same cached raw-page fetch)

TITLE = "2025 Major League Baseball draft"
SOURCE = "https://en.wikipedia.org/wiki/2025_Major_League_Baseball_draft"
OUT = ROOT / "app/mlb_draft_order_2025.csv"
SECTIONS = (("===First round===", "===Prospect promotion incentive picks===", "Round 1"),
            ("===Prospect promotion incentive picks===", "===Compensatory round===", "Prospect Promotion Incentive"),
            ("===Compensatory round===", "===Competitive balance round A===", "Compensatory (Round 1)"),
            ("===Competitive balance round A===", "===Second round===", "Competitive Balance Round A"))


def rows_of(section: str, label: str) -> list:
    out = []
    for block in section.split("|-"):
        cells = [c.strip() for c in re.split(r"\n[|!]", "\n" + block.strip())]
        cells = [c for c in cells if c]
        if len(cells) < 3:
            continue
        m = re.match(r"(?:\[\[[^\]|]*\|)?(\d+)\]?\]?", cells[0])
        if not m:
            continue
        pick = int(m.group(1))
        team_cell = next((c for c in cells[1:] if re.search(r"\[\[[^\]]*(Nationals|Angels|Mariners|Rockies|Cardinals|Pirates|Marlins|Blue Jays|Reds|White Sox|Athletics|Rangers|Giants|Rays|Red Sox|Twins|Cubs|Diamondbacks|Orioles|Brewers|Astros|Braves|Royals|Tigers|Padres|Phillies|Guardians|Dodgers|Yankees|Mets)", c)), None)
        if team_cell is None:
            continue
        team = plain(re.sub(r"\{\{#tag:ref.*", "", team_cell, flags=re.S)).strip()
        note = re.search(r"\{\{#tag:ref\|(.*?)\|group=", team_cell, re.S)
        out.append({"pick": pick, "round": label, "team": team, "note": plain(note.group(1)) if note else ""})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(ROOT / "scratch/wiki_cache"))
    a = ap.parse_args()
    w = Wiki(Path(a.cache), offline=False)
    txt = w.raw(TITLE)
    if not txt:
        raise SystemExit("the draft article could not be fetched")
    rows = []
    for start, end, label in SECTIONS:
        i = txt.index(start); j = txt.index(end, i + 1)
        rows += rows_of(txt[i:j], label)
    rows.sort(key=lambda r: r["pick"])
    assert [r["pick"] for r in rows] == list(range(1, len(rows) + 1)), [r["pick"] for r in rows]
    today = dt.date.today().isoformat()
    with OUT.open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["pick", "round", "team", "note", "source", "fetch_date"])
        wr.writeheader()
        for r in rows:
            wr.writerow(dict(r, source=SOURCE, fetch_date=today))
    print(f"{len(rows)} picks -> {OUT}")


if __name__ == "__main__":
    main()
