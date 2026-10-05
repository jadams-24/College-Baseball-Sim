"""Phase 7 season and world: cancellations, conference tournaments, RPI, NCAA selection and the NCAA
tournament (config.phase7; mechanisms and data in PHASE0_NOTES, Phase 7).

The engine decides nothing here: every game goes through PlayerGameEngine.play with the season's
Decider, and every committee or conference choice is a model fitted to the data:
  cancellations   each scheduled regular-season game is canceled (never made up) with the month's rate
  conference      standings from conference games; the published 2025 format of the conference
  tournaments     (data/conf_tournaments/formats_2025.json) with its qualifiers, seeds and site; the champion
                  takes the automatic bid (all 29 conferences in 2025)
  RPI             engine.rpi on every Division I game through the conference tournaments, sites as played
  selection       at-large: the open slots go to the teams with the largest
                  b_rpi * z(RPI) + b_p4 * P4 + logistic noise (scripts/build_phase7_selection.py);
                  national seeds 1-16 the same with the national-seed model; the other 48 teams fill the
                  2, 3 and 4 seed lines in the order of that score
  bracket         national seed k hosts regional k; 2, 3 and 4 seeds are placed at random (the sim has no
                  geography) with no two teams of a conference in one regional (NCAA bracketing principles);
                  super regionals pair regional k with 17 - k
  games           regionals: four-team double elimination at the host's park; super regionals: best of three
                  at the better national seed's park (else the better seed score); CWS: two four-team double-
                  elimination brackets (super pairs 1/16 + 8/9 with 4/13 + 5/12, and 2/15 + 7/10 with 3/14 + 6/11)
                  and a best-of-three final, neutral site
"""
from __future__ import annotations

import datetime as dt
import json

import numpy as np

from config import phase7
from engine.rpi import rpi
from engine.tournament import Played, conference_tournament, double_elim, series

FORMATS = phase7.ROOT / "data/conf_tournaments/formats_2025.json"


def _month(date: int) -> int:
    return (dt.date.fromisoformat(phase7.SEASON_START) + dt.timedelta(days=int(date))).month


def cancel_mask(schedule: list, rng: np.random.Generator) -> np.ndarray:
    """True for each scheduled game that is canceled: the month's cancellation rate (phase7_inputs cancel7)."""
    rates = phase7.load()["cancel7"]["rate_by_month"]
    u = rng.random(len(schedule))
    p = np.array([rates.get(str(_month(g.date)), rates["all"]) for g in schedule])
    return u < p


