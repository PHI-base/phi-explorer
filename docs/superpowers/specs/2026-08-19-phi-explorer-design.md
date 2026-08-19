# phi-explorer — Design Spec

**Date:** 2026-08-19
**Status:** Approved (pending implementation)
**Repo:** https://github.com/PHI-base/phi-explorer.git (public)

## 1. Purpose

phi-explorer is a reusable analysis toolkit for datamining pathogen-host
interaction data out of the published **PHI-base 5** database. It answers
questions like "what phenotypes are associated with gene X's alleles" or
"which effector proteins does organism Y have" by working directly with the
PHI-base v5.3 Zenodo JSON export.

It is a sibling project to `phi-weaver`, not a replacement or extension of
it. phi-weaver assists curators in *creating* new PHI-base annotations from
literature (curation-in). phi-explorer *reads* the already-published
database to extract and report on interaction data (analysis-out). Neither
project depends on or modifies the other.

## 2. Relationship to prior art

James Seager (Rothamsted) already built two analysis projects, both in
`OBS-MU-ResearchLab/02-PROJECTS/ACTIVE/PRO-James-Seager/`:

- **PHI5-data-mining-statistics** — basic stats extraction from the
  PHI-base v5.0 JSON export.
- **PHI5-zenodo-datamining** — more mature; works on the official v5.3
  Zenodo release. Documents the core dereferencing chain (`Gene → Allele →
  Genotype → Metagenotype → Annotation`) in `DATA_STRUCTURE_GUIDE.md`, and
  has production scripts (`fg_protein_phenotypes.py`,
  `fg_effector_proteins.py`) validated against *Fusarium graminearum*
  (taxon 5518): 1,344 proteins, split 912 unaffected / 421 reduced
  virulence / 32 loss of pathogenicity / 15 increased virulence.

phi-explorer **ports and generalizes** this work rather than starting from
zero or moving the originals:

- The dereferencing pattern and extraction logic are rewritten into an
  installable, organism-agnostic package (organism becomes a parameter,
  not a hardcoded taxon ID).
- The originals stay untouched in ResearchLab as the historical record —
  nothing is moved or deleted.
- `docs/PORTING-NOTES.md` in phi-explorer credits the source work and
  records what was generalized, so provenance isn't lost.
- The F. graminearum numbers above become the validation benchmark for
  the ported code (same role `PHI_ANALYSIS_WORKFLOW.md` gives them today).

A third, unrelated precursor — `/mnt/z/PHI5` (James Seager's PHI-base *4*
parsing scripts, `phi4_pipeline.py` etc.) — is legacy and out of scope; it
predates the v5 schema entirely and isn't ported.

## 3. Repository / vault structure

phi-explorer is a single fused git repo + Obsidian vault at
`/mnt/z/phi-explorer`, following the same pattern as `phi-weaver`:

```
phi-explorer/
├── phiexplorer/            # the installable Python package (see §4)
├── tests/
├── docs/
│   ├── DATA-STRUCTURE.md   # ported/updated from PHI5-zenodo-datamining's guide
│   ├── PORTING-NOTES.md    # provenance: what came from James Seager's work
│   └── superpowers/specs/  # this file and future specs
├── AGENTS.md                # tool-agnostic source of truth (Claude Code, OpenCode, etc.)
├── CLAUDE.md                 # thin bridge to AGENTS.md
├── README.md
├── pyproject.toml
└── .obsidian/                # vault config
```

- `AGENTS.md` / `CLAUDE.md` follow phi-weaver's split: stable project
  knowledge, mission/boundaries, coding standards, and pointers to
  `docs/`. No `11-CLAUDE-AI/` session-log machinery is copied wholesale —
  phi-explorer starts lean and adds structure only if it's actually needed.
- Registered in `OBS-BotVault/Claude-Knowledge/Cross-Vault-Coordination.md`
  as a new vault: public GitHub, 🔒 hands-off from BotVault (read-only
  reference, same tier as phi-weaver), self-governed by its own
  `AGENTS.md`.

## 4. Package layout

```
phiexplorer/
  dereference/   # core chain: Gene → Allele → Genotype → Metagenotype → Annotation
  extract/        # phenotype / effector / host extraction, organism as a parameter
  reports/         # stats & report generation, built on extract/
```

- Reusable toolkit first (`dereference/`, `extract/`); `reports/` is a thin
  consumer of it. No CLI in v1 (see §6).
- Mirrors phi-weaver's `phiweaver/` package convention (importable,
  `python3 -m phiexplorer....`, tests co-located in `tests/`).

## 5. Data handling

The PHI-base v5.3 JSON export (110MB) is **not committed to git** — same
principle as phi-weaver's external literature storage.

- Source of truth: the Zenodo release referenced in the official
  `phi-base_v5.3/README.md` (DOI 10.5281/zenodo.18449986), also mirrored
  locally in ResearchLab at
  `PRO-PHI-base/PRO-PHI-base5/phi-base_v5.3/phi-base_v5.3.json`.
  Location is overridable via a `PHI_DATA_ROOT` environment variable
  (mirrors phi-weaver's `PHI_LITERATURE_ROOT`), so the code isn't tied to a
  machine-specific path.
- `phiexplorer.repo_root()`-relative paths only; never hardcode
  `/mnt/z/...` in package code (same rule phi-weaver enforces).
- Tests run against a small fixture subset of the JSON, not the full file.

## 6. Initial scope and build order

1. **Core**: port the dereferencing chain and generalize the F.
   graminearum-specific extraction logic (from `fg_protein_phenotypes.py`
   / `fg_effector_proteins.py`) into organism-agnostic functions in
   `phiexplorer/dereference/` and `phiexplorer/extract/`. Validate against
   the F. graminearum benchmark numbers in §2.
2. **Reports**: stats/report generation layer in `phiexplorer/reports/`,
   generalizing `phibase5_stats.py`'s output shape to any organism/dataset
   slice.
3. **Query interface** (CLI or similar): explicitly deferred out of v1.
   Revisit once the toolkit and reports layers are validated and it's
   clear what queries are actually needed.

## 7. Out of scope

- Anything that writes back to PHI-base, PHI-Canto, or phi-weaver.
- Curation-assistance features (that's phi-weaver's job).
- The PHI-base 4 legacy scripts in `/mnt/z/PHI5`.
- A query CLI/API (deferred — see §6).
