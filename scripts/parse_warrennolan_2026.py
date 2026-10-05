"""Rebuild data/ncaa_2026/warrennolan/games_2026.csv from the raw WarrenNolan pages.

Input: data/ncaa_2026/warrennolan/raw/<slug>.html.gz, one 2026 schedule page per
D1 team (fetched by scripts/fetch_warrennolan_2026.py from
https://www.warrennolan.com/baseball/2026/schedule/<slug>).

Each <li class="team-schedule"> block on a page is one game from the page
team's side:
  * date: month and day (the season is 2026);
  * site: the location cell is empty for a home game, "AT" for a road game and
    "VS" for a neutral-site game;
  * opponent: a link to the opponent's schedule page for D1 opponents; non-D1
    opponents have no link and carry the marker "Non Div I";
  * result: "W"/"L"/"T" and "<page team runs> - <opponent runs>", optionally
    "(N Innings)", or a status word ("Canceled", "Postponed", ...);
  * the box score (when present) lists the visiting team first and the team
    batting last second; for neutral-site games the team batting last is
    written as `home` (the published site stays neutral=True);
  * a "special" header above some games names the event (tournament, classic).

Outputs:
  games_2026.csv         one row per game, deduplicated across the two teams'
                         pages (key: date + unordered team pair + score; repeat
                         keys on one date, such as two 6-8 games in a
                         doubleheader, are paired in page order). Both pages'
                         site labels are kept so they can be cross-checked.
  team_games_2026.csv    one row per page entry (team side), before dedup.
  parse_report.json      counts and every inconsistency found.

Run: python scripts/parse_warrennolan_2026.py
"""
from __future__ import annotations

import csv
import gzip
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WN = ROOT / "data" / "ncaa_2026" / "warrennolan"
RAW = WN / "raw"
YEAR = 2026
MONTHS = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}
SITE_LABEL = {"": "home", "AT": "away", "VS": "neutral"}
NON_D1_MARKER = "Non Div I"


