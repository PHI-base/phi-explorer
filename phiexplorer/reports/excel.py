"""Shared Excel export helper.

Deduplicated from the export_excel() function that was copy-pasted
identically in James Seager's fg_protein_phenotypes.py and
fg_effector_proteins.py - see docs/PORTING-NOTES.md.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_excel(df: pd.DataFrame, path: Path, sheet_name: str) -> None:
    """Write `df` to `path` as a single-sheet Excel file with auto-sized
    columns and the header row frozen."""
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        ws = writer.sheets[sheet_name]

        for col_cells in ws.columns:
            max_len = max(
                (len(str(cell.value)) if cell.value is not None else 0)
                for cell in col_cells
            )
            ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 2, 50)

        ws.freeze_panes = "A2"
