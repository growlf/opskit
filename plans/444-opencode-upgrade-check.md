# #444 — opskit go: pre-launch opencode upgrade check + launch handoff message

## Goal
Make `opskit go` (a) tell the operator when it hands off to opencode, and
(b) if online, check whether the installed opencode needs an upgrade and offer
to run it *before* launching — so a stale/broken opencode build can't silently
break the launched session.

## Scope
Two bundled changes, one PR:
1. **Launch handoff message** — one flushed line immediately before the final
   `os.execvpe("opencode", ...)` in `launch_project`.
2. **Upgrade check + offer** — pre-launch, daily-cached, tty-only check.

Out of scope: auto-upgrading non-interactively; touching the published-vs-dev
release feeds beyond reading the dev channel; changing opencode itself.

## Research
- Installed: `~/.opencode/bin/opencode` → `opencode v2.0.28`;
  `~/.opencode/bin/opencode2` is a 47-byte shim.
- Channel = `anomalyco/opencode` **dev**: repo `dev` branch `package.json` =
  `2.0.28`, tag `v2.0.28`. (Repo `fork:false`, default branch `dev`.)
- Published latest = `v1.19.0` (GitHub releases *and* npm `opencode-ai`) — LOWER
  than installed. Comparing to it would wrongly say "up to date"/downgrade.
- `opencode upgrade`/`update` has no `--check`/`--dry-run`; it self-reports
  ("already on the latest version" vs "Upgraded."). No cached latest-version
  file; no plaintext update endpoint in the binary.
- The multi-minute gap after selection is opencode's own background-server
  start (after exec), not opskit's pre-exec steps (skills setup + BW session are
  each ≤30s).

## Decisions
- **Detect "needed":** query the dev channel (highest `vX.Y.Z` tag via
  `git ls-remote --tags`) → used for display **and** the offer.
- **Act:** run `opencode upgrade` (idempotent; opencode is its own oracle).
- **Cache:** store in `~/.opskit/`, re-check at most ~once/24h.
- **Interactive only:** prompt only on a tty; never auto-upgrade otherwise.

## Design

**New `opskit/_opencode.py`** (pure, testable helpers):
- `parse_version(text) -> (int,int,int) | None` — regex `v?(\d+)\.(\d+)\.(\d+)`.
- `is_newer(latest, installed) -> bool` — tuple compare; ignore `-suffix`/`^{}`.
- `parse_latest_tag(ls_remote_output) -> str | None` — accept only
  `^refs/tags/v(\d+\.\d+\.\d+)$` (ignore `vscode-*`, peeled `^{}`); return max.
- `get_installed_version(runner=subprocess.run) -> str | None`.
- `get_latest_dev_version(repo, runner=subprocess.run) -> str | None` —
  `git ls-remote --tags https://github.com/<repo>`, timeout=10s.
- `DEFAULT_OPENCODE_REPO = "anomalyco/opencode"`; env override
  `OPSKIT_OPENCODE_REPO`.

**Edit `opskit/_cache.py`:**
- `OPENCODE_CHECK_FILE = CACHE_DIR / "opencode-version-check.json"`.
- `read_opencode_check()` / `write_opencode_check(data)` (atomic, existing style).
- `opencode_check_is_stale(data, installed)` — stale if missing, older than
  `CACHE_STALE_HOURS`, or `data["installed"] != installed`.

**Edit `bin/opskit-go.py`:**
- `maybe_offer_opencode_upgrade()` (tty-only; cache; fetch; compare; prompt;
  run `opencode upgrade`; re-read version).
- Call it at the start of `main()`.
- In `launch_project`, print
  `Now starting interactive OpenCode shell...` (flushed) before `execvpe`.

**New `tests/test_opencode_upgrade.py`** (TDD, written first).

## Task list
1. Write `tests/test_opencode_upgrade.py` (failing) — commit first.
2. Add `opskit/_opencode.py` helpers.
3. Add cache fns to `opskit/_cache.py`.
4. Wire `maybe_offer_opencode_upgrade()` + handoff message into `bin/opskit-go.py`.
5. `make test` green.
6. Plan → `plans/444-...md` + issue #444; PR; review; merge.

## Critique
- **SECURITY — upgrading can restart the running opencode service/session.**
  A nested `opskit go` from inside opencode could kill the caller's session.
  *Resolution:* prompt names the restart; tty-only; decline default ([y/N]);
  non-tty never upgrades.
- **SECURITY — network/secret exposure:** `git ls-remote` is read-only,
  unauthenticated, touches no secrets; nothing client-identifying is printed.
- **APPROPRIATENESS — source drift:** our tag query may not exactly match the
  channel `opencode upgrade` uses. *Resolution:* the action is
  `opencode upgrade` (authoritative); a wrong query can at worst mis-offer or
  miss an offer, never apply a wrong action.
- **APPROPRIATENESS — channel mismatch:** max-semver could offer a major jump.
  *Resolution:* operator wants standard *and* major upgrades; prompt is explicit
  and declinable; repo is env-overridable.
- **STABILITY — hanging launch:** `timeout=10`, exceptions swallowed, 24h cache.
- **STABILITY — after-upgrade state:** cache invalidated when installed
  differs; version re-read after upgrade.
- **MAINTAINABILITY:** pure parsing helpers; cache I/O reuses `_cache.py`.
- **EFFECTIVENESS/VALUE:** removes the silent-stale-opencode footgun and the
  unexplained silent gap at handoff.
