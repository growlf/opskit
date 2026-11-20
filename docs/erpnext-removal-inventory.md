# ERPNext/Frappe Removal — Inventory (Safety Net)

**Created:** 2026-11-20  
**Tag:** `erpNext-removal-safety-net-20261120`  
**Issue:** #413 (7 stages: #458–#464)  
**Status:** Stage 0 (safety net) — inventory only, no changes

---

## Stage 1: Add Vikunja Backend
- Migrate all ticket CRUD from ERPNext/Frappe API to Vikunja
- New scripts/skills will use Vikunja API

## Stage 2: Deprecate Schema
- Remove ERPNext/Frappe references from `schemas/env.schema.json`

## Stage 3: Remove Wiring
- Remove `erpnext_*` from `opencode.json` deny-globs and MCP launcher
- Update `bin/mcp-run.sh`, `bin/gen-mcp-config.py`
- Update `AGENTS.md`, `agents/code-reviewer.md`, `.claude/agents/code-reviewer.md`

## Stage 4: Migrate Env Layers
- Update `environments/*/` (bms, nwt, yc) — gitignored private repos
- Remove ERPNext host vars, device datasets, session notes

## Stage 5: Delete Code
- Delete `mcp/erpnext-mcp-server.py`
- Delete `ansible/roles/frappe-upgrade/`, `frappe-bench/`, `frappe-site/`, `frappe-dependencies/`, `mariadb-frappe/`, `erp_stack/`
- Delete `ansible/playbooks/provision-erpnext-dev-lxc.yml`
- Delete `bin/frappe-exec.py`
- Delete `.opencode/command/frappe-access.md`, `.opencode/skills/frappe-access/SKILL.md`
- Delete `docs/erpnext-mcp-setup.md`

## Stage 6: Delete Tests
- Delete `tests/test_erpnext_mcp_server.py`
- Delete `tests/test_frappe_exec.py`
- Delete `tests/test_erpnext_dev_lxc_playbook.py`

## Stage 7: Prove
- Full test suite passes
- `make test` clean
- CI green
- Announce removal complete

---

## Complete File Inventory

### Direct ERPNext/Frappe files (to be deleted in Stage 5)

| # | Path | Description |
|---|------|-------------|
| 1 | `mcp/erpnext-mcp-server.py` | ERPNext MCP server (tool: erpnext_*) |
| 2 | `ansible/roles/frappe-upgrade/` | Frappe upgrade Ansible role (11 files) |
| 3 | `ansible/roles/frappe-bench/` | Frappe bench Ansible role (2 files) |
| 4 | `ansible/roles/frappe-site/` | Frappe site Ansible role (2 files) |
| 5 | `ansible/roles/frappe-dependencies/` | Frappe dependencies role (2 files) |
| 6 | `ansible/roles/mariadb-frappe/` | MariaDB for Frappe role (2 files) |
| 7 | `ansible/roles/erp_stack/` | ERP stack Ansible role (3 files) |
| 8 | `ansible/playbooks/provision-erpnext-dev-lxc.yml` | ERPNext dev LXC provision |
| 9 | `bin/frappe-exec.py` | Frappe exec wrapper script |
| 10 | `.opencode/command/frappe-access.md` | /frappe-access command |
| 11 | `.opencode/skills/frappe-access/SKILL.md` | frappe-access skill |
| 12 | `docs/erpnext-mcp-setup.md` | ERPNext MCP setup docs |

### Indirect references (to be cleaned in Stages 2-3)

