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
EXPECTED_EFFECTOR_COUNT = 22


def run_unit_tests() -> bool:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        cwd=repo_root(),
    )
    return result.returncode == 0


def run_benchmark_check() -> bool | None:
    """Run the F. graminearum benchmark checks against the real dataset.

    Returns True/False for pass/fail, or None if the benchmark was skipped
    because the dataset isn't available.
    """
    from phiexplorer.extract.effectors import extract_effector_proteins
    from phiexplorer.extract.phenotypes import extract_protein_phenotypes

    path = input_json_path()
    if not path.exists():
        print(f"Skipping benchmark check: {path} not found (set PHI_DATA_ROOT)")
        return None

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

    effector_df = extract_effector_proteins(export, taxid=FG_TAXID, sciname=FG_SCINAME)
    effector_match = len(effector_df) == EXPECTED_EFFECTOR_COUNT
    ok = ok and effector_match
    print(
        f"F. graminearum effector proteins found: {len(effector_df)} "
        f"(expected {EXPECTED_EFFECTOR_COUNT}) {'OK' if effector_match else 'MISMATCH'}"
    )

    return ok


if __name__ == "__main__":
    print("Running unit tests...")
    tests_ok = run_unit_tests()
    print("\nRunning F. graminearum benchmark check...")
    benchmark_result = run_benchmark_check()
    benchmark_skipped = benchmark_result is None
    benchmark_ok = True if benchmark_skipped else benchmark_result

    if tests_ok and benchmark_ok:
        if benchmark_skipped:
            print(f"\nSmoke check PASSED (benchmark SKIPPED — no dataset at {input_json_path()})")
        else:
            print("\nSmoke check PASSED")
        sys.exit(0)
    else:
        print("\nSmoke check FAILED")
        sys.exit(1)
