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

  **A bug fix, not just a port.** The original's `is_effector_protein(gene_data,
  annotations)` read `gene_data.get("uniprot_data", {}).get("product", "")` —
  but the aggregated `gene_data` dict it was called with only ever has a flat
  `"product"` key, never a nested `"uniprot_data"` key. So `product` was always
  the empty string, and the keyword-based rules (matching "effector", "secreted",
  etc. in the product name) never actually fired; only the GO-term-based matches
  ever worked. phiexplorer's `is_effector(product, annotation_terms)` (in
  `phiexplorer/extract/effectors.py`) takes `product` directly as a parameter,
  so the keyword rules now work correctly. On the real dataset, this makes a
  measurable difference for *Fusarium graminearum* (taxid 5518): phiexplorer
  finds **22** effector proteins vs. the original script's committed output of
  **19** — a strict superset; the 3 additional hits (I1RI44, I1RVG3, Q6WER3)
  are correct matches under the stated keyword/GO rules that the original's bug
  prevented it from finding. This is tracked as a benchmark check in
  `phiexplorer/smoke.py` (`EXPECTED_EFFECTOR_COUNT = 22`).
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
`phiexplorer/reports/excel.py`'s `write_excel()`. `write_excel()` exists as
that deduplicated helper, ready for a future report-generation script to call;
it currently has no callers in package code (`extract/phenotypes.py` and
`extract/effectors.py` return DataFrames and don't call it themselves — only
`tests/reports/test_excel.py` exercises it today).

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

`phiexplorer/smoke.py` also re-runs `extract_effector_proteins()` for the same
organism and checks it finds **22** effector proteins (see the bug-fix note
above).

## A schema/reality discrepancy worth knowing

The formal `phi-base.schema.json` and the original `DATA_STRUCTURE_GUIDE.md`
describe `session["annotations"]` as an object keyed by annotation ID. The actual
v5.3 export — and both validated source scripts — treat it as a **list**.
`phiexplorer/dereference/chain.py` and the test fixture
(`tests/fixtures/sample_export.json`) follow the validated (list) behaviour, not
the formal schema description.
