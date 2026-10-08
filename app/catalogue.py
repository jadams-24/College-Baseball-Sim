"""The decision catalogue: what the engine asks a team, built from engine.control.DECISIONS.

Each kind gets a descriptor: which side it belongs to, when the engine asks it, the answer's shape, how a
human's value becomes the engine's answer (validated against the engine's own eligibility rules: a bench player
is a batter not yet in the game, a reliever a staff pitcher not yet used) and how an answer is described in the
feed. A kind in DECISIONS without a descriptor here gets the generic one (yes / no / league rate, raw arguments
shown), so a decision added to the engine later (PR B: steals before any pitch, pitchouts, ...) appears in the
UI on merge; giving it a specific descriptor is a one-entry follow-up.

Effects in today's engine (engine/game2.py, PR B), stated in each descriptor's `effect` for the UI:
  pre_pitch         before every pitch of your plate appearance: steal or hit-and-run (a runner on first with second
                    open, or on second with third open), bunt, swing away, or a pinch runner
  pre_pitch_defense before every pitch in the field: pitchout, intentional ball, intentional walk (awarded without
                    pitches, NCAA 8-2-b), mound visit (NCAA 9-4 limits), pitching change, defensive substitution
  bunt              before the plate appearance: a called bunt is a bunt on every pitch until two strikes
  intentional_walk  before the plate appearance: awarded without pitches
  steal_attempt     the pre-plate-appearance steal of the PR A engine; with the per-pitch steal model on it is not
                    asked (steals are called before a pitch instead)
  pitching_change   YES brings in the relief_pitcher answer after the plate appearance (at an inning's end, when the
                    side next fields)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from engine.control import DECISIONS
from engine.decider import Decision

CHOICE3 = ("yes", "no", "league_rate")
_DEC = {"yes": Decision.YES, "no": Decision.NO, "league_rate": Decision.LEAGUE_RATE}
_DEC_NAME = {v: k for k, v in _DEC.items()}

# when the engine asks, and which side (relative to the half-inning) it asks
PREGAME, HALF_START, PRE_PA, AFTER_REACH, POST_PA, PRE_PITCH = "pregame", "half_start", "pre_pa", "after_reach", "post_pa", "pre_pitch"
BATTING, FIELDING, OWN = "batting", "fielding", "own"
# the engine's order of asks in one window (from a plate appearance's end to the next pitch); the generic
# descriptor's kinds are placed last
ASK_ORDER = ("pitching_change", "relief_pitcher", "pinch_runner", "defensive_subs", "steal_attempt", "pinch_hit",
             "intentional_walk", "bunt", "pre_pitch", "pre_pitch_defense")
PRE_PITCH_CALLS = ("none", "steal", "hit_and_run", "bunt", "swing")
DEFENSE_CALLS = ("none", "pitchout", "intentional_ball", "ibb", "mound_visit")


def steal_base(state) -> int:
    """The base the lead runner would steal (engine.game2.GameSession._steal_base): 2, 3 or 0."""
    b = state.bases
    if b[0] is not None and b[1] is None:
        return 2
    if b[1] is not None and b[2] is None:
        return 3
    return 0


def runners(state, side) -> list:
    """The side's runners on base: [{"base": 1..3, "slot": lineup slot, "pid": ...}]."""
    out = []
    if state.batting_side != side:
        return out
    for i, b in enumerate(state.bases):
        if b is not None:
            slot = b[2]
            out.append({"base": i + 1, "slot": slot, "pid": state.lineup[side][slot].pid})
    return out


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
        if self.answer == "pre_pitch":
            sb = steal_base(state) if state.batting_side == side else 0
            return {"legal": True, "reason": "", "options": list(PRE_PITCH_CALLS),
                    "picks": {"steal_base": sb, "runners": runners(state, side), "bench": [p.pid for p in bench(state, side)]}}
        if self.answer == "pre_pitch_defense":
            return {"legal": True, "reason": "", "options": list(DEFENSE_CALLS),
                    "picks": {"bullpen": [p.pid for p in unused_pitchers(state, side)], "bench": [p.pid for p in bench(state, side)]}}
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
        if a == "pre_pitch":
            if isinstance(value, dict) and "pinch_runner" in value:
                slot = value.get("slot")
                if not any(r["slot"] == slot for r in runners(state, side)):
                    raise ValueError("pinch runner: that lineup slot has no runner on base")
                p = _pick(value["pinch_runner"], bench(state, side), "bench player")
                if p is None:
                    raise ValueError("pinch runner: a bench player is required")
                return ("pinch_runner", slot, p)
            if value not in PRE_PITCH_CALLS:
                raise ValueError(f"before the pitch: one of {PRE_PITCH_CALLS} or a pinch runner")
            if value in ("steal", "hit_and_run") and not steal_base(state):
                raise ValueError("no runner can steal: a runner on first with second open, or on second with third open")
            return None if value == "none" else value
        if a == "pre_pitch_defense":
            if isinstance(value, dict) and "pitching_change" in value:
                p = _pick(value["pitching_change"], unused_pitchers(state, side), "pitcher")
                if p is None:
                    raise ValueError("pitching change: a reliever is required")
                return ("pitching_change", p)
            if isinstance(value, dict) and "defensive_sub" in value:
                item = value["defensive_sub"]
                if not (isinstance(item, (list, tuple)) and len(item) == 2 and isinstance(item[0], int) and 0 <= item[0] <= 8):
                    raise ValueError("defensive sub: [slot, pid]")
                p = _pick(item[1], bench(state, side), "bench player")
                if p is None:
                    raise ValueError("defensive sub: a bench player is required")
                return ("defensive_sub", item[0], p)
            if value not in DEFENSE_CALLS:
                raise ValueError(f"defense call: one of {DEFENSE_CALLS}, a pitching change or a defensive sub")
            return None if value == "none" else value
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
        if a in ("pre_pitch", "pre_pitch_defense"):
            if answer is None or answer == "none":
                return None
            if isinstance(answer, tuple):
                if answer[0] == "pinch_runner":
                    return f"{answer[2].name} pinch-runs (slot {answer[1] + 1})"
                if answer[0] == "pitching_change":
                    return f"{answer[1].name} comes in to pitch"
                if answer[0] == "defensive_sub":
                    return f"{answer[2].name} in at slot {answer[1] + 1}"
            return {"steal": "steal on", "hit_and_run": "hit-and-run on", "bunt": "bunt on", "swing": "swing away",
                    "pitchout": "pitchout", "intentional_ball": "intentional ball", "ibb": "intentional walk", "mound_visit": "mound visit"}.get(str(answer), str(answer))
        return str(answer)

    def to_json(self) -> dict:
        return {"kind": self.kind, "side": self.side, "when": self.when, "answer": self.answer, "label": self.label,
                "effect": self.effect, "persistent": self.persistent, "repeat": self.repeat,
                "choices": list(CHOICE3) if self.answer in ("choice3", "generic") else list(PRE_PITCH_CALLS) if self.answer == "pre_pitch"
                else list(DEFENSE_CALLS) if self.answer == "pre_pitch_defense" else None}


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
    "steal_attempt": Descriptor("steal_attempt", BATTING, PRE_PA, "choice3", "Steal (league rate)",
                                "The PR A engine's steal before the plate appearance; not asked while the per-pitch steal model is on (call steals before a pitch instead).", repeat=True),
    "bunt": Descriptor("bunt", BATTING, PRE_PA, "choice3", "Bunt this at-bat",
                       "Yes: the batter bunts on every pitch until two strikes (then swings away); no: no bunt; league rate: the AI's call.", repeat=True),
    "intentional_walk": Descriptor("intentional_walk", FIELDING, PRE_PA, "choice3", "Intentional walk",
                                   "Yes: the batter due up is walked without pitches (NCAA 8-2-b).", repeat=True),
    "pre_pitch": Descriptor("pre_pitch", BATTING, PRE_PITCH, "pre_pitch", "Before the pitch",
                            "For the coming pitch: steal or hit-and-run (a runner on first with second open, or on second with third open), bunt, swing away, or a pinch runner."),
    "pre_pitch_defense": Descriptor("pre_pitch_defense", FIELDING, PRE_PITCH, "pre_pitch_defense", "Defense call",
                                    "For the coming pitch: pitchout, intentional ball, intentional walk (no pitches), mound visit (NCAA 9-4: a second trip to the same pitcher in an inning removes him; three free trips a game), pitching change or defensive sub."),
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
