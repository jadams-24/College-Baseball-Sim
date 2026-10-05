"""Cross-check WarrenNolan 2026 game results against the NCAA's published RPI records.

For each school on https://www.ncaa.com/rankings/baseball/d1/rpi ("Through
Games May. 24 2026", saved in data/ncaa_2026/rpi/), compute from
data/ncaa_2026/warrennolan/games_2026.csv the D1 record split into road /
neutral / home and the non-D1 record, for final games dated on or before
2026-05-24, and compare with the published W-L strings.

Writes:
  data/ncaa_2026/team_name_map.csv                         NCAA name <-> WarrenNolan slug and name
  data/ncaa_2026/warrennolan/record_check_through_2026-05-24.csv   one row per school

Does not compute RPI.
Run: python scripts/check_warrennolan_vs_ncaa_2026.py
"""
from __future__ import annotations

import csv
import gzip
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data" / "ncaa_2026"
CUTOFF = "2026-05-24"

# NCAA.com short names that do not match the WarrenNolan slug after normalising
# "St." to "State" and dropping punctuation. Checked one by one.
MANUAL = {
 'Southern California':'USC', 'Southeast Mo. St.':'Southeast-Missouri', 'NC State':'North-Carolina-State',
 'Western Caro.':'Western-Carolina', 'DBU':'Dallas-Baptist', 'Southeastern La.':'Southeastern-Louisiana',
 'Eastern Ill.':'Eastern-Illinois', 'NIU':'Northern-Illinois', 'South Fla.':'South-Florida',
 'USC Upstate':'South-Carolina-Upstate', 'Lamar University':'Lamar', 'UConn':'Connecticut',
 "St. John's (NY)":'Saint-Johns', 'ETSU':'East-Tennessee-State', 'App State':'Appalachian-State',
 'Fla. Atlantic':'FAU', 'Charleston So.':'Charleston-Southern', 'UNC Greensboro':'UNCG',
 'Western Ky.':'Western-Kentucky', "Saint Mary's (CA)":'Saint-Marys-College', 'Western Mich.':'Western-Michigan',
 'Central Ark.':'Central-Arkansas', 'North Ala.':'North-Alabama', 'Army West Point':'Army',
 'Sam Houston':'Sam-Houston-State', 'Col. of Charleston':'Charleston', 'UT Arlington':'UTA',
 'SFA':'Stephen-F-Austin', 'CSUN':'Cal-State-Northridge', 'Southern Ind.':'Southern-Indiana',
 'Southern U.':'Southern', 'LIU':'Long-Island', 'A&M-Corpus Christi':'Texas-AM-Corpus-Christi',
 'Ga. Southern':'Georgia-Southern', 'UIW':'Incarnate-Word', 'Middle Tenn.':'Middle-Tennessee',
 'FDU':'Fairleigh-Dickinson', 'Southern Ill.':'Southern-Illinois', 'UT Martin':'Tennessee-Martin',
 'CSU Bakersfield':'Cal-State-Bakersfield', 'Central Mich.':'Central-Michigan', 'Ark.-Pine Bluff':'Arkansas-Pine-Bluff',
 'Eastern Mich.':'Eastern-Michigan', 'Eastern Ky.':'Eastern-Kentucky', 'Seattle U':'Seattle-University',
 'Grambling':'Grambling-State', 'Massachusetts':'UMass', 'Queens (NC)':'Queens', 'Western Ill.':'Western-Illinois',
 "Mount St. Mary's":'Mount-Saint-Marys', 'West Ga.':'West-Georgia', 'Presbyterian':'Presbyterian-College',
 'UAlbany':'Albany', 'Northern Ky.':'Northern-Kentucky', 'N.C. A&T':'North-Carolina-AT',
 'St. Bonaventure':'Saint-Bonaventure', 'LMU (CA)':'Loyola-Marymount', 'St. Thomas (MN)':'Saint-Thomas',
 'Northern Colo.':'Northern-Colorado', 'Central Conn. St.':'Central-Connecticut', 'Mississippi Val.':'Mississippi-Valley-State',
 'Prairie View':'Prairie-View-AM', 'Alcorn':'Alcorn-State', 'UMES':'Maryland-Eastern-Shore',
}


def norm(s: str) -> str:
    s = s.lower().replace("&", "").replace("'", "").replace(".", "").replace("(", "").replace(")", "")
    s = re.sub(r"\bst\b", "state", s)
    return re.sub(r"[^a-z0-9]", "", s)


def wl(s: str) -> tuple[int, int]:
    w, l = s.split("-")
    return int(w), int(l)


def fmt(r: list[int]) -> str:
    return f"{r[0]}-{r[1]}" + (f"-{r[2]}" if r[2] else "")


