---
name: remember
description: Capture durable project decisions, user corrections, preferences, and verified lessons from the current conversation into project memory. Use for remember requests or newly established reusable knowledge.
---
# Remember

Save a short evidence-bearing episode under `.kiro/memory/episodes/`. These episodes
bridge sessions; they are not complete transcripts. Read
`.kiro/skills/dream/references/memory-format.md` for the episode format.

1. Identify what changed in this conversation. Distinguish explicit user statements,
   verified outcomes, and hypotheses. Preserve scope, exceptions, and decision rationale.
   Do not infer agreement from silence or describe proposed work as completed.
2. Read the active index and relevant topics, then search pending episodes for the
   same claim. Skip duplicates. A correction or new supporting outcome is new evidence.
3. Write a unique UTF-8 Markdown file under `.kiro/memory/episodes/`, named with a UTC
   timestamp and short random suffix. Never overwrite an existing episode. Use the
   current time from the environment, not a date copied from these instructions.
4. Include source excerpts or concise attributed paraphrases from visible conversation
   and actual verification evidence. If a durable transcript URL or file is unavailable,
   say `current conversation; transcript not exported`. Never invent session IDs,
   citations, commands, test outcomes, or missing conversation history.
5. Keep an episode around 100–300 words unless the evidence needs more. Store only
   reusable knowledge; code and specs remain authoritative for implementation details.
   Prefer one episode for the turn. Do not modify active stores or mark it processed.

For explicit `/remember`, briefly report what was captured and its path. For automatic
capture, add at most one short sentence to the task response. If nothing durable changed,
write nothing. `/remember` with no additional text reviews the visible conversation.

If asked to forget information, do not create a new episode repeating it. Explain which
active versions, episodes, and dream snapshots contain it and perform the user's scoped
deletion request, including retained copies; ordinary dream archival is not forgetting.
