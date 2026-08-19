# phi-explorer Extract Module Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the ~87% code duplication between `phiexplorer/extract/phenotypes.py` and `phiexplorer/extract/effectors.py`'s internal collector functions, without changing either module's public behavior.

**Architecture:** Extract the ~89 identical lines shared by both modules' `_collect_gene_data`/`_build_dataframe` functions into a new internal module, `phiexplorer/extract/_collect.py`, as six small, explicitly-named functions. Both `phenotypes.py` and `effectors.py` keep their own `_collect_gene_data`/`_new_gene_record`/`_build_dataframe` — still readable top-to-bottom — but call into the shared steps instead of repeating them, and each still handles its own divergent extras inline (`allele_synonyms`/`expression_levels` for phenotypes; `gene_annotations` tracking and `go_*` fields for effectors).

**Tech Stack:** Python >=3.11, pandas >=2.2, pytest (unchanged from the existing package).

**Spec:** This plan follows up on `docs/superpowers/plans/2026-08-19-phi-explorer-core-toolkit.md`, addressing deferred finding #4 from that plan's final whole-branch review (already merged to `main`, pushed to `PHI-base/phi-explorer`). No new spec document — the design was approved in-chat (bounded change; see the design discussion preceding this plan).

## Global Constraints

- This is a **pure internal refactor** — `extract_protein_phenotypes(export, taxid, sciname)`, `extract_effector_proteins(export, taxid, sciname)`, and `is_effector(product, annotation_terms)` must keep their exact existing signatures and behavior. Nothing outside `phiexplorer/extract/` may need to change.
- The existing test suites `tests/extract/test_phenotypes.py` and `tests/extract/test_effectors.py` must pass **completely unchanged** — if either needs editing to pass, that's a sign behavior changed and the refactor is wrong.
- `phiexplorer/smoke.py`'s real-data benchmark checks (F. graminearum: 1344 total proteins, phenotype split 32/421/912/15, 22 effectors) already hardcode the expected values — a passing `python3 -m phiexplorer.smoke` run after the refactor is proof of zero regression, no manual comparison needed.
- `PHENOTYPE_COLS` stays defined in `phiexplorer/extract/phenotypes.py` exactly as today; `effectors.py` keeps importing it from there (`from phiexplorer.extract.phenotypes import ... PHENOTYPE_COLS`) — unchanged.
- `INFECTIVE_ABILITY_TERMS` moves into `_collect.py` (it's now only used internally, inside `apply_common_annotation_fields`) — neither `phenotypes.py` nor `effectors.py` need to import it anymore after the refactor.
- No AI co-author or provenance trailer on commit messages (repo owner's standing preference).
- Test command: `python3 -m pytest tests/ -v`, run from the repo root (`/mnt/z/phi-explorer`).

---

### Task 1: `phiexplorer/extract/_collect.py` — shared gene-record collection helpers

**Files:**
- Create: `phiexplorer/extract/_collect.py`
- Test: `tests/extract/test_collect.py`

**Interfaces:**
- Consumes: `phiexplorer.dereference.chain`'s existing functions (`genes_for_organism`, `allele_to_gene_map`, `host_species_for_metagenotype`).
- Produces (used by Tasks 2 and 3):
  - `new_base_gene_record() -> dict`
  - `collect_gene_metadata(session: dict, sciname: str, gene_data: dict[str, dict]) -> None`
  - `collect_allele_fields(session: dict, sciname: str, gene_data: dict[str, dict]) -> dict[str, str]`
  - `collect_host_species(session: dict, metagenotype_to_genes: dict[str, set[str]], taxid_to_name: dict[int, str], gene_data: dict[str, dict]) -> None`
  - `apply_common_annotation_fields(ann: dict, gd: dict) -> None`
  - `sort_by_phenotype_priority(df: pandas.DataFrame, phenotype_cols: list[str]) -> pandas.DataFrame`
  - `INFECTIVE_ABILITY_TERMS: dict[str, str]` (internal constant, used only inside `apply_common_annotation_fields`)

- [ ] **Step 1: Write the failing tests**

```python
# tests/extract/test_collect.py
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pytest

from phiexplorer.dereference import chain
from phiexplorer.extract import _collect

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "sample_export.json"


@pytest.fixture
def export():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def session(export):
    return next(iter(export["curation_sessions"].values()))


def test_new_base_gene_record_has_expected_fields():
    gd = _collect.new_base_gene_record()
    assert gd["uniprot_id"] is None
    assert gd["gene_name"] is None
    assert gd["product"] is None
    assert gd["phig_id"] is None
    for field in [
        "phi4_ids", "high_level_phenotypes", "pathogen_phenotype_terms",
        "host_species", "infected_tissues", "allele_types", "allele_names",
        "allele_descriptions", "pmids",
    ]:
        assert gd[field] == set()


def test_collect_gene_metadata(session):
    gene_data = defaultdict(_collect.new_base_gene_record)
    _collect.collect_gene_metadata(session, "Testus pathogenicus", gene_data)

    assert set(gene_data) == {"Q00001", "Q00002"}
    assert gene_data["Q00001"]["uniprot_id"] == "Q00001"
    assert gene_data["Q00001"]["gene_name"] == "geneA"
    assert gene_data["Q00001"]["product"] == "putative secreted effector protein"
    assert gene_data["Q00002"]["gene_name"] == "geneB"


def test_collect_allele_fields(session):
    gene_data = defaultdict(_collect.new_base_gene_record)
    allele_to_gene = _collect.collect_allele_fields(session, "Testus pathogenicus", gene_data)

    assert allele_to_gene == {
        "Q00001:sess0001-1": "Q00001",
        "Q00002:sess0001-1": "Q00002",
    }
    assert gene_data["Q00001"]["allele_types"] == {"deletion"}
    assert gene_data["Q00001"]["allele_names"] == {"geneAdelta"}
    assert gene_data["Q00001"]["allele_descriptions"] == {"full deletion"}
    assert gene_data["Q00002"]["allele_types"] == {"deletion"}


def test_collect_host_species(session):
    gene_data = defaultdict(_collect.new_base_gene_record)
    allele_to_gene = chain.allele_to_gene_map(session, "Testus pathogenicus")
    genotype_to_genes = chain.genotype_to_genes_map(session, 90000, allele_to_gene)
    metagenotype_to_genes = chain.metagenotype_to_genes_map(session, genotype_to_genes)
    taxid_to_name = chain.taxid_to_name_map(session)

    _collect.collect_host_species(session, metagenotype_to_genes, taxid_to_name, gene_data)

    assert gene_data["Q00001"]["host_species"] == {"Testus hostus"}
    assert gene_data["Q00002"]["host_species"] == {"Testus hostus"}


def test_apply_common_annotation_fields_phenotype_and_tissue(session):
    gd = _collect.new_base_gene_record()
    ann = session["annotations"][0]  # pathogen_host_interaction_phenotype, metagenotype-1
    _collect.apply_common_annotation_fields(ann, gd)

    assert gd["pmids"] == {"PMID:11111111"}
    assert gd["phi4_ids"] == {"PHI:1"}
    assert gd["high_level_phenotypes"] == {"loss of pathogenicity"}
    assert gd["infected_tissues"] == {"leaf"}


def test_apply_common_annotation_fields_pathogen_phenotype_term(session):
    gd = _collect.new_base_gene_record()
    ann = session["annotations"][2]  # pathogen_phenotype, term PHIPO:0000015
    _collect.apply_common_annotation_fields(ann, gd)

    assert gd["pathogen_phenotype_terms"] == {"PHIPO:0000015"}
    assert gd["pmids"] == {"PMID:11111111"}


def test_sort_by_phenotype_priority_orders_by_priority_then_id():
    df = pd.DataFrame([
        {"uniprot_id": "B", "high_level_phenotype": "unaffected pathogenicity"},
        {"uniprot_id": "A", "high_level_phenotype": "loss of pathogenicity"},
        {"uniprot_id": "C", "high_level_phenotype": ""},
    ])
    phenotype_cols = [
        "loss of pathogenicity",
        "reduced virulence",
        "unaffected pathogenicity",
        "increased virulence",
    ]

    sorted_df = _collect.sort_by_phenotype_priority(df, phenotype_cols)

    assert list(sorted_df["uniprot_id"]) == ["A", "B", "C"]


def test_sort_by_phenotype_priority_empty_dataframe_passthrough():
    df = pd.DataFrame(columns=["uniprot_id", "high_level_phenotype"])
    phenotype_cols = ["loss of pathogenicity"]

    result = _collect.sort_by_phenotype_priority(df, phenotype_cols)

    assert result.empty
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/extract/test_collect.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'phiexplorer.extract._collect'`

- [ ] **Step 3: Write the implementation**

```python
# phiexplorer/extract/_collect.py
"""Shared gene-record collection helpers used by extract/phenotypes.py and
extract/effectors.py. Factored out because both modules' collector functions
were ~87% identical - see docs/PORTING-NOTES.md.

Internal module (leading underscore): not part of the public phiexplorer API.
"""
from __future__ import annotations

import pandas as pd

from phiexplorer.dereference import chain

INFECTIVE_ABILITY_TERMS = {
    "PHIPO:0000004": "unaffected pathogenicity",
    "PHIPO:0000010": "loss of pathogenicity",
    "PHIPO:0000014": "increased virulence",
    "PHIPO:0000015": "reduced virulence",
}


def new_base_gene_record() -> dict:
    """Fields common to every extract/ gene record. Callers add their own
    module-specific extra fields via dict assignment after calling this."""
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
        "pmids": set(),
    }


def collect_gene_metadata(session: dict, sciname: str, gene_data: dict[str, dict]) -> None:
    """Populate uniprot_id/gene_name/product/phig_id for genes of `sciname`
    in this session. Mutates `gene_data` in place."""
    genes = chain.genes_for_organism(session, sciname)
    for uid, gene in genes.items():
        gd = gene_data[uid]
        if gd["uniprot_id"] is None:
            gd["uniprot_id"] = uid
            ud = gene.get("uniprot_data", {})
            gd["gene_name"] = ud.get("name")
            gd["product"] = ud.get("product")
            gd["phig_id"] = gene.get("phig_id")


def collect_allele_fields(session: dict, sciname: str, gene_data: dict[str, dict]) -> dict[str, str]:
    """Populate allele_types/allele_names/allele_descriptions for genes of
    `sciname` in this session. Mutates `gene_data` in place. Returns the
    allele_id -> uniprot_id map (chain.allele_to_gene_map's result), which
    callers reuse for their own extra per-allele work (e.g. synonyms,
    expression levels)."""
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
    return allele_to_gene


def collect_host_species(
    session: dict,
    metagenotype_to_genes: dict[str, set[str]],
    taxid_to_name: dict[int, str],
    gene_data: dict[str, dict],
) -> None:
    """Populate host_species for genes covered by each metagenotype in this
    session. Mutates `gene_data` in place."""
    for mg_id, mg in session.get("metagenotypes", {}).items():
        uids = metagenotype_to_genes.get(mg_id)
        if not uids:
            continue
        host_name = chain.host_species_for_metagenotype(session, mg, taxid_to_name)
        if host_name:
            for uid in uids:
                gene_data[uid]["host_species"].add(host_name)


def apply_common_annotation_fields(ann: dict, gd: dict) -> None:
    """Mutate one gene's record for the fields common to phenotype and
    effector extraction, given one annotation already resolved to that gene:
    phi4_ids, pmids, high_level_phenotypes, infected_tissues,
    pathogen_phenotype_terms."""
    pmid = ann.get("publication")
    if pmid:
        gd["pmids"].add(pmid)
    for p4 in ann.get("phi4_id", []):
        gd["phi4_ids"].add(p4)

    ann_type = ann.get("type")
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


def sort_by_phenotype_priority(df: pd.DataFrame, phenotype_cols: list[str]) -> pd.DataFrame:
    """Sort a gene-record DataFrame by phenotype priority (loss of
    pathogenicity first, ..., no-phenotype-recorded last), then by
    uniprot_id. `df` must have a "high_level_phenotype" column. Returns
    `df` unchanged if it's empty."""
    if df.empty:
        return df

    def phenotype_sort_key(hlp_str: str) -> int:
        if not hlp_str:
            return len(phenotype_cols) + 1
        for i, p in enumerate(phenotype_cols):
            if p in hlp_str:
                return i
        return len(phenotype_cols)

    df = df.copy()
    df["_sort"] = df["high_level_phenotype"].map(phenotype_sort_key)
    df = df.sort_values(["_sort", "uniprot_id"]).drop(columns="_sort").reset_index(drop=True)
    return df
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/extract/test_collect.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add phiexplorer/extract/_collect.py tests/extract/test_collect.py
git commit -m "Add shared extract/ gene-record collection helpers"
```

---

### Task 2: Refactor `phiexplorer/extract/phenotypes.py` to consume `_collect.py`

**Files:**
- Modify: `phiexplorer/extract/phenotypes.py` (all of `_new_gene_record`, `_collect_gene_data`, `_build_dataframe`; delete the local `INFECTIVE_ABILITY_TERMS` definition)
- Test: `tests/extract/test_phenotypes.py` (must NOT need any changes — this is the proof the refactor didn't change behavior)

**Interfaces:**
- Consumes: `phiexplorer.extract._collect`'s six functions and `INFECTIVE_ABILITY_TERMS` (Task 1).
- Produces: `extract_protein_phenotypes(export, taxid, sciname) -> DataFrame` — **signature and behavior unchanged** from before this task; `PHENOTYPE_COLS` stays defined here, unchanged (Task 3 still imports it from here).

- [ ] **Step 1: Establish the regression baseline**

Run: `python3 -m pytest tests/extract/test_phenotypes.py -v`
Expected: PASS (2 tests) — record this as the "before" state. These tests are not being modified; they must pass identically after the refactor.

- [ ] **Step 2: Rewrite the file to consume `_collect.py`**

```python
# phiexplorer/extract/phenotypes.py
"""Protein-level phenotype extraction, generalized from James Seager's
fg_protein_phenotypes.py (PHI5-zenodo-datamining) - see docs/PORTING-NOTES.md.
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from phiexplorer.dereference import chain
from phiexplorer.extract import _collect

PHENOTYPE_COLS = [
    "loss of pathogenicity",
    "reduced virulence",
    "unaffected pathogenicity",
    "increased virulence",
]


def _new_gene_record() -> dict:
    gd = _collect.new_base_gene_record()
    gd["allele_synonyms"] = set()
    gd["expression_levels"] = set()
    return gd


def _collect_gene_data(export: dict, taxid: int, sciname: str) -> dict[str, dict]:
    gene_data: dict[str, dict] = defaultdict(_new_gene_record)

    for session in chain.sessions_with_organism(export, sciname):
        _collect.collect_gene_metadata(session, sciname, gene_data)

        allele_to_gene = _collect.collect_allele_fields(session, sciname, gene_data)
        for allele_id, allele in session.get("alleles", {}).items():
            uid = allele_to_gene.get(allele_id)
            if uid is None:
                continue
            for synonym in allele.get("synonyms", []):
                if synonym:
                    gene_data[uid]["allele_synonyms"].add(synonym)

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
        _collect.collect_host_species(session, metagenotype_to_genes, taxid_to_name, gene_data)

        for ann in session.get("annotations", []):
            uids = chain.resolve_annotation_gene_ids(
                ann, metagenotype_to_genes, genotype_to_genes, sciname
            )
            if not uids:
                continue
            for uid in uids:
                _collect.apply_common_annotation_fields(ann, gene_data[uid])

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
    return _collect.sort_by_phenotype_priority(df, PHENOTYPE_COLS)


def extract_protein_phenotypes(export: dict, taxid: int, sciname: str) -> pd.DataFrame:
    """Extract per-protein phenotype data for `sciname` (NCBI taxon `taxid`).

    Generalized from fg_protein_phenotypes.py - see docs/PORTING-NOTES.md.
    """
    gene_data = _collect_gene_data(export, taxid, sciname)
    return _build_dataframe(gene_data)
```

- [ ] **Step 3: Run the existing tests to prove zero regression**

Run: `python3 -m pytest tests/extract/test_phenotypes.py -v`
Expected: PASS (2 tests) — same 2 tests, same names, same pass count as Step 1. If anything about the test file needed to change to make this pass, stop: that means behavior changed and the refactor has a bug.

- [ ] **Step 4: Run the full suite to check nothing else broke**

Run: `python3 -m pytest tests/ -v`
Expected: PASS (all tests, including `tests/extract/test_effectors.py` which imports `PHENOTYPE_COLS` from this file — its import path is unchanged, so it should be unaffected)

- [ ] **Step 5: Commit**

```bash
git add phiexplorer/extract/phenotypes.py
git commit -m "Refactor extract/phenotypes.py to use shared _collect helpers"
```

---

### Task 3: Refactor `phiexplorer/extract/effectors.py` to consume `_collect.py`

**Files:**
- Modify: `phiexplorer/extract/effectors.py` (`_new_gene_record`, `_collect_gene_data`, `_build_dataframe`)
- Test: `tests/extract/test_effectors.py` (must NOT need any changes)

**Interfaces:**
- Consumes: `phiexplorer.extract._collect`'s six functions (Task 1); `PHENOTYPE_COLS` from `phiexplorer.extract.phenotypes` (unchanged import, Task 2).
- Produces: `is_effector(product, annotation_terms) -> tuple[bool, list[str]]` and `extract_effector_proteins(export, taxid, sciname) -> DataFrame` — **signatures and behavior unchanged**.

- [ ] **Step 1: Establish the regression baseline**

Run: `python3 -m pytest tests/extract/test_effectors.py -v`
Expected: PASS (4 tests) — record as the "before" state.

- [ ] **Step 2: Rewrite the collector portion of the file**

Keep `EFFECTOR_KEYWORDS`, `SECRETION_KEYWORDS`, `EFFECTOR_GO_TERMS`, `_GO_FIELD_BY_TYPE`, and `is_effector()` exactly as they are today (untouched — they're effector-specific logic, not part of the shared collection). Replace the import line, `_new_gene_record`, `_collect_gene_data`, and `_build_dataframe`:

```python
# phiexplorer/extract/effectors.py — top of file, replace the import block:
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from phiexplorer.dereference import chain
from phiexplorer.extract import _collect
from phiexplorer.extract.phenotypes import PHENOTYPE_COLS

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
    gd = _collect.new_base_gene_record()
    gd["go_biological_process"] = set()
    gd["go_molecular_function"] = set()
    gd["go_cellular_component"] = set()
    return gd


def _collect_gene_data(export: dict, taxid: int, sciname: str) -> tuple[dict[str, dict], dict[str, list]]:
    gene_data: dict[str, dict] = defaultdict(_new_gene_record)
    gene_annotations: dict[str, list] = defaultdict(list)

    for session in chain.sessions_with_organism(export, sciname):
        _collect.collect_gene_metadata(session, sciname, gene_data)
        allele_to_gene = _collect.collect_allele_fields(session, sciname, gene_data)

        genotype_to_genes = chain.genotype_to_genes_map(session, taxid, allele_to_gene)
        metagenotype_to_genes = chain.metagenotype_to_genes_map(session, genotype_to_genes)
        taxid_to_name = chain.taxid_to_name_map(session)
        _collect.collect_host_species(session, metagenotype_to_genes, taxid_to_name, gene_data)

        for ann in session.get("annotations", []):
            uids = chain.resolve_annotation_gene_ids(
                ann, metagenotype_to_genes, genotype_to_genes, sciname
            )
            if not uids:
                continue

            ann_type = ann.get("type")
            term = ann.get("term")

            for uid in uids:
                gene_annotations[uid].append(ann)
                gd = gene_data[uid]
                _collect.apply_common_annotation_fields(ann, gd)
                if ann_type in _GO_FIELD_BY_TYPE and term:
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
    return _collect.sort_by_phenotype_priority(df, PHENOTYPE_COLS)


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

- [ ] **Step 3: Run the existing tests to prove zero regression**

Run: `python3 -m pytest tests/extract/test_effectors.py -v`
Expected: PASS (4 tests) — same 4 tests, same names, same pass count as Step 1.

- [ ] **Step 4: Run the full suite**

Run: `python3 -m pytest tests/ -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add phiexplorer/extract/effectors.py
git commit -m "Refactor extract/effectors.py to use shared _collect helpers"
```

---

### Task 4: Final regression check and documentation

**Files:**
- Modify: `docs/PORTING-NOTES.md` (addition only — append a new section, don't rewrite existing content)

**Interfaces:**
- Consumes: everything from Tasks 1-3. This task makes no further code changes.

- [ ] **Step 1: Run the full unit test suite**

Run: `python3 -m pytest tests/ -v`
Expected: PASS, same total test count as before this plan started plus the 9 new `test_collect.py` tests (i.e. previous total + 9).

- [ ] **Step 2: Run the real end-to-end benchmark check**

Run: `python3 -m phiexplorer.smoke`
Expected: `Smoke check PASSED`, with F. graminearum proteins found = 1344, all four phenotype counts matching (32/421/912/15), and the effector count matching 22 — identical to the numbers `smoke.py` already asserts. This is the proof the refactor changed zero behavior on the real dataset, not just the fixture.

- [ ] **Step 3: Add a consolidation note to docs/PORTING-NOTES.md**

Append this new section to the end of the existing file (don't remove or rewrite any existing content):

```markdown

## Extract module consolidation (follow-up, 2026-08-19)

The original port (above) left `extract/phenotypes.py` and `extract/effectors.py`'s
internal collector functions ~87% duplicated — flagged as deferred finding #4 in the
original plan's final review, and judged a plan-authoring defect rather than an
implementer defect (the original plan's own reference code contained the duplication).

This was consolidated into `phiexplorer/extract/_collect.py`: six shared functions
(`new_base_gene_record`, `collect_gene_metadata`, `collect_allele_fields`,
`collect_host_species`, `apply_common_annotation_fields`, `sort_by_phenotype_priority`)
factor out the identical traversal/aggregation steps, while each module keeps its own
`_collect_gene_data`/`_build_dataframe` for its divergent extras (`allele_synonyms`/
`expression_levels` for phenotypes; `gene_annotations` tracking and `go_*` fields for
effectors). Public function signatures and behavior are unchanged — verified by the
existing test suites passing without modification, and by `phiexplorer/smoke.py`'s
real-data benchmarks (1344 F. graminearum proteins, 32/421/912/15 phenotype split, 22
effectors) continuing to match exactly.
```

- [ ] **Step 4: Commit**

```bash
git add docs/PORTING-NOTES.md
git commit -m "Document extract module consolidation in PORTING-NOTES"
```
