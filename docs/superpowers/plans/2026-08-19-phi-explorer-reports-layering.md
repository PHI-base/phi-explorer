# phi-explorer Reports/Extract Layering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire `phiexplorer/reports/` to actually consume `phiexplorer/extract/`, closing the reports/extract layering gap the original design spec called for but the core-toolkit plan never built.

**Architecture:** A new module, `phiexplorer/reports/generate.py`, holds three thin orchestration functions — one per report type — each composing an existing `extract/`/`reports/stats.py` function with an existing (or trivial) writer and returning the output file's path. `reports/generate.py` depends on `extract/`; `extract/` depends on nothing in `reports/` — the one-way dependency this plan exists to establish.

**Tech Stack:** Python >=3.11, pandas >=2.2, openpyxl >=3.1 (unchanged from the existing package).

**Spec:** `docs/superpowers/specs/2026-08-19-phi-explorer-reports-layering-design.md`

## Global Constraints

- `phiexplorer/reports/` may import from `phiexplorer/extract/`; `phiexplorer/extract/` must never import from `phiexplorer/reports/` — this one-way dependency is the entire point of this plan.
- No CLI/script entry point in this plan (deferred, per spec §2).
- No report-writer for `organism_summary()` (per spec §2) — the original source script never wrote per-organism stats to a file either.
- Output format per type, matching the original ported scripts: protein phenotype and effector reports → Excel via the existing `write_excel()`; dataset summary → CSV via plain `df.to_csv()` (no new CSV helper).
- Filenames: `{organism_slug}_protein_phenotypes_{timestamp}.xlsx`, `{organism_slug}_effectors_{timestamp}.xlsx`, `dataset_summary_{timestamp}.csv`. `organism_slug` = scientific name lowercased with spaces replaced by underscores. `timestamp` format: `%Y-%m-%d_%H-%M` (matches the convention already used by `phiexplorer/smoke.py` and the original ported scripts).
- `output_dir` parameter defaults to `phiexplorer.paths.output_dir()` when not supplied.
- No AI co-author or provenance trailer on commit messages.
- Test command: `python3 -m pytest tests/ -v`, run from the repo root (`/mnt/z/phi-explorer`).

---

### Task 1: `phiexplorer/reports/generate.py` — report-generation orchestration

**Files:**
- Create: `phiexplorer/reports/generate.py`
- Test: `tests/reports/test_generate.py`
- Modify: `README.md` (add a short "Generating reports" mention to the existing Quick Start section)

**Interfaces:**
- Consumes: `phiexplorer.paths.output_dir()`; `phiexplorer.extract.phenotypes.extract_protein_phenotypes(export, taxid, sciname)`; `phiexplorer.extract.effectors.extract_effector_proteins(export, taxid, sciname)`; `phiexplorer.reports.stats.dataset_summary(export)`; `phiexplorer.reports.excel.write_excel(df, path, sheet_name)`.
- Produces: `write_protein_phenotype_report(export, taxid, sciname, output_dir=None) -> Path`, `write_effector_report(export, taxid, sciname, output_dir=None) -> Path`, `write_dataset_summary_report(export, output_dir=None) -> Path`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/reports/test_generate.py
import json
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from phiexplorer.reports.generate import (
    write_dataset_summary_report,
    write_effector_report,
    write_protein_phenotype_report,
)

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_export.json"


@pytest.fixture
def export():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_write_protein_phenotype_report(export, tmp_path):
    path = write_protein_phenotype_report(export, 90000, "Testus pathogenicus", output_dir=tmp_path)

    assert path.exists()
    assert path.name.startswith("testus_pathogenicus_protein_phenotypes_")
    assert path.suffix == ".xlsx"

    wb = openpyxl.load_workbook(path)
    ws = wb["Protein Phenotypes"]
    assert ws["A1"].value == "uniprot_id"
    assert ws["A2"].value == "Q00001"
    assert ws["A3"].value == "Q00002"


def test_write_effector_report(export, tmp_path):
    path = write_effector_report(export, 90000, "Testus pathogenicus", output_dir=tmp_path)

    assert path.exists()
    assert path.name.startswith("testus_pathogenicus_effectors_")
    assert path.suffix == ".xlsx"

    wb = openpyxl.load_workbook(path)
    ws = wb["Effectors"]
    assert ws["A1"].value == "uniprot_id"
    assert ws["A2"].value == "Q00001"


def test_write_dataset_summary_report(export, tmp_path):
    path = write_dataset_summary_report(export, output_dir=tmp_path)

    assert path.exists()
    assert path.name.startswith("dataset_summary_")
    assert path.suffix == ".csv"

    df = pd.read_csv(path, index_col=0)
    assert df.loc["Genes", "Count"] == 2
    assert df.loc["Pathogens", "Count"] == 1


