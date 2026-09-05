# Dream Memory for Kiro IDE + Claude Opus

A workspace memory loop: capture durable lessons during work, retrieve relevant
context in later sessions, and reflect across saved notes to produce a new memory
version. Reflection runs in your Kiro conversation with **Claude Opus selected**.
No API keys, GPT configuration, external model calls, or background model workers.
This does not enable Anthropic's gated Managed Agents Dreams API or train Opus.

## Install

1. Copy this kit's `.kiro/` directory into your project root, merging directories.
   Review filename collisions; do not replace existing project configuration or memory.
   This workspace already contains the installed files.
2. In Kiro's chat model picker, select the **Claude Opus** version you use. Keep that
   explicit selection rather than Auto. A Markdown skill cannot force model routing.
3. Start a new Kiro chat. Check **Agent Steering & Skills** for `memory-policy`,
   `remember`, and `dream`. Type `/` and select `remember` or `dream`.
4. Run `python3 .kiro/skills/dream/scripts/memory.py status` in the project terminal.
   Requires Python 3.9+. No packages to install.

Targets the currently documented Kiro IDE 1.x skill and hook formats. If your IDE
does not discover skills, upgrade it or directly ask Kiro to read the relevant
`.kiro/skills/<name>/SKILL.md` and follow it. The optional session hook uses the v1
JSON schema; older `.hook` formats are not installed by this kit.

## Use

| Request in Kiro | Result |
| --- | --- |
| Work normally | Steering asks Opus to retrieve relevant memory and capture durable new lessons before finishing. |
| `/remember We use X for tests, but Y for deployments.` | Save an attributed, scoped episode. |
| `/dream audit` | Read-only findings; no files or state changes. |
| `/dream` | Reflect, verify, and activate a new version with rollback available. |
| `/dream preview` | Create a reviewed candidate while retaining the active version. |
| `/dream apply <candidate-id>` | Validate and activate that candidate if its inputs remain current. |
| `/dream rollback <version-id>` | Restore a retained version without deleting newer evidence. |
| `/dream Review all pending episodes in batches.` | Continue until all pending saved evidence is covered. |
| Start a session with consolidation due | Additive-only consolidation runs first and promotes itself. |

Slash-command text is interpreted by Opus, not a separate command parser. For
example, choose `/dream` from the menu and append `audit`. The Python helper has
explicit subcommands for deterministic storage operations.

Capture is agent-driven and best-effort. Use `/remember` before ending an important
session if you want explicit confirmation. The always-included steering provides
retrieval instructions; a local SessionStart hook also reports memory readiness and
whether consolidation is due. There is deliberately no Stop-triggered reflection loop.
The hook makes no model calls and starts no job; it only prints status, and steering
decides what to do with it. Disable it by setting `enabled: false` in its JSON.

## Two lanes

Reflection runs in one of two lanes, separated by authority rather than by schedule.

**Unattended** runs at session start when status reports `unattended_recommended` —
at least three pending episodes and roughly a day since the last consolidation. It may
only add new topics and new claims, and it promotes itself. The helper enforces that
independently of the model: existing claim text, topic metadata, and index lines must
stay byte-identical, so an unattended run cannot quietly reword a memory you rely on.
A candidate that tries is rejected and waits for review.

**Attended `/dream`** keeps full authority: merging duplicates, reconciling conflicts,
superseding corrected claims, and retiring stale ones.

This closes the loop without a scheduler and without a model call outside your chat:
consolidation happens just before memory is used rather than overnight. The cost is
that additions accumulate, since deduplication is itself a rewrite. Status reports
`compaction_recommended` when the index passes three quarters of its cap or seven
unattended versions have run without reconciliation; that is the cue to run `/dream`.
Every version from either lane is one `rollback` away.

## What is stored

```text
.kiro/
  steering/memory-policy.md       Small always-included retrieval/capture policy
  skills/remember/SKILL.md        Evidence capture
  skills/dream/                  Reflection instructions and storage helper
  hooks/dream-memory-session.json Read-only readiness at session start
  memory/
    CURRENT                      Active version name
    stores/<version>/            Immutable index, topics, processed-episode ledger
    episodes/                    Append-only notes from actual conversations
    dreams/<id>/                 Input snapshot, selected notes, candidate, report
```

