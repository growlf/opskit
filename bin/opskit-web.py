#!/usr/bin/env python3
"""
opskit-web.py — Thin wrapper for opencode web --mdns.

Sets up skills and secrets (same as opskit go), then launches:
  opencode web --mdns
"""

import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
_OPSKIT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(_OPSKIT_ROOT))


def run_openskill_setup():
    """Run opskit-skills.py setup (best-effort)."""
    try:
        subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "opskit-skills.py"), "setup"],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass


def get_bw_session():
    """Get BW_SESSION via opskit-secrets.py."""
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "opskit-secrets.py"), "bitwarden-session"],
            capture_output=True, text=True, timeout=30,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def main():
    # 1. Setup skills
    run_openskill_setup()

    # 2. Get BW_SESSION
    bw_session = get_bw_session()

    # 3. Launch opencode web --mdns
    env = os.environ.copy()
    if bw_session:
        env["BW_SESSION"] = bw_session

    try:
        os.execvpe("opencode", ["opencode", "web", "--mdns"], env)
    except FileNotFoundError:
        print("Error: opencode not found on PATH", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
