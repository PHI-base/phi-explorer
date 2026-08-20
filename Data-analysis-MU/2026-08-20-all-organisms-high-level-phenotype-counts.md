---
title: All organisms — high-level phenotype annotation counts
analyst: Claude (AI assistant), requested by Martin Urban (martin2urban)
date: 2026-08-20
project: phi-explorer
tags: [data-analysis, phenotype, all-organisms]
---

# All organisms — high-level phenotype annotation counts

## Question

Same as [[2026-08-20-fgraminearum-high-level-phenotype-counts]] but across every
species/organism in the PHI-base v5.3 export, not just *Fusarium graminearum*: how many
unique proteins (by UniProt ID) have a high-level phenotype annotation, broken down by
category, and how many have none at all?

## Method

- **Organisms:** all 546 distinct organisms in the export (`phiexplorer.dereference.chain.all_organisms()`)
  — both pathogen- and host-role entries, no filtering
- **Data:** PHI-base v5.3 official Zenodo export (local copy, `PHI_DATA_ROOT`)
- **Code:** `phiexplorer.extract.phenotypes.extract_protein_phenotypes(export, taxid, sciname)`
  called once per organism (no dataset-wide extraction helper exists yet — see
  `docs/BACKLOG.md`), results concatenated, then grouped by `uniprot_id` (boolean OR across
  the four phenotype columns) so a UniProt ID curated under more than one organism entry is
  counted once, not once per organism
- Run interactively against the real dataset (not the test fixture); loop over all 546
  organisms took ~8s

## Results

| High-level phenotype | Count (UniProt IDs) |
|---|---|
| Reduced virulence | 5,807 |
| Unaffected pathogenicity | 3,467 |
| Increased virulence | 804 |
| Loss of pathogenicity | 750 |
| **Total UniProt IDs with high-level annotation** | **9,210** |
| **Total UniProt IDs without high-level annotation** | **1,196** |

*All species/organisms, high-level phenotype counts, PHI-base Zenodo release v5.3, generated 2026-08-20.*

- 9,210 + 1,196 = 10,406 — the total number of distinct UniProt IDs across the whole dataset.
- Category counts sum to 10,828, not 9,210, for the same reason as the F. graminearum-only
  table: many proteins carry more than one high-level phenotype across different alleles/
  experiments/publications.
- **Data quirk found during this analysis:** 29 UniProt IDs are curated under *two different
  organism entries* each — e.g. the effector `avrB` (P13835) under both *Pseudomonas
  syringae* and *Pseudomonas savastanoi*; `SIX3` (Q2A0P1) under four different fungal genera.
  Looks like shared/ambiguous strain assignment or genuinely cross-referenced orthologs in
  PHI-base's curation, not an extraction bug — confirmed by inspecting the raw duplicate rows
  before merging. Logged as a backlog item (`docs/BACKLOG.md`) rather than silently resolved.
  Naively concatenating per-organism results without the groupby-merge step would have given
  10,437 rows instead of the correct 10,406 unique proteins.

## Reproduce

```python
import json
import pandas as pd
from phiexplorer.paths import input_json_path
from phiexplorer.dereference.chain import all_organisms
from phiexplorer.extract.phenotypes import extract_protein_phenotypes, PHENOTYPE_COLS

with open(input_json_path(), encoding="utf-8") as f:
    export = json.load(f)

orgs = all_organisms(export)
frames = []
for taxid, sciname in orgs.items():
    df = extract_protein_phenotypes(export, taxid=taxid, sciname=sciname)
    if len(df):
        frames.append(df)
all_df = pd.concat(frames, ignore_index=True)

bool_cols = [f"phenotype: {p}" for p in PHENOTYPE_COLS]
agg = all_df.groupby("uniprot_id")[bool_cols].any()

for col in bool_cols:
    print(col, agg[col].sum())

has_any = agg[bool_cols].any(axis=1)
print("with annotation:", has_any.sum())
print("without annotation:", (~has_any).sum())
```

## Related

[[2026-08-20-fgraminearum-high-level-phenotype-counts]] — same analysis, F. graminearum only