def test_write_protein_phenotype_report_default_output_dir(export, monkeypatch, tmp_path):
    monkeypatch.setattr("phiexplorer.reports.generate.paths.output_dir", lambda: tmp_path)

    path = write_protein_phenotype_report(export, 90000, "Testus pathogenicus")

    assert path.exists()
    assert path.parent == tmp_path
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/reports/test_generate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phiexplorer.reports.generate'`

- [ ] **Step 3: Write the implementation**

```python
# phiexplorer/reports/generate.py
"""Report-generation orchestration: extract/ and reports/stats.py output,
written to disk. Closes the reports/-consumes-extract/ gap flagged in the
core-toolkit plan's final review - see
docs/superpowers/specs/2026-08-19-phi-explorer-reports-layering-design.md.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from phiexplorer import paths
from phiexplorer.extract.effectors import extract_effector_proteins
from phiexplorer.extract.phenotypes import extract_protein_phenotypes
from phiexplorer.reports.excel import write_excel
from phiexplorer.reports.stats import dataset_summary


def _organism_slug(sciname: str) -> str:
    return sciname.lower().replace(" ", "_")


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M")


def _resolve_output_dir(output_dir: Path | None) -> Path:
    out_dir = output_dir if output_dir is not None else paths.output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def write_protein_phenotype_report(
    export: dict, taxid: int, sciname: str, output_dir: Path | None = None
) -> Path:
    """Extract protein phenotype data for `sciname` and write it to a
    timestamped Excel file under `output_dir` (default:
    phiexplorer.paths.output_dir()). Returns the file's path."""
    df = extract_protein_phenotypes(export, taxid, sciname)
    out_dir = _resolve_output_dir(output_dir)
    path = out_dir / f"{_organism_slug(sciname)}_protein_phenotypes_{_timestamp()}.xlsx"
    write_excel(df, path, sheet_name="Protein Phenotypes")
    return path


def write_effector_report(
    export: dict, taxid: int, sciname: str, output_dir: Path | None = None
) -> Path:
    """Extract effector protein data for `sciname` and write it to a
    timestamped Excel file under `output_dir` (default:
    phiexplorer.paths.output_dir()). Returns the file's path."""
    df = extract_effector_proteins(export, taxid, sciname)
    out_dir = _resolve_output_dir(output_dir)
    path = out_dir / f"{_organism_slug(sciname)}_effectors_{_timestamp()}.xlsx"
    write_excel(df, path, sheet_name="Effectors")
    return path


def write_dataset_summary_report(export: dict, output_dir: Path | None = None) -> Path:
    """Compute dataset-wide summary statistics and write them to a
    timestamped CSV file under `output_dir` (default:
    phiexplorer.paths.output_dir()). Returns the file's path."""
    df = dataset_summary(export)
    out_dir = _resolve_output_dir(output_dir)
    path = out_dir / f"dataset_summary_{_timestamp()}.csv"
    df.to_csv(path)
    return path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/reports/test_generate.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Run the full suite to check nothing else broke**

Run: `python3 -m pytest tests/ -v`
Expected: PASS (all tests, previous total + 4)

- [ ] **Step 6: Manually verify against the real dataset**

The sibling data folder is already seeded (`../phi-explorer-data/input/phi-base_v5.3.json`). From the repo root, run:

```bash
python3 -c "
import json
from phiexplorer.paths import input_json_path
from phiexplorer.reports.generate import (
    write_protein_phenotype_report,
    write_effector_report,
    write_dataset_summary_report,
)

with open(input_json_path(), encoding='utf-8') as f:
    export = json.load(f)

p1 = write_protein_phenotype_report(export, taxid=5518, sciname='Fusarium graminearum')
p2 = write_effector_report(export, taxid=5518, sciname='Fusarium graminearum')
p3 = write_dataset_summary_report(export)

print('phenotype report:', p1)
print('effector report:', p2)
print('dataset summary:', p3)
"
```

Expected: three files created under `output/`, no errors. Open (or `head`/inspect) each to confirm sane content: the phenotype and effector Excel files should have 1344 and 22 data rows respectively (matching the known F. graminearum benchmark), and the dataset summary CSV should show `Genes,10475` among its rows (matching the dataset's published totals). This is a manual sanity check, not a new automated test — the fixture-based tests in Step 4 are the permanent regression coverage.

- [ ] **Step 7: Add a short mention to README.md**

In `README.md`'s existing "Quick start" section, after the current `extract_protein_phenotypes` example, add:

```markdown

### Generating report files

To write extraction results straight to a file instead of working with the DataFrame directly:

```python
from phiexplorer.reports.generate import write_protein_phenotype_report

path = write_protein_phenotype_report(export, taxid=5518, sciname="Fusarium graminearum")
print(f"Wrote {path}")
```

`write_effector_report` and `write_dataset_summary_report` follow the same pattern. Files are
written to `output/` by default (gitignored) with a timestamped filename.
```

- [ ] **Step 8: Commit**

```bash
git add phiexplorer/reports/generate.py tests/reports/test_generate.py README.md
git commit -m "Add report-generation orchestration wiring reports/ to extract/"
```
