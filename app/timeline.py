"""Play-by-play and box score from what the engine recorded: the session's event log, the marks the controllers
took at every ask (app.connector._mark), the decision records, and the engine's accumulator rows. Nothing here
computes an outcome; it narrates the engine's.

Log entries (engine.game2.GameSession, log=True):
  ('p', pa_serial, sym)                                  one pitch: B ball, K called strike, S swinging strike,
                                                         F foul, P in play, H hit by pitch, N no change in count
  ('run', pa_serial, event, dests)                       base running before a plate appearance: SB_ATT, WP, PB,
                                                         PO (pickoff), BK (balk), OTHER; dests per origin base
  ('pa', pa_serial, batter, pitcher, res, dests, b_to)   the plate appearance's result and runner destinations
  ('steal', pa_serial, base, ok, (b, s))                 PR B: a steal of `base` on the pitch thrown at that count
  ('visit', pa_serial, side)                             PR B: a coach's trip to the mound
  ('pit', pa_serial, side, pid)                          PR B: a pitching change during the plate appearance
  ('final', inning, away, home)
A destination is '' (stays), '0' (out), '1'..'3' (to that base) or '4' (scores).
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right

from app.world import player_json, staff
from engine.game2 import (B_2B, B_3B, B_AB, B_BB, B_H, B_HBP, B_HR, B_K, B_PA, B_ROE, B_SF, B_SH, P_BB, P_BF, P_ER, P_H, P_HBP, P_HR,
                          P_K, P_OUTS, P_PITCH, P_R)

PITCH_TEXT = {"B": "Ball", "K": "Called strike", "S": "Swinging strike", "F": "Foul", "P": "In play", "H": "Hit by pitch", "N": "No change"}
RESULT_TEXT = {"K": "strikes out", "BB": "walks", "HBP": "is hit by the pitch", "1B": "singles", "2B": "doubles", "3B": "triples",
               "HR": "homers", "ROE": "reaches on an error", "IP_OUT": "is out on a ball in play", "SF": "hits a sacrifice fly",
               "SH": "lays down a sacrifice bunt", "FC": "reaches on a fielder's choice"}
RUN_TEXT = {"SB_ATT": "steal attempt", "WP": "wild pitch", "PB": "passed ball", "PO": "pickoff", "BK": "balk", "OTHER": "base-running play"}
ORD = {1: "1st", 2: "2nd", 3: "3rd"}
BASE_NAME = {"1": "first", "2": "second", "3": "third", "4": "home"}
SOURCE_TEXT = {"order": "You", "auto": "AUTO (AI ran your team)", "ai": "Opponent", "note": "Note"}


def ordinal(n: int) -> str:
    return ORD.get(n, f"{n}th")


def count_after(b: int, s: int, sym: str) -> tuple:
    """engine.game2.PlayerGameEngine._record_pitches' count rule."""
    if sym == "B":
        return b + 1, s
    if sym in "KS":
        return b, s + 1
    if sym == "F":
        return b, min(s + 1, 2)
    return b, s


