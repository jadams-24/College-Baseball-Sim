"""Phase 8 constants: roster rules (the container). Plan: plans/phase8_plan_2026-11-26.md (on ui-prototype);
yardstick: benchmarks_phase8_11.json, PHASE8_NOTES.md. Anything not traced there is marked # GUESS and listed in
GUESSES.md.
"""
from __future__ import annotations

FEATURES = {"classes": True}              # every player carries a class year on the five-year clock (engine.roster)


def on(feature: str) -> bool:
    return bool(FEATURES.get(feature))


# ---- class years and year-to-year turnover (engine.roster) ----------------------------------------------------
# NCAA Division I from 8/1/26 (benchmarks_phase8_11.json rules_2026_27; owner note 2026-11-26): five years to play
# five seasons, no redshirts. A player's class is his year on that clock.
CLASSES = ("Fr", "So", "Jr", "Sr", "5th")
YARDSTICK = __import__("pathlib").Path(__file__).resolve().parents[1] / "benchmarks_phase8_11.json"
_ROSTER = None


def roster() -> dict:
    """Class shares by tier, the share of each class that returns to the same program, and the class mix of each
    year's newcomers, from the Phase 8-11 yardstick (2025 rosters, 232 schools; WMT player seasons 2022-2026).

    shares[tier][class]   listed class shares (the yardstick's Gr is the fifth year), unknowns dropped
    stay[class]           P(back with the same program next season); 0 after the fifth year (the clock)
    entrants[tier][class] the class mix of newcomers that keeps the class shares where the rosters have them:
                          e(c) = share(c) - stay(c-1) share(c-1), floored at 0 and normalized. Freshmen are the
                          high-school class; the later classes are transfers (JUCO juniors, D1 transfers).
    turnover[tier]        the share of a roster that is new each year, sum over classes of e before normalizing
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
        shares, entrants, turnover = {}, {}, {}
        for tier in ("p4", "mid", "low"):
            raw = [float(cls[tier][src[c]]["share"]) for c in CLASSES]
            sh = [x / sum(raw) for x in raw]
            e = [sh[0]] + [max(sh[k] - stay[CLASSES[k - 1]] * sh[k - 1], 0.0) for k in range(1, len(CLASSES))]
            shares[tier] = dict(zip(CLASSES, sh)); turnover[tier] = sum(e)
            entrants[tier] = dict(zip(CLASSES, [x / sum(e) for x in e]))
        _ROSTER = {"shares": shares, "stay": stay, "entrants": entrants, "turnover": turnover}
    return _ROSTER
