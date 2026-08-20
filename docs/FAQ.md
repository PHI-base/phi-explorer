# FAQ

Practical answers for using phi-explorer. This is a lookup layer over the canonical docs —
short answers with pointers, not a re-explanation. If you're reading code and something's
still unclear, [docs/DATA-STRUCTURE.md](DATA-STRUCTURE.md) has the full data-shape reference.

## Quick searches from the command line

Just want to look something up, no Python required? These assume you've already installed
phi-explorer and have the PHI-base data in place (see the next two questions if not).

```bash
# Find an organism (fuzzy: grep the list)
python3 -m phiexplorer.cli organisms | grep -i fusarium

# Get everything known about an organism's phenotypes
python3 -m phiexplorer.cli phenotypes --sciname "Fusarium graminearum"

# Find its effector proteins
python3 -m phiexplorer.cli effectors --sciname "Fusarium graminearum"

# Quick gene/interaction counts for one organism
python3 -m phiexplorer.cli organism-summary --sciname "Fusarium graminearum"

# Whole-dataset overview
python3 -m phiexplorer.cli summary
```

See [Is there a command-line interface?](#is-there-a-command-line-interface) below for the
full flag reference (`--taxid`, `--output-dir`, `--input`, error behavior).

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

## What are all these top-level folders, and which ones matter?

phi-explorer is a git repo *and* an Obsidian vault at the same path, so Obsidian's file
explorer shows everything — code, docs, and per-machine config alike. Here's what's actually
there and why:

**The project itself (in git, what you're actually working on):**

| Folder/file | What it is |
|---|---|
| `phiexplorer/` | The installable Python package — `dereference/`, `extract/`, `reports/`, `cli.py`. This *is* the project. |
| `tests/` | The test suite (`python3 -m pytest tests/ -v`). |
| `docs/` | Everything else written about the project — this FAQ, `BACKLOG.md`, `DATA-STRUCTURE.md`, `PORTING-NOTES.md`, session logs, and the `superpowers/` specs/plans from how features here get designed and built. |
| `content-links/` | Pointer notes for data that lives outside the vault (see above) — not the data itself, just where to find it and its provenance. |
| `AGENTS.md` / `CLAUDE.md` | Agent-facing instructions — `AGENTS.md` is the tool-agnostic source of truth, `CLAUDE.md` bridges Claude Code to it. |
| `README.md`, `LICENSE`, `pyproject.toml`, `.gitignore` | Standard project files. |

**Generated, gitignored, safe to delete any time (they regenerate):**

| Folder | What it is |
|---|---|
| `output/` | Timestamped Excel/CSV reports from `write_*_report()` — see [Are generated report files committed to git?](#are-generated-report-files-committed-to-git) below. |
| `__pycache__/` | Python's compiled-bytecode cache, written on every import — see the next question if you want it redirected off the vault entirely. |
| `*.egg-info/` | Build metadata from `pip install -e .`. Only appears if you've run that; empty/missing is normal otherwise. |
| `.pytest_cache/` | Disabled entirely for this repo (see `pyproject.toml`) — you shouldn't see this one at all. |

**Per-machine config, gitignored, not shared or committed by design:**

| Folder | What it is |
|---|---|
| `.obsidian/` | This vault's Obsidian settings (plugins, appearance) — personal to whoever's editing, never synced via git. |
| `.claude/` | Claude Code's local project state for this repo. |
| `.superpowers/` | Scratch workspace for in-progress `superpowers:subagent-driven-development` plan execution (ledgers, task briefs, review packages) — deleted automatically once a plan's final review is clean, so it's usually empty or absent. |
| `.trash/` | **Obsidian's own trash** — where it moves notes you delete from inside the app (not OS-level delete). This one currently is *not* covered by `.gitignore`, which is a real gap worth fixing if you're accumulating deleted notes here; ask if you'd like that added. |

The one thing genuinely *not* visible here: the actual 110MB PHI-base dataset lives one level
up, in a sibling `phi-explorer-data/` folder outside the vault root entirely — Obsidian never
indexes it, which is deliberate (see the data question above).

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

If you're calling the CLI (see below), you only need to know one of the two — `python3 -m
phiexplorer.cli organisms` lists every organism in the loaded export, and any subcommand that
takes `--taxid`/`--sciname` will resolve the other half for you (case-insensitive exact match on
name), erroring clearly if it can't find a match.

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

## Can I keep `__pycache__/` folders out of the repo directory (so they don't clutter Obsidian's file view)?

They're already gitignored, so they're never committed — but they're real files on disk, in
`phiexplorer/__pycache__/`, `tests/__pycache__/`, etc., and this repo is also an Obsidian vault,
so they do show up in the file explorer. If that bothers you, redirect Python's bytecode cache
entirely outside the repo with an environment variable (one-time, per machine, matches how
`PHI_DATA_ROOT` keeps the dataset out of the repo too):

```bash
export PYTHONPYCACHEPREFIX="$HOME/.cache/phiexplorer-pycache"
```

Add that to your shell profile (`.bashrc`/`.zshrc`) and every `.pyc` file lands under
`~/.cache/phiexplorer-pycache/` (mirroring the source tree) instead of next to the source —
nothing else changes. `.pytest_cache/` is handled separately and doesn't need this: the
`[tool.pytest.ini_options]` setting in `pyproject.toml` disables pytest's cache provider
entirely (it also intermittently failed to write on this repo's `/mnt/z` SMB mount), so that
folder is never created at all.

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
