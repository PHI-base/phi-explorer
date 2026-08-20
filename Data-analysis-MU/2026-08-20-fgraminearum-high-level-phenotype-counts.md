---
title: Fusarium graminearum — high-level phenotype annotation counts
analyst: Claude (AI assistant), requested by Martin Urban (martin2urban)
date: 2026-08-20
project: phi-explorer
tags: [data-analysis, phenotype, fusarium-graminearum]
---

# Fusarium graminearum — high-level phenotype annotation counts

## Question

How many unique proteins (by UniProt ID) have a high-level phenotype annotation in the
PHI-base v5.3 export, broken down by phenotype category — and how many have none at all?

## Method

- **Organism:** *Fusarium graminearum*, NCBI taxon 5518 (the F. graminearum benchmark
  organism used throughout phi-explorer's validation — see `docs/PORTING-NOTES.md`)
- **Data:** PHI-base v5.3 official Zenodo export (local copy, `PHI_DATA_ROOT`)
- **Code:** `phiexplorer.extract.phenotypes.extract_protein_phenotypes(export, taxid=5518, sciname="Fusarium graminearum")`,
  run interactively against the real dataset (not the test fixture)
- One row per unique UniProt ID; the `high_level_phenotype` column lists every category
  (`; `-joined) a protein was annotated with across all its curated alleles/experiments/
  publications, so a protein annotated with two different outcomes in two different
  experiments counts once per category, not once overall

## Results

| High-level phenotype | Count (UniProt IDs) |
|---|---|
| Unaffected pathogenicity | 912 |
| Reduced virulence | 421 |
| Loss of pathogenicity | 32 |
| Increased virulence | 15 |
| **Total UniProt IDs with high-level annotation** | **1,263** |
| **Total UniProt IDs without high-level annotation** | **81** |

*Fusarium graminearum high-level phenotype counts, PHI-base Zenodo release v5.3, generated 2026-08-20.*

- 1,263 + 81 = 1,344, matching the total curated *F. graminearum* protein count exactly
  (the same benchmark number validated in `docs/PORTING-NOTES.md` /
  `python3 -m phiexplorer.smoke`).
- The four category counts sum to 1,380, not 1,263, because 114 proteins carry more than
  one high-level phenotype (different alleles/experiments/publications giving different
  results for the same protein) — most of those have exactly 2 categories, a few have 3.
- "Without annotation" means the protein has curated allele/gene records in PHI-base but no
  `pathogen_host_interaction_phenotype` annotation at this coarse level — it may still carry
  finer-grained `pathogen_phenotype` (PHIPO ontology) annotations not counted here.

## Reproduce

```python
import json
from phiexplorer.paths import input_json_path
from phiexplorer.extract.phenotypes import extract_protein_phenotypes, PHENOTYPE_COLS

with open(input_json_path(), encoding="utf-8") as f:
    export = json.load(f)

df = extract_protein_phenotypes(export, taxid=5518, sciname="Fusarium graminearum")

for col in [f"phenotype: {p}" for p in PHENOTYPE_COLS]:
    print(col, df[col].sum())

has_annotation = df["high_level_phenotype"] != ""
print("with annotation:", has_annotation.sum())
print("without annotation:", (~has_annotation).sum())
```

## Related

[[2026-08-20-all-organisms-high-level-phenotype-counts]] — same analysis, all 546 organisms in the export
