#!/usr/bin/env python3
"""
opskit-secrets.py — Secrets engine router.

Routes secret resolution to the configured engine based on:
  1. ~/.opskit/projects/<project-name>/secrets.yml (per-project override)
  2. ~/.opskit/secrets.yml (global fallback)

Supported engines:
  - bitwarden: calls ~/Projects/opskit/bin/bwunlock.sh, reads session output
  - env: reads from an environment variable specified in config

Usage:
  opskit-secrets.py bitwarden-session

Output: the resolved secret value to stdout.
Error: prints to stderr and exits 1 if resolution fails.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
_OPSKIT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(_OPSKIT_ROOT))

from opskit._cache import CACHE_DIR

GLOBAL_SECRETS_FILE = CACHE_DIR / "secrets.yml"
PROJECT_SECRETS_DIR = CACHE_DIR / "projects"


def _read_yaml_simple(path: Path):
    """Read a simple YAML file. Falls back to empty dict on error."""
    try:
        import yaml
        if not path.exists():
            return {}
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return data or {}
    except Exception:
        return {}


def _resolve_engine(project_path: str = None):
    """Resolve the secrets engine from config.

    Checks:
    1. Per-project secrets.yml (if project_path provided)
    2. Global secrets.yml
    3. Default: bitwarden
    """
    engine = "bitwarden"  # Default

    # Per-project override
    if project_path:
        project_name = Path(project_path).name
        project_secrets = PROJECT_SECRETS_DIR / project_name / "secrets.yml"
        data = _read_yaml_simple(project_secrets)
        if "engine" in data:
            return data["engine"]

    # Global fallback
    data = _read_yaml_simple(GLOBAL_SECRETS_FILE)
    if "engine" in data:
        return data["engine"]

    return engine


def resolve_bitwarden_session():
    """Resolve the vault session token.

    Delegates to bin/bw_session.py — the single source of truth for the
    env-wins rule, the session file path and the permission check (#155/#378).
    bin/bwunlock.sh (default mode) is called first to refresh a stale/absent
    session; it never prints the token, only writes the cache file.
    Returns '' when no usable session is available (non-fatal).
    """
    bwunlock_sh = _OPSKIT_ROOT / 'bin' / 'bwunlock.sh'
    bw_session_py = _OPSKIT_ROOT / 'bin' / 'bw_session.py'

    if bwunlock_sh.exists():
        try:
            subprocess.run(['bash', str(bwunlock_sh)],
                           capture_output=True, text=True, timeout=60)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

    try:
        result = subprocess.run(
            [sys.executable, str(bw_session_py), '--token'],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # Fall back to an explicitly exported token if the resolver is unavailable.
    return os.environ.get('BW_SESSION', '')


def resolve_env_secret(config_key: str = None):
    """Resolve a secret from an environment variable.

    The env var name is specified in the secrets.yml config:
      engine: env
      env_var: MY_SECRET_VAR
    """
    data = _read_yaml_simple(GLOBAL_SECRETS_FILE)
    env_var = data.get("env_var", "") if not config_key else config_key

    if not env_var:
        print("Error: no env_var specified in secrets config", file=sys.stderr)
        return None

    return os.environ.get(env_var, "")


def main():
    parser = argparse.ArgumentParser(description="Resolve secrets via configured engine")
    parser.add_argument("secret_name", help="Name of the secret to resolve (e.g. bitwarden-session)")

    args = parser.parse_args()

    # Determine project path from environment (set by opskit-go.py)
    project_path = os.environ.get("OPSKIT_PROJECT_PATH", "")

    # Resolve engine
    engine = _resolve_engine(project_path if project_path else None)

    if args.secret_name == "bitwarden-session":
        if engine == "bitwarden":
            session = resolve_bitwarden_session()
            if session:
                print(session, end="")
            else:
                # Non-fatal: continue without session
                pass
        elif engine == "env":
            session = resolve_env_secret()
            if session:
                print(session, end="")
        else:
            print(f"Error: unknown engine '{engine}' for bitwarden-session", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Error: unknown secret name '{args.secret_name}'", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
