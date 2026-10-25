#!/usr/bin/env bash
# bin/check-global-skills.sh — report broken symlinks in ~/.config/opencode/skills/
#
# Global skills live in ~/.config/opencode/skills/ and are symlinks into the
# opskit checkout. If they point into a worktree that gets removed they go
# silent — missing skills produce no error, they just become dead weight.
#
# Usage:
#   bin/check-global-skills.sh            # report broken links
#   bin/check-global-skills.sh --fix      # repoint broken links to main checkout
#   bin/check-global-skills.sh --check    # same as no flags (exit 1 if broken)
#
# Exit codes:
#   0  no broken links (or --fix repaired them all)
#   1  broken links found (--check mode) or repair failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# Resolve the *main checkout* path (not the worktree we happen to run from).
# If we are in the main checkout REPO_ROOT is it; if in a worktree, use the
# common git dir to find the real repo root.
if GIT_COMMON="$(git -C "$REPO_ROOT" rev-parse --git-common-dir 2>/dev/null)"; then
    MAIN_CHECKOUT="$(cd "$(dirname "$GIT_COMMON")" && pwd)"
else
    MAIN_CHECKOUT="$REPO_ROOT"
fi
GLOBAL_SKILLS="${HOME}/.config/opencode/skills"
FIX=0
CHECK=0

while [ $# -gt 0 ]; do
    case "$1" in
        --fix)     FIX=1 ;;
        --check)   CHECK=1; FIX=0 ;;
        *)         echo "Unknown flag: $1" >&2; exit 2 ;;
    esac
    shift
done

# Default: report + exit 1 on broken (check mode)
if [ $FIX -eq 0 ] && [ $CHECK -eq 0 ]; then
    CHECK=1
fi

if [ ! -d "$GLOBAL_SKILLS" ]; then
    echo "OK: $GLOBAL_SKILLS does not exist"
    exit 0
fi

BROKEN=0
REPAIRED=0

for link in "$GLOBAL_SKILLS"/*; do
    [ -L "$link" ] || continue          # not a symlink, skip
    target="$(readlink "$link")"
    if [ ! -e "$link" ]; then
        BROKEN=$((BROKEN + 1))
        echo "BROKEN: $link -> $target"

        if [ $FIX -eq 1 ]; then
            # Repaint: absolute symlink into the main checkout.
            # ~/.config/opencode/skills/<name> -> <main_checkout>/.opencode/skills/<name>
            skill_name="$(basename "$link")"
            dest_target="${MAIN_CHECKOUT}/.opencode/skills/${skill_name}"
            rm "$link"
            ln -s "$dest_target" "$link"
            if [ -e "$link" ]; then
                REPAIRED=$((REPAIRED + 1))
            else
                echo "FAIL: could not repoint $link -> $dest_target" >&2
            fi
        fi
    fi
done

if [ $BROKEN -eq 0 ]; then
    echo "OK: no broken global skill symlinks"
    exit 0
fi

if [ $FIX -eq 1 ] && [ $REPAIRED -eq $BROKEN ]; then
    echo "Repainted $REPAIRED broken link(s) to main checkout"
    exit 0
elif [ $FIX -eq 1 ]; then
    echo "WARNING: repaired $REPAIRED of $BROKEN broken links" >&2
    exit 1
else
    echo "Found $BROKEN broken global skill link(s) — missing skills are silent" >&2
    exit 1
fi