class Narrator:
    """One pass over the game so far; `entries` is the feed, `scored`/`rbi` per player feed the box score."""

    def __init__(self, runner):
        self.r = runner
        sess = runner.current
        self.sess = sess
        self.st = sess.st
        self.teams = {s: sess.st.team_obj[s] for s in ("away", "home")}
        self.players = {p.pid: p for s in self.teams.values() for p in s.batters + staff(s)}
        self.marks = runner.marks()
        self.mark_pos = [m["pos"] for m in self.marks]
        self.records = sorted(runner.records() + runner.human.notes, key=lambda x: x["pos"])
        self.entries: list = []
        self.scored: dict = {}
        self.rbi: dict = {}
        self._lineups: dict = {}
        self._lineup_at: list = []          # (mark index, lineups) when they changed

    # ---- marks around a log position --------------------------------------------------------
    def _before(self, j: int):
        """The last mark at or before log index j (the state before entry j)."""
        i = bisect_right(self.mark_pos, j) - 1
        return self.marks[i] if i >= 0 else None

    def _after(self, j: int):
        """The first mark after log index j (the state after entry j)."""
        i = bisect_left(self.mark_pos, j + 1)
        return self.marks[i] if i < len(self.marks) else None

    def _lineup_at_mark(self, mark) -> dict:
        """Lineups in force at a mark (marks carry them only when they change)."""
        i = self.marks.index(mark)
        cur = {}
        for m in self.marks[: i + 1]:
            if "lineups" in m:
                cur = m["lineups"]
        return cur

    def name(self, pid) -> str:
        p = self.players.get(pid)
        return p.name if p else f"#{pid}"

    def runner_name(self, mark, side: str, slot) -> str:
        lu = self._lineup_at_mark(mark).get(side, ())
        return self.name(lu[slot]) if slot is not None and slot < len(lu) else "runner"

    # ---- the pass --------------------------------------------------------------------------
    def build(self, since: int = 0) -> list:
        log = self.sess.log
        rec_i = 0
        # records before `since` were delivered earlier
        while rec_i < len(self.records) and self.records[rec_i]["pos"] < since:
            rec_i += 1
        b = s = 0
        last_count = (0, 0)
        cur_serial = None
        cur_half = None
        for j in range(since, len(log)):
            e = log[j]
            # decisions recorded before this entry
            while rec_i < len(self.records) and self.records[rec_i]["pos"] <= j:
                self._record(self.records[rec_i], j)
                rec_i += 1
            m = self._before(j)
            if m is not None and (m["inning"], m["half"]) != cur_half:
                cur_half = (m["inning"], m["half"])
                bat = "away" if m["half"] == "T" else "home"
                self.entries.append({"pos": j, "type": "half", "inning": m["inning"], "half": m["half"],
                                     "text": f"{'Top' if m['half'] == 'T' else 'Bottom'} of the {ordinal(m['inning'])}, {self.teams[bat].name} batting"})
            if e[0] in ("p", "steal") and e[1] != cur_serial:
                cur_serial, b, s = e[1], 0, 0           # a new plate appearance (also after a third out on the bases)
            if e[0] == "p":
                sym = e[2]
                last_count = (b, s)
                if sym in ("P", "H") or (sym in "KS" and s == 2) or (sym == "B" and b == 3):
                    continue                              # the pitch ends the plate appearance: the result line carries it
                text = PITCH_TEXT[sym]
                b, s = count_after(b, s, sym)
                self.entries.append({"pos": j, "type": "pitch", "text": f"{text}, {b}-{s}" if sym != "N" else text, "count": [b, s]})
            elif e[0] == "pa":
                self._pa(j, e, last_count, m)
                b = s = 0
            elif e[0] == "run":
                self._run(j, e, m)
            elif e[0] == "steal":
                self._steal(j, e, m)
            elif e[0] == "visit":
                side = e[2]
                self.entries.append({"pos": j, "type": "decision", "source": "note", "side": side, "kind": "mound_visit",
                                     "text": f"Mound visit, {self.teams[side].name}."})
            elif e[0] == "pit":
                side = e[2]
                self.entries.append({"pos": j, "type": "decision", "source": "note", "side": side, "kind": "pitching_change",
                                     "text": f"Pitching change during the at-bat: {self.name(e[3])} comes in for {self.teams[side].name}."})
            elif e[0] == "final":
                _, inn, aw, hm = e
                self.entries.append({"pos": j, "type": "final", "text": f"Final: {self.teams['away'].name} {aw}, {self.teams['home'].name} {hm}"
                                     + (f" ({inn} innings)" if inn != 9 else "") + (" by run rule" if self.st.ended_by_run_rule else "")})
        while rec_i < len(self.records) and self.records[rec_i]["pos"] <= len(log):
            self._record(self.records[rec_i], len(log))
            rec_i += 1
        return self.entries

    def _record(self, rec: dict, pos: int) -> None:
        kind, text, src = rec["kind"], rec["text"], rec["source"]
        side = rec["side"]
        who = SOURCE_TEXT.get(src, src)
        if src == "ai":
            who = f"{self.teams[side].name} (AI)"
        if kind == "pitching_change":
            line = "pitching change" if text == "called" else text
        elif kind == "relief_pitcher":
            line = f"{text} comes in to pitch"
        elif kind == "starting_pitcher":
            line = f"{text} starts"
        elif kind == "pinch_hit":
            line = f"{text} pinch-hits"
        elif kind == "pinch_runner":
            line = f"{text} pinch-runs"
        elif kind == "defensive_subs":
            line = f"defensive change: {text}"
        elif kind == "steal_attempt":
            line = {"called": "runners may go", "held off": "runners held"}.get(text, f"steal: {text}")
        elif kind == "bunt":
            line = {"called": "bunt on", "held off": "no bunt"}.get(text, f"bunt: {text}")
        elif kind == "intentional_walk":
            line = {"called": "intentional walk"}.get(text, f"intentional walk: {text}")
        elif kind in ("pre_pitch", "pre_pitch_defense"):
            line = f"{text} (before the pitch)"
        else:
            line = f"{kind.replace('_', ' ')}: {text}"
        self.entries.append({"pos": pos, "type": "decision", "source": src, "side": side, "kind": kind, "text": f"{who}: {line}"})

    def _runner_moves(self, dests, before, side: str, after_bases: list) -> tuple:
        """Texts for the runners' destinations and the list of scoring runner pids."""
        texts, scored = [], []
        if before is None:
            return texts, scored
        for origin in (3, 2, 1):
            slot = before["bases"][origin - 1]
            if slot is None:
                continue
            d = dests[origin - 1] if origin - 1 < len(dests) else ""
            nm = self.runner_name(before, side, slot)
            lu = self._lineup_at_mark(before).get(side, ())
            pid = lu[slot] if slot < len(lu) else None
            if d == "4":
                texts.append(f"{nm} scores")
                if pid is not None:
                    scored.append(pid)
            elif d == "0":
                texts.append(f"{nm} is out")
            elif d in ("1", "2", "3") and int(d) != origin:
                if slot in after_bases and after_bases.index(slot) == int(d) - 1:
                    texts.append(f"{nm} to {BASE_NAME[d]}")
                else:
                    texts.append(f"{nm} is out at {BASE_NAME[d]}")       # a collision (engine.game2._apply)
        return texts, scored

    def _pa(self, j: int, e, count, before) -> None:
        _, serial, bpid, ppid, res, dests, b_to = e
        after = self._after(j)
        side = "away" if before is None else ("away" if before["half"] == "T" else "home")
        after_bases = after["bases"] if after is not None else []
        texts, scored = self._runner_moves(dests, before, side, after_bases)
        batter = self.name(bpid)
        main = f"{batter} {RESULT_TEXT.get(res, res)}"
        no_pitches = j == 0 or self.sess.log[j - 1][0] != "p" or self.sess.log[j - 1][1] != serial
        if res == "BB" and no_pitches:
            main = f"{batter} is intentionally walked"
        if res == "K":
            last = self.sess.log[j - 1][2] if j > 0 and self.sess.log[j - 1][0] == "p" else ""
            main = f"{batter} strikes out {'looking' if last == 'K' else 'swinging'}"
        if b_to == "4":
            scored.append(bpid)
            if res != "HR":
                texts.append(f"{batter} scores")
        elif b_to in ("1", "2", "3") and res in ("ROE", "FC", "IP_OUT", "SF", "SH"):
            texts.append(f"{batter} to {BASE_NAME[b_to]}")
        runs = len(scored)
        for pid in scored:
            self.scored[pid] = self.scored.get(pid, 0) + 1
        if runs and res not in ("ROE",):
            self.rbi[bpid] = self.rbi.get(bpid, 0) + runs
        outs_before = before["outs"] if before else 0
        outs_after = after["outs"] if after is not None and (after["inning"], after["half"]) == ((before["inning"], before["half"]) if before else None) else None
        tail = ""
        if texts:
            tail = "; " + ", ".join(texts)
        if runs:
            tail += f" ({runs} run{'s' if runs > 1 else ''} score{'' if runs > 1 else 's'})"
        outs_txt = f" {outs_after} out{'s' if outs_after != 1 else ''}." if outs_after is not None and outs_after != outs_before else ""
        on_pitch = "" if (res == "BB" and no_pitches) else f" on a {count[0]}-{count[1]} pitch"
        self.entries.append({"pos": j, "type": "pa", "count": list(count), "res": res, "batter": bpid, "pitcher": ppid, "runs": runs,
                             "text": f"{main}{on_pitch}{tail}.{outs_txt}"})

    def _steal(self, j: int, e, before) -> None:
        _, serial, base, ok, count = e
        side = "away" if before is None else ("away" if before["half"] == "T" else "home")
        slot = before["bases"][base - 2] if before is not None and base >= 2 else None
        nm = self.runner_name(before, side, slot) if slot is not None else "the runner"
        lu = self._lineup_at_mark(before).get(side, ()) if before is not None else ()
        pid = lu[slot] if slot is not None and slot < len(lu) else None
        where = BASE_NAME[str(base)]
        if ok:
            text = f"Stolen base: {nm} steals {where} on the {count[0]}-{count[1]} pitch."
            if base == 4 and pid is not None:
                self.scored[pid] = self.scored.get(pid, 0) + 1
        else:
            text = f"Caught stealing: {nm} is out at {where} on the {count[0]}-{count[1]} pitch."
        self.entries.append({"pos": j, "type": "run", "event": "SB_PITCH", "text": text})

    def _run(self, j: int, e, before) -> None:
        _, serial, ev, dests = e
        after = self._after(j)
        side = "away" if before is None else ("away" if before["half"] == "T" else "home")
        texts, scored = self._runner_moves(dests, before, side, after["bases"] if after else [])
        for pid in scored:
            self.scored[pid] = self.scored.get(pid, 0) + 1
        if ev == "SB_ATT":
            ok = "0" not in dests
            head = "Stolen base" if ok else "Caught stealing"
        else:
            head = RUN_TEXT.get(ev, ev).capitalize()
        self.entries.append({"pos": j, "type": "run", "event": ev, "text": f"{head}: {', '.join(texts) if texts else 'no runner moves'}."})


