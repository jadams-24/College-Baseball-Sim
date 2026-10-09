"""Box-score bookkeeping (2026-10-09, owner request): runs, runs batted in, stolen bases and caught stealing per batter, and
the pitchers' decisions (win, loss, save, hold), for every game the engine plays, simmed or managed.

Bookkeeping only: nothing here draws a random number or feeds a decision, so game logs are identical with it on or off
(config.box.ENABLED; tests/test_boxscore.py plays 300 games both ways). The scoring follows the NCAA Baseball Rules
(data/ncaa_rules/PRMBA_RulesBook.pdf, 2025 and 2026), Rule 10:

  10-9  run batted in: a runner scores because of a base hit (the batter on a home run), a sacrifice bunt or fly, any putout,
        a forced advance (base on balls, hit batter), or an error with fewer than two outs when the runner on third would
        have scored without it. Not on a force double play. The scorer's judgment on errors is approximated: with an error
        on the play, only the runner from third is credited, and only with fewer than two outs (on a reached-on-error, the
        same). Runs on wild pitches, passed balls, balks, steals and pickoff plays are not runs batted in.
  10-11 stolen base and caught stealing, per runner who tries on a steal play. Exception 1: when any runner is thrown out on
        a double or triple steal, no runner is credited with a stolen base. A pickoff the engine scores as a caught stealing
        (PR B, config.decisions) is charged to the runner picked off.
  10-25 winning and losing pitchers. The winning pitcher is his team's pitcher of record when it took the lead for the last
        time; a starter needs five complete innings in a game of eight or more innings, four in a shorter game, otherwise
        the win goes to the relief pitcher who pitched most effectively (the scorer's judgment, approximated: most outs
        recorded, then fewest runs charged, then the earlier entry). The "brief and ineffective" exception (10-25-b-1) is
        a judgment call and is not applied. The losing pitcher is the one charged with the run that gave the winners the
        lead for the last time (10-25-d note).
  10-26 save: the finishing pitcher of a game his team won, not credited with the win, who entered with a lead of three runs
        or fewer and pitched at least one inning, or entered with the potential tying run on base, at bat or on deck, or
        pitched at least three innings (effectiveness assumed). At most one save per game.
  Hold: not an NCAA statistic (Rule 10 has none). The common definition is used: a relief pitcher who entered in a save
        situation (10-26-c-1's lead or 10-26-c-2's tying run), recorded at least one out, left with his team still ahead,
        did not finish the game and was not credited with the win or a save. Marked GUESS (definition) in GUESSES.md.

Counts go to the engine's season accumulators (new columns B_R, B_RBI, B_SB, B_CS and P_W, P_L, P_SV, P_HLD, appended so every
older index is unchanged) and each game's decisions to the game state (GameState2.box["decisions"]).
"""
from __future__ import annotations

_NO_RBI_RESULTS = ("GIDP", "DP")


class GameBox:
    """One game's bookkeeping, kept on the game state (pickled with a session save)."""

    __slots__ = ("starter", "order", "entry", "exit", "outs", "runs", "goahead", "decisions")

    def __init__(self):
        self.starter = {}          # side -> pid
        self.order = {"away": [], "home": []}
        self.entry = {}            # pid -> (lead of his team, runners on, outs in the inning) when he entered
        self.exit = {}             # pid -> lead of his team when he left
        self.outs = {}             # pid -> outs recorded this game
        self.runs = {}             # pid -> runs charged this game
        self.goahead = None        # (batting side, its pitcher of record, the pitcher charged with the go-ahead run)
        self.decisions = None


def _lead(st, side: str) -> int:
    other = "home" if side == "away" else "away"
    return st.score[side] - st.score[other]


def on_enter(eng, st, side: str, pid: int, starter: bool) -> None:
    box = st.box
    order = box.order[side]
    if order:
        box.exit[order[-1]] = _lead(st, side)
    if starter:
        box.starter[side] = pid
    order.append(pid)
    runners = sum(b is not None for b in st.bases) if st.fielding_side == side else 0
    box.entry[pid] = (_lead(st, side), runners, st.outs if st.fielding_side == side else 0)


