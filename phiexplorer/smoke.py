"""Smoke check: unit test suite + F. graminearum benchmark validation
against the real PHI-base v5.3 dataset (if available).

Run with: python3 -m phiexplorer.smoke
"""
from __future__ import annotations

import json
import subprocess
import sys

from phiexplorer.paths import input_json_path, repo_root

FG_TAXID = 5518
FG_SCINAME = "Fusarium graminearum"

EXPECTED_TOTAL = 1344
EXPECTED_PHENOTYPES = {
    "loss of pathogenicity": 32,
    "reduced virulence": 421,
    "unaffected pathogenicity": 912,
    "increased virulence": 15,
}


def run_unit_tests() -> bool:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        cwd=repo_root(),
    )
    return result.returncode == 0


def run_benchmark_check() -> bool:
    from phiexplorer.extract.phenotypes import extract_protein_phenotypes

    path = input_json_path()
    if not path.exists():
        print(f"Skipping benchmark check: {path} not found (set PHI_DATA_ROOT)")
        return True

    print(f"Loading {path} ...")
    with open(path, encoding="utf-8") as f:
        export = json.load(f)

    df = extract_protein_phenotypes(export, taxid=FG_TAXID, sciname=FG_SCINAME)

    print(f"F. graminearum proteins found: {len(df)} (expected {EXPECTED_TOTAL})")
    ok = len(df) == EXPECTED_TOTAL

    for label, expected in EXPECTED_PHENOTYPES.items():
        col = f"phenotype: {label}"
        actual = int(df[col].sum()) if col in df.columns else 0
        match = actual == expected
        ok = ok and match
        print(f"  {label}: {actual} (expected {expected}) {'OK' if match else 'MISMATCH'}")

    return ok


if __name__ == "__main__":
    print("Running unit tests...")
    tests_ok = run_unit_tests()
    print("\nRunning F. graminearum benchmark check...")
    benchmark_ok = run_benchmark_check()

    if tests_ok and benchmark_ok:
        print("\nSmoke check PASSED")
        sys.exit(0)
    else:
        print("\nSmoke check FAILED")
        sys.exit(1)
