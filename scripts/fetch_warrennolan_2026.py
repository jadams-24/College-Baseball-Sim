"""Fetch every 2026 D1 team schedule page from WarrenNolan.com.

Team slugs come from the site's sitemap
(https://www.warrennolan.com/sitemap/college-baseball-2026.xml, saved gzipped
next to the raw pages). Each page is
https://www.warrennolan.com/baseball/2026/schedule/<slug> and is saved
untouched as data/ncaa_2026/warrennolan/raw/<slug>.html.gz.

Politeness: robots.txt says "Allow: /"; 1.5 s between requests; a failed
request is retried at most 3 times after 5, 10 and 20 s, then logged and
skipped. A 403/407 or a bot-protection page stops the run.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "ncaa_2026" / "warrennolan"
RAW = OUT / "raw"
UA = "college-baseball-sim research (github.com/jadams-24/College-Baseball-Sim)"
DELAY = 1.5
RETRY_PAUSES = (5, 10, 20)
BASE = "https://www.warrennolan.com/baseball/2026/schedule/"


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def slugs() -> list[str]:
    xml = gzip.open(OUT / "sitemap_college-baseball-2026.xml.gz", "rt").read()
    return sorted(set(re.findall(r"college-baseball/team/schedule/_/2026/([^<\s]+)</loc>", xml)))


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    teams = slugs()
    log = {"started": datetime.now(timezone.utc).isoformat(), "source": BASE + "<slug>",
           "teams": len(teams), "fetched": [], "skipped_existing": [], "failed": {}}
    for i, slug in enumerate(teams):
        dest = RAW / f"{slug}.html.gz"
        if dest.exists() and dest.stat().st_size > 1000:
            log["skipped_existing"].append(slug)
            continue
        body = None
        for attempt in range(len(RETRY_PAUSES) + 1):
            try:
                body = get(BASE + slug)
                break
            except urllib.error.HTTPError as e:
                if e.code in (403, 407, 429):
                    print(f"BLOCKED {e.code} on {slug}; stopping", flush=True)
                    log["failed"][slug] = f"HTTP {e.code} (stopped)"
                    log["stopped"] = True
                    (OUT / "fetch_log.json").write_text(json.dumps(log, indent=1))
                    return 2
                err = f"HTTP {e.code}"
            except Exception as e:  # connection reset, timeout
                err = repr(e)
            if attempt < len(RETRY_PAUSES):
                print(f"  retry {slug} after {RETRY_PAUSES[attempt]}s: {err}", flush=True)
                time.sleep(RETRY_PAUSES[attempt])
        if body is None:
            log["failed"][slug] = err
            print(f"FAILED {slug}: {err}", flush=True)
        else:
            text = body.decode("utf-8", "replace")
            if "team-schedule" not in text:
                low = text.lower()
                if "captcha" in low or "cloudflare" in low or "access denied" in low:
                    print(f"BOT PROTECTION on {slug}; stopping", flush=True)
                    log["failed"][slug] = "bot protection page (stopped)"
                    log["stopped"] = True
                    (OUT / "fetch_log.json").write_text(json.dumps(log, indent=1))
                    return 2
                log["failed"][slug] = "page has no schedule list"
            dest.write_bytes(gzip.compress(body, 9))
            log["fetched"].append(slug)
            print(f"{i + 1}/{len(teams)} {slug} {len(body)}", flush=True)
        time.sleep(DELAY)
    log["finished"] = datetime.now(timezone.utc).isoformat()
    (OUT / "fetch_log.json").write_text(json.dumps(log, indent=1))
    print(f"done: {len(log['fetched'])} fetched, {len(log['failed'])} failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
