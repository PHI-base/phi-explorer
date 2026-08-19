# phi-explorer Reports/Extract Layering — Design Spec

**Date:** 2026-08-19
**Status:** Approved (pending implementation)
**Repo:** https://github.com/PHI-base/phi-explorer.git (public)

## 1. Purpose

Complete the `reports/` layer's intended dependency on `extract/`, closing deferred finding
#5 from the core-toolkit plan's final whole-branch review (and re-confirmed by the
extract-consolidation follow-up's own final review). The original design spec
(`docs/superpowers/specs/2026-08-19-phi-explorer-design.md`) §4 states "`reports/` is a thin
consumer of it [`extract/`]" and shows `reports/` built on `extract/` in the package layout
diagram — but this was never realized. Concretely:

- `phiexplorer/reports/excel.py`'s `write_excel()` has **zero callers** in package code — only a
  test calls it directly.
- `phiexplorer/reports/stats.py`'s `dataset_summary()` and `organism_summary()` never touch
  `extract/`, and neither is ever written to an output file.
- Nothing in the package ties `extract_protein_phenotypes()` or `extract_effector_proteins()`'s
  DataFrame output through `write_excel()` into an actual report file, even though that's
  precisely what the two ported source scripts (`fg_protein_phenotypes.py`,
  `fg_effector_proteins.py`) did.

This spec designs the missing orchestration layer: functions that call `extract/`, format the
result, write it to disk, and return the path — nothing more.

## 2. Scope decisions (from brainstorming)

- **Library functions only.** No CLI/script entry point in this follow-up. The original design
  spec explicitly deferred a query CLI to a later version; completing the reports layer doesn't
  change that — it stays a separate future decision.
- **Preserve the original scripts' per-type output format**, rather than standardizing on one
  format for everything:
  - Protein phenotype and effector reports → **Excel**, via the existing `write_excel()` helper
    (matching `fg_protein_phenotypes.py`/`fg_effector_proteins.py`).
  - Dataset summary → **CSV** (matching `phibase5_stats.py`, which wrote
    `output/phibase5_stats_{timestamp}.csv`).
- **No report-writer for `organism_summary()`.** The original `phibase5_stats.py` never wrote
  per-organism stats to a file either — it only printed them (`print(fusarium_df.loc([...]))`).
  Adding a writer for it now would invent scope beyond what this follow-up is restoring.

## 3. Design

### New module: `phiexplorer/reports/generate.py`

Three orchestration functions, one per report type. Each is a thin composition of an existing
`extract/`/`reports/stats.py` function plus an existing (or trivial) writer — no new abstraction
layer, no dispatcher:

```python
def write_protein_phenotype_report(
    export: dict, taxid: int, sciname: str, output_dir: Path | None = None
) -> Path:
    """Extract protein phenotype data for `sciname` and write it to a
    timestamped Excel file. Returns the file's path."""

def write_effector_report(
    export: dict, taxid: int, sciname: str, output_dir: Path | None = None
) -> Path:
    """Extract effector protein data for `sciname` and write it to a
    timestamped Excel file. Returns the file's path."""

def write_dataset_summary_report(
    export: dict, output_dir: Path | None = None
) -> Path:
    """Compute dataset-wide summary statistics and write them to a
    timestamped CSV file. Returns the file's path."""
```

- `output_dir` defaults to `phiexplorer.paths.output_dir()` (already exists, unused until now)
  when not given — the same gitignored `output/` folder the original scripts wrote to.
- Filenames generalize the original scripts' `{organism}_{report_type}_{timestamp}` convention
  to any organism (not just F. graminearum): `{organism_slug}_protein_phenotypes_{timestamp}.xlsx`,
  `{organism_slug}_effectors_{timestamp}.xlsx`, `dataset_summary_{timestamp}.csv`. `organism_slug`
  lowercases the scientific name and replaces spaces with underscores (e.g. "Fusarium graminearum"
  → "fusarium_graminearum"). Timestamp format matches the existing convention already used
  elsewhere in the codebase (`smoke.py` benchmarks, the original scripts): `%Y-%m-%d_%H-%M`.
- The dataset-summary CSV writer is `df.to_csv(path)` directly — no new CSV-writing helper module.
  `dataset_summary()`'s DataFrame already has a named index (`Feature`, via
  `.rename_axis('Feature')`), so the default `to_csv` behavior (`index=True`) reproduces the
  original script's output shape exactly.

### Dependency direction (why this belongs in `reports/`, not `extract/`)

`phiexplorer/reports/generate.py` imports from `phiexplorer.extract.phenotypes`,
`phiexplorer.extract.effectors`, `phiexplorer.reports.stats`, and `phiexplorer.reports.excel`.
`extract/` imports nothing from `reports/` — the dependency is one-way, `reports/` → `extract/`,
exactly as the original spec intended. Putting the writer functions inside `extract/phenotypes.py`
or `extract/effectors.py` instead would invert this (extract/ depending on reports/excel.py),
which is why that alternative was rejected during brainstorming.

## 4. Testing

New test file `tests/reports/test_generate.py`, using the existing fixture
(`tests/fixtures/sample_export.json`) and `tmp_path` for `output_dir` (avoiding writing into the
real `output/` folder during tests):

- `write_protein_phenotype_report`: call with the fixture's `Testus pathogenicus`/90000, assert
  the returned path exists, reopen it with `openpyxl` and confirm the sheet/columns match what
  `extract_protein_phenotypes()` itself produces for the same input.
- `write_effector_report`: same pattern for `extract_effector_proteins()`.
- `write_dataset_summary_report`: call with the fixture export, assert the returned CSV path
  exists, read it back with `pandas.read_csv` and confirm it matches `dataset_summary()`'s own
  output for the same input.
- A filename-format test confirming the organism-slug and extension are correct (without pinning
  the timestamp, since that's inherently non-deterministic).

## 5. Out of scope

- Any CLI/script entry point (deferred, per §2).
- A report-writer for `organism_summary()` (per §2).
- Changes to any existing public function in `dereference/`, `extract/`, or `reports/stats.py`/
  `reports/excel.py` — this is purely additive.
- Report formats beyond Excel/CSV (e.g. JSON, HTML).
