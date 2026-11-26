# data/wmt_player_seasons/ — player-season aggregates from the WMT stats API, 2022–2026

Built by `tools/fetch_wmt_player_seasons.py` (fetch dates and season ids in `coverage.csv` and the commit
message). Source: `https://api.wmt.games/api/statistics/teams?season_id=<id>` (the season's client teams)
and `/teams/<team_id>/players?with[]=season_stats` (every rostered player's season totals with class and
position). Only WMT's client schools (about 51 D1 programs a season, P4-heavy) have players; a player who
leaves for a non-client school disappears from the panel. No names, no player rows: the panel stays in the
fetch's working directory.

| File | Content |
|---|---|
| `coverage.csv` | teams, players, share with a known class, batters with 50+ PA and pitchers with 50+ BF, by season and tier |
| `teams.csv` | the client teams by season (team, conference, tier) |
| `aging_curves.csv` | consecutive-season pairs of the same person (both seasons over the floor, any client team): by class in the first season (and by tier, by playing-time tercile), role and rate: players, PA-weighted level in each season, mean, SD, SE, precision-weighted mean and median of the change (logit scale for rates, raw for ERA/SLG/ISO/OPS). Survivors only: a player must play both seasons |
| `levels_by_class.csv` | cross-sectional PA- or BF-weighted level of each rate by season, tier and class, with the between-player SD |
| `retention_by_class.csv` | each player-season's status the next season: same team, another client team, absent (left for a non-client school, drafted, graduated, cut, or not rostered), by class, tier, role x playing-time tercile and played/rostered |
| `tier_moves.csv` | moves between client teams by tier pair |
| `class_composition.csv` | players by season, tier, class, pitcher/position and played/rostered (stat rosters: everyone WMT lists, including players without a game) |
| `roster_size.csv` | stat-roster size per team by season and tier (mean, SD, min, max), pitchers and players with a game |
| `survivor_selection.csv` | survivor bias of the aging curves: by role, class and rate, the first-season level of the players who enter a pair against all players over the floor that season, the leavers' level, the selection gap in player SDs, the survivors' year-to-year correlation and the implied regression-to-the-mean bias (1 - r) x (population mean - survivors' mean), raw and on the logit scale. Reported, not applied |
