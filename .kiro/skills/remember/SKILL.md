---
name: remember
description: Record a durable project decision, correction, preference, or verified lesson into this repository's memory. Use for remember requests or newly established reusable knowledge about this project.
---
# Remember

Append one dated line to the right topic file under `.kiro/dreaming/topics/`.

1. Read `.kiro/dreaming/MEMORY.md` and the topic the claim belongs to. If the claim is
   already recorded, do nothing. If it contradicts an existing line, keep that line and
   mark it `(updated YYYY-MM-DD, previously: ...)` — never delete it.
2. Append one line in this format, and update the topic's `Updated:` date:

   ```markdown
   - [YYYY-MM-DD] The claim, with its conditions and exceptions.
     (scope: ...; source: ...; confidence: high|medium)
   ```

3. Use today's date from the environment, not one copied from these instructions. Record
   scope precisely: a preference for one area does not apply to the whole repository.
4. Create a new topic file only when no existing one fits, and add it to `MEMORY.md`.

Record only reusable knowledge: decisions and their rationale, explicit corrections,
stable preferences, verified lessons. Skip routine activity, speculation, and anything
the code or specs already state. Never save credentials. Respect requests not to record
something. If nothing durable was established, write nothing and say so in one clause.