Empty directories are created when needed. The initial store contains no invented
facts about you, your projects, or the Solidity examples in the earlier conversation.
The index is limited to 120 lines / 12 KiB by this kit, not by Kiro itself.

Normal retrieval reads the active index, relevant topics, and relevant pending notes.
A dream snapshots up to 20 pending episodes by default. Opus reconciles their meaning;
the helper checks structure, source hashes, and promotion conditions. Inferred patterns
retain their evidence and uncertainty. Unresolved contradictions remain visible.

The output is a separate store. Promotion switches a small pointer atomically and
retains the input version. Concurrent promotions are serialized; a candidate built
from an outdated store is rejected. New notes arriving during a dream stay pending.
Rollback also restores the processed-episode ledger, so later evidence can be revisited.

## Past sessions and privacy

This kit starts learning from visible conversations and saved episodes. It does not
read hidden Kiro transcript databases. To include older sessions, provide exports to
Kiro and ask it to create attributed episodes from them before dreaming. An episode
is a selective summary, so the quality of capture limits what dreaming can recover.

Generated episodes, snapshots, versions, and CURRENT are ignored by the included
memory `.gitignore`; the empty initial store remains shareable. Git ignore is not
encryption or access control. Existing tracked files stay tracked. Review generated
memory before deliberately sharing it. The kit retains history until you request
cleanup; an ordinary dream is not a sensitive-data erasure operation.

Do not edit an active store or an existing episode directly. Capture a correction
in a new episode. If changing the kit's schema, perform a deliberate migration.
Use one workspace memory root per project, especially with multiple worktrees.

## Validate locally

```sh
python3 .kiro/skills/dream/scripts/memory.py validate
python3 -m unittest discover -s tests -v
```

Tests cover rollback, preservation of source snapshots, newly arriving episodes,
conflicting promotions, immutable-source checks, broken indexes, symlinks, writer
locks, evidence-bearing topic promotion, cadence and compaction signals, and the
additive-only rule — additions accepted; rewrites, deletions, index rewording, and
topic metadata changes rejected, with the same candidate still promotable when
attended. The format validator checks required fields, links, and that nothing was
overwritten; it cannot prove a claim is true or that Opus reasoned correctly.

For the first real Opus session, perform this small acceptance check:

1. `/remember For this test only, use Atlas for unit tests and Beacon for releases.`
2. `/remember Correction for this test only: use Cedar for unit tests; keep Beacon for releases.`
3. `/dream preview`. Inspect the report and candidate: Cedar is scoped to unit tests,
   Beacon remains for releases, and no preference is generalized to other projects.
4. `/dream apply <id>`. Start a fresh chat and ask which test and release tools the
   test scenario uses. Ask which production deployment was verified: none was.
5. `/dream rollback initial` in a disposable test workspace. Confirm the episodes
   remain pending. Do not add fictional acceptance-test facts to real project memory.
6. For the unattended lane, capture three unrelated episodes in a disposable workspace
   and start a fresh chat. Consolidation should run first and report only additions.
   Then capture a correction to one of those claims and start another chat: the
   unattended attempt must refuse and leave a candidate for `/dream apply`, because
   superseding a claim is a rewrite.

Kiro IDE execution and Opus's semantic quality must be verified in Kiro; the local
tests exercise storage behavior, not the IDE runtime or the model. If a process crashes
with `.write-lock` present, verify no writer is running before removing that stale
lock. Failed candidates remain inspectable. Never force a stale candidate over new
memory; begin a fresh one. No automatic deletion of history runs.

## Documentation checked

Configuration follows official documentation checked September 6, 2026:

- [Kiro skills](https://kiro.dev/docs/skills/) — workspace discovery and invocation.
- [Kiro steering](https://kiro.dev/docs/steering/) — always-included policy.
- [Kiro hooks](https://kiro.dev/docs/hooks/) — v1 JSON configuration.
- [Hook triggers](https://kiro.dev/docs/hooks/types/) — IDE Session Start support.
- [Kiro models](https://kiro.dev/docs/models/) — model selection in chat.