# ---- state and box score ------------------------------------------------------------------------
def _ip(outs: int) -> str:
    return f"{outs // 3}.{outs % 3}"


def batting_line(row: list, r: int = 0, rbi: int = 0) -> dict:
    return {"pa": row[B_PA], "ab": row[B_AB], "r": r, "h": row[B_H], "2b": row[B_2B], "3b": row[B_3B], "hr": row[B_HR], "rbi": rbi,
            "bb": row[B_BB], "hbp": row[B_HBP], "k": row[B_K], "sf": row[B_SF], "sh": row[B_SH], "roe": row[B_ROE]}


def pitching_line(row: list) -> dict:
    return {"ip": _ip(row[P_OUTS]), "outs": row[P_OUTS], "bf": row[P_BF], "h": row[P_H], "hr": row[P_HR], "bb": row[P_BB], "hbp": row[P_HBP],
            "k": row[P_K], "r": row[P_R], "er": row[P_ER], "pitches": row[P_PITCH]}


def short_batting(line: dict) -> str:
    extras = [f"{line[k]} {lab}" for k, lab in (("hr", "HR"), ("3b", "3B"), ("2b", "2B"), ("bb", "BB"), ("k", "K")) if line[k]]
    return f"{line['h']}-{line['ab']}" + (", " + ", ".join(extras) if extras else "")


