"""Phase 8 constants: roster rules (the container). Plan: plans/phase8_plan_2026-11-26.md (on ui-prototype);
yardstick: benchmarks_phase8_11.json, PHASE8_NOTES.md. Anything not traced there is marked # GUESS and listed in
GUESSES.md.
"""
from __future__ import annotations

FEATURES = {"classes": True,              # every player carries a class year on the five-year clock (engine.roster)
            "individual_bench": True}     # bench batters draw their own Contact, Gap and Power (below)


def on(feature: str) -> bool:
    return bool(FEATURES.get(feature))


# ---- class years and year-to-year turnover (engine.roster) ----------------------------------------------------
# NCAA Division I from 8/1/26 (benchmarks_phase8_11.json rules_2026_27; owner note 2026-11-26): five years to play
# five seasons, no redshirts. A player's class is his year on that clock.
CLASSES = ("Fr", "So", "Jr", "Sr", "5th")
YARDSTICK = __import__("pathlib").Path(__file__).resolve().parents[1] / "benchmarks_phase8_11.json"
_ROSTER = None


def roster() -> dict:
    """Class shares by tier and the share of each class that returns to the same program, from the Phase 8-11 yardstick (2025 rosters, 232 schools; WMT player seasons 2022-2026).

    shares[tier][class]   listed class shares (the yardstick's Gr is the fifth year), unknowns dropped
    stay[class]           P(back with the same program next season); 0 after the fifth year (the clock)
    (The newcomers' class mix is solved each offseason from these shares: engine.roster apply_offseason.)
    The class shares and the return rates predate the five-year clock (2025 rosters; 2022-2026 pairs), so the
    fifth-year share and the seniors' return rate are the old rules' (graduate students, .12): to be replaced
    by the 2027 rosters."""
    global _ROSTER
    if _ROSTER is None:
        import json
        y = json.loads(YARDSTICK.read_text())
        cls, ret = y["roster_composition_2025"]["class_by_tier"], y["development_2022_2026_wmt"]["retention_by_class"]
        src = {"Fr": "Fr", "So": "So", "Jr": "Jr", "Sr": "Sr", "5th": "Gr"}
        stay = {c: (float(ret[src[c]]["same_team"]) if c != "5th" else 0.0) for c in CLASSES}
        shares = {}
        for tier in ("p4", "mid", "low"):
            raw = [float(cls[tier][src[c]]["share"]) for c in CLASSES]
            shares[tier] = dict(zip(CLASSES, [x / sum(raw) for x in raw]))
        _ROSTER = {"shares": shares, "stay": stay}
    return _ROSTER


# ---- who leaves: by class, role and playing time (engine.roster plan_offseason) -----------------------------------
# data/wmt_player_seasons/retention_by_class.csv, scope class_role_tercile (tools/fetch_wmt_player_seasons.py):
# each player-season's status the next season, seasons pooled. Playing time is the season's PA (batters) or BF
# (pitchers): under USAGE_FLOOR the bucket is "unknown" (the source's own floor, MIN_PA = MIN_BF = 50, a GUESS
# there and listed in GUESSES.md); over it, thirds of playing time among the players of the role over the floor
# that season (t1 the least used, t3 the most).
USAGE_FLOOR = 50
BUCKETS = ("unknown", "t1", "t2", "t3")
RETENTION_CSV = YARDSTICK.parent / "data" / "wmt_player_seasons" / "retention_by_class.csv"
_RETENTION = None


def retention() -> dict:
    """stay[role][class][bucket] = P(back with the same program next season), role "batter" or "pitcher"; n the
    player-seasons behind each cell. The fifth year is 0 (the clock). Seniors' rates are the old rules' (see
    roster()): a senior now has a fifth season, so they will rise once the 2027 rosters are in."""
    global _RETENTION
    if _RETENTION is None:
        import csv
        cnt = {}
        with open(RETENTION_CSV) as f:
            for r in csv.DictReader(f):
                if r["scope"] != "class_role_tercile" or r["class"] not in CLASSES:
                    continue
                c = cnt.setdefault((r["group"], r["class"], r["group2"]), [0, 0])
                c[0] += int(r["same_team"]); c[1] += int(r["same_team"]) + int(r["other_client_team"]) + int(r["absent"])
        stay, n = {}, {}
        for role in ("batter", "pitcher"):
            stay[role] = {c: {b: (cnt[(role, c, b)][0] / cnt[(role, c, b)][1] if c != "5th" else 0.0) for b in BUCKETS} for c in CLASSES}
            n[role] = {c: {b: (cnt[(role, c, b)][1] if c != "5th" else 0) for b in BUCKETS} for c in CLASSES}
        _RETENTION = {"stay": stay, "n": n}
    return _RETENTION


