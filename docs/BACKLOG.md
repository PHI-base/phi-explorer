# Backlog

Open items, not yet scheduled as a plan. When one of these gets picked up, it goes through
the normal brainstorming → spec → plan → subagent-driven-development cycle like everything
else in this repo — this file is just the "what's left" list.

## Smaller open items

All previously reviewed and explicitly parked as non-blocking — listed here so they don't get
lost, not because any of them are urgent.

- **`phiexplorer/dereference/chain.py:97`** — `taxid_to_name_map()` uses `org["full_name"]`
  (bracket access) where the rest of the file uses `.get()`. Cosmetic; would only matter if an
  organism entry is ever missing `full_name`, which the current fixture and design don't
  exercise. (Flagged in the core-toolkit plan's final review.)
- **Test file structure inconsistency** — `tests/dereference/__init__.py` exists but
  `tests/extract/` and `tests/reports/` don't have one. Harmless (pytest doesn't need it, test
  basenames are unique across the suite) but worth normalizing one way or the other.
- **`phiexplorer/extract/_collect.py`'s `INFECTIVE_ABILITY_TERMS` fallback path and the
  wild-type allele filter have zero test coverage** — the fixture's data always short-circuits
  both (every `infective_ability` extension already has a `rangeDisplayName`, and both fixture
  alleles are `"deletion"`, never `"wild type"`). Two small hand-built test cases would close
  it. (Flagged in the extract-consolidation plan's final review.)
- **`_organism_slug()` in `phiexplorer/reports/generate.py` doesn't neutralize path-hostile
  characters** (e.g. a `/` in a scientific name would break the output path). Hardening, not a
  live bug — PHI-base's actual fungal/bacterial organism names don't produce this today.
  (Flagged in the reports-layering plan's final review.)
- **No dataset-wide phenotype-extraction helper** — `extract_protein_phenotypes()` takes one
  organism at a time; a dataset-wide analysis (e.g. "phenotype counts across all organisms")
  has to loop over `chain.all_organisms()` and concatenate results by hand, as done in
  `Data-analysis-MU/2026-08-20-all-organisms-high-level-phenotype-counts.md`. A
  `extract_all_organisms_phenotypes()`-style wrapper would close this.
- **29 UniProt IDs are curated under two or more different organism entries** in the v5.3
  export (e.g. the effector `avrB`/P13835 under both *Pseudomonas syringae* and *Pseudomonas
  savastanoi*; `SIX3`/Q2A0P1 under four different fungal genera). Confirmed by inspecting the
  raw duplicate rows — looks like shared/ambiguous strain assignment or genuine cross-referenced
  orthologs in PHI-base's own curation, not an extraction bug, but any dataset-wide aggregation
  by UniProt ID must group/dedupe across organisms or it will overcount (see the same analysis
  note above). Not something to "fix" in phiexplorer; flagged here so future dataset-wide code
  doesn't rediscover it the hard way.
- **`reports/` isn't benchmark-validated against real data the way `extract/` is via
  `phiexplorer/smoke.py`.** The reports-layering plan's manual real-data verification step did
  confirm the report files reproduce the correct numbers, but that wasn't turned into a
  permanent regression check. A `smoke.py` extension asserting actual output-file row counts
  (not just the DataFrame the writer wraps) would close this properly.

## Possible future extraction dimensions

Not committed to — these are "Common Extensions" the ported prior-art workflow doc
(`PHI_ANALYSIS_WORKFLOW.md`, in James Seager's original `PHI5-zenodo-datamining` project) named
as future directions, never built here. Worth a fresh brainstorming pass each if they turn out
to matter:

- **Cross-species comparative analysis** — organism-wise summary tables, comparing phenotype
  distributions or host ranges across multiple organisms in one call, rather than one organism
  at a time.
- **Temporal analysis** — curation trends over time via `metadata.accepted_timestamp` and
  publication year, tracking how curation of a topic has grown.
- **Effector protein cross-referencing** — the current `is_effector()` rules are keyword +
  GO-term based; the original workflow doc also suggested cross-referencing against UniProt's
  own secreted-protein predictions, not yet implemented.
