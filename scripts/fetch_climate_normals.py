"""NOAA 1991-2020 monthly climate normals at each D1 campus (Phase 9 school report cards: Climate).

Source: NOAA NCEI's Access Data Service and Search Service (https://www.ncei.noaa.gov/access/services/...). NCEI's robots.txt
disallows /data* (the bulk normals files), so the bulk files are not fetched; the /access/services/ API paths are not under a
disallow rule. Public domain (U.S. government work).

Per campus (data/ncaa_2025/school_locations_2025.csv): the search service lists the normals stations in a box around the
campus (half-width 0.25, 0.5, 1 and 2 degrees in turn); the nearest station that has both the mean temperature normal
(MLY-TAVG-NORMAL) and days with 0.01" or more of precipitation (MLY-PRCP-AVGNDS-GE001HI) is used; the data service gives its
monthly values, and (2026-10-09) the station's mean daily high (MLY-TMAX-NORMAL), fetched separately. Kept: February-May (the college season), each month and their mean / sum, the station, its distance.
1.5 s between requests, a descriptive User-Agent, at most 3 retries on a reset connection, and a stop on 403/407/429 or a
bot-protection page (logged in the output's fetch log). Responses are cached under data/noaa/raw/ (gzipped JSON) so a rerun
fetches only what is missing.
    python3 scripts/fetch_climate_normals.py
Writes data/noaa/climate_normals_by_school.csv and data/noaa/fetch_log.json.
"""
from __future__ import annotations

import datetime
import gzip
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/noaa"
RAW = OUT / "raw"
LOC = ROOT / "data/ncaa_2025/school_locations_2025.csv"
SEARCH = "https://www.ncei.noaa.gov/access/services/search/v1/data"
DATA = "https://www.ncei.noaa.gov/access/services/data/v1"
DATASET = "normals-monthly-1991-2020"
TAVG, PDAYS, PRCP = "MLY-TAVG-NORMAL", "MLY-PRCP-AVGNDS-GE001HI", "MLY-PRCP-NORMAL"
TMAX = "MLY-TMAX-NORMAL"     # added 2026-10-09 (owner: score climate on daily highs in a comfortable band)
MONTHS = ("02", "03", "04", "05")
BOXES = (0.25, 0.5, 1.0, 2.0)
UA = "College-Baseball-Sim climate normals fetch (personal research; one request per 1.5 s)"
DELAY = 1.5


class Blocked(Exception):
    pass


def get(url: str, cache: Path):
    if cache.exists():
        return json.loads(gzip.decompress(cache.read_bytes()))
    for attempt in range(4):
        time.sleep(DELAY)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code in (403, 407, 429):
                raise Blocked(f"HTTP {e.code} on {url}")
            raise
        except (ConnectionResetError, urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(5 * 2 ** attempt)
    text = body.decode("utf-8", "replace")
    if text.lstrip()[:1] not in "[{":
        raise Blocked(f"non-JSON response (possible bot protection) on {url}: {text[:120]!r}")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(gzip.compress(body))
    return json.loads(text)


def miles(lat1, lon1, lat2, lon2) -> float:
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(a))


def station(lat: float, lon: float, key: str):
    for h in BOXES:
        q = urllib.parse.urlencode({"dataset": DATASET, "bbox": f"{lat + h:.4f},{lon - h:.4f},{lat - h:.4f},{lon + h:.4f}",
                                    "dataTypes": f"{TAVG},{PDAYS}", "limit": 1000})
        d = get(f"{SEARCH}?{q}", RAW / "search" / f"{key}_{h}.json.gz")
        best = None
        for r in d.get("results", []):
            st = r["stations"][0]
            ids = {t["id"] for t in st.get("dataTypes", [])}
            if TAVG in ids and PDAYS in ids:
                slon, slat = r["boundingPoints"][0]["coordinates"]
                dist = miles(lat, lon, slat, slon)
                if best is None or dist < best[0]:
                    best = (dist, st["id"], st.get("name", ""), slat, slon)
        if best:
            return best
    return None


def main() -> None:
    loc = pd.read_csv(LOC)
    rows, log = [], {"fetched": datetime.date.today().isoformat(), "blocked": None, "missing": []}
    try:
        for r in loc.itertuples():
            key = str(r.ncaa_team_id)
            s = station(r.latitude, r.longitude, key)
            if s is None:
                log["missing"].append(r.team)
                continue
            dist, sid, name, slat, slon = s
            q = urllib.parse.urlencode({"dataset": DATASET, "stations": sid, "dataTypes": f"{TAVG},{PDAYS},{PRCP}", "format": "json"})
            vals = {x["DATE"]: x for x in get(f"{DATA}?{q}", RAW / "data" / f"{sid}.json.gz")}
            q = urllib.parse.urlencode({"dataset": DATASET, "stations": sid, "dataTypes": TMAX, "format": "json"})
            for x in get(f"{DATA}?{q}", RAW / "data_tmax" / f"{sid}.json.gz"):
                vals.setdefault(x["DATE"], {})[TMAX] = x.get(TMAX, "")
            row = {"ncaa_team_id": r.ncaa_team_id, "team": r.team, "station": sid, "station_name": name,
                   "station_lat": slat, "station_lon": slon, "miles": round(dist, 1)}
            for m in MONTHS:
                x = vals.get(m, {})
                row[f"tavg_{m}"] = float(x[TAVG]) if x.get(TAVG, "").strip() else None
                row[f"pdays_{m}"] = float(x[PDAYS]) if x.get(PDAYS, "").strip() else None
                row[f"prcp_{m}"] = float(x[PRCP]) if x.get(PRCP, "").strip() else None
                row[f"tmax_{m}"] = float(x[TMAX]) if x.get(TMAX, "").strip() else None
            t = [row[f"tavg_{m}"] for m in MONTHS]
            pdd = [row[f"pdays_{m}"] for m in MONTHS]
            row["tavg_feb_may"] = round(sum(t) / 4, 2) if None not in t else None
            row["precip_days_feb_may"] = round(sum(pdd), 1) if None not in pdd else None
            tx = [row[f"tmax_{m}"] for m in MONTHS]
            row["tmax_feb_may"] = round(sum(tx) / 4, 2) if None not in tx else None
            rows.append(row)
            print(f"{r.team}: {sid} {name} {dist:.1f} mi, {row['tavg_feb_may']} F, {row['precip_days_feb_may']} days", flush=True)
    except Blocked as e:
        log["blocked"] = str(e)
        print("STOPPED:", e)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT / "climate_normals_by_school.csv", index=False)
    log["n_schools"] = len(rows)
    (OUT / "fetch_log.json").write_text(json.dumps(log, indent=1) + "\n")
    print(json.dumps(log, indent=1))


if __name__ == "__main__":
    sys.exit(main())