# Playing-time bucket when no season has been played (a league straight from the draw: tests and reports). The dynasty
# always passes the season's real PA and BF. By role group and rank within it (Player.order).
# GUESS: the top six regulars, weekend starters and the first reliever play like the most-used third, and so on down.
N_BENCH_PLAY = 12            # GUESS: bench batters ranked 9-11 by starts get 50+ PA (Player.order counts the regulars)


def role_bucket(group: str, order: int) -> str:
    if group == "regular":
        return "t3" if order < 6 else "t2"
    if group == "sp_weekend":
        return "t3"
    if group == "sp_midweek":
        return "t2"
    if group == "rp":
        return "t2" if order < 2 else "t1" if order < 7 else "unknown"
    return "t1" if order < N_BENCH_PLAY else "unknown"          # bench


# The label shown for why a player is leaving. Display only: the departure itself is the stay rate above. The draft
# and the portal get their own mechanisms in the next steps (plans/phase8_retention_2026-11-26.md).
# GUESS: a most-used junior leaving is a draft departure; a little-used underclassman leaves for playing time.
def reason(year: str, bucket: str) -> str:
    if year == "5th":
        return "Eligibility"
    if year == "Jr" and bucket == "t3":
        return "MLB Draft"
    if year == "Sr":
        return "Graduation"
    if bucket in ("unknown", "t1"):
        return "Playing time"
    return "Transfer"


# Persuasion (owner decision 2026-11-26): at the Players Leaving stage a coach may ask a leaving player to stay, one
# attempt per player. The number of attempts per offseason will come from coaching attributes, 3 to 8 (the skill
# tree, later); every coach has the base number until then. A fifth-year cannot be asked (the clock).
PERSUADE_ATTEMPTS = 3          # owner: 3-8 by coaching attributes; the base
PERSUADE_ATTEMPTS_MAX = 8
# GUESS: an attempt succeeds with the player's own stay rate (a senior is hard to keep, a freshman easy).


# ---- individual bench batters (owner decision 2026-11-26, "every player is an individual") --------------------
# The Phase 2 talent fit (scripts/build_phase2_benchmarks.py: method of moments on player-season rates) leaves the
# individual spread of bench batters unidentified for three rates: with their few plate appearances the observed
# variance is no larger than the binomial noise, so the estimate is 0 for BABIP and the extra-base share and .089 for
# HR, against .098, .225 and .456 for regulars. The engine then drew eight bench batters per team with the same Contact
# and Gap and nearly the same Power. From Phase 8 on a bench batter is a future regular and a pinch-hitting choice, so
# he needs his own talent: for those rates a bench batter's individual SD is the regulars' (the mean stays the bench
# group's own fitted mean). The fitted values are kept beside the ones used (`sd_ind_logit_fitted`).
BENCH_SD_FROM_REGULARS = ("HR", "BABIP", "XBH")     # GUESS (the bench spread is not identified by the data; grade C)


def individual_bench(talent: dict) -> dict:
    """The talent table with the bench batters' individual SDs of BENCH_SD_FROM_REGULARS replaced by the regulars'
    (a copy; the input is untouched). With the feature off, the table as fitted."""
    if not on("individual_bench"):
        return talent
    import copy
    out = copy.deepcopy(talent)
    for r in BENCH_SD_FROM_REGULARS:
        g = out["batter"][r]["groups"]
        g["bench"]["sd_ind_logit_fitted"] = g["bench"]["sd_ind_logit"]
        g["bench"]["sd_ind_logit"] = g["regular"]["sd_ind_logit"]
    return out
