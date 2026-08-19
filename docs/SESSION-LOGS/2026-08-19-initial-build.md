---
created: 2026-08-19
type: session-log
tags: [session-log, initial-build]
project: phi-explorer
summary: >
  Created phi-explorer from scratch as a datamining toolkit for PHI-base 5, ported and
  generalized from James Seager's prior-art scripts. Built via spec -> plan ->
  subagent-driven-development across four cycles (core toolkit, extract-module
  consolidation, reports/extract layering, plus FAQ/BACKLOG docs), each closing findings
  its own final review raised. Registered in BotVault's vault registry, pushed to
  PHI-base/phi-explorer on GitHub, and fixed the Obsidian CLI wrapper so this vault (and
  BotVault/phi-weaver) can be reached live from WSL.
---

# Session Log: phi-explorer Initial Build

## Overview

First session in a brand-new project folder (`/mnt/z/phi-explorer`, empty at session start).
Went from "check if there are notes for this" to a pushed, tested, documented public GitHub
package in one sitting, via four full spec-and-plan cycles plus supporting infrastructure work.

## What got built

### 1. Discovery and design

- Searched OBS-BotVault and OBS-MU-ResearchLab for prior art before writing anything. Found
  substantial relevant history: a trashed `_PHI-explorer.md` stub (2026-08-06, "New project
  folder. Details TBD."), and — the real find — James Seager's two working analysis projects
  in ResearchLab (`PHI5-data-mining-statistics`, `PHI5-zenodo-datamining`) with a documented
  Gene->Allele->Genotype->Metagenotype->Annotation dereferencing pattern and validated
  extraction scripts against the real PHI-base v5.3 dataset.
- Decided (with the user): build on that prior art rather than start fresh; new git repo
  (remote already existed at `PHI-base/phi-explorer`, public); full Obsidian vault fused with
  the repo, matching phi-weaver's pattern; self-contained data (own sibling
  `phi-explorer-data/` folder, not a live reference into ResearchLab).
- Wrote the design spec
  ([docs/superpowers/specs/2026-08-19-phi-explorer-design.md](../superpowers/specs/2026-08-19-phi-explorer-design.md)),
  scaffolded `.gitignore`, `content-links/data-index.md`, and seeded `phi-explorer-data/input/`
  with a checksum-verified copy of the official PHI-base v5.3 release.

### 2. Core toolkit plan (10 tasks, subagent-driven)

Built `phiexplorer/dereference/chain.py` (the dereferencing chain, 8 functions),
`extract/phenotypes.py` and `extract/effectors.py` (organism-parameterized, generalized from
James Seager's F.-graminearum-hardcoded scripts), `reports/excel.py` and `reports/stats.py`,
and `phiexplorer/smoke.py` (real-data benchmark: 1,344 F. graminearum proteins, 32/421/912/15
phenotype split). Every task passed its own review; the final whole-branch review (opus) found
a real bug the port had introduced — `organism_summary()` overcounted genes (1486 vs. the
correct 1344) — plus two documentation inaccuracies, fixed in one consolidated fix wave. Also
discovered and documented that the port had *fixed* a real bug in the original effector-
detection script (product field was always read as empty string upstream; phi-explorer now
correctly finds 22 F. graminearum effectors vs. the original's 19).

### 3. Extract-module consolidation (4 tasks)

Closed a deferred finding from the core-toolkit review: `phenotypes.py` and `effectors.py`'s
internal collector functions were ~87% duplicated. Factored the shared logic into
`phiexplorer/extract/_collect.py` (6 named functions), verified zero behavior change via the
unmodified existing test suites plus the same real-data benchmark. Final review caught one more
stale doc reference, fixed and re-verified.

### 4. Reports/extract layering (1 task)

Closed the other deferred finding: the design spec said `reports/` should be "a thin consumer
of `extract/`," but `write_excel()` had zero callers anywhere in the package. Added
`phiexplorer/reports/generate.py` (three orchestration functions:
`write_protein_phenotype_report`, `write_effector_report`, `write_dataset_summary_report`),
verified against real data. The task's own review caught a genuine gap it introduced — the
package's first CSV writer had no `.gitignore` coverage, a live risk of committing generated
report data to this public repo — fixed same-task. The final review caught one more stale doc
claim, plus recommended (and got) two test-strengthening additions.

### 5. Documentation and infrastructure

- `docs/FAQ.md` — practical how-to (installation, data setup, extraction, report generation,
  taxon IDs, gotchas).
- `docs/BACKLOG.md` — open items: the query CLI (deferred twice, the one piece of originally
  planned scope still missing), parked review findings, possible future extraction dimensions.
- Registered phi-explorer in `OBS-BotVault/Claude-Knowledge/Cross-Vault-Coordination.md`
  (public-GitHub / hands-off tier, same as phi-weaver).
- **Fixed the Obsidian CLI.** `~/.local/bin/obsidian` had been a *different*, unrelated Obsidian
  CLI product all session, one that only talks to a Linux-native Obsidian instance and could
  never reach the Windows-hosted vaults at all — not a phi-explorer-specific problem, despite
  how it first presented. Replaced it with a wrapper forwarding to the real Windows CLI
  (`/mnt/d/ObsidianProgram/Obsidian.com`), preserving the old binary as `obsidian-linux-cli`.
  Verified working for phi-explorer, OBS-BotVault, and phi-weaver.
- Enabled Developer Mode for the phi-explorer vault (user action, in Obsidian's Settings),
  switching `obs-put.sh` writes onto the live `eval` route instead of the fallback that needs a
  manual reload — verified via `test.md`/`docs/test2.md`. Two files created via direct disk
  write *before* the toggle (`docs/FAQ.md`, `docs/BACKLOG.md`) are stuck needing one manual
  reload each; anything written from now on should sync live.

## Decisions worth remembering

- **Bounded vs. architectural classification mattered in practice.** The extract-consolidation
  follow-up was treated as bounded (short in-chat design, no separate spec file, straight to a
  plan on explicit request) since it was a well-scoped refactor of code that already existed.
  The reports-layering follow-up was treated as architectural (full spec doc) because no
  "generate a report" flow existed yet to modify — new functionality, not a refactor, even
  though it touched only one new file.
- **Final reviews consistently earned their cost.** Every one of the three follow-up plans'
  final whole-branch reviews found something task-scoped reviews structurally couldn't see: a
  real correctness bug invisible to the fixture (single-session test data can't catch
  cross-session aggregation bugs — noted as a lesson for future fixture design), a stale doc
  reference, and a live public-repo data-leak risk. None were caught by any individual task's
  own review.
- **Git on `/mnt/z` has a recurring, well-understood failure mode.** `git init`, `git config`,
  and a first `git push`'s branch-tracking write can all fail on `.git/config.lock` chmod
  errors specific to this SMB mount — worked around every time by editing `.git/config`
  directly instead of trusting the failing command. Documented in Claude memory
  (`reference_git_init_z_mount`) for future sessions.

## Related

**Plans:** [core-toolkit](../superpowers/plans/2026-08-19-phi-explorer-core-toolkit.md) |
[extract-consolidation](../superpowers/plans/2026-08-19-phi-explorer-extract-consolidation.md) |
[reports-layering](../superpowers/plans/2026-08-19-phi-explorer-reports-layering.md)

**Specs:** [core design](../superpowers/specs/2026-08-19-phi-explorer-design.md) |
[reports-layering design](../superpowers/specs/2026-08-19-phi-explorer-reports-layering-design.md)

---
**Tags:** #session-log #initial-build #2026-08-19
