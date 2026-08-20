# phi-explorer

Datamining toolkit for pathogen-host interaction data in the published
**[PHI-base 5](http://phi-base.org/)** database.

phi-explorer is a sibling project to
[phi-weaver](https://github.com/PHI-base/phi-weaver): phi-weaver assists curators in
*creating* new PHI-base annotations from literature; phi-explorer *reads* the
already-published database to extract and report on interaction data. Neither
depends on the other.

## Status

Early development. Core extraction (`phiexplorer/dereference/`,
`phiexplorer/extract/`), reporting (`phiexplorer/reports/`), and a query CLI
(`phiexplorer/cli.py`) are implemented. The phenotype extraction path
(`extract/phenotypes.py`) and the effector extraction path (`extract/effectors.py`)
are validated against a F. graminearum benchmark via `python3 -m phiexplorer.smoke`;
`phiexplorer/reports/` is not yet benchmark-validated.

## Installation

```bash
pip install -e ".[dev]"
```

Requires Python >= 3.11.

## Quick start

```python
import json
from phiexplorer.paths import input_json_path
from phiexplorer.extract.phenotypes import extract_protein_phenotypes

with open(input_json_path(), encoding="utf-8") as f:
    export = json.load(f)

df = extract_protein_phenotypes(export, taxid=5518, sciname="Fusarium graminearum")
print(df.head())
```

### Generating report files

To write extraction results straight to a file instead of working with the DataFrame directly:

```python
from phiexplorer.reports.generate import write_protein_phenotype_report

path = write_protein_phenotype_report(export, taxid=5518, sciname="Fusarium graminearum")
print(f"Wrote {path}")
```

`write_effector_report` and `write_dataset_summary_report` follow the same pattern. Files are
written to `output/` by default (gitignored) with a timestamped filename.

### Using the CLI

The same operations are available from the command line:

```bash
python3 -m phiexplorer.cli phenotypes --taxid 5518
```

See [docs/FAQ.md](docs/FAQ.md#is-there-a-command-line-interface) for the full subcommand
list.

## Where the data lives

The PHI-base v5.3 JSON export isn't in this repo (110MB, and not something git
should carry). See [content-links/data-index.md](content-links/data-index.md) for
where it lives and how `PHI_DATA_ROOT` finds it.

## Documentation

- [docs/FAQ.md](docs/FAQ.md) — practical how-to: installation, data setup, extracting
  data, generating reports, common gotchas
- [docs/BACKLOG.md](docs/BACKLOG.md) — open items not yet scheduled as a plan (parked review
  findings, possible future extraction dimensions)
- [docs/SESSION-LOGS/](docs/SESSION-LOGS/) — one file per work session, for prior context
- [AGENTS.md](AGENTS.md) — project overview, mission, coding standards (the
  canonical agent-facing doc)
- [docs/DATA-STRUCTURE.md](docs/DATA-STRUCTURE.md) — the PHI-base v5.3 JSON
  dereferencing chain
- [docs/PORTING-NOTES.md](docs/PORTING-NOTES.md) — provenance: what this project
  ported from James Seager's prior work, and what was generalized
- [docs/superpowers/specs/](docs/superpowers/specs/) — design specs

## Testing

```bash
python3 -m pytest tests/ -v
```

For an end-to-end check against the real dataset (requires `PHI_DATA_ROOT` data):

```bash
python3 -m phiexplorer.smoke
```

## License

See [LICENSE](LICENSE). Data license terms are separate — see PHI-base's own
[data license](https://creativecommons.org/licenses/by/4.0/) (CC BY 4.0).