def text(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def parse_page(slug: str, h: str) -> tuple[str, list[dict]]:
    m = re.search(r'class="team-menu__name">(.*?)<span', h, re.S)
    team = text(m.group(1)) if m else slug
    body = h[h.find('<ul class="team-schedule">'):]
    # Split into special headers and game blocks, in page order.
    tokens = re.finditer(
        r'<li class="team-schedule__special--start">(.*?)</li>'
        r'|<li class="team-schedule__special--end">'
        r'|<li class="team-schedule"\s*>(.*?)</li>', body, re.S)
    event = ""
    rows = []
    for i, tok in enumerate(tokens):
        if tok.group(0).startswith('<li class="team-schedule__special--start"'):
            event = text(tok.group(1))
            continue
        if tok.group(0).startswith('<li class="team-schedule__special--end"'):
            event = ""
            continue
        li = tok.group(2)
        mon = re.search(r'game-date--month">(.*?)<', li).group(1).strip().upper()
        day = int(re.search(r'game-date--day">(.*?)<', li).group(1).strip())
        date = f"{YEAR}-{MONTHS[mon]:02d}-{day:02d}"
        loc = text(re.search(r'team-schedule__location">(.*?)</div>', li, re.S).group(1)).upper()
        if loc not in SITE_LABEL:
            raise ValueError(f"{slug}: unknown location label {loc!r}")
        opp_html = re.search(r'team-schedule__opp-line">(.*?)</span>', li, re.S).group(1)
        link = re.search(r'href="/baseball/2026/schedule/([^"]+)"', opp_html)
        opp_slug = link.group(1) if link else ""
        opp = text(opp_html)
        nd_html = re.search(r'opp-nond1-line">(.*?)</span>', li, re.S).group(1)
        non_d1 = NON_D1_MARKER.lower() in text(nd_html).lower()
        info = [text(x) for x in re.findall(
            r'<span class="team-schedule__info">(.*?)</span>', li, re.S)]
        rhtml = re.search(r'<div class="team-schedule__result[^"]*"\s*>(.*?)</div>', li, re.S).group(1)
        rtext = text(rhtml)
        mres = re.match(r"^([WLT])\s+(\d+)\s*-\s*(\d+)(?:\s*\((\d+) Innings\))?", rtext)
        if mres:
            status, wl = "final", mres.group(1)
            ts, os_ = int(mres.group(2)), int(mres.group(3))
            innings = int(mres.group(4)) if mres.group(4) else ""
        else:
            status, wl, ts, os_, innings = rtext.lower() or "unknown", "", "", "", ""
        # Box score: visiting team first, team batting last second.
        box_rows = re.findall(
            r'<tr>\s*<td class="team-schedule-bottom__box-score">(.*?)</td>(.*?)</tr>', li, re.S)
        box_names = [text(n) for n, _ in box_rows]
        box_runs = []
        for _, cells in box_rows:
            tot = re.findall(r'box-score--totals">(.*?)</td>', cells)
            box_runs.append(int(tot[0]) if tot and tot[0].strip().isdigit() else None)
        rows.append({
            "page": slug, "team": team, "date": date, "site": SITE_LABEL[loc], "label": loc,
            "opp": opp, "opp_slug": opp_slug, "opp_d1": not non_d1 and bool(opp_slug),
            "non_d1_marker": non_d1, "status": status, "wl": wl, "team_score": ts, "opp_score": os_,
            "innings": innings, "event": event, "result_text": rtext,
            "venue_city": info[0] if info else "", "venue": info[1] if len(info) > 1 else "",
            "box_first": box_names[0] if len(box_names) == 2 else "",
            "box_second": box_names[1] if len(box_names) == 2 else "",
            "box_first_runs": box_runs[0] if len(box_runs) == 2 else "",
            "box_second_runs": box_runs[1] if len(box_runs) == 2 else "",
        })
    return team, rows


def main() -> None:
    pages = sorted(RAW.glob("*.html.gz"))
    team_rows: list[dict] = []
    names: dict[str, str] = {}
    for p in pages:
        slug = p.name[: -len(".html.gz")]
        team, rows = parse_page(slug, gzip.open(p, "rt", encoding="utf-8", errors="replace").read())
        names[slug] = team
        team_rows.extend(rows)

    report: dict = {"pages": len(pages), "team_entries": len(team_rows),
                    "status_counts_entries": dict(Counter(r["status"] for r in team_rows)),
                    "issues": defaultdict(list)}
    repair_self_opponents(team_rows, names, report)

    # Group entries by game key; pair the two sides in page order.
    by_key: dict[tuple, list[dict]] = defaultdict(list)
    for r in team_rows:
        a = r["page"]
        b = r["opp_slug"] or f"nonD1:{r['opp']}"
        if r["status"] == "final":
            score = (r["team_score"], r["opp_score"]) if a < b else (r["opp_score"], r["team_score"])
        else:
            score = (r["status"],)
        key = (r["date"], tuple(sorted((a, b))), score)
        by_key[key].append(r)

    games = []
    for key, entries in by_key.items():
        date, pair, score = key
        sides = defaultdict(list)
        for r in entries:
            sides[r["page"]].append(r)
        a, b = pair
        la, lb = sides.get(a, []), sides.get(b, [])
        n = max(len(la), len(lb))
        if la and lb and len(la) != len(lb):
            report["issues"]["unpaired_count"].append(
                {"date": date, "pair": pair, "score": score, a: len(la), b: len(lb)})
        for k in range(n):
            ra = la[k] if k < len(la) else None
            rb = lb[k] if k < len(lb) else None
            games.append(build_game(ra, rb, names, report))

    games.sort(key=lambda g: (g["date"], g["home"], g["away"]))
    mark_home_venues(games, team_rows)
    cols = ["date", "home", "away", "neutral", "home_score", "away_score", "home_d1", "away_d1",
            "status", "home_slug", "away_slug", "home_page_site", "away_page_site", "pages",
            "site_agree", "innings", "event", "venue_city", "venue", "neutral_at_home_venue_of"]
    with open(WN / "games_2026.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(games)
    tcols = list(team_rows[0].keys())
    with open(WN / "team_games_2026.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=tcols)
        w.writeheader()
        w.writerows(team_rows)

    report["games"] = len(games)
    report["games_by_status"] = dict(Counter(g["status"] for g in games))
    report["games_final_through_2026_05_24"] = sum(
        1 for g in games if g["status"] == "final" and g["date"] <= "2026-05-24")
    report["games_by_pages"] = dict(Counter(g["pages"] for g in games))
    report["site_disagreements"] = sum(1 for g in games if g["site_agree"] == "False")
    report["issues"] = {k: v for k, v in report["issues"].items()}
    report["issue_counts"] = {k: len(v) for k, v in report["issues"].items()}
    (WN / "parse_report.json").write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({k: v for k, v in report.items() if k != "issues"}, indent=1, default=str))


def mark_home_venues(games: list[dict], team_rows: list[dict]) -> None:
    """For games WarrenNolan marks neutral ("VS"), name the participant whose home park
    the venue is: the stadium where that team played the most of its own home-labeled
    games. Conference tournaments hosted at a participant's park are the typical case.
    The WarrenNolan label is left unchanged; this is an extra column."""
    counts: dict[str, Counter] = defaultdict(Counter)
    for r in team_rows:
        if r["site"] == "home" and r["venue"]:
            counts[r["page"]][r["venue"]] += 1
    main_venue = {t: c.most_common(1)[0][0] for t, c in counts.items()}
    for g in games:
        g["neutral_at_home_venue_of"] = ""
        if not g["neutral"] or not g["venue"]:
            continue
        h = main_venue.get(g["home_slug"]) == g["venue"]
        a = main_venue.get(g["away_slug"]) == g["venue"]
        if h != a:
            g["neutral_at_home_venue_of"] = g["home_slug"] if h else g["away_slug"]


def repair_self_opponents(team_rows: list[dict], names: dict, report: dict) -> None:
    """A page entry whose opponent link is the page team itself (seen once: Fairfield,
    2026-05-23, "L 7 - 12") is a WarrenNolan data-entry slip. Repair it when exactly one
    other page lists a game against this team on that date with the mirrored score;
    otherwise drop the entry. Every case is logged in parse_report.json."""
    for r in list(team_rows):
        if r["opp_slug"] != r["page"]:
            continue
        cands = [c for c in team_rows if c["opp_slug"] == r["page"] and c["date"] == r["date"]
                 and c["page"] != r["page"] and c["status"] == r["status"]
                 and c["team_score"] == r["opp_score"] and c["opp_score"] == r["team_score"]]
        # Keep only candidates whose own game is not already matched on this page.
        cands = [c for c in cands if not any(
            o["page"] == r["page"] and o["opp_slug"] == c["page"] and o["date"] == c["date"]
            and o["team_score"] == c["opp_score"] and o["opp_score"] == c["team_score"]
            for o in team_rows)]
        entry = {"page": r["page"], "date": r["date"], "result": r["result_text"]}
        if len(cands) == 1:
            c = cands[0]
            r["opp_slug"], r["opp"] = c["page"], names.get(c["page"], c["team"])
            entry["repaired_opponent"] = c["page"]
        else:
            team_rows.remove(r)
            entry["dropped"] = f"{len(cands)} candidate opponents"
        report["issues"]["self_opponent_entry"].append(entry)


def build_game(ra: dict | None, rb: dict | None, names: dict, report: dict) -> dict:
    """One game from one or both page entries (ra on page a, rb on page b)."""
    main_r = ra or rb
    other = rb if ra else None
    t_slug, t_name = main_r["page"], main_r["team"]
    o_slug = main_r["opp_slug"]
    o_name = names.get(o_slug, main_r["opp"]) if o_slug else main_r["opp"]
    o_d1 = main_r["opp_d1"]
    if o_slug and o_slug not in names:
        report["issues"]["opponent_page_missing"].append({"team": t_slug, "opp": o_slug, "date": main_r["date"]})
    if o_slug and other is None and o_slug in names:
        report["issues"]["one_sided_d1_game"].append(
            {"date": main_r["date"], "team": t_slug, "opp": o_slug, "status": main_r["status"],
             "result": main_r["result_text"]})

    site = main_r["site"]
    site_agree = ""
    if other is not None:
        expected = {"home": "away", "away": "home", "neutral": "neutral"}[site]
        site_agree = str(other["site"] == expected)
        if other["site"] != expected:
            report["issues"]["site_label_disagreement"].append(
                {"date": main_r["date"], t_slug: site, other["page"]: other["site"],
                 "score": f"{main_r['team_score']}-{main_r['opp_score']}"})

    # Who is home: page site label; for neutral games the team batting last in the box score.
    if site == "home":
        team_home = True
    elif site == "away":
        team_home = False
    else:
        team_home = True
        if main_r["box_second"]:
            if main_r["box_second"] == t_name or main_r["box_second"] == main_r["team"]:
                team_home = True
            elif main_r["box_first"] == t_name:
                team_home = False
            elif main_r["box_second"] == main_r["opp"]:
                team_home = False
    if main_r["status"] == "final" and main_r["box_second_runs"] != "":
        # Check box totals against the result line.
        bt = {main_r["box_first"]: main_r["box_first_runs"], main_r["box_second"]: main_r["box_second_runs"]}
        if bt.get(t_name, main_r["team_score"]) != main_r["team_score"]:
            report["issues"]["box_score_mismatch"].append({"date": main_r["date"], "team": t_slug})
        if site != "neutral" and main_r["box_second"] and \
                (main_r["box_second"] == t_name) != team_home:
            report["issues"]["box_order_vs_site_label"].append(
                {"date": main_r["date"], "team": t_slug, "site": site,
                 "box_second": main_r["box_second"]})

    th = {"slug": t_slug, "name": t_name, "score": main_r["team_score"], "d1": True, "site": site}
    oh = {"slug": o_slug, "name": o_name, "score": main_r["opp_score"], "d1": o_d1,
          "site": other["site"] if other is not None else ""}
    home, away = (th, oh) if team_home else (oh, th)
    status = main_r["status"]
    if other is not None and other["status"] != status:
        report["issues"]["status_disagreement"].append(
            {"date": main_r["date"], t_slug: status, other["page"]: other["status"]})
    return {
        "date": main_r["date"], "home": home["name"], "away": away["name"],
        "neutral": site == "neutral", "home_score": home["score"], "away_score": away["score"],
        "home_d1": home["d1"], "away_d1": away["d1"], "status": status,
        "home_slug": home["slug"], "away_slug": away["slug"],
        "home_page_site": home["site"], "away_page_site": away["site"],
        "pages": 2 if other is not None else 1, "site_agree": site_agree,
        "innings": main_r["innings"], "event": main_r["event"] or (other or {}).get("event", ""),
        "venue_city": main_r["venue_city"], "venue": main_r["venue"],
    }


if __name__ == "__main__":
    main()
