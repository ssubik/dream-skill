# Memory design

Updated: 2026-09-06

- [2026-09-06] A byte-level "nothing was overwritten" check does not imply consistency. A new
  section can reverse an existing claim while preserving its text, and any queue that marks
  inputs processed can retire evidence that was never applied. Check contradiction and queue
  retirement separately from preservation. (scope: this repo; source: session 2026-09-05;
  confidence: high)
- [2026-09-06] Claude Code session transcripts are readable on disk at
  `~/.claude/projects/<cwd with / and spaces replaced by ->/<uuid>.jsonl`. User records have
  type `user` and `message.content` as a list of `{type,text}` blocks. There is no
  `sessions/` subdirectory and no `human` type. Mining these removes the need for the
  agent to remember to capture. (scope: this repo; source: session 2026-09-05; confidence: high)
- [2026-09-06] Superseded: the versioned-store design (immutable stores, promotion, rollback,
  additive-only lane, Python helper) was replaced by this simple file-based kit on request.
  The archived implementation is in `legacy-dream-kit/`.
  (updated 2026-09-06, previously: two-lane versioned consolidation; source: session 2026-09-05)
