# Knowledge Base

Troubleshooting findings and solutions, captured so they don't have to be
re-discovered. One file per topic in this directory, written under the
Knowledge Base template in `.opencode/skills/templates/SKILL.md`. Use the
`knowledge-base` skill when adding or updating an entry.

## Entries

- [`initramfs-troubleshooting.md`](initramfs-troubleshooting.md) — boot drops
  to an `initramfs>` prompt; how to repair the root filesystem.
- [`mcp-session-restart.md`](mcp-session-restart.md) — after a machine crash,
  secret-dependent MCP servers show "Connection closed"; closing the whole
  shell fixes it.
- [`vikunja-mcp-update-wipes-fields.md`](vikunja-mcp-update-wipes-fields.md) —
  `update_task` with a partial body clears `description` and resets `priority`;
  always send the complete task (reactions/related_tasks = `null`, not `[]`).
- [`opencode-desktop-window-never-opens.md`](opencode-desktop-window-never-opens.md)
  — OpenCode desktop is "running" but no window ever appears; a wedged
  Electron child-process bootstrap plus single-instance lock; kill to recover.
- [`frappe-500-after-restart-db-grant.md`](frappe-500-after-restart-db-grant.md) —
  a Frappe site 500s after a container restart because its DB user was granted for
  one container IP instead of `%`; diagnose from the backend log, fix the grant.
- [`bitwarden-cli-serves-stale-cache.md`](bitwarden-cli-serves-stale-cache.md) —
  `bw list` answers from its local cache even while locked, so "not in the vault"
  can be false; `lastSync` is the only freshness signal, and a TTY-less prompt
  reads as an empty result.
