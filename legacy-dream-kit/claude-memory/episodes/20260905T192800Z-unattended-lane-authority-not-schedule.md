# Unattended consolidation is gated by authority, not by a schedule
Recorded: 2026-09-05T19:28:00Z
Scope: this repository / dream memory kit
Source: current conversation; transcript not exported

## Evidence
- The user shared a diagram showing dreaming as a periodic batch process feeding the
  next day's agent sessions, and asked whether this kit matched it.
- The user corrected an early claim of mine that the kit was "not batch": batching
  already existed via `begin --limit 20`; only automatic scheduling was missing.
- The user rejected scheduled `/dream preview` as a sufficient answer: previews alone
  do not improve tomorrow's active memory until something promotes them.
- No wall-clock scheduler is possible here. Reflection runs inside the agent
  conversation and the helper makes no model calls, so cron could only run
  deterministic storage operations, which cannot reflect.

## Durable takeaway
Kind: decision
Consolidation is split by authority rather than by schedule. The unattended lane runs
at session start under a cadence floor, may only add topics and claim sections, and
promotes itself with `promote --unattended`. The attended `/dream` retains merging,
reconciling, superseding, and retiring. "Periodic" is realised as session start rather
than overnight, so consolidation happens just before memory is read.

## Limits
The restriction is enforced in the helper, but the trigger is steering prose the model
may skip, so the lane is guaranteed in what it cannot do and best-effort in whether it
runs. Verified by unit tests and scratch CLI runs, not yet by a live session start.