class World:
    """Runs everything after the regular season. play_game(home, away, date, neutral) plays one game with
    the season's engine and Decider (tournament usage) and returns (home runs, away runs)."""

    def __init__(self, cfg, league, rng: np.random.Generator):
        self.cfg, self.league, self.rng = cfg, league, rng
        self.real_conf = {tid: c for tid, (_, c, _) in enumerate(cfg.teams)}
        self.formats = json.loads(FORMATS.read_text())["conferences"]
        self.sel = phase7.load()["selection7"]
        self.games = []          # (date, home, away, home_runs, away_runs, neutral, stage)
        # predetermined member hosts (campus_predetermined): one member per conference, drawn before the season
        self.member_host = {}
        for c, f in self.formats.items():
            if f["site_detail"] == "campus_predetermined":
                members = [t for t, rc in self.real_conf.items() if rc == c]
                if members:
                    self.member_host[c] = int(rng.choice(members))

    # ---- standings ------------------------------------------------------------------------------
    @staticmethod
    def records(games: list, conf_only: dict | None = None) -> dict:
        """wins, losses by team; conf_only: team -> conference to count conference games only."""
        rec: dict = {}
        for _, h, a, hr, ar, *_ in games:
            if conf_only is not None and conf_only[h] != conf_only[a]:
                continue
            w, l = (h, a) if hr > ar else (a, h)
            rec.setdefault(w, [0, 0])[0] += 1
            rec.setdefault(l, [0, 0])[1] += 1
        return rec

    def seeds(self, conf: str, reg_games: list) -> list:
        """Conference members by conference win%, then overall win%, then a random draw."""
        members = [t for t, c in self.real_conf.items() if c == conf]
        cr = self.records(reg_games, self.real_conf)
        orr = self.records(reg_games)
        pct = lambda r: r[0] / (r[0] + r[1]) if r[0] + r[1] else 0.0
        tie = {t: self.rng.random() for t in members}
        return sorted(members, key=lambda t: (-pct(cr.get(t, [0, 0])), -pct(orr.get(t, [0, 0])), tie[t]))

    # ---- conference tournaments -------------------------------------------------------------------
    def conference_tournaments(self, reg_games: list, start: int, play_game) -> dict:
        out = {}
        for conf, f in sorted(self.formats.items()):
            order = self.seeds(conf, reg_games)
            if not order:
                continue
            teams = order[:f["teams"]]
            host = None
            if f["site_detail"] in ("campus", "campus_regular_season_champion"):
                host = teams[0]
            elif f["site_detail"] == "campus_predetermined":
                h = self.member_host.get(conf)
                host = h if h in teams else None

            def play(h, a, day, neutral, conf=conf):
                hr, ar = play_game(h, a, start + day, neutral, "conf")
                return h if hr > ar else a
            champ, rec = conference_tournament(f["format"], teams, play, host)
            cr = self.records(reg_games, self.real_conf)
            pct = {t: cr.get(t, [0, 0])[0] / max(sum(cr.get(t, [0, 0])), 1) for t in order}
            out[conf] = {"champion": champ, "champion_seed": teams.index(champ) + 1, "teams": teams, "games": len(rec.games), "days": rec.day,
                         "champion_is_regular_season_champion": bool(pct[champ] >= max(pct.values()) - 1e-12)}
        return out

    # ---- selection and seeding --------------------------------------------------------------------
    def field(self, all_games: list, autos: dict) -> dict:
        r = rpi((h, a, hr > ar, n) for _, h, a, hr, ar, n, *_ in all_games)
        teams = list(r)
        v = np.array([r[t]["rpi"] for t in teams])
        z = dict(zip(teams, (v - v.mean()) / v.std()))
        rank = {t: i + 1 for i, t in enumerate(sorted(teams, key=lambda t: -r[t]["rpi"]))}
        tier = {t.tid: t.tier for t in self.league.teams}
        auto = set(autos.values())
        a_coef = dict(zip(self.sel["at_large"]["predictors"], self.sel["at_large"]["coef"]))
        noise = lambda: float(self.rng.logistic())
        score = {t: a_coef["rpi_z"] * z[t] + a_coef.get("p4", 0.0) * (tier[t] == "p4") + noise() for t in teams if t not in auto}
        k = phase7.FIELD_SIZE - len(auto)
        at_large = sorted(score, key=lambda t: -score[t])[:k]
        fld = sorted(auto) + at_large
        n_coef = dict(zip(self.sel["national_seed"]["predictors"], self.sel["national_seed"]["coef"]))
        sscore = {t: n_coef["rpi_z"] * z[t] + n_coef.get("p4", 0.0) * (tier[t] == "p4") + noise() for t in fld}
        order = sorted(fld, key=lambda t: -sscore[t])
        return {"rpi": r, "rank": rank, "auto": sorted(auto), "at_large": at_large, "field": fld, "seed_order": order,
                "national_seeds": order[:phase7.N_NATIONAL_SEEDS], "seed_score": sscore}

    def bracket(self, f: dict) -> list:
        """16 regionals: [host (national seed k), 2 seed, 3 seed, 4 seed], same-conference teams apart."""
        order = f["seed_order"]
        lines = [order[16 * i:16 * (i + 1)] for i in range(4)]
        regs = [[t] for t in lines[0]]
        for line in lines[1:]:
            for _ in range(200):
                perm = list(self.rng.permutation(line))
                if all(self.real_conf[t] not in {self.real_conf[x] for x in reg} or self.real_conf[t] == "DI Independent"
                       for t, reg in zip(perm, regs)):
                    break
            else:
                perm = self._place(line, regs)
            for t, reg in zip(perm, regs):
                reg.append(int(t))
        return regs

    def _place(self, line: list, regs: list) -> list:
        """Backtracking placement when random draws fail (a conference with many bids)."""
        conf = self.real_conf
        out = [None] * len(regs)

        def go(i, left):
            if i == len(regs):
                return True
            for t in list(self.rng.permutation(left)):
                if conf[t] == "DI Independent" or conf[t] not in {conf[x] for x in regs[i]}:
                    out[i] = t
                    if go(i + 1, [x for x in left if x != t]):
                        return True
            return False
        if not go(0, list(line)):
            return list(self.rng.permutation(line))   # infeasible: the rule cannot hold (reported)
        return out

    # ---- NCAA tournament ----------------------------------------------------------------------------
    def ncaa(self, f: dict, regs: list, dates: dict, play_game) -> dict:
        seed_no = {t: k + 1 for k, t in enumerate(f["national_seeds"])}
        sscore = f["seed_score"]
        rank_key = {t: (seed_no.get(t, 99), -sscore[t]) for t in f["field"]}

        def caller(stage, day0):
            def play(h, a, day, neutral):
                hr, ar = play_game(h, a, day0 + day, neutral, stage)
                return h if hr > ar else a
            return play
        reg_w, reg_rows = [], []
        for k, reg in enumerate(regs):
            rec = Played()
            seed = {t: i for i, t in enumerate(reg)}
            w, _ = double_elim(rec, caller("regional", dates["regional"]), reg, seed, None, True, reg[0])   # host at home, others neutral
            reg_w.append(w)
            reg_rows.append({"host": reg[0], "teams": reg, "winner": w, "games": len(rec.games)})
        sup_w, sup_rows = [], []
        for k in range(8):
            a, b = reg_w[k], reg_w[15 - k]
            host = min((a, b), key=lambda t: rank_key[t])
            rec = Played()
            w, _ = series(rec, caller("super", dates["super"]), a, b, {t: rank_key[t] for t in (a, b)}, host=host)
            sup_w.append(w)
            sup_rows.append({"teams": [a, b], "host": host, "winner": w})
        # CWS brackets: super k pairs regional k with 16 - k; bracket 1 = supers 1, 8, 4, 5; bracket 2 = 2, 7, 3, 6
        b1 = [sup_w[i] for i in (0, 7, 3, 4)]
        b2 = [sup_w[i] for i in (1, 6, 2, 5)]
        rk = {t: rank_key[t] for t in sup_w}
        rec = Played()
        play = caller("cws", dates["cws"])
        w1, _ = double_elim(rec, play, sorted(b1, key=lambda t: rk[t]), {t: i for i, t in enumerate(sorted(b1, key=lambda t: rk[t]))}, None, True, None)
        d1 = rec.day
        rec.day = 0
        w2, _ = double_elim(rec, play, sorted(b2, key=lambda t: rk[t]), {t: i for i, t in enumerate(sorted(b2, key=lambda t: rk[t]))}, None, True, None)
        rec.day = max(rec.day, d1) + 1
        champ, runner = series(rec, play, w1, w2, rk, neutral=True)
        return {"regionals": reg_rows, "supers": sup_rows, "cws": sup_w, "champion": champ, "runner_up": runner}