def state_json(runner) -> dict:
    sess = runner.current
    st = sess.st
    teams = {s: st.team_obj[s] for s in ("away", "home")}
    lines = runner.lines()
    nar = Narrator(runner)
    nar.build()
    bat, fld = st.batting_side, st.fielding_side

    def card(p, side):
        d = player_json(p)
        if p.side == "bat":
            d["line"] = batting_line(lines[p.pid][0], nar.scored.get(p.pid, 0), nar.rbi.get(p.pid, 0))
            d["line_text"] = short_batting(d["line"])
        else:
            d["line"] = pitching_line(lines[p.pid][1])
            o = st.outing.get(side)
            if o and st.pitcher.get(side) is p:
                d["outing"] = {"pitches": o["pitches"], "runs": o["runs"], "outs": o["pa_outs"], "starter": o["starter"]}
        return d

    # the batter: in a plate appearance, its batter; at a stop between plate appearances, the batter due
    kind = runner.raised.kind if runner.raised is not None else None
    if sess.pa is not None:
        batter = sess.pa["batter"]
    elif bat in st.lineup:
        slot = st.slot[bat] - (1 if kind in ("intentional_walk", "bunt") else 0)
        batter = st.lineup[bat][slot % 9]
    else:
        batter = None
    pitcher = st.pitcher.get(fld)
    bases = []
    for b in st.bases:
        if b is None:
            bases.append(None)
        else:
            slot = b[2]
            p = st.lineup[bat][slot]
            bases.append({"slot": slot, "pid": p.pid, "name": p.name})
    # line score: completed halves plus the half in progress
    halves = {("T", i): None for i in range(1, max(9, st.inning) + 1)}
    halves.update({("B", i): None for i in range(1, max(9, st.inning) + 1)})
    for inn, half, runs, _ in st.half_innings:
        halves[(half, inn)] = runs
    if not st.over and bat in st.lineup:
        halves[(st.half, st.inning)] = st.score[bat] - sess.half_start[0]
    n_inn = max(9, st.inning)
    line_score = {"innings": list(range(1, n_inn + 1)),
                  "away": [halves.get(("T", i)) for i in range(1, n_inn + 1)], "home": [halves.get(("B", i)) for i in range(1, n_inn + 1)]}
    due = []
    if bat in st.lineup and batter is not None:
        i0 = st.lineup[bat].index(batter) if batter in st.lineup[bat] else 0
        due = [st.lineup[bat][(i0 + k) % 9].name for k in range(1, 3)]
    # per-plate-appearance results by batter (the lineup panel), from the narration
    pa_results: dict = {}
    for e in nar.entries:
        if e["type"] == "pa":
            pa_results.setdefault(e["batter"], []).append(e["res"])
    # PR B: the fielding side's mound trips (NCAA 9-4), for the mound-visit button's state
    mound = None
    m = getattr(st, "mound", None)
    if m is not None and pitcher is not None:
        from config.decisions import FREE_TRIPS, FREE_TRIPS_EXTRA
        limit = FREE_TRIPS + (FREE_TRIPS_EXTRA if st.inning > 9 else 0)
        mound = {"free_used": m["free"].get(fld, 0), "free_limit": limit,
                 "visited_this_pitcher_inning": bool(m["trips"].get((fld, st.inning, pitcher.pid))),
                 "same_batter": m["batter"].get(fld) == (st.inning, sess.pa_serial)}
    out = {"score": dict(st.score), "inning": st.inning, "half": st.half, "outs": st.outs, "over": st.over,
           "pa_results": {str(k): v for k, v in pa_results.items()}, "mound": mound,
           "ended_by_run_rule": st.ended_by_run_rule, "run_rule_in_effect": st.run_rule_in_effect,
           "count": [sess.pa["b"], sess.pa["s"]] if sess.pa is not None else None,
           "batting_side": bat, "bases": bases, "line_score": line_score, "hits": dict(st.hits), "errors": dict(st.errors),
           "teams": {s: {"tid": teams[s].tid, "name": teams[s].name, "tier": teams[s].tier} for s in teams},
           "batter": card(batter, bat) if batter is not None else None, "pitcher": card(pitcher, fld) if pitcher is not None else None,
           "due_up": due, "lineups": {}, "bench": {}, "bullpen": {}, "used_pitchers": {}}
    for s in ("away", "home"):
        lu = st.lineup.get(s, [])
        out["lineups"][s] = [dict(card(p, s), slot=i, on_base=any(bb is not None and bb[2] == i for bb in st.bases) if s == bat else False)
                             for i, p in enumerate(lu)]
        out["bench"][s] = [card(p, s) for p in teams[s].batters if p.pid not in st.in_game[s]]
        out["bullpen"][s] = [card(p, s) for p in staff(teams[s]) if p.pid not in st.used[s]]
        out["used_pitchers"][s] = [card(p, s) for p in staff(teams[s]) if p.pid in st.used[s]]
    return out


