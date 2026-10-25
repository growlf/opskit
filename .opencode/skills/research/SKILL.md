---
name: research
description: Evidence-first procedure for factual questions — route through repo, live tools, and web, then report sources and confidence instead of guesses
mode: skill
triggers: research,verify claim,fact check,look up,find out,investigate,evidence,is it true
---

# research

> Load this skill when: asked to research, verify, or answer a factual question
> whose answer is not already in context — and always when a wrong answer would
> cost something.

## The rule

**No claim reaches the operator unless a source was read in this session.**

Memory is a lead, never a finding. It tells you where to look; it never tells
you what is true. "Unverified" and "I don't know" are complete answers. A
confident guess is not, because the operator cannot tell it apart from a sourced
one.

## Evidence ladder — cheapest authoritative rung first

| Rung | Source | Reach for |
|---|---|---|
| 1 | This repo and its code | `grep`, `read`, run the tool or test |
| 2 | Live system state | `proxmox_*`, `technitium_*`, `mikromcp` via `bin/mcp-call.py`, `gh`, `vikunja` |
| 3 | Vendor docs, API reference, upstream source | `websearch` skill → `donsetch` |
| 4 | Blog, news, forum, another model's output | corroboration only — never load-bearing |

Stop at the first rung that answers the question. Rung 1 is cheaper than rung 3
every time: look before you search.

## Procedure

1. **Restate** the question and the decision it feeds, in one line. If the
   answer changes nothing, say so instead of researching it.
2. **Decompose** into the claims the answer depends on — you will source each.
3. **Walk the ladder** per claim, loading the domain skill that governs how that
   source is read (`django-expert`, `proxmox-cli`, `routeros`, `gh`, …).
4. **Cross-check** load-bearing claims: two independent sources, or one primary
   source plus a reproduction. Two pages quoting one press release are one
   source.
5. **Date it.** Record version and date for anything that drifts — APIs, prices,
   defaults, package behaviour. An undated fact is a guess with a citation.

## Output

    Answer: <one paragraph, direct>

    | Claim | Source | How verified |
    |---|---|---|
    | … | url / file:line / tool call | read / reproduced / cross-checked |

    Confidence: high | medium | low — <why>
    Unverified: <what you could not confirm, and what would confirm it>

Name the gaps. Silence about a gap reads as certainty.

## Do NOT

- Answer from memory because the question "feels" settled.
- Let one blog post carry a factual answer.
- Repeat a failed search verbatim — reformulate twice, then report the dead end.
- Pad a thin evidence base with confident prose.

## Related

`websearch` (the web rung's tool) · `knowledge-base` (write up what you learned) ·
`gh`, `github-cli` (issue and PR evidence)
