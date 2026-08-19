# phi-explorer Core Toolkit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `phiexplorer` package's core dereferencing/extraction/reporting toolkit, ported and generalized from James Seager's PHI5-zenodo-datamining and PHI5-data-mining-statistics scripts, plus the docs and vault files the spec requires.

**Architecture:** A layered package — `phiexplorer/dereference/chain.py` implements the Gene → Allele → Genotype → Metagenotype → Annotation traversal as small, tested functions parameterized by organism (taxon ID + scientific name, never hardcoded); `phiexplorer/extract/` builds on it to produce per-protein phenotype and effector DataFrames; `phiexplorer/reports/` builds on `extract/` to produce dataset-wide and per-organism summaries plus a shared Excel writer. `phiexplorer/smoke.py` ties it together as an end-to-end check against the real dataset. A synthetic fixture (`tests/fixtures/sample_export.json`) drives all unit tests; the real 110MB dataset (already seeded at `../phi-explorer-data/input/`) is used only for the smoke check.

**Tech Stack:** Python ≥3.11, pandas ≥2.2, openpyxl ≥3.1, pytest (dev only).

**Spec:** `docs/superpowers/specs/2026-08-19-phi-explorer-design.md`

## Global Constraints

- Python ≥3.11; pandas ≥2.2; openpyxl ≥3.1 — same floors as James Seager's source scripts.
- Organism is always a function parameter (`taxid: int`, `sciname: str`) — never a hardcoded constant like the original `FG_TAXID`/`FG_SCINAME`.
- Never hardcode `/mnt/z/...` in package code — use `phiexplorer.paths.repo_root()` / `data_root()`.
- `PHI_DATA_ROOT` env var overrides data location; defaults to `../phi-explorer-data/` relative to the repo.
- The real PHI-base JSON/xlsx is never read by unit tests — only `tests/fixtures/sample_export.json`. It's already gitignored (`.gitignore`: `phi-base_v5*.json`, `*.xlsx`).
- No CLI/query interface in this plan — deferred per spec §6.
- No AI co-author or provenance trailer on commit messages (repo owner's standing preference).
- Test command: `python3 -m pytest tests/ -v`, run from the repo root.

---

### Task 1: Package scaffolding — `phiexplorer.paths`

**Files:**
- Create: `pyproject.toml`
- Create: `phiexplorer/__init__.py`
- Create: `phiexplorer/paths.py`
- Test: `tests/test_paths.py`

**Interfaces:**
- Produces: `phiexplorer.paths.repo_root() -> Path`, `phiexplorer.paths.data_root() -> Path`, `phiexplorer.paths.input_json_path() -> Path`, `phiexplorer.paths.output_dir() -> Path`. Every later task imports paths from here — no task hardcodes a filesystem path itself.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_paths.py
from phiexplorer.paths import data_root, repo_root


def test_repo_root_is_package_parent():
    root = repo_root()
    assert (root / "phiexplorer").is_dir()
    assert (root / "pyproject.toml").is_file()


def test_data_root_default(monkeypatch):
    monkeypatch.delenv("PHI_DATA_ROOT", raising=False)
    root = data_root()
    assert root.name == "phi-explorer-data"
    assert root.parent == repo_root().parent


def test_data_root_override(monkeypatch, tmp_path):
    monkeypatch.setenv("PHI_DATA_ROOT", str(tmp_path))
    assert data_root() == tmp_path.resolve()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_paths.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phiexplorer'`

- [ ] **Step 3: Write pyproject.toml**

```toml
[project]
name = "phiexplorer"
version = "0.1.0"
description = "Datamining toolkit for pathogen-host interaction data in PHI-base 5"
requires-python = ">=3.11"
dependencies = [
    "pandas>=2.2",
    "openpyxl>=3.1",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["phiexplorer*"]
```

- [ ] **Step 4: Write the package init and paths module**

```python
# phiexplorer/__init__.py
```

```python
# phiexplorer/paths.py
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
```

- [ ] **Step 5: Install the package in editable mode**

Run: `pip install -e ".[dev]"`

- [ ] **Step 6: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_paths.py -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml phiexplorer/__init__.py phiexplorer/paths.py tests/test_paths.py
git commit -m "Add phiexplorer package scaffolding and path resolution"
```

---

### Task 2: Test fixture — synthetic PHI-base v5.3 export

**Files:**
- Create: `tests/fixtures/sample_export.json`
- Test: `tests/test_fixtures.py`

**Interfaces:**
- Produces: a fixture file at `tests/fixtures/sample_export.json` with one curation session, pathogen organism "Testus pathogenicus" (taxid 90000, 2 genes Q00001/Q00002), host organism "Testus hostus" (taxid 90001), and 5 annotations. Every later test task loads this file directly (no shared pytest fixture module — each test file opens the JSON itself, matching the pattern below).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fixtures.py
import json
from pathlib import Path

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_export.json"


def test_fixture_loads_and_has_expected_shape():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        export = json.load(f)

    assert export["schema_version"] == 1
    sessions = export["curation_sessions"]
    assert len(sessions) == 1

    session = next(iter(sessions.values()))
    assert len(session["genes"]) == 2
    assert len(session["organisms"]) == 2
    assert len(session["annotations"]) == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_fixtures.py -v`
Expected: FAIL with `FileNotFoundError`

- [ ] **Step 3: Write the fixture**

```json
{
  "schema_version": 1,
  "curation_sessions": {
    "sess0001": {
      "organisms": {
        "90000": {"full_name": "Testus pathogenicus", "role": "pathogen"},
        "90001": {"full_name": "Testus hostus", "role": "host"}
      },
      "genes": {
        "Testus pathogenicus Q00001": {
          "uniquename": "Q00001",
          "organism": "Testus pathogenicus",
          "uniprot_data": {"name": "geneA", "product": "putative secreted effector protein"}
        },
        "Testus pathogenicus Q00002": {
          "uniquename": "Q00002",
          "organism": "Testus pathogenicus",
          "uniprot_data": {"name": "geneB", "product": "hypothetical protein"}
        }
      },
      "alleles": {
        "Q00001:sess0001-1": {
          "gene": "Testus pathogenicus Q00001",
          "name": "geneAdelta",
          "allele_type": "deletion",
          "description": "full deletion",
          "synonyms": ["geneA-KO"]
        },
        "Q00002:sess0001-1": {
          "gene": "Testus pathogenicus Q00002",
          "name": "geneBdelta",
          "allele_type": "deletion"
        }
      },
      "genotypes": {
        "sess0001-genotype-1": {
          "organism_taxonid": 90000,
          "organism_strain": "WT-1",
          "loci": [[{"id": "Q00001:sess0001-1", "expression": "Not assayed"}]]
        },
        "sess0001-genotype-2": {
          "organism_taxonid": 90000,
          "organism_strain": "WT-1",
          "loci": [[{"id": "Q00002:sess0001-1", "expression": "Not assayed"}]]
        },
        "sess0001-genotype-host": {
          "organism_taxonid": 90001,
          "organism_strain": "wild type",
          "loci": []
        }
      },
      "metagenotypes": {
        "sess0001-metagenotype-1": {
          "pathogen_genotype": "sess0001-genotype-1",
          "host_genotype": "sess0001-genotype-host"
        },
        "sess0001-metagenotype-2": {
          "pathogen_genotype": "sess0001-genotype-2",
          "host_genotype": "sess0001-genotype-host"
        }
      },
      "annotations": [
        {
          "type": "pathogen_host_interaction_phenotype",
          "metagenotype": "sess0001-metagenotype-1",
          "publication": "PMID:11111111",
          "phi4_id": ["PHI:1"],
          "extension": [
            {"relation": "infective_ability", "rangeValue": "PHIPO:0000010", "rangeDisplayName": "loss of pathogenicity"},
            {"relation": "infects_tissue", "rangeValue": "BTO:0000713", "rangeDisplayName": "leaf"}
          ]
        },
        {
          "type": "pathogen_host_interaction_phenotype",
          "metagenotype": "sess0001-metagenotype-2",
          "publication": "PMID:11111111",
          "extension": [
            {"relation": "infective_ability", "rangeValue": "PHIPO:0000004", "rangeDisplayName": "unaffected pathogenicity"}
          ]
        },
        {
          "type": "pathogen_phenotype",
          "metagenotype": "sess0001-metagenotype-1",
          "publication": "PMID:11111111",
          "term": "PHIPO:0000015"
        },
        {
          "type": "disease_name",
          "metagenotype": "sess0001-metagenotype-1",
          "publication": "PMID:11111111",
          "term": "PHIDO:0000123"
        },
        {
          "type": "cellular_component",
          "gene": "Testus pathogenicus Q00001",
          "publication": "PMID:11111111",
          "term": "GO:0005576"
        }
      ],
      "metadata": {"curation_pub_id": "PMID:11111111"},
      "publications": {
        "PMID:11111111": {
          "title": "A test paper",
          "pubmed_data": {"year": 2025},
          "journal_abbr": "J. Test",
          "author": "Tester A"
        }
      }
    }
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_fixtures.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/sample_export.json tests/test_fixtures.py
git commit -m "Add synthetic PHI-base v5.3 test fixture"
```

---

### Task 3: `phiexplorer.dereference.chain` — the core dereferencing chain

**Files:**
- Create: `phiexplorer/dereference/__init__.py`
- Create: `phiexplorer/dereference/chain.py`
- Test: `tests/dereference/test_chain.py`

**Interfaces:**
- Consumes: nothing beyond stdlib; reads raw session/export dicts as loaded from `tests/fixtures/sample_export.json` (Task 2) or the real export.
- Produces (used by Tasks 4, 5, 7):
  - `sessions_with_organism(export: dict, sciname: str) -> Iterator[dict]`
  - `genes_for_organism(session: dict, sciname: str) -> dict[str, dict]`
  - `allele_to_gene_map(session: dict, sciname: str) -> dict[str, str]`
  - `genotype_to_genes_map(session: dict, taxid: int, allele_to_gene: dict[str, str]) -> dict[str, set[str]]`
  - `metagenotype_to_genes_map(session: dict, genotype_to_genes: dict[str, set[str]]) -> dict[str, set[str]]`
  - `taxid_to_name_map(session: dict) -> dict[int, str]`
  - `host_species_for_metagenotype(session: dict, metagenotype: dict, taxid_to_name: dict[int, str]) -> str | None`
  - `resolve_annotation_gene_ids(annotation: dict, metagenotype_to_genes: dict[str, set[str]], genotype_to_genes: dict[str, set[str]], sciname: str) -> set[str]`

- [ ] **Step 1: Write the failing tests**

```python
# tests/dereference/test_chain.py
import json
from pathlib import Path

import pytest

from phiexplorer.dereference import chain

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_export.json"


@pytest.fixture
def export():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def session(export):
    return next(iter(export["curation_sessions"].values()))


def test_sessions_with_organism(export):
    sessions = list(chain.sessions_with_organism(export, "Testus pathogenicus"))
    assert len(sessions) == 1

    no_match = list(chain.sessions_with_organism(export, "Nonexistent species"))
    assert no_match == []


def test_genes_for_organism(session):
    genes = chain.genes_for_organism(session, "Testus pathogenicus")
    assert set(genes) == {"Q00001", "Q00002"}


def test_allele_to_gene_map(session):
    mapping = chain.allele_to_gene_map(session, "Testus pathogenicus")
    assert mapping == {
        "Q00001:sess0001-1": "Q00001",
        "Q00002:sess0001-1": "Q00002",
    }


def test_genotype_to_genes_map(session):
    allele_to_gene = chain.allele_to_gene_map(session, "Testus pathogenicus")
    mapping = chain.genotype_to_genes_map(session, 90000, allele_to_gene)
    assert mapping == {
        "sess0001-genotype-1": {"Q00001"},
        "sess0001-genotype-2": {"Q00002"},
    }


def test_metagenotype_to_genes_map(session):
    allele_to_gene = chain.allele_to_gene_map(session, "Testus pathogenicus")
    genotype_to_genes = chain.genotype_to_genes_map(session, 90000, allele_to_gene)
    mapping = chain.metagenotype_to_genes_map(session, genotype_to_genes)
    assert mapping == {
        "sess0001-metagenotype-1": {"Q00001"},
        "sess0001-metagenotype-2": {"Q00002"},
    }


def test_taxid_to_name_map(session):
    assert chain.taxid_to_name_map(session) == {
        90000: "Testus pathogenicus",
        90001: "Testus hostus",
    }


def test_host_species_for_metagenotype(session):
    taxid_to_name = chain.taxid_to_name_map(session)
    mg = session["metagenotypes"]["sess0001-metagenotype-1"]
    assert chain.host_species_for_metagenotype(session, mg, taxid_to_name) == "Testus hostus"


def test_resolve_annotation_gene_ids_metagenotype(session):
    allele_to_gene = chain.allele_to_gene_map(session, "Testus pathogenicus")
    genotype_to_genes = chain.genotype_to_genes_map(session, 90000, allele_to_gene)
    metagenotype_to_genes = chain.metagenotype_to_genes_map(session, genotype_to_genes)

    ann = session["annotations"][0]
    uids = chain.resolve_annotation_gene_ids(
        ann, metagenotype_to_genes, genotype_to_genes, "Testus pathogenicus"
    )
    assert uids == {"Q00001"}


def test_resolve_annotation_gene_ids_gene(session):
    ann = session["annotations"][4]
    uids = chain.resolve_annotation_gene_ids(ann, {}, {}, "Testus pathogenicus")
    assert uids == {"Q00001"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/dereference/test_chain.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phiexplorer.dereference'`

- [ ] **Step 3: Write the implementation**

```python
# phiexplorer/dereference/__init__.py
```

```python
# phiexplorer/dereference/chain.py
"""Gene -> Allele -> Genotype -> Metagenotype -> Annotation dereferencing chain.

Ported and generalized from James Seager's PHI5-zenodo-datamining scripts
(fg_protein_phenotypes.py, fg_effector_proteins.py) - see docs/PORTING-NOTES.md.
Organism is a parameter throughout, not a hardcoded taxon ID/name.
"""
from __future__ import annotations


def sessions_with_organism(export: dict, sciname: str):
    """Yield curation sessions that include `sciname` among their organisms."""
    for session in export.get("curation_sessions", {}).values():
        organisms = session.get("organisms", {})
        if any(org.get("full_name") == sciname for org in organisms.values()):
            yield session


def genes_for_organism(session: dict, sciname: str) -> dict[str, dict]:
    """Return {uniprot_id: gene_dict} for genes of `sciname` in this session."""
    genes = {}
    for gene in session.get("genes", {}).values():
        if gene.get("organism") != sciname:
            continue
        uid = gene.get("uniquename")
        if uid:
            genes[uid] = gene
    return genes


def allele_to_gene_map(session: dict, sciname: str) -> dict[str, str]:
    """Return {allele_id: uniprot_id} for alleles of genes belonging to `sciname`."""
    prefix = f"{sciname} "
    mapping = {}
    for allele_id, allele in session.get("alleles", {}).items():
        gene_key = allele.get("gene", "")
        if not gene_key.startswith(prefix):
            continue
        mapping[allele_id] = gene_key[len(prefix):]
    return mapping


def genotype_to_genes_map(
    session: dict, taxid: int, allele_to_gene: dict[str, str]
) -> dict[str, set[str]]:
    """Return {genotype_id: {uniprot_id, ...}} for genotypes of `taxid`."""
    mapping: dict[str, set[str]] = {}
    for geno_id, geno in session.get("genotypes", {}).items():
        if geno.get("organism_taxonid") != taxid:
            continue
        uids = set()
        for locus in geno.get("loci", []):
            for locus_allele in locus:
                allele_id = locus_allele.get("id")
                if allele_id in allele_to_gene:
                    uids.add(allele_to_gene[allele_id])
        if uids:
            mapping[geno_id] = uids
    return mapping


def metagenotype_to_genes_map(
    session: dict, genotype_to_genes: dict[str, set[str]]
) -> dict[str, set[str]]:
    """Return {metagenotype_id: {uniprot_id, ...}} via pathogen_genotype linkage."""
    mapping = {}
    for mg_id, mg in session.get("metagenotypes", {}).items():
        uids = genotype_to_genes.get(mg.get("pathogen_genotype"), set())
        if uids:
            mapping[mg_id] = uids
    return mapping


def taxid_to_name_map(session: dict) -> dict[int, str]:
    """Return {taxid: full_name} for all organisms in this session."""
    return {
        int(taxid): org["full_name"]
        for taxid, org in session.get("organisms", {}).items()
    }


def host_species_for_metagenotype(
    session: dict, metagenotype: dict, taxid_to_name: dict[int, str]
) -> str | None:
    """Resolve the host organism's full_name for a metagenotype."""
    host_genotype_id = metagenotype.get("host_genotype")
    host_genotype = session.get("genotypes", {}).get(host_genotype_id, {})
    host_taxid = host_genotype.get("organism_taxonid")
    return taxid_to_name.get(host_taxid)


def resolve_annotation_gene_ids(
    annotation: dict,
    metagenotype_to_genes: dict[str, set[str]],
    genotype_to_genes: dict[str, set[str]],
    sciname: str,
) -> set[str]:
    """Resolve which uniprot_ids an annotation applies to."""
    if "metagenotype" in annotation:
        return metagenotype_to_genes.get(annotation["metagenotype"], set())
    if "genotype" in annotation:
        return genotype_to_genes.get(annotation["genotype"], set())
    if "gene" in annotation:
        gene_key = annotation["gene"]
        prefix = f"{sciname} "
        if gene_key.startswith(prefix):
            return {gene_key[len(prefix):]}
    return set()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/dereference/test_chain.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add phiexplorer/dereference/ tests/dereference/
git commit -m "Add organism-agnostic dereferencing chain"
```

---

### Task 4: `phiexplorer.extract.phenotypes`

**Files:**
- Create: `phiexplorer/extract/__init__.py`
- Create: `phiexplorer/extract/phenotypes.py`
- Test: `tests/extract/test_phenotypes.py`

**Interfaces:**
- Consumes: all of `phiexplorer.dereference.chain` from Task 3.
- Produces (used by Task 5): `INFECTIVE_ABILITY_TERMS: dict[str, str]`, `PHENOTYPE_COLS: list[str]`, `extract_protein_phenotypes(export: dict, taxid: int, sciname: str) -> pandas.DataFrame`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/extract/test_phenotypes.py
import json
from pathlib import Path

import pytest

from phiexplorer.extract.phenotypes import extract_protein_phenotypes

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_export.json"


@pytest.fixture
def export():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_extract_protein_phenotypes(export):
    df = extract_protein_phenotypes(export, taxid=90000, sciname="Testus pathogenicus")

    assert len(df) == 2
    assert set(df["uniprot_id"]) == {"Q00001", "Q00002"}

    q1 = df[df["uniprot_id"] == "Q00001"].iloc[0]
    assert q1["high_level_phenotype"] == "loss of pathogenicity"
    assert bool(q1["phenotype: loss of pathogenicity"]) is True
    assert q1["infected_tissues"] == "leaf"
    assert q1["pathogen_phenotype_terms"] == "PHIPO:0000015"
    assert q1["host_species"] == "Testus hostus"
    assert q1["num_publications"] == 1
    assert q1["allele_synonyms"] == "geneA-KO"

    q2 = df[df["uniprot_id"] == "Q00002"].iloc[0]
    assert q2["high_level_phenotype"] == "unaffected pathogenicity"


def test_extract_protein_phenotypes_no_match(export):
    df = extract_protein_phenotypes(export, taxid=1, sciname="Nonexistent species")
    assert df.empty
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/extract/test_phenotypes.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phiexplorer.extract'`

- [ ] **Step 3: Write the implementation**

```python
# phiexplorer/extract/__init__.py
```

```python
# phiexplorer/extract/phenotypes.py
"""Protein-level phenotype extraction, generalized from James Seager's
fg_protein_phenotypes.py (PHI5-zenodo-datamining) - see docs/PORTING-NOTES.md.
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from phiexplorer.dereference import chain

INFECTIVE_ABILITY_TERMS = {
    "PHIPO:0000004": "unaffected pathogenicity",
    "PHIPO:0000010": "loss of pathogenicity",
    "PHIPO:0000014": "increased virulence",
    "PHIPO:0000015": "reduced virulence",
}

PHENOTYPE_COLS = [
    "loss of pathogenicity",
    "reduced virulence",
    "unaffected pathogenicity",
    "increased virulence",
]


def _new_gene_record() -> dict:
    return {
        "uniprot_id": None,
        "gene_name": None,
        "product": None,
        "phig_id": None,
        "phi4_ids": set(),
        "high_level_phenotypes": set(),
        "pathogen_phenotype_terms": set(),
        "host_species": set(),
        "infected_tissues": set(),
        "allele_types": set(),
        "allele_names": set(),
        "allele_descriptions": set(),
        "allele_synonyms": set(),
        "expression_levels": set(),
        "pmids": set(),
    }


def _collect_gene_data(export: dict, taxid: int, sciname: str) -> dict[str, dict]:
    gene_data: dict[str, dict] = defaultdict(_new_gene_record)

    for session in chain.sessions_with_organism(export, sciname):
        genes = chain.genes_for_organism(session, sciname)
        for uid, gene in genes.items():
            gd = gene_data[uid]
            if gd["uniprot_id"] is None:
                gd["uniprot_id"] = uid
                ud = gene.get("uniprot_data", {})
                gd["gene_name"] = ud.get("name")
                gd["product"] = ud.get("product")
                gd["phig_id"] = gene.get("phig_id")

        allele_to_gene = chain.allele_to_gene_map(session, sciname)
        for allele_id, allele in session.get("alleles", {}).items():
            uid = allele_to_gene.get(allele_id)
            if uid is None:
                continue
            gd = gene_data[uid]
            atype = allele.get("allele_type")
            if atype and atype not in ("wild type", "wild_type"):
                gd["allele_types"].add(atype)
            name = allele.get("name")
            if name:
                gd["allele_names"].add(name)
            description = allele.get("description")
            if description:
                gd["allele_descriptions"].add(description)
            for synonym in allele.get("synonyms", []):
                if synonym:
                    gd["allele_synonyms"].add(synonym)

        genotype_to_genes = chain.genotype_to_genes_map(session, taxid, allele_to_gene)
        for geno_id, geno in session.get("genotypes", {}).items():
            uids = genotype_to_genes.get(geno_id)
            if not uids:
                continue
            for locus in geno.get("loci", []):
                for locus_allele in locus:
                    expression = locus_allele.get("expression")
                    if expression and expression != "Not assayed":
                        allele_uid = allele_to_gene.get(locus_allele.get("id"))
                        if allele_uid:
                            gene_data[allele_uid]["expression_levels"].add(expression)

        metagenotype_to_genes = chain.metagenotype_to_genes_map(session, genotype_to_genes)
        taxid_to_name = chain.taxid_to_name_map(session)
        for mg_id, mg in session.get("metagenotypes", {}).items():
            uids = metagenotype_to_genes.get(mg_id)
            if not uids:
                continue
            host_name = chain.host_species_for_metagenotype(session, mg, taxid_to_name)
            if host_name:
                for uid in uids:
                    gene_data[uid]["host_species"].add(host_name)

        for ann in session.get("annotations", []):
            uids = chain.resolve_annotation_gene_ids(
                ann, metagenotype_to_genes, genotype_to_genes, sciname
            )
            if not uids:
                continue

            ann_type = ann.get("type")
            pmid = ann.get("publication")
            phi4_ids = ann.get("phi4_id", [])

            for uid in uids:
                gd = gene_data[uid]
                if pmid:
                    gd["pmids"].add(pmid)
                for p4 in phi4_ids:
                    gd["phi4_ids"].add(p4)

                if ann_type == "pathogen_host_interaction_phenotype":
                    for ext in ann.get("extension", []):
                        if ext.get("relation") == "infective_ability":
                            label = ext.get("rangeDisplayName") or INFECTIVE_ABILITY_TERMS.get(
                                ext.get("rangeValue"), ext.get("rangeValue")
                            )
                            gd["high_level_phenotypes"].add(label)
                        elif ext.get("relation") == "infects_tissue":
                            tissue = ext.get("rangeDisplayName")
                            if tissue:
                                gd["infected_tissues"].add(tissue)
                elif ann_type == "pathogen_phenotype":
                    term = ann.get("term")
                    if term:
                        gd["pathogen_phenotype_terms"].add(term)

    return dict(gene_data)


def _build_dataframe(gene_data: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for gd in gene_data.values():
        if gd["uniprot_id"] is None:
            continue
        hlp = gd["high_level_phenotypes"]
        rows.append({
            "uniprot_id": gd["uniprot_id"],
            "gene_name": gd["gene_name"] or "",
            "product": gd["product"] or "",
            "phig_id": gd["phig_id"] or "",
            "phi4_ids": "; ".join(sorted(gd["phi4_ids"])),
            "high_level_phenotype": "; ".join(sorted(hlp)),
            **{f"phenotype: {p}": p in hlp for p in PHENOTYPE_COLS},
            "pathogen_phenotype_terms": "; ".join(sorted(gd["pathogen_phenotype_terms"])),
            "host_species": "; ".join(sorted(gd["host_species"])),
            "infected_tissues": "; ".join(sorted(gd["infected_tissues"])),
            "allele_types": "; ".join(sorted(gd["allele_types"])),
            "allele_names": "; ".join(sorted(gd["allele_names"])),
            "allele_descriptions": "; ".join(sorted(gd["allele_descriptions"])),
            "allele_synonyms": "; ".join(sorted(gd["allele_synonyms"])),
            "expression_levels": "; ".join(sorted(gd["expression_levels"])),
            "num_publications": len(gd["pmids"]),
            "pmids": "; ".join(sorted(gd["pmids"])),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    def phenotype_sort_key(hlp_str: str) -> int:
        if not hlp_str:
            return len(PHENOTYPE_COLS) + 1
        for i, p in enumerate(PHENOTYPE_COLS):
            if p in hlp_str:
                return i
        return len(PHENOTYPE_COLS)

    df["_sort"] = df["high_level_phenotype"].map(phenotype_sort_key)
    df = df.sort_values(["_sort", "uniprot_id"]).drop(columns="_sort").reset_index(drop=True)
    return df


def extract_protein_phenotypes(export: dict, taxid: int, sciname: str) -> pd.DataFrame:
    """Extract per-protein phenotype data for `sciname` (NCBI taxon `taxid`).

    Generalized from fg_protein_phenotypes.py - see docs/PORTING-NOTES.md.
    """
    gene_data = _collect_gene_data(export, taxid, sciname)
    return _build_dataframe(gene_data)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/extract/test_phenotypes.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add phiexplorer/extract/__init__.py phiexplorer/extract/phenotypes.py tests/extract/test_phenotypes.py
git commit -m "Add organism-agnostic protein phenotype extraction"
```

---

### Task 5: `phiexplorer.extract.effectors`

**Files:**
- Create: `phiexplorer/extract/effectors.py`
- Test: `tests/extract/test_effectors.py`

**Interfaces:**
- Consumes: `phiexplorer.dereference.chain` (Task 3), `INFECTIVE_ABILITY_TERMS` and `PHENOTYPE_COLS` from `phiexplorer.extract.phenotypes` (Task 4).
- Produces (used by Task 8/smoke and future work): `is_effector(product: str, annotation_terms: list[tuple[str, str]]) -> tuple[bool, list[str]]`, `extract_effector_proteins(export: dict, taxid: int, sciname: str) -> pandas.DataFrame`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/extract/test_effectors.py
import json
from pathlib import Path

import pytest

from phiexplorer.extract.effectors import extract_effector_proteins, is_effector

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_export.json"


@pytest.fixture
def export():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_is_effector_by_keyword():
    is_eff, reasons = is_effector("putative secreted effector protein", [])
    assert is_eff
    assert any("effector" in r for r in reasons)
    assert any("secret" in r for r in reasons)


def test_is_effector_by_go_term():
    is_eff, reasons = is_effector("hypothetical protein", [("cellular_component", "GO:0005576")])
    assert is_eff
    assert any("GO:0005576" in r for r in reasons)


def test_is_effector_negative():
    is_eff, reasons = is_effector("hypothetical protein", [])
    assert not is_eff
    assert reasons == []


def test_extract_effector_proteins(export):
    df = extract_effector_proteins(export, taxid=90000, sciname="Testus pathogenicus")

    assert len(df) == 1
    assert df.iloc[0]["uniprot_id"] == "Q00001"
    assert "effector" in df.iloc[0]["effector_evidence"]
    assert df.iloc[0]["go_cellular_component"] == "GO:0005576"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/extract/test_effectors.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phiexplorer.extract.effectors'`

- [ ] **Step 3: Write the implementation**

```python
# phiexplorer/extract/effectors.py
"""Effector protein identification, generalized from James Seager's
fg_effector_proteins.py (PHI5-zenodo-datamining) - see docs/PORTING-NOTES.md.
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from phiexplorer.dereference import chain
from phiexplorer.extract.phenotypes import INFECTIVE_ABILITY_TERMS, PHENOTYPE_COLS

EFFECTOR_KEYWORDS = ["effector", "avirulence", "avr", "virulence factor"]

SECRETION_KEYWORDS = ["secret", "extracellular", "signal peptide", "small secreted"]

EFFECTOR_GO_TERMS = {
    "GO:0005576": "extracellular region",
    "GO:0005615": "extracellular space",
    "GO:0030446": "hyphal cell wall",
    "GO:0009405": "pathogenesis",
    "GO:0052031": "modulation by symbiont of host defense response",
    "GO:0052200": "response to host immune response",
    "GO:0140404": "pathogen-associated molecular pattern",
}

_GO_FIELD_BY_TYPE = {
    "biological_process": "go_biological_process",
    "molecular_function": "go_molecular_function",
    "cellular_component": "go_cellular_component",
}


def is_effector(product: str, annotation_terms: list[tuple[str, str]]) -> tuple[bool, list[str]]:
    """Determine effector status from a product name and (ann_type, term) pairs.

    Returns (is_effector, reasons).
    """
    reasons = []
    product_lower = (product or "").lower()

    for keyword in EFFECTOR_KEYWORDS:
        if keyword in product_lower:
            reasons.append(f"Product contains '{keyword}': {product}")

    for keyword in SECRETION_KEYWORDS:
        if keyword in product_lower:
            reasons.append(f"Secreted protein ('{keyword}'): {product}")

    for ann_type, term in annotation_terms:
        if term in EFFECTOR_GO_TERMS:
            reasons.append(f"GO {ann_type}: {term} ({EFFECTOR_GO_TERMS[term]})")

    return len(reasons) > 0, reasons


def _new_gene_record() -> dict:
    return {
        "uniprot_id": None,
        "gene_name": None,
        "product": None,
        "phig_id": None,
        "phi4_ids": set(),
        "high_level_phenotypes": set(),
        "pathogen_phenotype_terms": set(),
        "host_species": set(),
        "infected_tissues": set(),
        "allele_types": set(),
        "allele_names": set(),
        "allele_descriptions": set(),
        "go_biological_process": set(),
        "go_molecular_function": set(),
        "go_cellular_component": set(),
        "pmids": set(),
    }


def _collect_gene_data(export: dict, taxid: int, sciname: str) -> tuple[dict[str, dict], dict[str, list]]:
    gene_data: dict[str, dict] = defaultdict(_new_gene_record)
    gene_annotations: dict[str, list] = defaultdict(list)

    for session in chain.sessions_with_organism(export, sciname):
        genes = chain.genes_for_organism(session, sciname)
        for uid, gene in genes.items():
            gd = gene_data[uid]
            if gd["uniprot_id"] is None:
                gd["uniprot_id"] = uid
                ud = gene.get("uniprot_data", {})
                gd["gene_name"] = ud.get("name")
                gd["product"] = ud.get("product")
                gd["phig_id"] = gene.get("phig_id")

        allele_to_gene = chain.allele_to_gene_map(session, sciname)
        for allele_id, allele in session.get("alleles", {}).items():
            uid = allele_to_gene.get(allele_id)
            if uid is None:
                continue
            gd = gene_data[uid]
            atype = allele.get("allele_type")
            if atype and atype not in ("wild type", "wild_type"):
                gd["allele_types"].add(atype)
            name = allele.get("name")
            if name:
                gd["allele_names"].add(name)
            description = allele.get("description")
            if description:
                gd["allele_descriptions"].add(description)

        genotype_to_genes = chain.genotype_to_genes_map(session, taxid, allele_to_gene)
        metagenotype_to_genes = chain.metagenotype_to_genes_map(session, genotype_to_genes)
        taxid_to_name = chain.taxid_to_name_map(session)

        for mg_id, mg in session.get("metagenotypes", {}).items():
            uids = metagenotype_to_genes.get(mg_id)
            if not uids:
                continue
            host_name = chain.host_species_for_metagenotype(session, mg, taxid_to_name)
            if host_name:
                for uid in uids:
                    gene_data[uid]["host_species"].add(host_name)

        for ann in session.get("annotations", []):
            uids = chain.resolve_annotation_gene_ids(
                ann, metagenotype_to_genes, genotype_to_genes, sciname
            )
            if not uids:
                continue

            ann_type = ann.get("type")
            pmid = ann.get("publication")
            phi4_ids = ann.get("phi4_id", [])
            term = ann.get("term")

            for uid in uids:
                gene_annotations[uid].append(ann)
                gd = gene_data[uid]
                if pmid:
                    gd["pmids"].add(pmid)
                for p4 in phi4_ids:
                    gd["phi4_ids"].add(p4)

                if ann_type == "pathogen_host_interaction_phenotype":
                    for ext in ann.get("extension", []):
                        if ext.get("relation") == "infective_ability":
                            label = ext.get("rangeDisplayName") or INFECTIVE_ABILITY_TERMS.get(
                                ext.get("rangeValue"), ext.get("rangeValue")
                            )
                            gd["high_level_phenotypes"].add(label)
                        elif ext.get("relation") == "infects_tissue":
                            tissue = ext.get("rangeDisplayName")
                            if tissue:
                                gd["infected_tissues"].add(tissue)
                elif ann_type == "pathogen_phenotype" and term:
                    gd["pathogen_phenotype_terms"].add(term)
                elif ann_type in _GO_FIELD_BY_TYPE and term:
                    gd[_GO_FIELD_BY_TYPE[ann_type]].add(term)

    return dict(gene_data), dict(gene_annotations)


def _build_dataframe(effector_data: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for gd in effector_data.values():
        hlp = gd["high_level_phenotypes"]
        rows.append({
            "uniprot_id": gd["uniprot_id"],
            "gene_name": gd["gene_name"] or "",
            "product": gd["product"] or "",
            "phig_id": gd["phig_id"] or "",
            "effector_evidence": " | ".join(gd["effector_evidence"]),
            "phi4_ids": "; ".join(sorted(gd["phi4_ids"])),
            "high_level_phenotype": "; ".join(sorted(hlp)),
            **{f"phenotype: {p}": p in hlp for p in PHENOTYPE_COLS},
            "pathogen_phenotype_terms": "; ".join(sorted(gd["pathogen_phenotype_terms"])),
            "go_biological_process": "; ".join(sorted(gd["go_biological_process"])),
            "go_molecular_function": "; ".join(sorted(gd["go_molecular_function"])),
            "go_cellular_component": "; ".join(sorted(gd["go_cellular_component"])),
            "host_species": "; ".join(sorted(gd["host_species"])),
            "infected_tissues": "; ".join(sorted(gd["infected_tissues"])),
            "allele_types": "; ".join(sorted(gd["allele_types"])),
            "allele_names": "; ".join(sorted(gd["allele_names"])),
            "allele_descriptions": "; ".join(sorted(gd["allele_descriptions"])),
            "num_publications": len(gd["pmids"]),
            "pmids": "; ".join(sorted(gd["pmids"])),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    def phenotype_sort_key(hlp_str: str) -> int:
        if not hlp_str:
            return len(PHENOTYPE_COLS) + 1
        for i, p in enumerate(PHENOTYPE_COLS):
            if p in hlp_str:
                return i
        return len(PHENOTYPE_COLS)

    df["_sort"] = df["high_level_phenotype"].map(phenotype_sort_key)
    df = df.sort_values(["_sort", "uniprot_id"]).drop(columns="_sort").reset_index(drop=True)
    return df


def extract_effector_proteins(export: dict, taxid: int, sciname: str) -> pd.DataFrame:
    """Extract effector/secreted proteins for `sciname` (NCBI taxon `taxid`).

    Generalized from fg_effector_proteins.py - see docs/PORTING-NOTES.md.
    """
    gene_data, gene_annotations = _collect_gene_data(export, taxid, sciname)

    for uid, gd in gene_data.items():
        annotation_terms = [
            (ann.get("type"), ann.get("term"))
            for ann in gene_annotations.get(uid, [])
            if ann.get("term")
        ]
        is_eff, reasons = is_effector(gd["product"], annotation_terms)
        gd["is_effector"] = is_eff
        gd["effector_evidence"] = reasons

    effector_data = {uid: gd for uid, gd in gene_data.items() if gd.get("is_effector")}
    return _build_dataframe(effector_data)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/extract/test_effectors.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add phiexplorer/extract/effectors.py tests/extract/test_effectors.py
git commit -m "Add organism-agnostic effector protein extraction"
```

---

### Task 6: `phiexplorer.reports.excel` — shared Excel writer

**Files:**
- Create: `phiexplorer/reports/__init__.py`
- Create: `phiexplorer/reports/excel.py`
- Test: `tests/reports/test_excel.py`

**Interfaces:**
- Consumes: nothing beyond pandas/openpyxl.
- Produces (used by Task 7 and any future report script): `write_excel(df: pandas.DataFrame, path: Path, sheet_name: str) -> None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/reports/test_excel.py
from pathlib import Path

import openpyxl
import pandas as pd

from phiexplorer.reports.excel import write_excel


def test_write_excel(tmp_path: Path):
    df = pd.DataFrame({"uniprot_id": ["Q00001", "Q00002"], "gene_name": ["geneA", "geneB"]})
    out_path = tmp_path / "test_output.xlsx"

    write_excel(df, out_path, sheet_name="Proteins")

    assert out_path.exists()
    wb = openpyxl.load_workbook(out_path)
    ws = wb["Proteins"]
    assert ws.freeze_panes == "A2"
    assert ws["A1"].value == "uniprot_id"
    assert ws["A2"].value == "Q00001"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/reports/test_excel.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phiexplorer.reports'`

- [ ] **Step 3: Write the implementation**

```python
# phiexplorer/reports/__init__.py
```

```python
# phiexplorer/reports/excel.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/reports/test_excel.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add phiexplorer/reports/__init__.py phiexplorer/reports/excel.py tests/reports/test_excel.py
git commit -m "Add shared Excel export helper"
```

---

### Task 7: `phiexplorer.reports.stats`

**Files:**
- Create: `phiexplorer/reports/stats.py`
- Test: `tests/reports/test_stats.py`

**Interfaces:**
- Consumes: `phiexplorer.dereference.chain` (Task 3).
- Produces: `dataset_summary(export: dict) -> pandas.DataFrame`, `organism_summary(export: dict, taxid: int, sciname: str) -> dict[str, int]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/reports/test_stats.py
import json
from pathlib import Path

import pytest

from phiexplorer.reports.stats import dataset_summary, organism_summary

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_export.json"


@pytest.fixture
def export():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_dataset_summary(export):
    df = dataset_summary(export)
    counts = df["Count"]

    assert counts["Genes"] == 2
    assert counts["Interactions"] == 2
    assert counts["Interactions (unique)"] == 2
    assert counts["Pathogens"] == 1
    assert counts["Hosts"] == 1
    assert counts["Diseases"] == 1
    assert counts["Publications"] == 1
    assert counts["Pathogen-host interaction phenotype"] == 2
    assert counts["Pathogen phenotype"] == 1
    assert counts["Disease name"] == 1
    assert counts["GO Cellular Component"] == 1
    assert counts["Gene-for-gene phenotype"] == 0


def test_organism_summary(export):
    result = organism_summary(export, 90000, "Testus pathogenicus")
    assert result == {"genes": 2, "interactions": 2}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/reports/test_stats.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phiexplorer.reports.stats'`

- [ ] **Step 3: Write the implementation**

```python
# phiexplorer/reports/stats.py
"""Dataset-wide and per-organism summary statistics, generalized from
James Seager's phibase5_stats.py (PHI5-data-mining-statistics) -
see docs/PORTING-NOTES.md.
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from phiexplorer.dereference import chain


def _metagenotype_key(metagenotype: dict, session: dict) -> tuple:
    def genotype_key(genotype_id):
        genotype = session["genotypes"][genotype_id]
        alleles = tuple(
            locus_allele["id"]
            for locus in genotype["loci"]
            for locus_allele in locus
        )
        return (genotype["organism_taxonid"], genotype["organism_strain"], alleles)

    return (
        genotype_key(metagenotype["pathogen_genotype"]),
        genotype_key(metagenotype["host_genotype"]),
    )


def dataset_summary(export: dict) -> pd.DataFrame:
    """Dataset-wide counts: genes, interactions, pathogens, hosts,
    diseases, publications, and per-annotation-type counts.
    """
    annotation_counts: dict[str, int] = defaultdict(int)
    diseases, genes, publications = set(), set(), set()
    pathogens, hosts = set(), set()
    metagenotypes, metagenotypes_unique = set(), set()

    for session in export.get("curation_sessions", {}).values():
        publications.add(session["metadata"]["curation_pub_id"])

        for annotation in session.get("annotations", []):
            ann_type = annotation["type"]
            annotation_counts[ann_type] += 1
            if ann_type == "disease_name":
                diseases.add(annotation["term"])

        for gene_id in session.get("genes", {}):
            genes.add(gene_id)

        for mg in session.get("metagenotypes", {}).values():
            metagenotypes.add((mg["pathogen_genotype"], mg["host_genotype"]))
            metagenotypes_unique.add(_metagenotype_key(mg, session))

        for taxon_id, organism in session.get("organisms", {}).items():
            if organism["role"] == "pathogen":
                pathogens.add(taxon_id)
            elif organism["role"] == "host":
                hosts.add(taxon_id)

    return pd.DataFrame(
        {
            "Genes": len(genes),
            "Interactions": len(metagenotypes),
            "Interactions (unique)": len(metagenotypes_unique),
            "Pathogens": len(pathogens),
            "Hosts": len(hosts),
            "Diseases": len(diseases),
            "Publications": len(publications),
            "Pathogen-host interaction phenotype": annotation_counts["pathogen_host_interaction_phenotype"],
            "Gene-for-gene phenotype": annotation_counts["gene_for_gene_phenotype"],
            "Pathogen phenotype": annotation_counts["pathogen_phenotype"],
            "Host phenotype": annotation_counts["host_phenotype"],
            "GO Biological Process": annotation_counts["biological_process"],
            "GO Molecular Function": annotation_counts["molecular_function"],
            "GO Cellular Component": annotation_counts["cellular_component"],
            "Disease name": annotation_counts["disease_name"],
            "Physical interaction": annotation_counts["physical_interaction"],
            "Post-translational modification": annotation_counts["post_translational_modification"],
            "Wild-type protein expression": annotation_counts["wt_protein_expression"],
            "Wild-type RNA expression": annotation_counts["wt_rna_expression"],
        },
        index=["Count"],
    ).transpose().rename_axis("Feature")


def organism_summary(export: dict, taxid: int, sciname: str) -> dict[str, int]:
    """Gene and unique-interaction counts for a single organism."""
    gene_count = 0
    interactions: set = set()

    for session in chain.sessions_with_organism(export, sciname):
        for gene in session.get("genes", {}).values():
            if gene.get("organism") == sciname:
                gene_count += 1

        for mg in session.get("metagenotypes", {}).values():
            pathogen_genotype = session["genotypes"][mg["pathogen_genotype"]]
            if pathogen_genotype["organism_taxonid"] != taxid:
                continue
            interactions.add(_metagenotype_key(mg, session))

    return {"genes": gene_count, "interactions": len(interactions)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/reports/test_stats.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add phiexplorer/reports/stats.py tests/reports/test_stats.py
git commit -m "Add dataset-wide and per-organism summary statistics"
```

---

### Task 8: `phiexplorer.smoke` — end-to-end F. graminearum benchmark check

**Files:**
- Create: `phiexplorer/smoke.py`
- Test: `tests/test_smoke.py`

**Interfaces:**
- Consumes: `phiexplorer.paths.repo_root()`, `input_json_path()` (Task 1); `phiexplorer.extract.phenotypes.extract_protein_phenotypes()` (Task 4).
- Produces: `run_unit_tests() -> bool`, `run_benchmark_check() -> bool`. Runnable as `python3 -m phiexplorer.smoke`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_smoke.py
from phiexplorer.smoke import run_benchmark_check


def test_run_benchmark_check_skips_when_data_absent(monkeypatch, tmp_path):
    monkeypatch.setenv("PHI_DATA_ROOT", str(tmp_path))
    assert run_benchmark_check() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_smoke.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phiexplorer.smoke'`

- [ ] **Step 3: Write the implementation**

```python
# phiexplorer/smoke.py
"""Smoke check: unit test suite + F. graminearum benchmark validation
against the real PHI-base v5.3 dataset (if available).

Run with: python3 -m phiexplorer.smoke
"""
from __future__ import annotations

import json
import subprocess
import sys

from phiexplorer.paths import input_json_path, repo_root

FG_TAXID = 5518
FG_SCINAME = "Fusarium graminearum"

EXPECTED_TOTAL = 1344
EXPECTED_PHENOTYPES = {
    "loss of pathogenicity": 32,
    "reduced virulence": 421,
    "unaffected pathogenicity": 912,
    "increased virulence": 15,
}


def run_unit_tests() -> bool:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        cwd=repo_root(),
    )
    return result.returncode == 0


def run_benchmark_check() -> bool:
    from phiexplorer.extract.phenotypes import extract_protein_phenotypes

    path = input_json_path()
    if not path.exists():
        print(f"Skipping benchmark check: {path} not found (set PHI_DATA_ROOT)")
        return True

    print(f"Loading {path} ...")
    with open(path, encoding="utf-8") as f:
        export = json.load(f)

    df = extract_protein_phenotypes(export, taxid=FG_TAXID, sciname=FG_SCINAME)

    print(f"F. graminearum proteins found: {len(df)} (expected {EXPECTED_TOTAL})")
    ok = len(df) == EXPECTED_TOTAL

    for label, expected in EXPECTED_PHENOTYPES.items():
        col = f"phenotype: {label}"
        actual = int(df[col].sum()) if col in df.columns else 0
        match = actual == expected
        ok = ok and match
        print(f"  {label}: {actual} (expected {expected}) {'OK' if match else 'MISMATCH'}")

    return ok


if __name__ == "__main__":
    print("Running unit tests...")
    tests_ok = run_unit_tests()
    print("\nRunning F. graminearum benchmark check...")
    benchmark_ok = run_benchmark_check()

    if tests_ok and benchmark_ok:
        print("\nSmoke check PASSED")
        sys.exit(0)
    else:
        print("\nSmoke check FAILED")
        sys.exit(1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_smoke.py -v`
Expected: PASS

- [ ] **Step 5: Run the real end-to-end benchmark check**

The sibling data folder is already seeded (`../phi-explorer-data/input/phi-base_v5.3.json`), so this runs against the real dataset:

Run: `python3 -m phiexplorer.smoke`
Expected: `Smoke check PASSED`, with F. graminearum proteins found = 1344 and all four phenotype counts matching (32/421/912/15).

- [ ] **Step 6: Commit**

```bash
git add phiexplorer/smoke.py tests/test_smoke.py
git commit -m "Add end-to-end F. graminearum benchmark smoke check"
```

---

### Task 9: Documentation — `docs/DATA-STRUCTURE.md` and `docs/PORTING-NOTES.md`

**Files:**
- Create: `docs/DATA-STRUCTURE.md`
- Create: `docs/PORTING-NOTES.md`

**Interfaces:**
- Consumes: function names/signatures from Tasks 3–8 (must match exactly — this is prose, not code, so there's no automated test; verification is a manual read-through).

- [ ] **Step 1: Write docs/DATA-STRUCTURE.md**

```markdown
# PHI-base v5.3 JSON Data Structure

Practical reference for `phiexplorer/dereference/chain.py`. For the formal schema,
see `phi-base.schema.json` in the data folder (see
[content-links/data-index.md](../content-links/data-index.md)).

Ported and updated from James Seager's `DATA_STRUCTURE_GUIDE.md`
(`PHI5-zenodo-datamining`) — see [PORTING-NOTES.md](PORTING-NOTES.md).

## Top-level structure

```json
{
  "curation_sessions": { "...": "..." },
  "schema_version": 1
}
```

`publications` is **not** top-level in v5.3 — it's nested under each session
(`session["publications"]`), keyed by PMID.

## Curation session structure

Each session (hex key, e.g. `"ae5f4ed044163d0c"`) contains:

```json
{
  "genes": {},
  "alleles": {},
  "genotypes": {},
  "metagenotypes": {},
  "annotations": [],
  "organisms": {},
  "metadata": {},
  "publications": {}
}
```

**Gotcha:** the formal schema documents `annotations` as an object keyed by
annotation ID, but the actual v5.3 export — and every validated script that reads
it — treats it as a **list** of annotation objects. `phiexplorer` follows the
validated (list) behaviour.

## The dereferencing chain

```
Gene -> Allele -> Genotype -> Metagenotype -> Annotation
```

Implemented in `phiexplorer/dereference/chain.py`:

| Step | Function | Returns |
|---|---|---|
| Sessions containing an organism | `sessions_with_organism(export, sciname)` | iterator of session dicts |
| Genes for an organism | `genes_for_organism(session, sciname)` | `{uniprot_id: gene_dict}` |
| Allele -> gene | `allele_to_gene_map(session, sciname)` | `{allele_id: uniprot_id}` |
| Genotype -> genes | `genotype_to_genes_map(session, taxid, allele_to_gene)` | `{genotype_id: {uniprot_id, ...}}` |
| Metagenotype -> genes | `metagenotype_to_genes_map(session, genotype_to_genes)` | `{metagenotype_id: {uniprot_id, ...}}` |
| Annotation -> genes | `resolve_annotation_gene_ids(annotation, metagenotype_to_genes, genotype_to_genes, sciname)` | `{uniprot_id, ...}` |
| Taxon ID -> name | `taxid_to_name_map(session)` | `{taxid: full_name}` |
| Metagenotype -> host | `host_species_for_metagenotype(session, metagenotype, taxid_to_name)` | `str or None` |

An allele reference inside `genotype["loci"][n][m]` carries `id` (references
`alleles`) and `expression` (expression level — this lives on the locus reference,
not the allele object itself).

## Key annotation types

For pathogen-host interaction analysis:

| Type | Purpose |
|---|---|
| `pathogen_host_interaction_phenotype` | High-level phenotype via the `infective_ability` extension |
| `pathogen_phenotype` | PHIPO ontology terms |
| `disease_name` | Disease classifications |
| `biological_process` / `molecular_function` / `cellular_component` | GO terms |

### High-level phenotype extraction

Look for `extension` entries where `relation == "infective_ability"`
(`phiexplorer.extract.phenotypes.INFECTIVE_ABILITY_TERMS`):

```python
{
    "PHIPO:0000004": "unaffected pathogenicity",
    "PHIPO:0000010": "loss of pathogenicity",
    "PHIPO:0000014": "increased virulence",
    "PHIPO:0000015": "reduced virulence",
}
```

### Host and tissue extraction

`infects_organism` and `infects_tissue` extension relations carry `rangeValue`
(ontology ID) and `rangeDisplayName` (label).

## Organism filtering gotchas

- Organism keys in `session["organisms"]` are **strings**; `genotype["organism_taxonid"]`
  is an **int**. `taxid_to_name_map()` normalizes both to int.
- Gene keys are `"{sciname} {uniprot_id}"` (species name, a single space, then the
  UniProt accession) — `allele_to_gene_map()` strips this prefix.

## Undocumented fields

- `alleles[*].description` — mutation details (e.g. `"R699C"`), present on some
  allele types but not in the formal schema.

## Performance notes

- Pre-filter sessions by organism early (`sessions_with_organism`) rather than
  scanning every session's full content.
- The full v5.3 export is 110MB — load it once per process, not per function call.
```

- [ ] **Step 2: Write docs/PORTING-NOTES.md**

```markdown
# Porting Notes

phi-explorer's `phiexplorer/dereference/` and `phiexplorer/extract/` modules are
ported and generalized from James Seager's prior analysis work in
`OBS-MU-ResearchLab/02-PROJECTS/ACTIVE/PRO-James-Seager/`, not written from
scratch. This note records what came from where and what changed, per the design
spec (§2).

## Sources

- **`PHI5-zenodo-datamining/fg_protein_phenotypes.py`** -> generalized into
  `phiexplorer/extract/phenotypes.py`. Original was hardcoded to
  `FG_TAXID = 5518` / `FG_SCINAME = "Fusarium graminearum"`; phiexplorer takes
  `taxid` and `sciname` as parameters to `extract_protein_phenotypes()`.
- **`PHI5-zenodo-datamining/fg_effector_proteins.py`** -> generalized into
  `phiexplorer/extract/effectors.py`, same organism-parameterization. The effector
  identification keyword/GO-term lists (`EFFECTOR_KEYWORDS`, `SECRETION_KEYWORDS`,
  `EFFECTOR_GO_TERMS`) are dataset-wide constants in the original, not
  organism-specific, so they're kept as-is.
- **`PHI5-zenodo-datamining/DATA_STRUCTURE_GUIDE.md`** -> ported and updated into
  `docs/DATA-STRUCTURE.md`, with the dereferencing-chain code turned into named,
  tested functions in `phiexplorer/dereference/chain.py` instead of inline
  snippets repeated per script.
- **`PHI5-data-mining-statistics/phibase5_stats.py`** -> generalized into
  `phiexplorer/reports/stats.py`. `get_fusarium_names_and_taxids` /
  `get_fusarium_interactions_and_genes` (Fusarium-specific wrappers) were replaced
  by a single `organism_summary(export, taxid, sciname)` — the underlying
  `get_pathogen_interactions` / `get_pathogen_gene_count` logic was already
  organism-parameterized, so only the Fusarium-only wrapper layer was dropped.

## What was deduplicated

Both `fg_protein_phenotypes.py` and `fg_effector_proteins.py` contained an
**identical, copy-pasted** `export_excel()` function (auto-size columns, freeze
header row) and near-identical session/gene/allele/genotype/metagenotype
extraction boilerplate. phiexplorer factors the shared extraction steps into
`phiexplorer/dereference/chain.py` and the shared Excel export into
`phiexplorer/reports/excel.py`, used by both `extract/phenotypes.py` and
`extract/effectors.py`.

## What was NOT ported

- `PHI5-data-mining-statistics` targets the older PHI-base **v5.0** export
  (`phibase_v5.0_uniprot_pubmed.json`); phi-explorer targets **v5.3** only. The
  v5.0-specific script isn't ported, only its organism-agnostic stats logic.
- `/mnt/z/PHI5` (legacy PHI-base **4** parsing scripts) — predates the v5 schema
  entirely, unrelated to this port.
- A query CLI — deferred (see design spec §6).

## Validation benchmark

`phiexplorer/smoke.py` re-runs `extract_protein_phenotypes()` against the real
v5.3 dataset (via `PHI_DATA_ROOT`) for *Fusarium graminearum* (taxon 5518) and
checks it reproduces the original script's validated output:

| Metric | Expected |
|---|---|
| Total proteins | 1,344 |
| Loss of pathogenicity | 32 |
| Reduced virulence | 421 |
| Unaffected pathogenicity | 912 |
| Increased virulence | 15 |
| Top host | *Triticum aestivum* (wheat) |

## A schema/reality discrepancy worth knowing

The formal `phi-base.schema.json` and the original `DATA_STRUCTURE_GUIDE.md`
describe `session["annotations"]` as an object keyed by annotation ID. The actual
v5.3 export — and both validated source scripts — treat it as a **list**.
`phiexplorer/dereference/chain.py` and the test fixture
(`tests/fixtures/sample_export.json`) follow the validated (list) behaviour, not
the formal schema description.
```

- [ ] **Step 3: Verify cross-references**

Read both files back and confirm every function name mentioned (`sessions_with_organism`, `genes_for_organism`, `allele_to_gene_map`, `genotype_to_genes_map`, `metagenotype_to_genes_map`, `resolve_annotation_gene_ids`, `taxid_to_name_map`, `host_species_for_metagenotype`, `extract_protein_phenotypes`, `organism_summary`) matches the actual signature from Tasks 3, 4, and 7 exactly.

- [ ] **Step 4: Commit**

```bash
git add docs/DATA-STRUCTURE.md docs/PORTING-NOTES.md
git commit -m "Add data structure reference and porting notes"
```

---

### Task 10: `AGENTS.md`, `CLAUDE.md`, `README.md`

**Files:**
- Create: `AGENTS.md`
- Create: `CLAUDE.md`
- Create: `README.md`

**Interfaces:**
- Consumes: everything from Tasks 1–9 (paths, module names, docs, spec) — this is the final assembly task, referencing but not modifying any prior code.

- [ ] **Step 1: Write AGENTS.md**

```markdown
# AGENTS.md — phi-explorer

Main source of truth for all agent instructions in this repository. Tool-agnostic:
Claude Code reads it via `CLAUDE.md`; other tools read it natively.

## 1. Project Overview

phi-explorer is a datamining toolkit for pathogen-host interaction data in the
published **PHI-base 5** database. It is a sibling project to `phi-weaver`, not a
replacement or extension of it: phi-weaver assists curators in *creating* new
PHI-base annotations from literature; phi-explorer *reads* the already-published
database to extract and report on interaction data. Neither project depends on or
modifies the other.

- GitHub: `PHI-base/phi-explorer` (public).
- Engine code is the importable **`phiexplorer/`** package (`dereference/`,
  `extract/`, `reports/`). Run from the repo root, e.g.
  `python3 -m pytest tests/` or `python3 -m phiexplorer.smoke`.
- Input data lives outside the repo, in a sibling `phi-explorer-data/` folder
  (default; overridable via `PHI_DATA_ROOT`). See
  [content-links/data-index.md](content-links/data-index.md) for its provenance, and
  `phiexplorer/paths.py` for how it's resolved.
- Ported from James Seager's PHI5-zenodo-datamining / PHI5-data-mining-statistics
  projects in ResearchLab — see [docs/PORTING-NOTES.md](docs/PORTING-NOTES.md) for
  what was generalized and why.
- Data structure reference: [docs/DATA-STRUCTURE.md](docs/DATA-STRUCTURE.md) — the
  Gene -> Allele -> Genotype -> Metagenotype -> Annotation dereferencing chain used
  throughout `phiexplorer/dereference/chain.py`.
- Design spec: [docs/superpowers/specs/2026-08-19-phi-explorer-design.md](docs/superpowers/specs/2026-08-19-phi-explorer-design.md).

## 2. Mission & Boundaries

- **Read-only analysis of published PHI-base data.** phi-explorer never writes back
  to PHI-base, PHI-Canto, or phi-weaver.
- Surface uncertainty; never present a guess as a fact about the underlying biology.
- Curation-assistance features are out of scope — that's phi-weaver's job.

## 3. Scientific Accuracy Rules

- **Never invent** gene names, phenotype terms, ontology IDs, or organism data. If a
  field is missing from the export, say so rather than filling it in.
- Validate extraction logic against the F. graminearum benchmark in
  `docs/PORTING-NOTES.md` (taxon 5518: 1,344 proteins, 912/421/32/15 phenotype
  split) before trusting results for other organisms.
- Ontology term labels (PHIPO, GO, BTO) in the export are a convenience, not a
  stable identifier — the term ID is authoritative.

## 4. Coding Standards

- Match surrounding code's style; don't reformat unrelated code.
- Engine code lives in `phiexplorer/`; organism is always a parameter (taxon ID +
  scientific name), never hardcoded.
- **Derive paths from `phiexplorer.paths.repo_root()` / `data_root()`**, never
  hardcode `/mnt/z/...` in package code.
- Keep changes small and reviewable; explain non-obvious choices in a brief comment.
- Verify before claiming done: `python3 -m pytest tests/ -v`. For an end-to-end
  check against the real dataset (if `PHI_DATA_ROOT` data is present), run
  `python3 -m phiexplorer.smoke`.

## 5. File Safety Rules

- **Do not delete or overwrite existing files without first showing the proposed
  change.**
- **Never commit** the PHI-base JSON/xlsx exports or anything else under
  `phi-explorer-data/` — they're gitignored and live outside the repo. Tests use
  the fixture at `tests/fixtures/sample_export.json` only.
- Git: on the `z:` Windows mount, `git config` / `git remote set-url` / a fresh
  `git init` can fail on lock-file chmod — edit `.git/config` directly instead, and
  if `git init` leaves `.git/objects` missing, `mkdir -p .git/objects/{pack,info}`
  fixes it.
- **No AI co-author or provenance trailer** on commit messages.

## 6. Reusable Workflows (skills)

None yet — phi-explorer starts lean. Add a `skills/` folder (matching phi-weaver's
convention) only once a workflow is repeated enough to justify one.

## 7. Tool-Specific Settings

- **Claude Code**: `CLAUDE.md` bridges to this file.
- **Other tools**: read this `AGENTS.md` natively.
```

- [ ] **Step 2: Write CLAUDE.md**

```markdown
# CLAUDE.md

This file bridges Claude Code to this repository's agent instructions.

**Read [AGENTS.md](AGENTS.md) first** — it is the tool-agnostic source of truth for
project overview, mission/boundaries, scientific accuracy rules, coding standards,
and file safety rules. Everything below is Claude-Code-specific.

## Claude Code specifics

- Skills (if any are added later) run via the `Skill` tool from `./skills/`.
- This vault is registered in `OBS-BotVault`'s `Cross-Vault-Coordination.md` as
  public-GitHub / hands-off: read-only reference from BotVault, self-governed here.
- At session start, no session-log index exists yet (phi-explorer doesn't use
  phi-weaver's `11-CLAUDE-AI/SESSION-LOGS/` machinery) — rely on `git log` and
  `docs/superpowers/specs/` and `docs/superpowers/plans/` for prior context.
```

- [ ] **Step 3: Write README.md**

```markdown
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
`phiexplorer/extract/`) and reporting (`phiexplorer/reports/`) are implemented and
validated against a F. graminearum benchmark. No query CLI yet (planned).

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

## Where the data lives

The PHI-base v5.3 JSON export isn't in this repo (110MB, and not something git
should carry). See [content-links/data-index.md](content-links/data-index.md) for
where it lives and how `PHI_DATA_ROOT` finds it.

## Documentation

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
```

- [ ] **Step 4: Run the full test suite as a final check**

Run: `python3 -m pytest tests/ -v`
Expected: PASS (all tests from Tasks 1–8)

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md CLAUDE.md README.md
git commit -m "Add AGENTS.md, CLAUDE.md, and README.md"
```
