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
