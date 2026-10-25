---
description: Research a topic from primary sources — per-claim citations, confidence, and explicit unknowns instead of guesses
---

# /research

Topic: $ARGUMENTS

**Mandate:** use all available and appropriate skills, tools, web research, and
other resources to establish what is factually true. No claim reaches the
operator unless a source was read in this session. A guess is a defect;
"unverified" is an acceptable answer.

Load the `research` skill (skill tool, id `research`) for the evidence ladder,
then:

1. Restate the question and the decision it feeds.
2. Walk the ladder — repo/code first, then live tools, then vendor docs, then
   secondary sources.
3. Cross-check load-bearing claims, and date anything that drifts.
4. Answer in exactly three parts. Prose alone is a failed run:

   **Answer:** one paragraph, direct.

   | Claim | Source | How verified |
   |---|---|---|
   | … | url / `file:line` / tool call | read / reproduced / cross-checked |

   **Confidence:** high · medium · low — why.
   **Unverified:** what you could not confirm, or "none".

If the topic above is empty, ask what to research. Never answer from memory.
