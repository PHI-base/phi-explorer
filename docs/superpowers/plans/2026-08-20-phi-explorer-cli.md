# phi-explorer Query CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every existing `phiexplorer` library entry point (phenotype/effector extraction, dataset/organism summary, the three report writers) a command-line front door, and solve the organism lookup ergonomics gap `docs/BACKLOG.md` flags — a typo'd taxid/sciname currently silently returns zero rows instead of erroring.

**Architecture:** Two new library functions in `phiexplorer/dereference/chain.py` (`all_organisms`, `resolve_organism`) provide dataset-wide organism lookup/validation, reusable outside the CLI. A new `phiexplorer/cli.py` module is a thin `argparse`-based wrapper: it loads the export once, resolves organism args through `resolve_organism`, and dispatches to the existing `extract/`/`reports/` functions — no new extraction or reporting logic.

**Tech Stack:** Python >=3.11, stdlib `argparse` only (no new runtime dependency). Existing deps: pandas >=2.2, openpyxl >=3.1.

**Spec:** `docs/superpowers/specs/2026-08-20-phi-explorer-cli-design.md`

## Global Constraints

- `phiexplorer/cli.py` is a thin wrapper: no new extraction, resolution, or report-writing logic beyond what `dereference/`, `extract/`, and `reports/` already provide.
- `argparse`, stdlib only — no new runtime dependency.
- `--input PATH` is a **top-level** argument (precedes the subcommand token), default `phiexplorer.paths.input_json_path()`.
- Organism resolution: `resolve_organism(export, taxid=None, sciname=None) -> tuple[int, str]`. Case-insensitive **exact match** only for sciname (no substring/partial matching). Raises `ValueError` on: neither given, taxid not found, sciname not found, or a given taxid+sciname pair that don't refer to the same organism.
- Error handling: `main()` catches `ValueError` and `OSError` around dispatch, prints `error: <message>` to stderr, exits 1. Unexpected exceptions propagate normally (no blanket `except Exception`).
- Report-writing subcommands (`phenotypes`, `effectors`, `summary`) default to `phiexplorer.paths.output_dir()`, overridable with `--output-dir`; behavior otherwise unchanged from `reports/generate.py`'s existing writers.
- `organism-summary` prints `{genes, interactions}` directly — no report file (matches `organism_summary()`'s existing behavior; the ported original never wrote one either).
- Test command: `python3 -m pytest tests/ -v`, run from the repo root (`/mnt/z/phi-explorer`).
- No AI co-author or provenance trailer on commit messages.
- After writing/editing vault markdown (`docs/...`, `README.md`), push it through Obsidian's CLI so it's live immediately: `bash /mnt/z/OBS-BotVault/Claude-Automation/obs-put.sh <path-on-disk> <vault-relative-path> phi-explorer`. Not needed for `.py` files.

---

### Task 1: `chain.all_organisms` and `chain.resolve_organism`

**Files:**
- Modify: `phiexplorer/dereference/chain.py` (append at end of file)
- Test: `tests/dereference/test_chain.py` (append at end of file)

**Interfaces:**
- Consumes: `chain.taxid_to_name_map(session) -> dict[int, str]` (existing, `phiexplorer/dereference/chain.py:73-78`).
- Produces: `chain.all_organisms(export: dict) -> dict[int, str]`; `chain.resolve_organism(export: dict, taxid: int | None = None, sciname: str | None = None) -> tuple[int, str]`. Both consumed by Task 3's `cli.py`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/dereference/test_chain.py` (the file already has `FIXTURE_PATH`, `export`, and `session` fixtures at the top — see existing content):

```python
def test_all_organisms(export):
    assert chain.all_organisms(export) == {
        90000: "Testus pathogenicus",
        90001: "Testus hostus",
    }


def test_resolve_organism_by_taxid(export):
    assert chain.resolve_organism(export, taxid=90000) == (90000, "Testus pathogenicus")


def test_resolve_organism_by_sciname(export):
    result = chain.resolve_organism(export, sciname="Testus pathogenicus")
    assert result == (90000, "Testus pathogenicus")


def test_resolve_organism_by_sciname_case_insensitive(export):
    result = chain.resolve_organism(export, sciname="testus PATHOGENICUS")
    assert result == (90000, "Testus pathogenicus")


def test_resolve_organism_both_given_consistent(export):
    result = chain.resolve_organism(export, taxid=90000, sciname="Testus pathogenicus")
    assert result == (90000, "Testus pathogenicus")


def test_resolve_organism_both_given_mismatched(export):
    with pytest.raises(ValueError, match="not 'Testus hostus'"):
        chain.resolve_organism(export, taxid=90000, sciname="Testus hostus")


def test_resolve_organism_unknown_taxid(export):
    with pytest.raises(ValueError, match="no organism with taxid 1 "):
        chain.resolve_organism(export, taxid=1)


def test_resolve_organism_unknown_sciname(export):
    with pytest.raises(ValueError, match="no organism named"):
        chain.resolve_organism(export, sciname="Nonexistent species")


def test_resolve_organism_neither_given(export):
    with pytest.raises(ValueError, match="must provide"):
        chain.resolve_organism(export)


def test_resolve_organism_ambiguous_sciname():
    """Defensive case: two taxids sharing one display name (shouldn't happen in
    real PHI-base data, but resolve_organism must not silently pick one)."""
    export = {
        "curation_sessions": {
            "sessA": {
                "organisms": {
                    "90000": {"full_name": "Testus pathogenicus", "role": "pathogen"},
                },
            },
            "sessB": {
                "organisms": {
                    "90002": {"full_name": "Testus pathogenicus", "role": "pathogen"},
                },
            },
        },
    }
    with pytest.raises(ValueError, match="matches multiple organisms"):
        chain.resolve_organism(export, sciname="Testus pathogenicus")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/dereference/test_chain.py -v`
Expected: the 9 new tests FAIL with `AttributeError: module 'phiexplorer.dereference.chain' has no attribute 'all_organisms'` (or `'resolve_organism'`).

- [ ] **Step 3: Implement `all_organisms` and `resolve_organism`**

Append to `phiexplorer/dereference/chain.py`, after `resolve_annotation_gene_ids` (the last function in the file):

```python
def all_organisms(export: dict) -> dict[int, str]:
    """Return {taxid: full_name} for every organism across all curation sessions."""
    organisms: dict[int, str] = {}
    for session in export.get("curation_sessions", {}).values():
        organisms.update(taxid_to_name_map(session))
    return organisms


def resolve_organism(
    export: dict, taxid: int | None = None, sciname: str | None = None
) -> tuple[int, str]:
    """Resolve a (taxid, sciname) pair from either half, validated against `export`.

    - Both given: validated against all_organisms(); raises ValueError if they
      don't refer to the same organism.
    - Only one given: the other is looked up. sciname matching is case-insensitive
      exact match. Raises ValueError if not found, or if a sciname matches more
      than one taxid.
    - Neither given: raises ValueError.
    """
    if taxid is None and sciname is None:
        raise ValueError("must provide --taxid, --sciname, or both")

    organisms = all_organisms(export)

    if taxid is not None:
        resolved_name = organisms.get(taxid)
        if resolved_name is None:
            raise ValueError(f"no organism with taxid {taxid} found in the loaded export")
        if sciname is not None and resolved_name.lower() != sciname.lower():
            raise ValueError(
                f"taxid {taxid} is '{resolved_name}' in the loaded export, not '{sciname}'"
            )
        return taxid, resolved_name

    matches = [(t, name) for t, name in organisms.items() if name.lower() == sciname.lower()]
    if not matches:
        raise ValueError(f"no organism named '{sciname}' found in the loaded export")
    if len(matches) > 1:
        candidates = ", ".join(f"{t} ({name})" for t, name in matches)
        raise ValueError(f"'{sciname}' matches multiple organisms: {candidates}")
    return matches[0]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/dereference/test_chain.py -v`
Expected: all tests PASS (the 12 pre-existing plus the 9 new ones).

- [ ] **Step 5: Commit**

```bash
git add phiexplorer/dereference/chain.py tests/dereference/test_chain.py
git commit -m "Add all_organisms/resolve_organism for dataset-wide organism lookup"
```

---

### Task 2: `phiexplorer/cli.py` skeleton — `organisms` and `summary` subcommands

**Files:**
- Create: `phiexplorer/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `phiexplorer.paths.input_json_path()`; `phiexplorer.dereference.chain.all_organisms(export)` (Task 1); `phiexplorer.reports.generate.write_dataset_summary_report(export, output_dir=None) -> Path` (existing, `phiexplorer/reports/generate.py:58-66`).
- Produces: `build_parser() -> argparse.ArgumentParser`; `main(argv: list[str] | None = None) -> int` — the process entry point, extended by Task 3 with three more subcommands.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli.py
from pathlib import Path

from phiexplorer.cli import main

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_export.json"


def test_organisms_lists_all_organisms(capsys):
    exit_code = main(["--input", str(FIXTURE_PATH), "organisms"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "90000\tTestus pathogenicus" in out
    assert "90001\tTestus hostus" in out


def test_summary_writes_report(tmp_path, capsys):
    exit_code = main(
        ["--input", str(FIXTURE_PATH), "summary", "--output-dir", str(tmp_path)]
    )
    assert exit_code == 0
    out_path = Path(capsys.readouterr().out.strip())
    assert out_path.exists()
    assert out_path.parent == tmp_path


def test_bad_input_path_errors_cleanly(capsys):
    exit_code = main(["--input", "/nonexistent/export.json", "organisms"])
    assert exit_code == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phiexplorer.cli'`.

- [ ] **Step 3: Implement the CLI skeleton**

```python
# phiexplorer/cli.py
"""Command-line front door for phiexplorer's extract/reports layers.

Thin argparse wrapper: loads the export once, resolves organism args through
phiexplorer.dereference.chain.resolve_organism, and dispatches to the existing
extract/ and reports/ functions - no new extraction or reporting logic here.
Run via `python3 -m phiexplorer.cli <subcommand> [args]`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from phiexplorer import paths
from phiexplorer.dereference.chain import all_organisms
from phiexplorer.reports.generate import write_dataset_summary_report


def _load_export(input_path: Path) -> dict:
    with open(input_path, encoding="utf-8") as f:
        return json.load(f)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phiexplorer",
        description="Query PHI-base v5.3 export data: phenotypes, effectors, and summaries.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Path to the PHI-base export JSON (default: phiexplorer.paths.input_json_path())",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("organisms", help="List every (taxid, sciname) pair in the loaded export")

    summary_parser = subparsers.add_parser("summary", help="Write a dataset-wide summary report")
    summary_parser.add_argument("--output-dir", type=Path, default=None)

    return parser


def run(args: argparse.Namespace) -> None:
    input_path = args.input if args.input is not None else paths.input_json_path()
    export = _load_export(input_path)

    if args.command == "organisms":
        for taxid, sciname in sorted(all_organisms(export).items(), key=lambda kv: kv[1]):
            print(f"{taxid}\t{sciname}")
        return

    if args.command == "summary":
        path = write_dataset_summary_report(export, args.output_dir)
        print(path)
        return

    raise ValueError(f"unhandled command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        run(args)
    except (ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_cli.py -v`
Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add phiexplorer/cli.py tests/test_cli.py
git commit -m "Add phiexplorer.cli skeleton with organisms and summary subcommands"
```

---

### Task 3: `phenotypes`, `effectors`, `organism-summary` subcommands

**Files:**
- Modify: `phiexplorer/cli.py`
- Test: `tests/test_cli.py` (append)

**Interfaces:**
- Consumes: `chain.resolve_organism(export, taxid=None, sciname=None) -> tuple[int, str]` (Task 1); `reports.generate.write_protein_phenotype_report(export, taxid, sciname, output_dir=None) -> Path` and `write_effector_report(export, taxid, sciname, output_dir=None) -> Path` (existing, `phiexplorer/reports/generate.py:32-55`); `reports.stats.organism_summary(export, taxid, sciname) -> dict[str, int]` (existing, `phiexplorer/reports/stats.py:87-103`).
- Produces: `main()` now handles all 5 subcommands; no new public names beyond Task 2's.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cli.py`:

```python
def test_phenotypes_writes_report_by_taxid(tmp_path, capsys):
    exit_code = main(
        [
            "--input", str(FIXTURE_PATH),
            "phenotypes", "--taxid", "90000", "--output-dir", str(tmp_path),
        ]
    )
    assert exit_code == 0
    out_path = Path(capsys.readouterr().out.strip())
    assert out_path.exists()


def test_phenotypes_writes_report_by_sciname(tmp_path, capsys):
    exit_code = main(
        [
            "--input", str(FIXTURE_PATH),
            "phenotypes", "--sciname", "Testus pathogenicus", "--output-dir", str(tmp_path),
        ]
    )
    assert exit_code == 0
    out_path = Path(capsys.readouterr().out.strip())
    assert out_path.exists()


def test_effectors_writes_report(tmp_path, capsys):
    exit_code = main(
        [
            "--input", str(FIXTURE_PATH),
            "effectors", "--taxid", "90000", "--output-dir", str(tmp_path),
        ]
    )
    assert exit_code == 0
    out_path = Path(capsys.readouterr().out.strip())
    assert out_path.exists()


def test_organism_summary_prints_counts(capsys):
    exit_code = main(["--input", str(FIXTURE_PATH), "organism-summary", "--taxid", "90000"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "genes\t2" in out
    assert "interactions\t2" in out


def test_unresolvable_taxid_errors_cleanly(capsys):
    exit_code = main(["--input", str(FIXTURE_PATH), "phenotypes", "--taxid", "1"])
    assert exit_code == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")


def test_missing_organism_args_errors_cleanly(capsys):
    exit_code = main(["--input", str(FIXTURE_PATH), "phenotypes"])
    assert exit_code == 1
    err = capsys.readouterr().err
    assert "must provide" in err


def test_mismatched_taxid_sciname_errors_cleanly(capsys):
    exit_code = main(
        [
            "--input", str(FIXTURE_PATH),
            "phenotypes", "--taxid", "90000", "--sciname", "Testus hostus",
        ]
    )
    assert exit_code == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_cli.py -v`
Expected: the 7 new tests FAIL — `phenotypes`/`effectors`/`organism-summary` aren't recognized subcommands, so argparse exits with `error: argument command: invalid choice`.

- [ ] **Step 3: Add the three subcommands**

In `phiexplorer/cli.py`, update the two `from phiexplorer...` import lines to add `resolve_organism`
and the three new functions the CLI now calls (`extract_protein_phenotypes`/
`extract_effector_proteins` are NOT imported here — `reports.generate`'s writers already call
them internally, the CLI never calls them directly):

```python
from phiexplorer.dereference.chain import all_organisms, resolve_organism
from phiexplorer.reports.generate import (
    write_dataset_summary_report,
    write_effector_report,
    write_protein_phenotype_report,
)
from phiexplorer.reports.stats import organism_summary
```

Add a small helper above `build_parser()` to avoid repeating the `--taxid`/`--sciname` pair across three subparsers:

```python
def _add_organism_args(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("--taxid", type=int, default=None)
    subparser.add_argument("--sciname", default=None)
```

Inside `build_parser()`, after the `summary_parser` block and before `return parser`, add:

```python
    phenotypes_parser = subparsers.add_parser(
        "phenotypes", help="Write a protein phenotype report for one organism"
    )
    _add_organism_args(phenotypes_parser)
    phenotypes_parser.add_argument("--output-dir", type=Path, default=None)

    effectors_parser = subparsers.add_parser(
        "effectors", help="Write an effector protein report for one organism"
    )
    _add_organism_args(effectors_parser)
    effectors_parser.add_argument("--output-dir", type=Path, default=None)

    organism_summary_parser = subparsers.add_parser(
        "organism-summary", help="Print gene/interaction counts for one organism"
    )
    _add_organism_args(organism_summary_parser)
```

Inside `run()`, replace the final `raise ValueError(f"unhandled command: {args.command}")` line with the three new branches followed by the same fallback raise:

```python
    if args.command == "phenotypes":
        taxid, sciname = resolve_organism(export, args.taxid, args.sciname)
        path = write_protein_phenotype_report(export, taxid, sciname, args.output_dir)
        print(path)
        return

    if args.command == "effectors":
        taxid, sciname = resolve_organism(export, args.taxid, args.sciname)
        path = write_effector_report(export, taxid, sciname, args.output_dir)
        print(path)
        return

    if args.command == "organism-summary":
        taxid, sciname = resolve_organism(export, args.taxid, args.sciname)
        result = organism_summary(export, taxid, sciname)
        print(f"genes\t{result['genes']}")
        print(f"interactions\t{result['interactions']}")
        return

    raise ValueError(f"unhandled command: {args.command}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_cli.py -v`
Expected: all 10 tests PASS.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest tests/ -v`
Expected: all tests PASS (no regressions in `dereference/`, `extract/`, `reports/`).

- [ ] **Step 6: Commit**

```bash
git add phiexplorer/cli.py tests/test_cli.py
git commit -m "Add phenotypes, effectors, and organism-summary CLI subcommands"
```

---

### Task 4: Documentation — `docs/FAQ.md`, `docs/BACKLOG.md`, `README.md`

**Files:**
- Modify: `docs/FAQ.md`
- Modify: `docs/BACKLOG.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: nothing new — documents the CLI built in Tasks 2-3.
- Produces: nothing consumed by later tasks (this is the final task in this plan).

- [ ] **Step 1: Rewrite `docs/FAQ.md`'s CLI entry**

Find this entry (currently reads "Not yet"):

```markdown
## Is there a command-line interface?

Not yet — phi-explorer is library-functions-only for now (see the design spec's explicit
deferral in
[docs/superpowers/specs/2026-08-19-phi-explorer-design.md](superpowers/specs/2026-08-19-phi-explorer-design.md)
§6, reaffirmed in the reports-layering follow-up's spec §2). Everything above is meant to be
called from a Python script or notebook.
```

Replace it with:

````markdown
## Is there a command-line interface?

Yes — `python3 -m phiexplorer.cli`, covering the same operations as the Python API above.
`--input PATH` (before the subcommand) overrides which export JSON is loaded; every
subcommand defaults to `phiexplorer.paths.input_json_path()`.

```bash
# Discover what's in the loaded export
python3 -m phiexplorer.cli organisms

# Write a protein phenotype report (by taxid or sciname)
python3 -m phiexplorer.cli phenotypes --taxid 5518
python3 -m phiexplorer.cli effectors --sciname "Fusarium graminearum"

# Dataset-wide and per-organism summaries
python3 -m phiexplorer.cli summary
python3 -m phiexplorer.cli organism-summary --taxid 5518
```

`phenotypes`/`effectors`/`summary` write timestamped files under `output/` by default
(override with `--output-dir`) and print the path written; `organisms` and
`organism-summary` print directly to stdout. If a `--taxid`/`--sciname` pair doesn't
match anything in the loaded export — a typo, or the wrong export loaded — the CLI exits
1 with a clear `error: ...` message rather than silently producing an empty report. See
[docs/superpowers/specs/2026-08-20-phi-explorer-cli-design.md](superpowers/specs/2026-08-20-phi-explorer-cli-design.md)
for the full design.
````

- [ ] **Step 2: Remove the "Query CLI" section from `docs/BACKLOG.md`**

Delete the entire `## Query CLI` section (from its heading down to, but not including, the
`## Smaller open items` heading) — it's now built, not backlog.

- [ ] **Step 3: Update `README.md`**

In the `## Status` section, replace:

```markdown
Early development. Core extraction (`phiexplorer/dereference/`,
`phiexplorer/extract/`) and reporting (`phiexplorer/reports/`) are implemented.
The phenotype extraction path (`extract/phenotypes.py`) and the effector
extraction path (`extract/effectors.py`) are validated against a F. graminearum
benchmark via `python3 -m phiexplorer.smoke`; `phiexplorer/reports/` is not yet
benchmark-validated. No query CLI yet (planned).
```

with:

```markdown
Early development. Core extraction (`phiexplorer/dereference/`,
`phiexplorer/extract/`), reporting (`phiexplorer/reports/`), and a query CLI
(`phiexplorer/cli.py`) are implemented. The phenotype extraction path
(`extract/phenotypes.py`) and the effector extraction path (`extract/effectors.py`)
are validated against a F. graminearum benchmark via `python3 -m phiexplorer.smoke`;
`phiexplorer/reports/` is not yet benchmark-validated.
```

In the `## Quick start` section, after the existing "Generating report files" subsection,
add:

````markdown
### Using the CLI

The same operations are available from the command line:

```bash
python3 -m phiexplorer.cli phenotypes --taxid 5518
```

See [docs/FAQ.md](docs/FAQ.md#is-there-a-command-line-interface) for the full subcommand
list.
````

- [ ] **Step 4: Verify**

Run: `python3 -m pytest tests/ -v`
Expected: all tests PASS (docs changes don't affect test collection).

Run: `python3 -m phiexplorer.cli --help`
Expected: prints usage listing `organisms`, `phenotypes`, `effectors`, `summary`,
`organism-summary` as available subcommands, exit code 0.

Run: `grep -n "Not yet\|No query CLI yet\|## Query CLI" docs/FAQ.md docs/BACKLOG.md README.md`
Expected: no output (stale deferral language fully removed).

- [ ] **Step 5: Push the doc changes through Obsidian's CLI**

```bash
bash /mnt/z/OBS-BotVault/Claude-Automation/obs-put.sh docs/FAQ.md docs/FAQ.md phi-explorer
bash /mnt/z/OBS-BotVault/Claude-Automation/obs-put.sh docs/BACKLOG.md docs/BACKLOG.md phi-explorer
bash /mnt/z/OBS-BotVault/Claude-Automation/obs-put.sh README.md README.md phi-explorer
```

Expected: each prints `eval: => modified` followed by `verified identical: ...`.

- [ ] **Step 6: Commit**

```bash
git add docs/FAQ.md docs/BACKLOG.md README.md
git commit -m "Document the query CLI; remove it from the backlog"
```
