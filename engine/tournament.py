"""Tournament brackets: conference tournaments and the NCAA tournament (Phase 7).

The engine never decides a game here; it asks `play(home, away, day, neutral)` for the winner, so the
same runner works with any game engine and any Decider. Teams are given in seed order (best first).
One round is one day; every game records its day so pitchers' rest carries through the tournament.

Building blocks (the published formats, data/conf_tournaments/formats_2025.json, are compositions):
  single_elim   seeded single elimination; byes go to the top seeds, a whole group of seeds entering in a
                later round (e.g. SEC/ACC 2025: seeds 1-4 enter in the quarterfinals, 5-8 in round two)
  double_elim   double elimination; a team is out after its second loss; byes to the top seeds; the final
                is the last unbeaten team against the last one-loss team, with an if-necessary game
  pools         round-robin pools of three; pool winners (best record, then run difference) advance
  series        best of three
Within a bracket the best remaining seed meets the worst, avoiding a rematch when another pairing
exists. The published descriptions fix how many teams enter each round and the bracket shape; game
counts of a double-elimination bracket (2n - 2 or 2n - 1) do not depend on the pairing within it.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Played:
    games: list = field(default_factory=list)    # (day, home, away, winner, neutral)
    day: int = 0


def _game(rec: Played, play, home, away, neutral, host=None):
    """Home side: the host at its own park, else the better seed (listed home at a neutral site)."""
    if host is not None and away == host:
        home, away = away, home
    w = play(home, away, rec.day, neutral and host not in (home, away))
    rec.games.append((rec.day, home, away, w, neutral and host not in (home, away)))
    return w, (away if w == home else home)


def _pairs(teams: list, seed: dict, met: set) -> tuple[list, list]:
    """Best remaining seed against the worst, avoiding rematches where possible; an odd team out (the
    best seed) sits."""
    t = sorted(teams, key=lambda x: seed[x])
    bye = []
    if len(t) % 2:
        bye = [t.pop(0)]
    pairs = []
    while t:
        a = t.pop(0)
        j = next((k for k in range(len(t) - 1, -1, -1) if frozenset((a, t[k])) not in met), len(t) - 1)
        pairs.append((a, t.pop(j)))
    return pairs, bye


def single_elim(rec: Played, play, teams: list, seed: dict, enter: dict | None = None, neutral=True, host=None) -> tuple:
    """Single elimination. enter[team] = round (0-based) in which the team enters (byes); default 0.
    Returns (champion, order of elimination)."""
    enter = enter or {}
    alive = [t for t in teams if enter.get(t, 0) == 0]
    waiting = sorted({enter.get(t, 0) for t in teams} - {0})
    rnd, out, met = 0, [], set()
    while True:
        alive += [t for t in teams if enter.get(t, 0) == rnd and rnd > 0]
        if len(alive) == 1 and not any(r > rnd for r in waiting):
            return alive[0], out
        pairs, bye = _pairs(alive, seed, met)
        nxt = list(bye)
        for a, b in pairs:
            met.add(frozenset((a, b)))
            w, l = _game(rec, play, a, b, neutral, host)
            nxt.append(w); out.append(l)
        rec.day += 1
        alive, rnd = nxt, rnd + 1


def double_elim(rec: Played, play, teams: list, seed: dict, enter: dict | None = None, neutral=True, host=None) -> tuple:
    """Double elimination. enter[team] = round in which the team enters (byes). Returns (champion, out)."""
    enter = enter or {}
    loss = {t: 0 for t in teams}
    active = [t for t in teams if enter.get(t, 0) == 0]
    out, met, rnd = [], set(), 0
    while True:
        active += [t for t in teams if enter.get(t, 0) == rnd and rnd > 0 and t not in active]
        pending = any(enter.get(t, 0) > rnd for t in teams)
        alive = [t for t in active if loss[t] < 2]
        if len(alive) == 1 and not pending:
            return alive[0], out
        if len(alive) == 2 and not pending:
            # final: unbeaten vs one loss (or two one-loss teams), if-necessary game when the unbeaten loses
            a, b = sorted(alive, key=lambda x: (loss[x], seed[x]))
            while loss[a] < 2 and loss[b] < 2:
                w, l = _game(rec, play, a, b, neutral, host)
                loss[l] += 1
                rec.day += 1
            champ = a if loss[a] < 2 else b
            out.append(b if champ == a else a)
            return champ, out
        games = []
        for k in (0, 1):                             # winners' bracket, then losers' bracket
            pool = [t for t in alive if loss[t] == k]
            p, _ = _pairs(pool, seed, met)
            games += p
        if not games:                                # one team in each bracket but more to enter: wait a day
            rec.day += 1; rnd += 1
            continue
        for a, b in games:
            met.add(frozenset((a, b)))
            w, l = _game(rec, play, a, b, neutral, host)
            loss[l] += 1
            if loss[l] == 2:
                out.append(l)
        rec.day += 1
        rnd += 1


def pools(rec: Played, play, groups: list, seed: dict, neutral=True, host=None) -> list:
    """Round-robin pools of three, one game per pool per day. Returns pool winners (most wins, then
    seed: run difference is not tracked by the play callback)."""
    winners = []
    days = [(0, 1), (0, 2), (1, 2)]
    w_count = {t: 0 for g in groups for t in g}
    for a_i, b_i in days:
        for g in groups:
            g = sorted(g, key=lambda x: seed[x])
            w, _ = _game(rec, play, g[a_i], g[b_i], neutral, host)
            w_count[w] += 1
        rec.day += 1
    for g in groups:
        winners.append(max(g, key=lambda x: (w_count[x], -seed[x])))
    return winners


def series(rec: Played, play, a, b, seed: dict, wins_needed: int = 2, neutral=False, host=None) -> tuple:
    """Best of 2 * wins_needed - 1. Returns (winner, loser)."""
    a, b = sorted((a, b), key=lambda x: seed[x])
    host = a if host is None and not neutral else host
    w = {a: 0, b: 0}
    while max(w.values()) < wins_needed:
        x, _ = _game(rec, play, a, b, neutral, host)
        w[x] += 1
        rec.day += 1
    return (a, b) if w[a] == wins_needed else (b, a)


def _parallel(rec: Played, runs: list) -> list:
    """Run brackets on the same days (separate sites): each from the current day; the round ends when
    the longest is done."""
    start, ends, out = rec.day, [], []
    for fn in runs:
        rec.day = start
        out.append(fn())
        ends.append(rec.day)
    rec.day = max(ends)
    return out


def conference_tournament(code: str, teams: list, play, host=None) -> tuple[object, Played]:
    """One conference tournament in a published format (data/conf_tournaments/formats_2025.json codes).
    teams: qualifiers in seed order. host: the team whose park holds the tournament, or None (neutral
    site; campus formats host at the better seed's park). Returns (champion, games)."""
    rec = Played()
    seed = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    s = lambda *k: [teams[i - 1] for i in k]              # seeds, 1-based
    nt = host is None
    if code in ("de4", "de8", "de8_divisions_crossover"):
        return double_elim(rec, play, teams, seed, neutral=nt, host=host)[0], rec
    if code in ("de6", "de6_reseeded"):                   # seeds 1-2 enter in round two
        return double_elim(rec, play, teams, seed, {t: 1 for t in s(1, 2)}, nt, host)[0], rec
    if code == "de7":                                     # top seed's first-round bye
        return double_elim(rec, play, teams, seed, {teams[0]: 1}, nt, host)[0], rec
    if code == "se16_byes":
        enter = {t: 2 for t in s(1, 2, 3, 4)} | {t: 1 for t in s(5, 6, 7, 8)}
        return single_elim(rec, play, teams, seed, enter, nt, host)[0], rec
    if code == "se12_byes":
        return single_elim(rec, play, teams, seed, {t: 1 for t in s(1, 2, 3, 4)}, nt, host)[0], rec
    if code in ("se_playin4_then_de4", "se_playin_then_de4"):
        k = 3 if code == "se_playin4_then_de4" else 4     # first play-in seed
        ws = _playin_round(rec, play, teams[k - 1:], seed, nt, host)
        return double_elim(rec, play, teams[:k - 1] + ws, seed, None, nt, host)[0], rec
    if code == "se_playin4_then_de6":
        ws = _playin_round(rec, play, teams[4:], seed, nt, host)
        return double_elim(rec, play, teams[:4] + ws, seed, {t: 1 for t in s(1, 2)}, nt, host)[0], rec
    if code == "se2rounds_then_de4":
        ws = _playin_round(rec, play, teams[4:], seed, nt, host)
        ws = _playin_round(rec, play, s(3, 4) + ws, seed, nt, host)
        return double_elim(rec, play, s(1, 2) + ws, seed, None, nt, host)[0], rec
    if code == "pool4x3_then_se4":
        groups = [s(1, 8, 12), s(2, 7, 11), s(3, 6, 10), s(4, 5, 9)]
        ws = pools(rec, play, groups, seed, nt, host)
        return single_elim(rec, play, ws, seed, None, nt, host)[0], rec
    if code in ("de8_two_brackets_final", "playin2_de8_two_brackets_final", "de8_two_brackets_campus_bo3_final"):
        eight = teams
        if code == "playin2_de8_two_brackets_final":
            eight = teams[:6] + _playin_round(rec, play, teams[6:], seed, nt, host)
        e = lambda *k: [eight[i - 1] for i in k]
        campus = code == "de8_two_brackets_campus_bo3_final"
        a, b = _parallel(rec, [lambda: double_elim(rec, play, e(1, 8, 4, 5), seed, None, nt and not campus, e(1)[0] if campus else host)[0],
                               lambda: double_elim(rec, play, e(2, 7, 3, 6), seed, None, nt and not campus, e(2)[0] if campus else host)[0]])
        if campus:
            return series(rec, play, a, b, seed)[0], rec
        return single_elim(rec, play, [a, b], seed, None, nt, host)[0], rec
    if code == "bo3_series_4":
        x, y = _parallel(rec, [lambda: series(rec, play, *s(1, 4), seed)[0], lambda: series(rec, play, *s(2, 3), seed)[0]])
        return series(rec, play, x, y, seed)[0], rec
    raise ValueError(f"unknown tournament format {code!r} ({n} teams)")


def _playin(teams: list, seed: dict) -> list:
    t = sorted(teams, key=lambda x: seed[x])
    return [(t[i], t[-1 - i]) for i in range(len(t) // 2)]


def _playin_round(rec: Played, play, teams: list, seed: dict, neutral, host) -> list:
    """One single-elimination round, best vs worst, all on one day; returns the winners in seed order."""
    ws = [_game(rec, play, a, b, neutral, host)[0] for a, b in _playin(teams, seed)]
    rec.day += 1
    return sorted(ws, key=lambda x: seed[x])
