"""Write the Phase 4 blocks of benchmarks.json from the derived Phase 4 files.

Reads data/ncaa_2025/derived/phase4_inputs_2025.json (scripts/build_phase4_inputs.py: the
individual pitcher leash from the 2025 play-by-play) and phase4_rating_scale_2025.json
(scripts/build_phase4_scale.py: the D1 mean and true SD of each rated rate). Writes
stamina_2025 and ratings_scale_2025. No other block is changed; every write is recorded in
data/ncaa_2025/derived/benchmark_changes_phase4.json.
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_pbp_benchmarks import dumps_compact  # noqa: E402
from config.phase4 import BATTER_RATINGS, PITCHER_RATINGS  # noqa: E402

D = Path("data/ncaa_2025/derived")
BENCH = Path("benchmarks.json")


def main() -> None:
    inp = json.loads((D / "phase4_inputs_2025.json").read_text())
    sc = json.loads((D / "phase4_rating_scale_2025.json").read_text())
    b = json.loads(BENCH.read_text())
    changes = []

    def setv(key, new):
        if json.loads(json.dumps(b.get(key), default=str)) != json.loads(json.dumps(new, default=str)):
            changes.append({"path": key, "old": b.get(key), "new": new})
        b[key] = new

    setv("stamina_2025", {
        "_note": ("Individual pitcher leash, WMT play-by-play 2025 (data/ncaa_2025/pbp). Each decision after a batter has the baseline pull hazard h of "
                  "the Phase 2 usage tables (role, weekend, rotation rank, outing pitches, outing runs, inning ended); a pitcher's hazard is "
                  "1 - (1 - h)^theta with log theta ~ N(log_mean, log_sd^2) by role, fitted by marginal maximum likelihood with the exact "
                  "survival likelihood (engine/eb.py). Pitchers with 5+ appearances in the role. mom_log_sd: method-of-moments check on the "
                  "observed/expected pull ratio. Stamina = 50 - 10 (log theta - log_mean) / log_sd."),
        "conf": "B", "src": inp["src"],
        **{role: {"n_pitchers": e["n_pitchers"], "log_mean": e["log_mean"], "log_sd": e["log_sd"], "mom_log_sd": e["mom_check"]["log_sd"]}
           for role, e in inp["stamina"].items()},
    })
    setv("ratings_scale_2025", {
        "_note": ("The 20-80 scale: rating = 50 + 10 sign (z - mean) / sd, z the player's true logit offset of the rate. mean and sd are the "
                  "PA-weighted (batters) or BF-weighted (pitchers) mean and SD of true z across all D1 players, all tiers, as the Phase 2 "
                  "talent distributions (player_talent_2025, team_talent_2025: sampling noise removed) generate them; usage weights from "
                  f"simulated seasons (seeds {sc['seeds'][0]}-{sc['seeds'][1]}). A definition of the scale, not a target."),
        "conf": "B",
        "batter": {name: {"rate": rate, "sign": sign, **sc["scale"]["bat"][rate]} for name, rate, sign in BATTER_RATINGS},
        "pitcher": {name: {"rate": rate, "sign": sign, **sc["scale"]["pit"][rate]} for name, rate, sign in PITCHER_RATINGS},
    })
    BENCH.write_text(dumps_compact(b) + "\n")
    if changes:
        log = D / "benchmark_changes_phase4.json"
        prior = json.loads(log.read_text()) if log.exists() else []
        stamp = datetime.date.today().isoformat()
        log.write_text(json.dumps(prior + [{**c, "date": stamp} for c in changes], indent=1, default=str) + "\n")
    print("wrote", [c["path"] for c in changes])


if __name__ == "__main__":
    main()
