# OpsKit Roadmap

Generated: 2026-11-20

---

## Project Health Snapshot

| Metric | Value |
|---|---|
| Total commits | 427 |
| Local branches | 7 |
| Plan files | 30 (5 with status fields) |
| Proposals | 2 open (`mcp-credential-bootstrap`, `vikunja-unified-cli`) |
| Ansible roles | 17 (only 3 directly referenced: `caddy`, `docker`, `vaultwarden`) |
| Ansible playbooks | 31 |
| MCP servers | 8 |
| Bin scripts | 62 |
| Test files / suite | 86 / 1715 (1 broken: `test_local_config_isolation.py` import path) |
| Git size / total | 35M / 876M |
| Recent activity | 5 commits in last 30 days |

---

## Active Work

### OpsKit CLI & Agent Tooling

| Item | Plan | Branch | Status | Priority | Scope |
|---|---|---|---|---|---|
| **opskit go TUI launcher** | #437 | `454-fix-dead-symlinks` | In progress | High | Fuzzy-search project launcher, secrets passthru, skill symlink mgmt |
| **opskit go config-driven projects** | #440 | — | In progress | High | `~/.opskit/config.yml` for enabled projects, nested dir discovery |
| **opskit go picker columns + no timeout** | #442 | — | In progress | Medium | Fix fzf column layout, remove 60s timeout |
| **opencode upgrade check** | #444 | — | In progress | Medium | Pre-launch opencode version check + daily cache |
| **opskit doctor** | `opskit-doctor.md` | — | **Approved** (high) | High | Aggregate self-diagnostic + safe auto-fixes + lifecycle hygiene |

### DjangoCMS / LFNW Site

| Item | Plan | Branch | Status | Priority | Scope |
|---|---|---|---|---|---|
| **lfnw-django production deployment** | #460 | `deploy-lfnw-django` | In progress | High | Deploy Django CMS 5.x on nwt LXC (CT115), Caddy reverse proxy, dev↔live sync |
| **lfnw CI/CD pipeline** | `lfnw-django-cicd-pipeline.md` | `deploy-lfnw-django-work` | Draft (high) | High | Zero-downtime tagged releases, automatic rollback |

### MCP / Credential / Infra Tooling

