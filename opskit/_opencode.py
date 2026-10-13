#!/usr/bin/env python3
"""
_opencode.py — opencode version detection + upgrade-check helpers.

Pure parsing/comparison helpers plus thin subprocess wrappers, so the
``opskit go`` pre-launch check can be unit-tested without a network or a real
opencode binary.

The installed opencode in this environment tracks the ``anomalyco/opencode``
*dev* channel (its ``dev`` branch / ``vX.Y.Z`` tags). The published GitHub
"latest release" and npm ``opencode-ai`` lag behind that channel, so the dev
tags are the source we compare against for display and the upgrade offer. The
upgrade itself is delegated to ``opencode upgrade``, which is its own oracle.
"""

import os
import re
import subprocess

DEFAULT_OPENCODE_REPO = "anomalyco/opencode"
REPO_ENV_VAR = "OPSKIT_OPENCODE_REPO"
_TIMEOUT = 10

_VERSION_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")
_TAG_RE = re.compile(r"^refs/tags/v(\d+\.\d+\.\d+)$")


def _as_tuple(version):
    """Coerce a version string (or tuple) to a (major, minor, patch) tuple."""
    if isinstance(version, tuple):
        return version
    if not version:
        return None
    match = _VERSION_RE.search(version)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def parse_version(text):
    """Extract a (major, minor, patch) tuple from text, or None."""
    if not text:
        return None
    match = _VERSION_RE.search(text)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def is_newer(latest, installed):
    """True when ``latest`` is a strictly newer semver than ``installed``."""
    a = _as_tuple(latest)
    b = _as_tuple(installed)
    if a is None or b is None:
        return False
    return a > b


def parse_latest_tag(ls_remote_output):
    """Highest plain ``vX.Y.Z`` tag from ``git ls-remote --tags`` output.

    Ignores ``vscode-*`` tags and peeled ``^{}`` entries.
    """
    best = None
    best_v = None
    for line in (ls_remote_output or "").splitlines():
        parts = line.split()
        if not parts:
            continue
        match = _TAG_RE.match(parts[-1])
        if not match:
            continue
        version = tuple(int(part) for part in match.group(1).split("."))
        if best_v is None or version > best_v:
            best_v = version
            best = match.group(1)
    return best


def opencode_repo():
    """Repo whose dev tags define the upgrade channel."""
    return os.environ.get(REPO_ENV_VAR, DEFAULT_OPENCODE_REPO)


def get_installed_version(runner=subprocess.run):
    """Installed opencode version as a string, or None if unavailable."""
    try:
        result = runner(
            ["opencode", "--version"],
            capture_output=True, text=True, timeout=_TIMEOUT,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    version = parse_version((result.stdout or "") + (result.stderr or ""))
    if version is None:
        return None
    return ".".join(str(part) for part in version)


def get_latest_dev_version(repo=None, runner=subprocess.run):
    """Latest dev-channel version via ``git ls-remote --tags``, or None.

    Any network/tool failure (offline, blocked, timeout) returns None so the
    caller can silently skip the offer.
    """
    url = f"https://github.com/{repo or opencode_repo()}"
    try:
        result = runner(
            ["git", "ls-remote", "--tags", url],
            capture_output=True, text=True, timeout=_TIMEOUT,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if getattr(result, "returncode", 1) != 0:
        return None
    return parse_latest_tag(result.stdout or "")
