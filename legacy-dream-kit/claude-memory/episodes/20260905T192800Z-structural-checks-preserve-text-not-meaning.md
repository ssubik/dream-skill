# Structural memory checks preserve text, not meaning
Recorded: 2026-09-05T19:28:00Z
Scope: this repository / dream memory kit
Source: current conversation; transcript not exported

## Evidence
- The user reviewed the first unattended implementation and identified four defects:
  additions can contradict preserved claims; promotion marked every selected episode
  processed, silently retiring corrections the additive lane was not allowed to apply;
  a rejected candidate did not stop another automatic attempt; and the cadence measured
  candidate creation time rather than promotion time.
- All four were confirmed against the code before any fix was written.
- Fixes applied: refuse added claims of kind `correction` or `unresolved`; optional
  `deferred.json` excluding unapplied episodes from the processed ledger;
  `blocked_by_candidates` suppressing retries; a `promoted-at` marker for cadence.
- Verified outcome: 24 unit tests pass and a scratch CLI run reproduced each behaviour.

## Durable takeaway
Kind: lesson
A byte-level "nothing was overwritten" guarantee does not imply consistency. A new
section can reverse an existing claim while preserving its text, and any queue that
marks inputs processed on promotion can retire evidence that was never applied. When
automating memory writes, check contradiction and queue retirement separately from
preservation; they are distinct failure modes.

## Limits
A contradiction written as an ordinary `fact` or `decision` remains undetectable by
the helper. That judgement is delegated to the skill's instructions and is unverified.
