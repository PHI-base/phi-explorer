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
from phiexplorer.dereference.chain import all_organisms, resolve_organism
from phiexplorer.reports.generate import (
    write_dataset_summary_report,
    write_effector_report,
    write_protein_phenotype_report,
)
from phiexplorer.reports.stats import organism_summary


def _load_export(input_path: Path) -> dict:
    with open(input_path, encoding="utf-8") as f:
        return json.load(f)


def _add_organism_args(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("--taxid", type=int, default=None)
    subparser.add_argument("--sciname", default=None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m phiexplorer.cli",
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
