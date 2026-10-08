"""Baseball rows of the EADA 2024-25 data file for the D1 programs (Phase 9 report cards: Money and its proxies).

Source: U.S. Department of Education, Equity in Athletics Disclosure Act data, "Data for academic year 2024-25"
(https://ope.ed.gov/athletics/api/dataFiles/file?fileName=EADA_2024-2025.zip, the file the site's Data File page links;
fetched 2026-10-08; public). The 12 MB archive is not committed: this script reads it from data/eada/EADA_2024-2025.zip
(re-download it from the URL above to rerun) and writes the baseball rows of the 307 programs' institutions:
data/eada/baseball_eada_2024_25.csv. Dollar amounts are as reported (nominal 2024-25). The service academies do not file.
    python3 scripts/extract_eada.py
"""
from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "data/eada/EADA_2024-2025.zip"
OUT = ROOT / "data/eada/baseball_eada_2024_25.csv"
COLS = {"unitid": "unitid", "institution_name": "institution_name", "classification_name": "classification",
        "PARTIC_MEN": "participants", "MEN_TOTAL_HEADCOACH": "head_coaches", "MEN_TOTAL_ASSTCOACH": "assistant_coaches",
        "TOTAL_OPEXP_MENWOMEN": "baseball_operating_expenses", "EXPENSE_MENALL": "baseball_total_expenses",
        "REVENUE_MENALL": "baseball_total_revenue"}


def main() -> None:
    loc = pd.read_csv(ROOT / "data/ncaa_2025/school_locations_2025.csv")
    with tempfile.TemporaryDirectory() as td:
        zipfile.ZipFile(ZIP).extract("schools.sas7bdat", td)
        s = pd.read_sas(Path(td) / "schools.sas7bdat", encoding="latin-1")
    b = s[(s.Sports == "Baseball") & s.unitid.isin(loc.unitid)][list(COLS)].rename(columns=COLS)
    b["unitid"] = b.unitid.astype(int)
    for c in COLS.values():
        if c not in ("unitid", "institution_name", "classification"):
            b[c] = b[c].round(0).astype("Int64")
    b.sort_values("unitid").to_csv(OUT, index=False)
    print(f"{len(b)} of {loc.unitid.nunique()} institutions; missing: {sorted(set(loc.team[~loc.unitid.isin(b.unitid)]))}")


if __name__ == "__main__":
    main()
