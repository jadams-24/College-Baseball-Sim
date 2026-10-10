# data/mlb_draft/ — MLB draft aggregates, 2021–2026 (MLB Stats API)

Built by `tools/fetch_mlb_draft.py` from `https://statsapi.mlb.com/api/v1/draft/<year>` (fetched
2026-10-10). Counts only; the raw feed (names, blurbs) stays outside the repository.

| File | Content |
|---|---|
| `picks_by_round_source.csv` | `year, round (1–20; supplemental and compensation picks folded into the round they follow), band (R1+, R2-5, R6-10, R11-20), source (HS, JC, D1 p4/mid/low on the current conference map, D2, D3, NAIA, 4YR unclassified, other/none), picks, unsigned_proxy` (picks with no signing bonus on file: equals MLB.com's deadline-day unsigned counts in the top 10 rounds 2021–2025 and Baseball America's 39 of 615 for all of 2025; an upper bound in rounds 11–20 and for 2026) |
| `picks_by_class.csv` | four-year and JC picks by the feed's school class (4YR JR/SO/SR/5S/GR; JC J1/J2/J3) |
| `picks_by_conference.csv` | D1 picks by conference (current map) |
| `picks_by_d1_program.csv` | D1 picks per program and year (the Draft Development input) |
| `slot_values.csv` | every pick with a slot value (rounds 1–10): year, overall pick, round code, MLB team, value, source type |
| `summary.csv` | per year: picks, HS, JC, D1, D1 per program (÷307), programs with a pick, top-10-round picks, unsigned proxy (all, top 10), bonuses on file, unclassified four-year picks |
| `unclassified_schools.csv` | four-year school names the matcher could not place, with counts (to extend the alias table) |

Grades: picks, round, class, slot value A (MLB's own feed); D1 and tier assignment B (name match to the
307 programs, validated against the NCAA's D1 counts: 428 = 428 in 2023, 432 vs 431 in 2025); D2 / D3 /
NAIA split C (hand list); unsigned proxy B in rounds 1–10, C in 11–20.
