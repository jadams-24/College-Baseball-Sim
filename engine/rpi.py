"""Rating Percentage Index, the NCAA's Division I baseball method (config.phase7).

    RPI = w1 WP + w2 OWP + w3 OOWP
WP is the team's winning percentage with each result weighted by site (a road win counts more than a
home win, a home loss more than a road loss). OWP: for every game the team played, the opponent's
unweighted winning percentage in its Division I games other than those against the team; averaged
over the team's games (an opponent met three times counts three times). OOWP: the same average of the
opponents' OWP. Only games between Division I teams enter, and only decided games (no ties).
"""
from __future__ import annotations

from collections import defaultdict

from config.phase7 import RPI_SITE_WEIGHT, RPI_WEIGHTS


def rpi(games) -> dict:
    """games: iterable of (home, away, home_won, neutral) between Division I teams. Returns
    {team: {"rpi", "wp", "owp", "oowp", "w", "l"}}."""
    sw = RPI_SITE_WEIGHT
    wins, losses = defaultdict(int), defaultdict(int)
    ww, wl = defaultdict(float), defaultdict(float)            # site-weighted wins and losses
    vs = defaultdict(lambda: defaultdict(lambda: [0, 0]))     # vs[a][b] = [wins of a over b, losses]
    opps = defaultdict(list)                                  # one entry per game
    for home, away, home_won, neutral in games:
        win, lose = (home, away) if home_won else (away, home)
        wins[win] += 1; losses[lose] += 1
        vs[win][lose][0] += 1; vs[lose][win][1] += 1
        opps[home].append(away); opps[away].append(home)
        if neutral:
            ww[win] += sw["neutral"]; wl[lose] += sw["neutral"]
        elif home_won:
            ww[win] += sw["home_win"]; wl[lose] += sw["road_loss"]
        else:
            ww[win] += sw["road_win"]; wl[lose] += sw["home_loss"]
    teams = set(opps)

    def wp_without(t, o):
        w, l = wins[t] - vs[t][o][0], losses[t] - vs[t][o][1]
        return w / (w + l) if w + l else 0.0

    owp = {t: sum(wp_without(o, t) for o in opps[t]) / len(opps[t]) for t in teams}
    oowp = {t: sum(owp[o] for o in opps[t]) / len(opps[t]) for t in teams}
    out = {}
    for t in teams:
        wp = ww[t] / (ww[t] + wl[t]) if ww[t] + wl[t] else 0.0
        out[t] = {"rpi": RPI_WEIGHTS[0] * wp + RPI_WEIGHTS[1] * owp[t] + RPI_WEIGHTS[2] * oowp[t],
                  "wp": wp, "owp": owp[t], "oowp": oowp[t], "w": wins[t], "l": losses[t]}
    return out
