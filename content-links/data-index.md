---
title: PHI-base v5.3 data index
tags:
  - content-link
date: 2026-08-19
---

# PHI-base v5.3 data index

This is a **pointer note** — the actual data lives outside the vault, at:

```
/mnt/z/phi-explorer-data/input/
├── phi-base_v5.3.json      # 110MB — main dataset (Gene → Allele → Genotype → Metagenotype → Annotation)
├── phi-base_v5.3.xlsx      # 4.8MB — spreadsheet form, for non-technical users
├── phi-base.schema.json    # JSON Schema for the dataset
├── README.md                # official release notes (release stats, citation, authors)
└── LICENSE
```

Kept outside the vault so Obsidian doesn't index 115MB of data, and outside
git so it isn't committed (see
[docs/superpowers/specs/2026-08-19-phi-explorer-design.md](../docs/superpowers/specs/2026-08-19-phi-explorer-design.md)
§5). Code should read this path via the `PHI_DATA_ROOT` environment
variable (default `../phi-explorer-data/`), never hardcoded.

## Provenance

- **Source:** copied 2026-08-19 from the official release mirror at
  `OBS-MU-ResearchLab/02-PROJECTS/ACTIVE/PRO-PHI-base/PRO-PHI-base5/phi-base_v5.3/`
  (verified identical via `md5sum` on `phi-base_v5.3.json`).
- **Original release:** Zenodo DOI
  [10.5281/zenodo.18449986](https://doi.org/10.5281/zenodo.18449986),
  release date 31 January 2026, version 5.3.
- **This is a one-time copy, not kept in sync.** If a newer PHI-base
  release is needed, re-copy from Zenodo or the ResearchLab mirror and
  update this note's date.

## Dataset stats (v5.3)

10,475 genes · 33,876 interactions · 309 pathogen species · 237 host
species · 344 diseases · 5,273 references. See `README.md` in the data
folder for the full annotation-type breakdown.
