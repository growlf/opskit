# OpsKit Reference — opskit

This project is wired to **OpsKit** via `.opskit/pack.yml`.
OpsKit's tools, subagents, and skills are available when working on this project
from an OpsKit-managed session.

## Quick reference

### Member commands (from OpsKit root)

```bash
opskit member status       # show mount state for all members
opskit member sync         # clone/pull members + symlinks
opskit member mount        # validate + render agents/skills
opskit member sync-mount   # sync + mount in one step
opskit member prune        # remove stale rendered items
```

### From this project

```bash
opskit check               # validate .opskit/pack.yml against schema
```

## What gets mounted

When `opskit member sync-mount` runs from OpsKit, it renders:

- **Agents** (`agents/*.md`) — subagent definitions that can be invoked via `@name`
- **Skills** (`.opencode/skills/`) — loadable workflows for `opencode tool skill use <name>`
- **Rules** (`.opencode/rules/`) — guardrails that apply to sessions in this project

All mounted items are **read-only** from OpsKit's perspective.
Changes to agents/skills/rules should be made in this project's source and
re-synced.

## Trust levels

The `trust` field in `.opskit/pack.yml` controls what mounted agents can do:

- `read` — documentation and reference only, no tool calls
- `suggest` — may suggest commands but not execute them
- `execute` — may run non-destructive commands
- `admin` — full tool access (use with caution)

## Keeping it aligned

After making changes to agents, skills, or rules in this project, re-sync:

```bash
# From OpsKit root:
opskit member sync-mount
```

For the full design, see `docs/design/member-mount.md` in the OpsKit repo.
