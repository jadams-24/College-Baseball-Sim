"""The decision catalogue: what the engine asks a team, built from engine.control.DECISIONS.

Each kind gets a descriptor: which side it belongs to, when the engine asks it, the answer's shape, how a
human's value becomes the engine's answer (validated against the engine's own eligibility rules: a bench player
is a batter not yet in the game, a reliever a staff pitcher not yet used) and how an answer is described in the
feed. A kind in DECISIONS without a descriptor here gets the generic one (yes / no / league rate, raw arguments
shown), so a decision added to the engine later (PR B: steals before any pitch, pitchouts, ...) appears in the
UI on merge; giving it a specific descriptor is a one-entry follow-up.

Honest effects in today's engine (engine/game2.py), stated in each descriptor's `effect` for the UI:
  steal_attempt     NO holds the runners; YES and LEAGUE_RATE let them run at the league's rates (a forced
                    steal is PR B)
  bunt              YES makes an in-play out a sacrifice bunt when one is feasible; NO rules the sacrifice out
  intentional_walk  asked and recorded, but the engine does not act on it yet (PR B)
  pitching_change   YES brings in the relief_pitcher answer now (at an inning's end, when the side next fields)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from engine.control import DECISIONS
from engine.decider import Decision

CHOICE3 = ("yes", "no", "league_rate")
_DEC = {"yes": Decision.YES, "no": Decision.NO, "league_rate": Decision.LEAGUE_RATE}
_DEC_NAME = {v: k for k, v in _DEC.items()}

# when the engine asks, and which side (relative to the half-inning) it asks
PREGAME, HALF_START, PRE_PA, AFTER_REACH, POST_PA = "pregame", "half_start", "pre_pa", "after_reach", "post_pa"
BATTING, FIELDING, OWN = "batting", "fielding", "own"
# the engine's order of asks in one window (from a plate appearance's end to the next pitch); the generic
# descriptor's kinds are placed last
ASK_ORDER = ("pitching_change", "relief_pitcher", "pinch_runner", "defensive_subs", "steal_attempt", "pinch_hit",
             "intentional_walk", "bunt")


def bench(state, side) -> list:
    """Position players not yet in the game: the only eligible pinch hitters, pinch runners and defensive
    substitutes (engine.manager.Manager._bench_pick, engine.game2.PlayerGameEngine._sub)."""
    return [p for p in state.team_obj[side].batters if p.pid not in state.in_game[side]]


def staff(team) -> list:
    return list(team.weekend_sp) + list(team.midweek_sp) + list(team.relievers)


def unused_pitchers(state, side) -> list:
    """Pitchers who have not appeared: the only eligible relievers (engine.manager.Manager.relief_pitcher)."""
    return [p for p in staff(state.team_obj[side]) if p.pid not in state.used[side]]


def _pid(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("a player id is an integer")
    return value


def _pick(value, pool: list, what: str):
    pid = _pid(value)
    if pid is None:
        return None
    for p in pool:
        if p.pid == pid:
            return p
    raise ValueError(f"player {pid} is not an eligible {what}")


@dataclass
class Descriptor:
    kind: str
    side: str            # BATTING, FIELDING or OWN (each side answers for itself)
    when: str
    answer: str          # choice3 | pick_batter | pick_pitcher | subs | lineup | pitching_change | generic
    label: str
    effect: str
    persistent: bool = False   # an order waits past the window it was queued for (asked only now and then)
    repeat: bool = False       # an order answers every ask of the kind in its window (the engine asks a steal per opportunity)
    extra: dict = field(default_factory=dict)

    # ---- eligibility and options -------------------------------------------------------------
    def legal(self, state, side: str) -> dict:
        """Whether the side could give a non-default answer now, and the options it can pick from."""
        team = state.team_obj[side]
        if self.answer in ("pick_batter",):
            opts = bench(state, side)
            return {"legal": bool(opts), "reason": "" if opts else "no bench player left", "options": [p.pid for p in opts]}
        if self.answer == "subs":
            opts = bench(state, side)
            return {"legal": bool(opts), "reason": "" if opts else "no bench player left", "options": [p.pid for p in opts]}
        if self.answer == "pick_pitcher":
            opts = unused_pitchers(state, side) if self.kind != "starting_pitcher" else staff(team)
            return {"legal": bool(opts), "reason": "" if opts else "no pitcher left", "options": [p.pid for p in opts]}
        if self.answer == "pitching_change":
            opts = unused_pitchers(state, side)
            return {"legal": bool(opts), "reason": "" if opts else "no pitcher left", "options": [p.pid for p in opts]}
        if self.answer == "lineup":
            return {"legal": True, "reason": "", "options": [p.pid for p in team.batters]}
        return {"legal": True, "reason": "", "options": list(CHOICE3)}

    # ---- a human's value -> the engine's answer --------------------------------------------------
    def to_engine(self, value, state, side: str):
        a = self.answer
        if a in ("choice3", "generic"):
            if value not in _DEC:
                raise ValueError(f"{self.kind}: answer one of {CHOICE3}")
            return _DEC[value]
        if a == "pitching_change":
            if isinstance(value, dict):
                value = "yes" if value.get("yes") else "no"
            if value not in ("yes", "no"):
                raise ValueError("pitching_change: yes or no")
            if value == "yes" and not unused_pitchers(state, side):
                raise ValueError("pitching_change: no pitcher left")
            return _DEC[value]
        if a == "pick_batter":
            return _pick(value, bench(state, side), "bench player")
        if a == "pick_pitcher":
            team = state.team_obj[side]
            pool = staff(team) if self.kind == "starting_pitcher" else unused_pitchers(state, side)
            p = _pick(value, pool, "pitcher")
            if p is None:
                raise ValueError(f"{self.kind}: a pitcher is required")
            return p
        if a == "subs":
            if not isinstance(value, list):
                raise ValueError("defensive_subs: a list of [slot, pid]")
            pool, out, slots, used = bench(state, side), [], set(), set()
            for item in value:
                if not (isinstance(item, (list, tuple)) and len(item) == 2):
                    raise ValueError("defensive_subs: each item is [slot, pid]")
                slot, pid = item
                if not isinstance(slot, int) or not 0 <= slot <= 8:
                    raise ValueError("defensive_subs: slot is 0..8")
                p = _pick(pid, pool, "bench player")
                if p is None or slot in slots or p.pid in used:
                    raise ValueError("defensive_subs: distinct slots and distinct players")
                slots.add(slot); used.add(p.pid)
                out.append((slot, p))
            return out
        if a == "lineup":
            team = state.team_obj[side]
            if not (isinstance(value, list) and len(value) == 9 and len(set(value)) == 9):
                raise ValueError("lineup: nine distinct player ids in batting order")
            return [_pick(pid, team.batters, "batter") for pid in value]
        raise ValueError(self.kind)

    # ---- feed text -----------------------------------------------------------------------------
    def describe(self, answer) -> str | None:
        """A short description of a non-default answer, or None when nothing happened."""
        a = self.answer
        if a in ("choice3", "generic", "pitching_change"):
            name = _DEC_NAME.get(answer, str(answer))
            if name == "league_rate" or (a == "pitching_change" and name == "no"):
                return None
            return {"yes": "called", "no": "held off"}.get(name, name)
        if a in ("pick_batter", "pick_pitcher"):
            return None if answer is None else answer.name
        if a == "subs":
            return None if not answer else ", ".join(f"{p.name} in at slot {slot + 1}" for slot, p in answer)
        if a == "lineup":
            return None if not answer else "lineup set"
        return str(answer)

    def to_json(self) -> dict:
        return {"kind": self.kind, "side": self.side, "when": self.when, "answer": self.answer, "label": self.label,
                "effect": self.effect, "persistent": self.persistent, "repeat": self.repeat,
                "choices": list(CHOICE3) if self.answer in ("choice3", "generic") else None}


_SPECIFIC = {
    "lineup": Descriptor("lineup", OWN, PREGAME, "lineup", "Starting lineup", "Nine batters in order; the AI's suggestion is prefilled."),
    "starting_pitcher": Descriptor("starting_pitcher", OWN, PREGAME, "pick_pitcher", "Starting pitcher", "Any pitcher on the staff."),
    "defensive_subs": Descriptor("defensive_subs", FIELDING, HALF_START, "subs", "Defensive change",
                                 "Bench players take lineup slots when your side next takes the field.", persistent=True),
    "relief_pitcher": Descriptor("relief_pitcher", FIELDING, HALF_START, "pick_pitcher", "Reliever",
                                 "The pitcher who comes in at the next pitching change.", persistent=True),
    "pinch_hit": Descriptor("pinch_hit", BATTING, PRE_PA, "pick_batter", "Pinch hitter", "A bench player bats in the slot due up."),
    "pinch_runner": Descriptor("pinch_runner", BATTING, AFTER_REACH, "pick_batter", "Pinch runner",
                               "A bench position player runs for the batter who just reached."),
    "steal_attempt": Descriptor("steal_attempt", BATTING, PRE_PA, "choice3", "Steal",
                                "No holds the runners; yes or league rate lets them run at the league's rates (a forced steal is PR B).", repeat=True),
    "bunt": Descriptor("bunt", BATTING, PRE_PA, "choice3", "Bunt",
                       "Yes makes an in-play out a sacrifice when one is feasible; no rules the sacrifice out.", repeat=True),
    "intentional_walk": Descriptor("intentional_walk", FIELDING, PRE_PA, "choice3", "Intentional walk",
                                   "Recorded; the engine does not act on it yet (PR B).", repeat=True),
    "pitching_change": Descriptor("pitching_change", FIELDING, POST_PA, "pitching_change", "Pitching change",
                                  "Yes brings in the chosen reliever after this plate appearance (at an inning's end, when you next take the field)."),
}


def _generic(kind: str) -> Descriptor:
    return Descriptor(kind, OWN, PRE_PA, "generic", kind.replace("_", " ").capitalize(),
                      "New engine decision without a specific descriptor yet: yes, no or league rate.", repeat=True)


CATALOGUE: dict = {k: _SPECIFIC.get(k) or _generic(k) for k in DECISIONS}
GENERIC_KINDS = [k for k in DECISIONS if k not in _SPECIFIC]


def describe(kind: str, answer) -> str | None:
    return CATALOGUE[kind].describe(answer)


def catalogue_json() -> list:
    return [CATALOGUE[k].to_json() for k in DECISIONS]
