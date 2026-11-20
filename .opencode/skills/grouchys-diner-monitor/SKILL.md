---
name: grouchys-diner-monitor
description: Monitor grouchysdiner.com infrastructure state over time. Capture snapshots, compare changes, generate reports. Use when user asks about grouchysdiner.com, its status, or what changed.
mode: skill
triggers: grouchysdiner, grouchys diner, grouchys monitor, grouchys status, grouchysdiner.com monitoring
---

# grouchys-diner-monitor

> Load this skill when: the user asks about grouchysdiner.com's infrastructure
> state, what changed, or wants to run a monitoring check.

## What this is

A read-only monitoring system for `grouchysdiner.com`. It captures DNS, HTTP/HTTPS
status, page titles, security headers, platform detection, and issue flags into
structured JSON snapshots. Comparing snapshots shows what changed over time.

The system is **not our responsibility** — `grouchysdiner.com` is owned by a
separate party. We removed all local references to it from this repo on 2026-11-04.
The monitoring is purely observational.

## Where it lives

```
~/Documents/Reports/GrouchysDiner/
├── capture-state.sh        — runs all probes, saves snapshot file
├── compare-snapshots.sh    — diffs two snapshots
├── grouchysdiner.com-assessment-2026-11-04.md  — initial full report
├── README.md              — usage instructions
└── snapshot-*.json        — auto-generated state snapshots
```

## How to use

### Capture current state

```bash
cd ~/Documents/Reports/GrouchysDiner
bash capture-state.sh
```

Creates `snapshot-YYYY-MM-DD_HH-MM-SS.json`. Run it once per check.

### Compare against previous run

```bash
cd ~/Documents/Reports/GrouchysDiner
bash compare-snapshots.sh
```

Compares the two most recent snapshots. Shows only fields that changed.

### Compare specific files

```bash
bash compare-snapshots.sh snapshot-2026-11-04_18-10-00.json snapshot-2026-11-05_09-00-00.json
```

### Quick check (no file management)

```bash
cd ~/Documents/Reports/GrouchysDiner
bash capture-state.sh && bash compare-snapshots.sh
```

## What gets captured

| Category | Fields |
|---|---|
| **DNS** | A records for apex, www, erp, vault |
| **HTTP (apex)** | Status line, page title, server header, security headers, cookies, canonical/OG URLs |
| **HTTPS (apex)** | Status line (confirms TLS works) |
| **Subdomains** | Status + title for www, erp, vault |
| **Content** | Platform detection (Odoo, ERPNext, Vaultwarden), Cloudflare at www |
| **Issues** | Auto-detected: no HTTPS, canonical leaks IP, insecure cookie, misconfigured subdomains, www redirecting away |

## Snapshot JSON shape

```json
{
  "timestamp": "2026-11-05T02:06:23Z",
  "dns": { "apex": "...", "www": "...", "erp": "...", "vault": "..." },
  "http_apex": {
    "status_line": "HTTP/1.1 200 OK",
    "title": "...",
    "server": "nginx",
    "has_security_headers": true,
    "canonical_url": "...",
    "og_url": "...",
    "cookie_secure": false
  },
  "https_apex": { "status_line": "CONNECTION_FAILED" },
  "subdomains": {
    "www": { "status": "...", "title": "...", "redirect_target": "..." },
    "erp": { "status": "...", "title": "..." },
    "vault": { "status": "...", "title": "..." }
  },
  "content": {
    "platform_odoo": true,
    "platform_erpnext": false,
    "platform_vaultwarden": false,
    "cloudflare_at_www": true
  },
  "issues": {
    "no_https": true,
    "canonical_leaks_ip": true,
    "cookie_not_secure": true,
    "subdomains_misconfigured": true,
    "www_redirects_away": true
  }
}
```

## Interpretation guide

When reporting results, use this context:

- **no_https: true** → No TLS at all. The domain serves HTTP only. This is the highest-priority issue.
- **canonical_leaks_ip: true** → The site embeds its server IP in `<link rel="canonical">` and OpenGraph tags, exposing infrastructure details.
- **cookie_not_secure: true** → Session cookies lack the `Secure` flag — sent over plaintext HTTP.
- **subdomains_misconfigured: true** → `erp.` and `vault.` subdomains resolve to the same server as the apex and serve identical content. They should point elsewhere or redirect.
- **www_redirects_away: true** → `www.` redirects to a third-party site (Square). This may be intentional.
- **platform_odoo: true** → The site runs on Odoo 18.0, not ERPNext/Frappe as originally planned.
- **cloudflare_at_www: true** → The www subdomain goes through Cloudflare's Anycast CDN.

## Safety

- **Read-only.** Never modify anything at `grouchysdiner.com`.
- **Never touch their Cloudflare account.** The domain belongs to another party.
- **Snapshots are local only.** No data leaves this machine.
- **All probes use short timeouts** (5–10s) — safe to run from any session.

## Related

`grouchysdiner.com-assessment-2026-11-04.md` — the original full assessment report.