def box_score(runner) -> dict:
    sess = runner.current
    st = sess.st
    teams = {s: st.team_obj[s] for s in ("away", "home")}
    lines = runner.lines()
    nar = Narrator(runner)
    feed = nar.build()
    out = {"score": dict(st.score), "hits": dict(st.hits), "errors": dict(st.errors), "inning": st.inning, "over": st.over,
           "teams": {s: teams[s].name for s in teams}, "batting": {}, "pitching": {}, "feed": feed}
    for s in ("away", "home"):
        rows = []
        order = {p.pid: i for i, p in enumerate(st.lineup.get(s, []))}
        for p in teams[s].batters:
            b = lines[p.pid][0]
            if b[B_PA] == 0 and p.pid not in st.in_game[s]:
                continue
            rows.append(dict(player_json(p), slot=order.get(p.pid), starter=p.pid in order and b[B_PA] > 0,
                             line=batting_line(b, nar.scored.get(p.pid, 0), nar.rbi.get(p.pid, 0))))
        rows.sort(key=lambda x: (x["slot"] if x["slot"] is not None else 99))
        out["batting"][s] = rows
        prow = []
        for p in staff(teams[s]):
            if p.pid in st.used[s]:
                prow.append(dict(player_json(p), line=pitching_line(lines[p.pid][1])))
        out["pitching"][s] = prow
    return out