| Item | Proposal | Status | Priority | Scope |
|---|---|---|---|---|
| **MCP credential bootstrap** | `mcp-credential-bootstrap.md` | **In progress** (pri:3) | High | `opskit mcp` CLI, `gen-mcp-config.py`, `install.sh` step_mcp() fix |
| **ERPNext/Frappe removal** | `#413` (7 stages: #458–#464) | **Planned** (D1: Vikunja) | High | Remove all ERPNext/Frappe ties: MCP server, Ansible roles (6), playbooks, skills, commands, tests, docs. 7 stages: safety net → add Vikunja backend → deprecate schema → remove wiring → migrate env layers → delete code → prove. |
| **Vikunja unified CLI** | `vikunja-unified-cli.md` | **Approved** | Medium | Single `bin/vikunja-cli.py` replacing `vikunja-manage-user.py` |

### Environment / Infrastructure

| Item | Plan | Status | Priority | Scope |
|---|---|---|---|---|
| **NWT→TNY environment migration** | 10-phase plan (master + 9 sub-plans) | Draft | High | Retire predecessor, rename infrastructure to TNY identity |
| **RouterOS TLS migration** | `issue-106.md` | Open | Medium | Enable TLS on all RouterOS REST API endpoints (HTTP→443) |
| **Tree-wide token audit** | `issue-170.md` | Open | Medium | Resolve client-token references flagged by publication-guard |
| **AGENTS.md governance audit** | `agents-md-governance-audit.md` | Open | Low | Fix redundancy, unclear guidance, broken refs in AGENTS.md + governance files |
| **Member-mount contract cleanup** | #415 (phase 3) | `415-member-mount-prune` | In progress | Medium | Prune native agents and skill references |
| **opencode.json + global-memory templates** | `issue-216.md` | Open | Low | Redacted templates for workstation/runner parity |
| **Scoped bw-session resolver** | `issue-221.md` | Open | Low | Resolve only the secrets an automation needs (not whole-vault) |

### In-Flight Branches (unpushed)

| Branch | Unique commits | Notes |
|---|---|---|
| `373-manage-llama-server-systemd-unit` | 2 | BMS-0700: llama server systemd unit + LLM cache cleanup |
| `415-member-mount-prune-deletes-native-agents-and-skill` | 0 | Phase 1-2 done, phase 3 pending (contract siblings branch) |
| `415-phase-3-contract-siblings` | 0 | Dependent on above |
| `454-fix-dead-symlinks` | 1 | Dead symlink doctor + check-global-skills.sh |
| `docs/session-note-2026-08-25` | 1 | Session note, not a plan |
| `feat/generic-search-members-skill` | 1 | Generic member-search reference skill |
| `main` | — | 77a5216 |

---

## Completed (Archive)

| Item | Plan | Closed | Notes |
|---|---|---|---|
| Bidirectional project connectivity | `bidirectional-project-connectivity.md` | #281 (2026-08-27) | `opskit init` wires bidirectional sync |
| LXC maintenance role | `370-lxc-maintenance` (merged, branch deleted) | — | `lxc_maintenance` ansible role (unattended-upgrades + disk-watch) |
| Fix test_reports_server_count CI | `issue-395-ci-test-npx.md` | #418 (ca66ae7) | Replaced npx placeholder with echo |

---

## Technical Debt

### Immediate (blocks progress)

| # | Finding | Impact | Effort |
|---|---|---|---|
| 1 | `test_local_config_isolation.py:22` imports `from tests.conftest` instead of `from conftest` | 1 test file fails to collect | 5 min |
| 2 | 5 local branches merged but still present (deleted in this session) | — | Done |

### Medium priority

| # | Finding | Impact | Effort |
|---|---|---|---|
| 3 | 14 of 17 ansible roles not referenced by any playbook | Stale code, confusion for new work | Review |
| 4 | `ansible_collections/` (45M) installed but `ansible_collections/` is gitignored | Hard to track versions across operators | `ansible-galaxy install -r requirements.yml` |
| 5 | `sys` file (42M) untracked, not in gitignore | Wastes disk, confusing | Delete or document |
| 6 | `.venv` (166M) — not in gitignore (but in `.git/info/exclude` via PEP 668) | Confusing size | Review `.gitignore` |
| 7 | 31 plan files, many are sub-phases of the same migration (NWT→TNY) | Hard to see the big picture | Consolidated in roadmap (this file) |
| 8 | `issues/` directory is empty — all converted to plans | No open issue backlog visible | Expected state |

### Low priority

| # | Finding | Impact |
|---|---|---|
| 9 | `.git` (35M) growing — no unreachable objects after gc | Normal |
| 10 | `grind-state.md` (881 bytes) — grinder state file | Expected |
| 11 | `proxmox-jobs.sqlite3` (40K) — tracked, not in gitignore | Acceptable |

---

## Open Questions

1. **NWT→TNY migration** — master plan is draft, depends on helpdesk retirement decision. 10 phases (G0–G10) spanning DNS, SSH, Caddy, WireGuard, Vault, Ansible, cleanup.
2. **Vikunja Pro license** — determines whether admin API path in `vikunja-unified-cli` is worth investing in now.
3. **opskit doctor** — approved, high priority. Needs scoping and implementation plan.
4. **Wazuh monitoring stack** — work was committed to main then removed. Restore or abandon?
5. **Ansible role cleanup** — 14 orphaned roles. Delete, or move to `provision-*` playbooks where needed?

---

## Milestones (Target Order)

1. **Merge in-flight work** — push `373-`, `454-fix-dead-symlinks`, `feat/generic-search-members-skill`, `deploy-lfnw-django`
2. **Fix test suite** — fix `test_local_config_isolation.py` import path
3. **Ansible role audit** — delete or wire in orphaned roles
4. **opskit doctor** — implement approved plan
5. **NWT→TNY migration** — execute phase G0 (access proof, snapshots)
6. **MCP credential bootstrap** — complete in-progress work
7. **Vikunja unified CLI** — implement approved proposal
8. **ERPNext/Frappe removal** — execute 7-stage plan (#413, sub-issues #458–#464)
9. **RouterOS TLS migration** — `issue-106`
10. **Token audit** — `issue-170`
