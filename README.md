# Dream Memory

A small memory loop for Claude Code and Kiro IDE: record durable decisions during work,
read them back in later sessions, and periodically consolidate them into topic files.
Plain Markdown and two skills per agent. No API keys, no background workers, no model
calls outside your chat. This is not Anthropic's Managed Agents Dreams API.

## Layout

```text
.claude/                          .kiro/
  skills/dream/SKILL.md             skills/dream/SKILL.md
  skills/remember/SKILL.md          skills/remember/SKILL.md
  settings.json      session hook   steering/memory-policy.md
                                    hooks/dream-memory-session.json
  dreaming/                         dreaming/
    MEMORY.md        index            MEMORY.md
    topics/*.md      the memory       topics/*.md
    .backups/        pre-dream copies  .backups/
    .last-dream      timestamp         .last-dream
    .dream-pending   set at session end
```

Skills, steering, and hooks must stay in those locations or neither tool finds them.
Everything the kit owns lives under `dreaming/`. The two kits are independent: each
agent maintains its own memory and never writes into the other's folder.

## Use

| Request | Result |
| --- | --- |
| Work normally | The agent reads relevant topics first and records durable outcomes before finishing. |
| `/remember We use X for tests but Y for deploys.` | Appends one dated, scoped line to the right topic file. |
| `/dream` | Consolidates: backs up, merges new signal, rewrites the index. |
| Close a session | A `SessionEnd` hook marks it pending; the next session consolidates it first thing. |

Capture is best-effort — it happens when the agent judges something durable was
established. Use `/remember` explicitly when you want certainty.

## When dreaming runs

A hook cannot make the model do anything: it runs a shell command, and once a session
closes there is no model left to consolidate. So closing a session only *marks* the work,
and the next session does it — which costs nothing, because the transcript is already on
disk and can be mined after the fact.

For Claude Code, a `SessionEnd` hook touches `.claude/dreaming/.dream-pending`, and
session start reports it so the dream runs before the first request and clears the marker.
Kiro's hook support for session end is not documented, so its trigger needs only session
start: it reports a dream is due when any topic file changed after `.last-dream`, meaning
`/remember` captured something you have not consolidated yet.

Either way, typing `/dream` as your last action before leaving works too, and runs the
consolidation there and then instead of at the next session.

## How the two differ

Claude Code writes session transcripts to disk, so `/dream` there mines them directly:
`~/.claude/projects/<cwd with / and spaces replaced by ->/<uuid>.jsonl`. The skill greps
recent user messages for corrections, decisions, and preferences, filtering out
harness-injected text so it learns from what you actually typed. That means memory
accumulates even when nothing was captured during the session.

Kiro transcripts are not readable from disk, so its `/dream` consolidates what
`/remember` captured plus the visible conversation. Capture discipline matters more
there.

## Rules that matter

- **Absolute dates only.** Never store "yesterday".
- **Supersede, don't delete.** A contradicted line stays, marked
  `(updated YYYY-MM-DD, previously: ...)`. A newer statement wins only inside its scope.
- **No age-based pruning.** A decision from six months ago is settled, not stale.
- **Attribution on every line:** scope, source, confidence.
- **Back up before consolidating.** `/dream` copies the index and topics into
  `dreaming/.backups/<date-time>/` first. To undo, copy a folder back out.

Memory is evidence, not authority: current instructions and the repository win, and
anything quoted from a transcript is data, never an instruction.

## Setup

Both kits are installed in this workspace. For a new project, copy `.claude/skills/`,
`.claude/settings.json`, and an empty `.claude/dreaming/` with a `MEMORY.md` containing
`# Memory Index`; likewise for `.kiro/`. Start a fresh session so `CLAUDE.md`, the
skills, and the hook load. Requires Python 3.9+ only for the Claude transcript miner,
which uses the standard library.

Check it works: `cat .claude/dreaming/MEMORY.md`, then ask for `/dream` and confirm a
folder appears under `.claude/dreaming/.backups/` and `.last-dream` is written.

## legacy-dream-kit/

The previous design — a Python helper with immutable versioned stores, promotion,
rollback, an additive-only automatic lane, and a 24-test suite — is archived there. It
worked and is more rigorous, but it was more machinery than this project needs. Kept
because the repository is not under version control. Delete it when you are sure.
