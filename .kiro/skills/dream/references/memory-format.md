# Memory contract

These are kit conventions, not Kiro platform limits.

`CURRENT` contains a version folder name. Each immutable `stores/<version>/` has
`MEMORY.md`, `topics/`, and helper-owned `processed.json`. Readers use the current
version once per task; writers only edit a dream's candidate. Episodes remain outside
stores, so rollback makes later evidence pending again rather than destroying it.

## Episodes

Use a new `.kiro/memory/episodes/<UTC-timestamp>-<random-suffix>.md`:

```markdown
# Deployment tooling correction
Recorded: 2026-09-06T10:30:00Z
Scope: this repository / contract deployment
Source: current conversation; transcript not exported

## Evidence
- User explicitly said Foundry is used for tests and Hardhat for deployments.
- This corrects the earlier statement that Foundry handles all tooling.

## Durable takeaway
Kind: correction
Use Foundry for tests; retain Hardhat for deployment in this project.

## Limits
No production deployment was performed or verified in this conversation.
```

The example is fictional; never seed it as user memory. Use actual evidence and date.
Record relevant repository paths and observed check outcomes where available.
Avoid secrets, raw environment dumps, and unrelated personal information.

## Topic files

Use flat descriptive filenames under `topics/`, with frontmatter:

```yaml
---
name: deployment
description: Deployment decisions, constraints, and known exceptions.
type: project
updated: 2026-09-06
---
```

Types: `project`, `user`, `feedback`, `reference`, `insight`. A user preference here
is project-scoped unless the user explicitly establishes a broader scope.

Each durable claim belongs in its own `## ` section, because the additive-only lane
below compares whole sections: a claim split across sections cannot be extended later
without counting as a rewrite. Each claim needs `Kind:`, `Scope:`, and `Evidence:`.
Kinds: fact, decision, preference, correction, lesson, hypothesis, unresolved.
Use episode paths relative to `.kiro/memory/` and enough excerpt/context to audit the
claim. Existing imported claims with unavailable evidence must be labeled unverified.
Keep conditions and exceptions with the claim, not in a distant topic.

For hypotheses add `Confidence:` (low/medium/high with justification), contrary
evidence, and what would validate it. Confidence is qualitative, not a probability.
Do not silently turn a hypothesis into a fact on a later dream. Unresolved conflicts
retain both claims and sources, with guidance not to assume either is established.

Prefer short topical sections. Around 1,000 words per topic is a review threshold,
not a reason to discard useful evidence. Split by task-relevant subject when needed.

## Index

`MEMORY.md` contains only headings, blank lines, and one-line topic links:

```markdown
# Memory Index

## Project
- [Deployment](topics/deployment.md) — Tooling and release constraints.
```

All topics must be linked exactly once; all links must exist. Limit the index to
120 lines and 12 KiB to keep retrieval cheap. Topic detail does not belong in the
index. Do not index raw episodes, reports, or old stores. An empty index is valid.

## Additive-only promotion

`promote --unattended` accepts a candidate only if it adds. New topics and new `## `
sections are allowed, and `updated:` may change; existing claim text, other frontmatter
fields, and existing index lines must stay byte-identical apart from trailing blank
lines. A new section may not carry `Kind: correction` or `Kind: unresolved`, since those
kinds exist to act on an existing claim. Merging duplicates, rewording, reconciling a
conflict, and retiring a claim all require an attended `/dream`.

The check is structural. It proves nothing was overwritten and no reconciling kind was
added; it cannot tell whether an addition is true, and it cannot detect a contradiction
written as an ordinary `fact` or `decision`. Guard that by reading a topic's existing
claims before appending to it.

`<dream>/deferred.json` is an optional JSON array of selected episode filenames the
reflection did not incorporate. Promotion marks every other selected episode processed,
so a correction the additive lane could not apply must be listed here to stay pending;
otherwise it leaves the queue unresolved. Deferring all of them refuses the promotion.

Because additions accumulate, `status` reports `compaction_recommended` when the index
passes three quarters of its limit or several unattended versions have run with no
reconciliation. Treat that as the signal to run an attended dream, not as an error.
A candidate awaiting a decision sets `blocked_by_candidates`, which stops the unattended
lane from retrying the same evidence and piling up candidates.

## Retention and concurrency

The helper snapshots source bytes and checks their hashes before promotion. Ordinary
capture appends unique episodes; new episodes arriving during a dream stay pending.
Promotion and rollback share a short-lived filesystem lock. Never remove a lock that
another process may own. A crash can leave `.write-lock`; inspect running processes
and state before manually removing a confirmed stale lock.

Old versions, original episodes, and dream snapshots are retained. No age-based deletion
or retention purge runs automatically. For large histories, archive reviewed material
deliberately with its evidence links, or ask for a separate retention migration.
