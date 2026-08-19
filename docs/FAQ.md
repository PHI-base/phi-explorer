# FAQ

Practical answers for using phi-explorer. This is a lookup layer over the canonical docs —
short answers with pointers, not a re-explanation. If you're reading code and something's
still unclear, [docs/DATA-STRUCTURE.md](DATA-STRUCTURE.md) has the full data-shape reference.

## What is phi-explorer, and how is it different from phi-weaver?

phi-explorer *reads* the already-published PHI-base 5 database and extracts/reports on
pathogen-host interaction data. [phi-weaver](https://github.com/PHI-base/phi-weaver) is the
opposite direction: it assists curators in *creating* new PHI-base annotations from
literature. Neither depends on or modifies the other. See [AGENTS.md](../AGENTS.md) §1.

## How do I install it?

```bash
pip install -e ".[dev]"
```

Requires Python ≥3.11. No other setup needed — paths are resolved relative to the repo
(see next question for the one exception: the dataset itself).

## Where does the PHI-base data come from, and how do I point phi-explorer at it?

The 110MB PHI-base v5.3 JSON export lives **outside this repo**, in a sibling
`phi-explorer-data/` folder — it's too big for git and isn't something git should track.
`phiexplorer.paths.input_json_path()` finds it automatically via the `PHI_DATA_ROOT`
environment variable, which defaults to `../phi-explorer-data/`. See
[content-links/data-index.md](../content-links/data-index.md) for exactly where the copy
came from and its provenance.

If you're on a machine that doesn't have `phi-explorer-data/` seeded yet: download the v5.3
release from Zenodo (DOI in `content-links/data-index.md`) or copy it from wherever your team
keeps a mirror, then either place it at the default sibling path or set `PHI_DATA_ROOT` to
wherever you put it.

## How do I extract protein phenotype data for an organism?

```python
import json
from phiexplorer.paths import input_json_path
from phiexplorer.extract.phenotypes import extract_protein_phenotypes

with open(input_json_path(), encoding="utf-8") as f:
    export = json.load(f)

df = extract_protein_phenotypes(export, taxid=5518, sciname="Fusarium graminearum")
```

Returns a pandas DataFrame — one row per protein, with columns for high-level phenotype,
pathogen phenotype terms, host species, infected tissues, allele info, and publications. See
[README.md](../README.md#quick-start) for the minimal version of this example.

## How do I find effector proteins for an organism?

Same shape, different function:

```python
from phiexplorer.extract.effectors import extract_effector_proteins

df = extract_effector_proteins(export, taxid=5518, sciname="Fusarium graminearum")
```

Effector status is decided by keyword matches in the protein's product name (e.g.
"effector", "secreted") plus GO cellular-component/biological-process terms — see
`EFFECTOR_KEYWORDS`/`EFFECTOR_GO_TERMS` in `phiexplorer/extract/effectors.py` for the exact
rules, and `is_effector()` if you want to test a product name against them directly.

## How do I get dataset-wide or per-organism statistics?

```python
from phiexplorer.reports.stats import dataset_summary, organism_summary

dataset_summary(export)                                   # whole-dataset counts (genes, interactions, annotation types, ...)
organism_summary(export, taxid=5518, sciname="Fusarium graminearum")  # {"genes": N, "interactions": N} for one organism
```

`dataset_summary` doesn't take an organism — it's dataset-wide by design.

## How do I generate a report file instead of working with the DataFrame directly?

```python
from phiexplorer.reports.generate import (
    write_protein_phenotype_report,
    write_effector_report,
    write_dataset_summary_report,
)

path = write_protein_phenotype_report(export, taxid=5518, sciname="Fusarium graminearum")
```

Phenotype and effector reports write timestamped Excel files; the dataset summary writes a
timestamped CSV. All three default to writing under `output/` (gitignored — nothing generated
here ever gets committed) and return the path they wrote. See
[README.md](../README.md#generating-report-files) for the other two functions.

## What organism do I use, and how do I find NCBI taxon IDs?

You need both a **scientific name** (exactly as it appears in the PHI-base export, e.g.
`"Fusarium graminearum"`) and its **NCBI taxon ID** as an int (e.g. `5518`). If you don't
already know the taxid for an organism you're interested in, look it up on
[NCBI Taxonomy](https://www.ncbi.nlm.nih.gov/taxonomy) — phi-explorer doesn't do name
resolution for you, it just filters the export by exact match on both.

## Is there a command-line interface?

Not yet — phi-explorer is library-functions-only for now (see the design spec's explicit
deferral in
[docs/superpowers/specs/2026-08-19-phi-explorer-design.md](superpowers/specs/2026-08-19-phi-explorer-design.md)
§6, reaffirmed in the reports-layering follow-up's spec §2). Everything above is meant to be
called from a Python script or notebook.

## How do I verify everything is working?

```bash
python3 -m pytest tests/ -v
```

runs the full test suite against a small synthetic fixture (fast, no real data needed). For an
end-to-end check against the real dataset:

```bash
python3 -m phiexplorer.smoke
```

This validates `extract_protein_phenotypes`/`extract_effector_proteins` against a known
benchmark (F. graminearum: 1,344 proteins, 32/421/912/15 phenotype split, 22 effectors) —
useful after pulling changes, or if you're not sure your `PHI_DATA_ROOT` data is intact.

## Are generated report files committed to git?

No. `output/` is gitignored entirely (covers Excel and CSV alike). Regenerate reports any
time by calling the `write_*_report()` functions again — nothing about them is meant to be
checked in.

## What's the difference between "high-level phenotype" and "pathogen phenotype"?

High-level phenotype (`pathogen_host_interaction_phenotype` annotations) is the coarse
loss-of-pathogenicity / reduced-virulence / unaffected / increased-virulence classification —
the four categories in `PHENOTYPE_COLS`. Pathogen phenotype (`pathogen_phenotype`
annotations) is the finer-grained PHIPO ontology term. Both show up as separate columns in
`extract_protein_phenotypes()`'s output. See
[docs/DATA-STRUCTURE.md](DATA-STRUCTURE.md#key-annotation-types) for the full annotation-type
reference.

## A few gotchas worth knowing before you dig into the raw JSON yourself

- **`session["annotations"]` is a list, not a dict**, despite what the formal schema and the
  original data-structure guide say — see
  [docs/DATA-STRUCTURE.md](DATA-STRUCTURE.md#top-level-structure) for why.
- **Gene keys are `"{scientific name} {uniprot_id}"`** (species name, one space, accession) —
  don't try to split on anything else.
- **Organism taxon IDs are strings in `session["organisms"]` but ints in
  `genotype["organism_taxonid"]`.** `phiexplorer.dereference.chain.taxid_to_name_map()`
  already normalizes this for you if you're calling into `chain.py` directly.
