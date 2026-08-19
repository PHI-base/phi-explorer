"""Filesystem paths for phiexplorer. Never hardcode /mnt/z/... elsewhere -
resolve everything through these functions instead.
"""
from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """The phi-explorer repo root (parent of the phiexplorer/ package)."""
    return Path(__file__).resolve().parent.parent


def data_root() -> Path:
    """Root of the external data folder.

    Defaults to a sibling `phi-explorer-data/` folder next to the repo;
    override with the PHI_DATA_ROOT environment variable.
    """
    override = os.environ.get("PHI_DATA_ROOT")
    if override:
        return Path(override).resolve()
    return (repo_root() / ".." / "phi-explorer-data").resolve()


def input_json_path() -> Path:
    """Path to the PHI-base v5.3 JSON export under data_root()."""
    return data_root() / "input" / "phi-base_v5.3.json"


def output_dir() -> Path:
    """Local, gitignored output/ folder inside the repo, created if missing."""
    d = repo_root() / "output"
    d.mkdir(exist_ok=True)
    return d
