#!/usr/bin/env python3
"""check-mcp-wiring.py — flag MCP entries wired to copies outside this repo.

Every copy-drift incident of 2026-08 had the same shape: a sibling checkout's
copy kept executing long after this repo's version became canonical, and
nothing could tell it was stale (issues #80/#81, #143, #146). This reporter
makes that staleness LOUD: it reads the local opencode config and flags any
MCP server this repo ships that is wired to run from somewhere else.

Verdicts per configured MCP entry naming a shipped server:
  ERROR — command resolves through a filesystem path outside this repo:
          a sibling checkout's copy is live. Exit 1.
  WARN  — command uses a package runner (uvx/npx/pipx) instead of the
          in-repo server: a duplicate implementation exists. Exit 0.

Entries for servers this repo does not ship (other projects' MCP servers,
external services) are normally none of our business.  The catalog
(external-servers.json) is advisory — it is not a policy.  If a declared
external server uses a package runner instead of bin/mcp-run.sh the
reporter prints an INFO note (not a warning) to point out the routing gap.
If an undeclared server uses a package runner the reporter prints an INFO
note suggesting catalog addition so the launcher can resolve vault sessions
(e.g. the bitwarden MCP server).

Usage:
  bin/check-mcp-wiring.py [--config PATH]

Config path default: ~/.config/opencode/opencode.json
Repo root: OPSKIT_ROOT env var > this script's parent directory. (OPSKIT_ROOT
is the caller-overridable DATA root elsewhere; here the check is about THIS
checkout, so the script's own location is the honest default.)
"""

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_REPO = Path(__file__).resolve().parent.parent
PACKAGE_RUNNERS = ('uvx', 'npx', 'pipx')


def shipped_servers(repo: Path) -> set[str]:
    """Server names this repo can launch — derived from bin/mcp-run.sh --list's
    source of truth: mcp/*-mcp-server.py plus generated external configs."""
    names = {
        p.name.removesuffix('-mcp-server.py')
        for p in (repo / 'mcp').glob('*-mcp-server.py')
    }
    # mikromcp is launched via generated config rather than an in-repo *.py
    if (repo / 'bin' / 'gen-mikromcp-config.py').exists():
        names.add('mikromcp')
    return names


def external_server_names(repo: Path) -> set[str]:
    """Names registered in mcp/external-servers.json."""
    ext_map = repo / 'mcp' / 'external-servers.json'
    if not ext_map.exists():
        return set()
    try:
        return set(json.loads(ext_map.read_text())) - {k for k in json.loads(ext_map.read_text()) if k.startswith('_')}
    except Exception:
        return set()


def command_text(entry) -> str:
    """opencode accepts a string or argv list for an MCP server command."""
    cmd = entry.get('command') if isinstance(entry, dict) else None
    if isinstance(cmd, list):
        return ' '.join(str(c) for c in cmd)
    return str(cmd or '')


def check(config: dict, repo: Path) -> tuple[list[str], list[str], list[str]]:
    """Returns (errors, warnings, infos)."""
    servers = shipped_servers(repo)
    ext_names = external_server_names(repo)
    errors, warnings, infos = [], [], []

    for name, entry in (config.get('mcp') or {}).items():
        cmd = command_text(entry)
        if not cmd:
            continue
        hit = next(
            (s for s in servers
             if s in name or s in cmd),
            None)
        if hit is None:
            continue
        if str(repo) in cmd:
            continue  # wired to this checkout — correct
        first = cmd.split()[0] if cmd.split() else ''
        if os.path.basename(first) in PACKAGE_RUNNERS:
            warnings.append(
                f"{name}: shipped server '{hit}' runs via package runner "
                f"({first}) — duplicate implementation of {repo}/mcp; "
                f"consider bin/mcp-run.sh {hit}")
        elif '/' in cmd:
            errors.append(
                f"{name}: shipped server '{hit}' executes from OUTSIDE this "
                f"repo: {cmd} — a sibling checkout's copy is live "
                f"(fix: {repo}/bin/mcp-run.sh {hit})")
        else:
            warnings.append(
                f"{name}: shipped server '{hit}' wired as '{cmd}' — "
                f"not this repo's launcher; verify intentional")

    # Verify external-servers.json entries are actually routed through
    # mcp-run.sh in opencode.json (not via a bare package runner).
    # This catches the class of defect where a server is declared in the
    # catalog but opencode.json launches it directly, bypassing the session
    # resolver (opskit #386 — the bitwarden MCP server).
    #
    # Note: this is informational, not a warning.  The catalog is advisory —
    # users may run the MCP server with a different vault solution (or none
    # at all) and that's fine.  We just point out the routing gap.
    run_sh = f'{repo}/bin/mcp-run.sh'
    for name in ext_names:
        if name in servers:
            continue  # shipped server, handled above
        entry = config.get('mcp', {}).get(name)
        if not entry:
            continue
        cmd = command_text(entry)
        if not cmd:
            continue
        first = cmd.split()[0] if cmd.split() else ''
        if os.path.basename(first) in PACKAGE_RUNNERS and run_sh not in cmd:
            ext_map_rel = str((repo / 'mcp' / 'external-servers.json').relative_to(repo.parent))
            infos.append(
                f"{name}: declared in {ext_map_rel} but opencode routes "
                f"via package runner ({first}) instead of bin/mcp-run.sh {name} — "
                f"the launcher will resolve vault sessions for this server")

    # For non-shipped servers using a package runner that are also not in
    # external-servers.json, suggest adding the entry so the launcher can
    # handle vault sessions.
    for name, entry in (config.get('mcp') or {}).items():
        cmd = command_text(entry)
        if not cmd:
            continue
        first = cmd.split()[0] if cmd.split() else ''
        if os.path.basename(first) not in PACKAGE_RUNNERS:
            continue
        if name in servers or name in ext_names:
            continue  # already handled or known
        ext_map_rel = str((repo / 'mcp' / 'external-servers.json').relative_to(repo.parent))
        warnings.append(
            f"{name}: uses package runner ({first}) but is not declared in "
            f"{ext_map_rel}; if this server needs vault-session support, "
            f"add it to mcp/external-servers.json so bin/mcp-run.sh can launch it")

    return errors, warnings, infos


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--config',
                    default=os.path.expanduser('~/.config/opencode/opencode.json'))
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        print(f"NOTE: no opencode config at {cfg_path} — nothing to check.")
        return 0
    try:
        # JSONC is legal (opencode configs carry "//" comments); strip
        # line-leading comments before json.load so the parser doesn't choke.
        text = cfg_path.read_text()
        lines = text.splitlines()
        clean = '\n'.join(
            line for line in lines
            if not line.lstrip().startswith('//')
        )
        config = json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"ERROR: {cfg_path} is not valid JSON: {e}")
        return 1

    repo = Path(os.environ.get('OPSKIT_ROOT', SCRIPT_REPO)).resolve()
    errors, warnings, infos = check(config, repo)

    for i in infos:
        print(f"INFO  {i}")
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    if errors:
        print(f"\n{len(errors)} sibling-checkout execution(s) — "
              "this is the drift bin/mcp-run.sh exists to end (#146).")
        return 1
    if not warnings and not infos:
        print("MCP wiring clean: every shipped server runs from this repo.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
