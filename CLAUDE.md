# Kiro Dreaming Optimization

Two independent, parallel memory kits live here. Each has its own store and serves one
agent. Never let one write into the other's memory root.

- `.kiro/` serves Kiro IDE, storing memory in `.kiro/memory/`.
- `.claude/` serves Claude Code, storing memory in `.claude/memory/`.

Working in Claude Code, use only `.claude/`. Treat `.kiro/` as read-only reference
unless the user asks for a change there.

## Memory

This project's memory policy is always in effect: @.claude/memory-policy.md

In short: read `.claude/memory/CURRENT` and the active store's `MEMORY.md` before
substantive work, use the `remember` skill to capture durable decisions and corrections,
and use the `dream` skill to consolidate. Project memory under `.claude/memory/` is
scoped to this repository and is separate from the user-level memory directory under
`~/.claude/projects/`.

## Helper

`python3 .claude/skills/dream/scripts/memory.py <status|begin|validate|diff|promote|rollback>`
is deterministic storage only, Python 3.9+ standard library, no network and no model
calls. `promote --unattended` accepts additions but refuses any rewrite of an existing
claim. The two kits' copies of this script are byte-identical by design; `tests/` covers
the shared implementation and guards against drift.
