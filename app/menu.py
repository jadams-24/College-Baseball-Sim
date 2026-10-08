"""The action menu (manager screen v2, 2026-10-08): the calls the user's side can make before the coming pitch.

Built on the server from the connector's turn and the engine state, so the page never decides what is legal:
each item names the order it sends (kind and value, or the pick it needs), whether it can be sent now and, when it
cannot, why. Batting items appear only when the user's team bats the coming pitch, pitching items only when it
fields it. An enabled item's order validates against the engine's eligibility rules (app.catalogue.to_engine),
which tests/test_app_menu.py checks on paused games.

Items: {"id", "kind", "value", "label", "group", "default", "enabled", "reason", "queued", "pick"}
  group: offense (batting calls) | pitching (the pitch itself) | defense (the fielding side's moves): the page's sub-panels.
  pick (when the order needs a player): {"what": bench | bullpen | sub, "options": [pid, ...]}; "sub" also needs
  a lineup slot. Steal items name the runner who goes (the engine's lead-runner rule, app.catalogue.steal_base);
  there is no double steal in the engine, so the menu never offers one; nor a shift: the engine has no fielder positioning.
"""
from __future__ import annotations

from app import catalogue as cat
from app.timeline import ordinal

TEXT_9_4_C = "no second trip with the same batter at bat (NCAA 9-4-c)"
TEXT_9_4_B = "a second trip this inning removes him (NCAA 9-4-b)"


def _queued(orders: list, kind: str, value=None) -> bool:
    for o in orders:
        if o["kind"] != kind:
            continue
        if value is None or o["value"] == value:
            return True
        if isinstance(value, dict) and isinstance(o["value"], dict) and set(value) & set(o["value"]) and all(
                o["value"].get(k) == v for k, v in value.items() if v is not None):
            return True
    return False


def menu(runner) -> list:
    st = runner.current.st
    user = runner.user
    turn_actions = {a["kind"]: a for a in runner.actions(st)}
    orders = [{"kind": o.kind, "value": o.value} for o in runner.human.all_orders() if o.index is None]
    phase = runner.base.phase
    out: list = []
    if phase in ("pregame", "over") or st.over:
        return out
    pre, dfn = turn_actions["pre_pitch"], turn_actions["pre_pitch_defense"]
    bats_next = (st.batting_side != user) if st.outs >= 3 else (st.batting_side == user)
    in_pa = runner.current.pa is not None
    names = {p.pid: p for t in st.team_obj.values() for p in t.batters + cat.staff(t)}

    def item(id_, kind, value, label, enabled, reason="", default=False, pick=None, queued=None, group=None):
        out.append({"id": id_, "kind": kind, "value": value, "label": label, "group": group or ("offense" if bats_next else "pitching"),
                    "default": default, "enabled": bool(enabled),
                    "reason": "" if enabled else reason, "pick": pick,
                    "queued": _queued(orders, kind, value) if queued is None else queued})

    if bats_next:
        picks = pre.get("picks") or {}
        ok, why = pre["legal"], pre["reason"]
        item("swing", "pre_pitch", "swing", "Swing away", ok, why, default=True)
        item("bunt", "pre_pitch", "bunt", "Bunt", ok, why)
        sb = picks.get("steal_base", 0)
        if ok and sb:
            runner_on = next((r for r in picks.get("runners", []) if r["base"] == sb - 1), None)
            who = names[runner_on["pid"]].name if runner_on else "the runner"
            item("steal", "pre_pitch", "steal", f"Steal {ordinal(sb)} · {who} goes", True)
            item("hit_and_run", "pre_pitch", "hit_and_run", f"Hit & run · {who} goes", True)
        ph = turn_actions["pinch_hit"]
        item("pinch_hit", "pinch_hit", None, "Pinch hit (next batter)" if in_pa else "Pinch hit", ph["legal"], ph["reason"],
             pick={"what": "bench", "options": ph["options"]}, queued=_queued(orders, "pinch_hit"))
        bench = picks.get("bench", [])
        for r in picks.get("runners", []):
            item(f"pinch_run_{r['base']}", "pre_pitch", {"pinch_runner": None, "slot": r["slot"]},
                 f"Pinch run {ordinal(r['base'])} · for {names[r['pid']].name}", ok and bool(bench), why or "no bench player left",
                 pick={"what": "bench", "options": bench})
    else:
        picks = dfn.get("picks") or {}
        ok, why = dfn["legal"], dfn["reason"]
        item("pitch", "pre_pitch_defense", "none", "Pitch", ok, why, default=True)
        item("pitch_around", "pre_pitch_defense", "intentional_ball", "Pitch around", ok, why)
        item("ibb", "pre_pitch_defense", "ibb", "Intentional walk", ok, why)
        runner_on = any(b is not None for b in st.bases)
        item("pitchout", "pre_pitch_defense", "pitchout", "Pitchout", ok and runner_on, why or "no runner on")
        m = getattr(st, "mound", None)
        fld = st.fielding_side if st.outs < 3 else st.batting_side
        pitcher = st.pitcher.get(user)
        note = ""
        visit_ok = ok
        if m is not None and pitcher is not None:
            from config.decisions import FREE_TRIPS, FREE_TRIPS_EXTRA
            limit = FREE_TRIPS + (FREE_TRIPS_EXTRA if st.inning > 9 else 0)
            if m["batter"].get(user) == (st.inning, runner.current.pa_serial) and in_pa:
                visit_ok, note = False, TEXT_9_4_C
            elif m["trips"].get((user, st.inning, pitcher.pid)):
                note = TEXT_9_4_B
            elif m["free"].get(user, 0) >= limit:
                note = f"no free trips left ({m['free'].get(user, 0)} of {limit}): a trip removes him"
        item("mound_visit", "pre_pitch_defense", "mound_visit", "Mound visit" + (f" · {note}" if note and visit_ok else ""), visit_ok, why or note, group="defense")
        pen = picks.get("bullpen", [])
        if in_pa:
            item("pitching_change", "pre_pitch_defense", {"pitching_change": None}, "Pitching change (now)", ok and bool(pen), why or "no pitcher left",
                 pick={"what": "bullpen", "options": pen}, queued=_queued(orders, "pre_pitch_defense", {"pitching_change": None}), group="defense")
            bench = picks.get("bench", [])
            item("defensive_change", "pre_pitch_defense", {"defensive_sub": None}, "Defensive change (now)", ok and bool(bench), why or "no bench player left",
                 pick={"what": "sub", "options": bench}, queued=_queued(orders, "pre_pitch_defense", {"defensive_sub": None}), group="defense")
        else:
            pc = turn_actions["pitching_change"]
            item("pitching_change", "pitching_change", {"yes": True, "reliever": None}, "Pitching change", pc["legal"], pc["reason"],
                 pick={"what": "bullpen", "options": pc["options"]}, queued=_queued(orders, "pitching_change"), group="defense")
            ds = turn_actions["defensive_subs"]
            item("defensive_change", "defensive_subs", None, "Defensive change", ds["legal"], ds["reason"],
                 pick={"what": "sub", "options": ds["options"]}, queued=_queued(orders, "defensive_subs"), group="defense")
    return out
