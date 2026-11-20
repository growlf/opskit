1:# OpsKit Roadmap
1:
1:Generated: 2026-11-20
1:
1:---
1:
1:## Project Health Snapshot
1:
1:| Metric | Value |
1:|---|---|
1:| Total commits | 431 |
1:| Local branches | 1 (main) |
1:| Plan files | 30 (5 with status fields) |
1:| Proposals | 2 open (`mcp-credential-bootstrap`, `vikunja-unified-cli`) |
1:| Ansible roles | 17 (only 3 directly referenced: `caddy`, `docker`, `vaultwarden`) |
1:| Ansible playbooks | 31 |
1:| MCP servers | 8 |
1:| Bin scripts | 62 |
1:| Test files / suite | 86 / 1715 (all passing) |
1:| Git size / total | 35M / 876M |
1:| Recent activity | 5 commits in last 30 days |
1:
1:---
1:
1:## Active Work
1:
1:### OpsKit CLI & Agent Tooling
1:
1:| Item | Plan | Branch | Status | Priority | Scope |
1:|---|---|---|---|---|---|
1:| **opskit go TUI launcher** | #437 | `454-fix-dead-symlinks` | In progress | High | Fuzzy-search project launcher, secrets passthru, skill symlink mgmt |
1:| **opskit go config-driven projects** | #440 | — | In progress | High | `~/.opskit/config.yml` for enabled projects, nested dir discovery |
1:| **opskit go picker columns + no timeout** | #442 | — | In progress | Medium | Fix fzf column layout, remove 60s timeout |
1:| **opencode upgrade check** | #444 | — | In progress | Medium | Pre-launch opencode version check + daily cache |
1:| **opskit doctor** | `opskit-doctor.md` | — | **Approved** (high) | High | Aggregate self-diagnostic + safe auto-fixes + lifecycle hygiene |
1:
1:### DjangoCMS / LFNW Site
1:
1:| Item | Plan | Branch | Status | Priority | Scope |
1:|---|---|---|---|---|---|
1:| **lfnw-django production deployment** | #460 | `deploy-lfnw-django` | In progress | High | Deploy Django CMS 5.x on nwt LXC (CT115), Caddy reverse proxy, dev↔live sync |
1:| **lfnw CI/CD pipeline** | `lfnw-django-cicd-pipeline.md` | `deploy-lfnw-django-work` | Draft (high) | High | Zero-downtime tagged releases, automatic rollback |
1:
1:### MCP / Credential / Infra Tooling
1:
1:| Item | Proposal | Status | Priority | Scope |
1:|---|---|---|---|---|
1:| **MCP credential bootstrap** | `mcp-credential-bootstrap.md` | **In progress** (pri:3) | High | `opskit mcp` CLI, `gen-mcp-config.py`, `install.sh` step_mcp() fix |
1:| **ERPNext/Frappe removal** | `#413` (7 stages: #458–#464) | **Stage 0: safety net done** — inventory + tag `erpNext-removal-safety-net-20261120`. Remaining: Stage 1 (Vikunja backend), 2 (deprecate schema), 3 (remove wiring), 4 (migrate env layers), 5 (delete code), 6 (delete tests), 7 (prove) | High |
1:| **Vikunja unified CLI** | `vikunja-unified-cli.md` | **Approved** | Medium | Single `bin/vikunja-cli.py` replacing `vikunja-manage-user.py` |
1:
1:### Environment / Infrastructure
1:
1:| Item | Plan | Status | Priority | Scope |
1:|---|---|---|---|---|
1:| **NWT→TNY environment migration** | 10-phase plan (master + 9 sub-plans) | Draft | High | Retire predecessor, rename infrastructure to TNY identity |
1:| **RouterOS TLS migration** | `issue-106.md` | Open | Medium | Enable TLS on all RouterOS REST API endpoints (HTTP→443) |
1:| **Tree-wide token audit** | `issue-170.md` | Open | Medium | Resolve client-token references flagged by publication-guard |
1:| **AGENTS.md governance audit** | `agents-md-governance-audit.md` | Open | Low | Fix redundancy, unclear guidance, broken refs in AGENTS.md + governance files |
1:| **Member-mount contract cleanup** | #415 (phase 3) | `415-member-mount-prune` | In progress | Medium | Prune native agents and skill references |
1:| **opencode.json + global-memory templates** | `issue-216.md` | Open | Low | Redacted templates for workstation/runner parity |
1:| **Scoped bw-session resolver** | `issue-221.md` | Open | Low | Resolve only the secrets an automation needs (not whole-vault) |
1:

**All previously listed branches have been merged to main. No unpushed in-flight branches remain.**
1:---
1:
1:## Completed (Archive)
1:
1:| Item | Plan | Closed | Notes |
1:|---|---|---|---|
1:| Bidirectional project connectivity | `bidirectional-project-connectivity.md` | #281 (2026-08-27) | `opskit init` wires bidirectional sync |
1:| LXC maintenance role | `370-lxc-maintenance` (merged, branch deleted) | — | `lxc_maintenance` ansible role (unattended-upgrades + disk-watch) |
1:| Fix test_reports_server_count CI | `issue-395-ci-test-npx.md` | #418 (ca66ae7) | Replaced npx placeholder with echo |
1:
1:---
1:
1:## Technical Debt
1:
1:### Immediate (blocks progress)
1:
1:| # | Finding | Impact | Effort |
1:|---|---|---|---|
| 1 | `test_local_config_isolation.py:22` import path — **fixed** (commit `8cc70e6`) | 1 test file was failing to collect | Done |
| 2 | Stale local branch refs (deleted in this session) | — | Done |
1:
1:### Medium priority
1:
1:| # | Finding | Impact | Effort |
1:|---|---|---|---|
1:| 3 | 14 of 17 ansible roles not referenced by any playbook | Stale code, confusion for new work | Review |
1:| 4 | `ansible_collections/` (45M) installed but `ansible_collections/` is gitignored | Hard to track versions across operators | `ansible-galaxy install -r requirements.yml` |
1:| 5 | `sys` file (42M) untracked, not in gitignore | Wastes disk, confusing | Delete or document |
1:| 6 | `.venv` (166M) — not in gitignore (but in `.git/info/exclude` via PEP 668) | Confusing size | Review `.gitignore` |
1:| 7 | 31 plan files, many are sub-phases of the same migration (NWT→TNY) | Hard to see the big picture | Consolidated in roadmap (this file) |
1:| 8 | `issues/` directory is empty — all converted to plans | Expected state |
1:
1:### Low priority
1:
1:| # | Finding | Impact |
1:|---|---|---|
1:| 9 | `.git` (35M) growing — no unreachable objects after gc | Normal |
1:| 10 | `grind-state.md` (881 bytes) — grinder state file | Expected |
1:| 11 | `proxmox-jobs.sqlite3` (40K) — tracked, not in gitignore | Acceptable |
1:
1:---
1:
1:## Open Questions
1:
1:1. **NWT→TNY migration** — master plan is draft, depends on helpdesk retirement decision. 10 phases (G0–G10) spanning DNS, SSH, Caddy, WireGuard, Vault, Ansible, cleanup.
1:2. **Vikunja Pro license** — determines whether admin API path in `vikunja-unified-cli` is worth investing in now.
1:3. **opskit doctor** — approved, high priority. Needs scoping and implementation plan.
1:4. **Wazuh monitoring stack** — work was committed to main then removed. Restore or abandon?
1:5. **Ansible role cleanup** — 14 orphaned roles. Delete, or move to `provision-*` playbooks where needed?
1:
1:---
1:
1:## Milestones (Target Order)
1:
1. **Merge in-flight work** — **done** (commit `9f8f94c`, all branches merged)
2. **Fix test suite** — **done** (commit `8cc70e6`)
1:3. **Ansible role audit** — delete or wire in orphaned roles
1:4. **opskit doctor** — implement approved plan
1:5. **NWT→TNY migration** — execute phase G0 (access proof, snapshots)
1:6. **MCP credential bootstrap** — complete in-progress work
1:7. **Vikunja unified CLI** — implement approved proposal
1:8. **ERPNext/Frappe removal** — execute 7-stage plan (#413, sub-issues #458–#464)
1:9. **RouterOS TLS migration** — `issue-106`
1:10. **Token audit** — `issue-170`
