# CLAUDE.md

This file bridges Claude Code to this repository's agent instructions.

**Read [AGENTS.md](AGENTS.md) first** — it is the tool-agnostic source of truth for
project overview, mission/boundaries, scientific accuracy rules, coding standards,
and file safety rules. Everything below is Claude-Code-specific.

## Claude Code specifics

- Skills (if any are added later) run via the `Skill` tool from `./skills/`.
- This vault is registered in `OBS-BotVault`'s `Cross-Vault-Coordination.md` as
  public-GitHub / hands-off: read-only reference from BotVault, self-governed here.
- At session start, no session-log index exists yet (phi-explorer doesn't use
  phi-weaver's `11-CLAUDE-AI/SESSION-LOGS/` machinery) — rely on `git log` and
  `docs/superpowers/specs/` and `docs/superpowers/plans/` for prior context.
