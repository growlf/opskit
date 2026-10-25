---
description: Research a topic from primary sources — per-claim citations, confidence, and explicit unknowns instead of guesses
---

# /research — evidence-first answer

## Description

Research a topic to a sourced answer. Every load-bearing claim carries a source read in this session; confidence and unverified gaps are stated plainly.

## Triggers

`/research`, `research <topic>`, `find out whether`, `verify that`, `is it true that`, `look up`

## Procedure

Load the `research` skill and run it against: $ARGUMENTS

1. Restate the question and the decision it feeds.
2. Walk the evidence ladder — repo/code, then live tools, then vendor docs, then
   secondary sources.
3. Cross-check load-bearing claims, and date anything that drifts.
4. Return the answer with the evidence table, confidence, and the unverified list.

If `$ARGUMENTS` is empty, ask what to research. Never answer from memory.
