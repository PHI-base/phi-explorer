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