def main() -> None:
    ncaa = list(csv.DictReader(open(D / "rpi" / "ncaa_rpi_through_2026-05-24.csv")))
    wn_names: dict[str, str] = {}
    for p in sorted((D / "warrennolan" / "raw").glob("*.html.gz")):
        h = gzip.open(p, "rt", encoding="utf-8", errors="replace").read()
        m = re.search(r'class="team-menu__name">(.*?)<span', h, re.S)
        wn_names[p.name[:-8]] = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    by_norm = {norm(s.replace("-", " ")): s for s in wn_names}

    mapping = {}
    for r in ncaa:
        school = r["school"]
        if school in MANUAL:
            slug, how = MANUAL[school], "manual"
        else:
            slug, how = by_norm.get(norm(school), ""), "normalised name"
        if slug not in wn_names:
            raise SystemExit(f"no WarrenNolan page for {school!r} (slug {slug!r})")
        mapping[school] = (slug, how)
    slugs = [v[0] for v in mapping.values()]
    assert len(set(slugs)) == len(slugs), "two NCAA schools map to one WarrenNolan slug"
    unmapped = sorted(set(wn_names) - set(slugs))
    with open(D / "team_name_map.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ncaa_name", "ncaa_conference", "warrennolan_slug", "warrennolan_name", "match"])
        for r in ncaa:
            slug, how = mapping[r["school"]]
            w.writerow([r["school"], r["conference"], slug, wn_names[slug], how])

    games = list(csv.DictReader(open(D / "warrennolan" / "games_2026.csv")))
    results = {}
    for rule in ("warrennolan", "host_venue"):
        results[rule] = compare(ncaa, mapping, records(games, rule))
    out_a, out_b = results["warrennolan"], results["host_venue"]
    for ra, rb in zip(out_a, out_b):
        ra["all_match_host_venue_rule"] = rb["all_match"]
        for split in ("road", "neutral", "home"):
            ra[f"wn_{split}_host_venue_rule"] = rb[f"wn_{split}"]
    with open(D / "warrennolan" / "record_check_through_2026-05-24.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_a[0].keys()))
        w.writeheader()
        w.writerows(out_a)

    print(f"schools on NCAA page: {len(ncaa)}; WarrenNolan pages: {len(wn_names)}; "
          f"WarrenNolan pages not on NCAA page: {unmapped}")
    print("D1 W-L total matches:", sum(r["ncaa_record"] == "-".join(r["wn_record"].split("-")[:2])
                                       for r in out_a))
    print("schools with a WarrenNolan tie (NCAA prints W-L only):", sum(r["wn_ties"] > 0 for r in out_a))
    for rule, out in results.items():
        n = sum(r["all_match"] for r in out)
        print(f"\n[{rule} site rule] all four splits match: {n}/{len(ncaa)}; "
              f"road/neutral/home all match: {sum(r['site_moves'] == 0 for r in out)}; "
              f"team-games with a different site: {sum(r['site_moves'] for r in out)}; "
              f"non-D1 games differing: {sum(r['non_d1_diff'] for r in out)}")
        for split in ("road", "neutral", "home", "non_d1"):
            print(f"  {split} matches: {sum(r[f'{split}_ok'] for r in out)}")
        for r in out:
            if not r["all_match"]:
                diffs = [f"{s}: NCAA {r['ncaa_' + s]} vs WN {r['wn_' + s]}"
                         for s in ("road", "neutral", "home", "non_d1") if not r[f"{s}_ok"]]
                print(f"  {r['school']} ({r['warrennolan_slug']}): " + "; ".join(diffs))


def records(games: list[dict], rule: str) -> dict:
    """[W, L, T] per slug per split for final games on or before the cutoff.

    rule "warrennolan": sites exactly as WarrenNolan labels them.
    rule "host_venue": a game WarrenNolan labels neutral but played at one
    participant's main home park (column neutral_at_home_venue_of) counts as a
    home game for that team and a road game for the other."""
    rec: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    for g in games:
        if g["status"] != "final" or g["date"] > CUTOFF:
            continue
        hs, as_ = int(g["home_score"]), int(g["away_score"])
        both_d1 = g["home_d1"] == "True" and g["away_d1"] == "True"
        neutral = g["neutral"] == "True"
        host = g["neutral_at_home_venue_of"] if rule != "warrennolan" else ""
        for slug, me, opp, side in ((g["home_slug"], hs, as_, "home"), (g["away_slug"], as_, hs, "road")):
            if not slug or slug.startswith("nonD1:"):
                continue
            if not both_d1:
                split = "non_d1"
            elif neutral and host:
                split = "home" if slug == host else "road"
            else:
                split = "neutral" if neutral else side
            k = 0 if me > opp else 1 if me < opp else 2
            rec[slug][split][k] += 1
    return rec


def compare(ncaa: list[dict], mapping: dict, rec: dict) -> list[dict]:
    out = []
    for r in ncaa:
        slug, _ = mapping[r["school"]]
        row = {"rank": r["rank"], "school": r["school"], "warrennolan_slug": slug}
        ok_all = True
        ties = 0
        for split in ("road", "neutral", "home", "non_d1"):
            mine = rec[slug][split]
            row[f"ncaa_{split}"] = r[split]
            row[f"wn_{split}"] = fmt(mine)
            # The NCAA page prints W-L only; WarrenNolan shows ties (suspended games
            # never finished) as a third number. Compare W-L and count ties apart.
            ok = list(wl(r[split])) == mine[:2]
            row[f"{split}_ok"] = ok
            ok_all &= ok
            ties += mine[2]
        tot = [sum(rec[slug][s][i] for s in ("road", "neutral", "home")) for i in range(3)]
        row["ncaa_record"], row["wn_record"] = r["record"], fmt(tot)
        row["wn_ties"] = ties
        # Team-games whose site differs: games NCAA has in a split beyond WarrenNolan's.
        row["site_moves"] = sum(max(0, a - b) for split in ("road", "neutral", "home")
                                for a, b in zip(wl(r[split]), rec[slug][split][:2]))
        row["non_d1_diff"] = sum(abs(a - b) for a, b in zip(wl(r["non_d1"]), rec[slug]["non_d1"][:2]))
        row["all_match"] = ok_all
        out.append(row)
    return out


if __name__ == "__main__":
    main()