def on_apply(eng, st, scored: list, origins: list, cur: int, outs: int, res, event, errors: int, outs_before: int,
             batter_slot) -> None:
    """After a play moved runners: runs, runs batted in, outs and runs charged, and a change of lead.
    scored: the runner entries that scored, origins their bases (4 for the batter); res the plate appearance's result (None
    for base running); batter_slot the batter's lineup slot (None for base running)."""
    from engine.game2 import B_R, B_RBI
    box = st.box
    bat, fld = st.batting_side, st.fielding_side
    box.outs[cur] = box.outs.get(cur, 0) + outs
    if not scored:
        return
    lineup = st.lineup[bat]
    before = st.score[bat] - len(scored)          # _apply has already added the runs
    other = st.score[fld]
    rbi = 0
    for r, origin in zip(scored, origins):
        if len(r) > 2:
            eng.bstats[lineup[r[2]].pid][B_R] += 1
        box.runs[r[0]] = box.runs.get(r[0], 0) + 1
        if res is None or res in _NO_RBI_RESULTS:
            continue
        if errors or res == "ROE":
            if origin == 3 and outs_before < 2:
                rbi += 1
        else:
            rbi += 1
    if rbi and batter_slot is not None:
        eng.bstats[lineup[batter_slot].pid][B_RBI] += rbi
    # the run that put the batting team ahead, if it went ahead on this play
    if before <= other < st.score[bat]:
        go = scored[other - before]               # the (other - before + 1)-th run scored is the go-ahead run
        box.goahead = (bat, st.pitcher[bat].pid, go[0])


def on_steal(eng, st, dests: list, picked_off: bool = False) -> None:
    """A steal play (or a pickoff scored as a caught stealing): every runner who moved tried; Rule 10-11."""
    from engine.game2 import B_CS, B_SB
    lineup = st.lineup[st.batting_side]
    movers = [k for k in range(3) if st.bases[k] is not None and len(st.bases[k]) > 2 and dests[k] != str(k + 1)]
    out = [k for k in movers if dests[k] == "0"]
    for k in movers:
        pid = lineup[st.bases[k][2]].pid
        if dests[k] == "0":
            eng.bstats[pid][B_CS] += 1
        elif not out and not picked_off:
            eng.bstats[pid][B_SB] += 1


def on_final(eng, st) -> None:
    """The pitchers' decisions, Rules 10-25 and 10-26."""
    from engine.game2 import P_HLD, P_L, P_SV, P_W
    box = st.box
    for side in ("away", "home"):
        if box.order[side]:
            box.exit.setdefault(box.order[side][-1], _lead(st, side))
    if st.score["home"] == st.score["away"] or box.goahead is None:
        box.decisions = {"W": None, "L": None, "SV": None, "HLD": []}
        return
    win = "home" if st.score["home"] > st.score["away"] else "away"
    lose = "away" if win == "home" else "home"
    side, w, loser = box.goahead
    if side != win:                               # cannot happen: the last go-ahead belongs to the winner
        w, loser = box.order[win][-1], box.order[lose][0]
    starter = box.starter.get(win)
    if w == starter:
        need = 15 if st.inning >= 8 else 12        # five complete innings (four in a game of fewer than eight)
        if box.outs.get(w, 0) < need and len(box.order[win]) > 1:
            rel = box.order[win][1:]
            w = max(rel, key=lambda p: (box.outs.get(p, 0), -box.runs.get(p, 0), -rel.index(p)))
    sv = None
    fin = box.order[win][-1]
    if fin != w and fin != starter:
        lead0, runners0, _ = box.entry[fin]
        o = box.outs.get(fin, 0)
        if lead0 > 0 and ((lead0 <= 3 and o >= 3) or lead0 <= runners0 + 2 or o >= 9):
            sv = fin
    holds = []
    for s in ("away", "home"):
        for p in box.order[s][1:-1]:                # relievers who did not finish
            if p in (w, sv, loser):
                continue
            lead0, runners0, _ = box.entry[p]
            save_sit = lead0 > 0 and (lead0 <= 3 or lead0 <= runners0 + 2)
            if save_sit and box.outs.get(p, 0) >= 1 and box.exit.get(p, 0) > 0:
                holds.append(p)
    eng.pstats[w][P_W] += 1
    eng.pstats[loser][P_L] += 1
    if sv is not None:
        eng.pstats[sv][P_SV] += 1
    for p in holds:
        eng.pstats[p][P_HLD] += 1
    box.decisions = {"W": w, "L": loser, "SV": sv, "HLD": holds}
