# phi-explorer Query CLI — Design Spec

**Date:** 2026-08-20
**Status:** Approved (pending implementation)
**Repo:** https://github.com/PHI-base/phi-explorer.git (public)

## 1. Purpose

Build the query CLI deferred twice already: the original design spec
(`docs/superpowers/specs/2026-08-19-phi-explorer-design.md`) §6 scoped it out of v1, and the
reports-layering follow-up's spec §2 reaffirmed the deferral. `docs/BACKLOG.md`'s "Query CLI"
entry tracks it as the one piece of originally-planned scope still missing — everything else the
design spec called for now exists (`dereference/`, `extract/`, `reports/`).

This gives every existing library entry point (`extract_protein_phenotypes`,
`extract_effector_proteins`, `dataset_summary`, `organism_summary`, and the three
`reports/generate.py` writers) a command-line front door, plus solves the organism lookup
ergonomics problem the backlog flagged: callers currently need to already know both the exact
scientific name string and the NCBI taxon ID before calling anything, with a typo silently
returning zero rows rather than an error.

## 2. Scope decisions (from brainstorming)

- **Mirror the library 1:1.** One subcommand per existing entry point, no new extraction or
  reporting logic — the CLI is a thin wrapper, same relationship `reports/` has to `extract/`.
- **`argparse`, stdlib only.** No new runtime dependency, matching this project's lean-dependency
  posture (pandas + openpyxl are the only deps so far).
- **Fuzzy organism resolution.** A user may supply just `--taxid` or just `--sciname`; the CLI
  resolves the other from the loaded export and errors clearly on a bad or ambiguous value,
  rather than silently producing an empty report.
- **Case-insensitive exact match only** for sciname resolution — no substring/partial matching.
  Keeps the resolution logic simple and its failure modes predictable; the new `organisms`
  subcommand (below) covers discovery for anyone who doesn't already know the exact name.
- **File output by default**, matching the existing `reports/generate.py` writers exactly
  (`phiexplorer.paths.output_dir()`, timestamped Excel/CSV, `--output-dir` overrides the
  directory). No new stdout-vs-file mode — the CLI doesn't change what the library already does,
  it just exposes it.

## 3. New library additions

`phiexplorer/dereference/chain.py` gains two functions, in the same style as its existing
per-session helpers (`taxid_to_name_map` etc.) but scoped to the whole export:

```python
def all_organisms(export: dict) -> dict[int, str]:
    """{taxid: full_name} for every organism across all curation sessions."""

def resolve_organism(
    export: dict, taxid: int | None = None, sciname: str | None = None
) -> tuple[int, str]:
    """Resolve a (taxid, sciname) pair from either half, validated against the export.

    - Both given: validated against all_organisms(); raises ValueError if they
      don't refer to the same organism (wrong taxid for that name, or vice versa).
    - Only one given: the other is looked up. sciname matching is case-insensitive
      exact match. Raises ValueError if not found.
    - Neither given: raises ValueError.
    """
```

Pure library code, independently testable against the existing fixture
(`tests/fixtures/sample_export.json`), and reusable outside the CLI. Lives in `chain.py` because
it operates on the raw export the same way that module's other functions do — not
report-specific, so it doesn't belong in `reports/` or `extract/`.

## 4. CLI structure

New module `phiexplorer/cli.py`. Entry point: `python3 -m phiexplorer.cli <subcommand> [args]`.
Every subcommand accepts `--input PATH` (default: `phiexplorer.paths.input_json_path()`) to
override which export JSON is loaded; the export is loaded once in `main()` before dispatch.

Subcommands:

- **`organisms`** — prints every `(taxid, sciname)` pair in the loaded export, sorted by name.
  No organism arguments. Pure discovery command for the "what do I use" problem in
  `docs/FAQ.md`.
- **`phenotypes (--taxid N | --sciname NAME) [--output-dir DIR]`** — resolves the organism via
  `resolve_organism`, calls `write_protein_phenotype_report`, prints the written path.
- **`effectors (--taxid N | --sciname NAME) [--output-dir DIR]`** — same shape, calls
  `write_effector_report`.
- **`summary [--output-dir DIR]`** — dataset-wide, no organism arguments, calls
  `write_dataset_summary_report`.
- **`organism-summary (--taxid N | --sciname NAME)`** — calls `reports.stats.organism_summary`
  and prints the resulting `{genes, interactions}` dict. No report file — `organism_summary`
  itself has never written one (the ported original didn't either, per the reports-layering
  spec §2), and this follows that precedent rather than introducing a new one-off report format.

`--taxid` and `--sciname` are mutually optional but at least one is required on the three
organism-scoped commands (argparse: not `required=True` individually, checked in the handler via
`resolve_organism`, which already raises on "neither given"). If both are given, they're
validated for consistency by the same function.

## 5. Error handling

A single try/except boundary in `main()` around subcommand dispatch catches `ValueError` (from
`resolve_organism` or a bad `--input` path) and any other expected failure, prints
`error: <message>` to stderr, and exits 1 — no tracebacks for user-facing errors like a typo'd
organism name or a missing export file. Unexpected exceptions (bugs) still propagate normally.

## 6. Testing

- `tests/dereference/test_chain.py` — unit tests for `all_organisms` and `resolve_organism`
  against the existing fixture: found-by-taxid, found-by-sciname, case-insensitive match,
  mismatched pair, not-found, neither-given.
- `tests/test_cli.py` (new) — one test per subcommand's happy path plus the error paths
  (unresolvable taxid/sciname, mismatched pair, missing organism args on the three
  organism-scoped commands), driven by calling the parser/dispatch function directly against the
  fixture — no subprocess spawning.
- `docs/FAQ.md`'s "Is there a command-line interface?" entry is rewritten from "not yet" to show
  actual usage examples.
- `docs/BACKLOG.md`'s "Query CLI" section is removed once this ships.

## 7. Out of scope

- Any new extraction, resolution beyond exact-match, or report format — this is a wrapper around
  what already exists.
- Substring/partial name matching, or resolving from a taxid/name not present in the loaded
  export at all (e.g. querying NCBI) — `docs/FAQ.md` already tells users to look up unfamiliar
  taxon IDs at NCBI Taxonomy themselves.
- Interactive/REPL mode, shell completion, or config files.