| # | Path | What references erpnext/frappe |
|---|------|-------------------------------|
| 13 | `opencode.json` | `erpnext_*` deny-glob in tools section |
| 14 | `AGENTS.md` | frappe-access skill registration, erpnext references |
| 15 | `agents/code-reviewer.md` | `erpnext_*` deny in tool permissions |
| 16 | `.claude/agents/code-reviewer.md` | `erpnext_*` deny in tool permissions |
| 17 | `bin/mcp-run.sh` | erpnext MCP server launch path |
| 18 | `bin/gen-mcp-config.py` | erpnext MCP config generation |
| 19 | `bin/hd-ticket-triage.py` | frappe API calls for ticket triage |
| 20 | `bin/open-ticket.sh` | frappe API calls for ticket creation |
| 21 | `bin/triage.py` | frappe references in triage logic |
| 22 | `schemas/env.schema.json` | frappe/erpnext in env schema |
| 23 | `templates/opencode.json` | template with erpnext deny-globs |
| 24 | `templates/global-memory.md` | template with frappe references |
| 25 | `rules/no-plaintext-creds.md` | erpnext credential examples |
| 26 | `.opencode/rules/iac-required.md` | erpnext in IaC examples |
| 27 | `.opencode/command/helpdesk-ticket.md` | frappe access in helpdesk command |
| 28 | `.opencode/skills/helpdesk-ticket/SKILL.md` | frappe API references |
| 29 | `.opencode/skills/dogfood-cycle/SKILL.md` | frappe references |
| 30 | `.opencode/skills/ticket-triage/SKILL.md` | frappe references |
| 31 | `.ansible-lint.yml` | excludes for frappe roles |

### Test files (to be deleted in Stage 6)

| # | Path | Description |
|---|------|-------------|
| 32 | `tests/test_erpnext_mcp_server.py` | ERPNext MCP server tests |
| 33 | `tests/test_frappe_exec.py` | frappe-exec script tests |
| 34 | `tests/test_erpnext_dev_lxc_playbook.py` | ERPNext playbook tests |

### Plan/proposal files (to be cleaned in Stage 3)

| # | Path | What references erpnext/frappe |
|---|------|-------------------------------|
| 35 | `plans/environment-migration-nwt-cs-to-tny.md` | migration references |
| 36 | `plans/environment-migration-nwt-cs-to-tny-ansible.md` | migration references |
| 37 | `plans/issue-170.md` | token audit references |
| 38 | `plans/issue-216.md` | opencode.json template references |
| 39 | `plans/mcp-credential-bootstrap.md` | MCP credential references |
| 40 | `proposals/mcp-credential-bootstrap.md` | MCP proposal references |

### Documentation (to be cleaned in Stage 3)

| # | Path | What references erpnext/frappe |
|---|------|-------------------------------|
| 41 | `docs/ARCHITECTURE.md` | architecture references |
| 42 | `docs/CONTRIBUTING.md` | contributing references |
| 43 | `docs/DEV-GUIDE.md` | dev guide references |
| 44 | `docs/ENVIRONMENT.md` | environment references |
| 45 | `docs/INSTALL.md` | install references |
| 46 | `docs/kb/mcp-session-restart.md` | kb article references |
| 47 | `docs/kb/README.md` | kb readme references |
| 48 | `docs/ideas.md` | idea references |
| 49 | `SESSION-LOG.md` | session log references |

### Environment layers (to be cleaned in Stage 4)
- `environments/bms/` — host vars, datasets, session notes referencing frappe/erpnext
- `environments/nwt/` — host vars, datasets, scripts, session notes referencing frappe/erpnext
- `environments/yc/` — session notes referencing frappe/erpnext
- `environments/example/env.yml` — example env template

### Other references

| # | Path | What references erpnext/frappe |
|---|------|-------------------------------|
| 50 | `.reconcile/actions.json` | reconciliation action references |

---

## Counts

| Category | Count |
|----------|-------|
| Direct ERPNext/Frappe files (delete) | 12 |
| Indirect references (clean) | 18 |
| Test files (delete) | 3 |
| Plans/proposals (clean) | 6 |
| Documentation (clean) | 9 |
| Environment layers (clean) | 3 envs |
| Other (clean) | 1 |
| **Total files to touch** | **~52** |

---

## Rollback

If any stage breaks the suite:
1. Reset to tag: `git checkout erpNext-removal-safety-net-20261120 -- .`
2. Or revert individual commits
3. Tag should NEVER be deleted until all 7 stages are verified complete
