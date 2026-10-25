# `bw` answers from a stale cache while locked — "not in the vault" can be false

## Symptom

A search for a credential returns items, so the vault looks readable and current.
Then the answer drawn from it is wrong: the item you were told does not exist turns
out to exist, or every copy of a password tests as rejected while a working copy
was written days ago.

The signal that was visible but easy to dismiss: `bw status` reported
`"status": "locked"` and a `lastSync` timestamp days older than the change being
investigated — while `bw list items` kept answering normally.

## Diagnosis

Ask the vault how fresh its answer is, not just whether it answers:

```
bw status | jq -r '.lastSync, .status'
```

Compare `lastSync` against the age of the change you are chasing. If the cache is
older than the change, you have no data — not a negative result.

Force a refresh and watch what happens to reads:

```
bw sync          # can print "Syncing complete." while the vault stays locked
bw list items    # then prompts "? Master password:" — with no TTY this yields
                 # empty output, which a caller easily reads as "no items"
```

Use the repo's own gate, because it validates with a real API call rather than
trusting a status field:

```
bin/bwunlock.sh --check     # unlocked | locked | missing | permission
```

## Cause

The CLI serves `bw list` and `bw get` from its local encrypted cache
(`~/.config/Bitwarden CLI/data.json`). A locked session does not stop it from
answering — it only stops fresh decryption. Whatever the cache holds is what you
get, and its age is exactly `lastSync`.

`bw status` reports the lock state of the local vault, which is a different
question from "is the data I just read current". Both can be true at once, so
"locked" looks like cosmetic noise right up until it isn't.

## Fix

Refresh the session, then sync, then re-query:

```
bin/bwunlock.sh          # password popup; writes the cache atomically
bw sync
bw list items --search <term>
```

Headless equivalent:

```
(umask 077; bw unlock --raw > ~/.cache/opskit/bw-session)
```

## Prevention

- Treat `lastSync` older than the change under investigation as "no data". Report
  "I cannot see it in a cache this old", never "it is not in the vault".
- Gate vault reads through `bin/bwunlock.sh --check`, not through `bw status`.
- When verifying a rotated credential, prefer **one** real authentication attempt
  over item metadata. A revision date records intent; only the service records
  whether the password works. (Check for lockout policy first — some services
  rate-limit or fail-lock on bad attempts.)
- An empty result from a command run without a TTY may be a prompt, not an
  absence. `bw` prints `? Master password:` to stderr and nothing to stdout.

## Notes

- Stale duplicates are the usual aftermath of a rotation: a new item is written,
  the old copies keep the dead password, and a reader that resolves by *name*
  can land on a stale one. The resulting `401` looks like a broken service.
- Resolve by item **id**, and confirm the id against `revisionDate` before acting.
- `bw delete item <id>` moves the item to the trash and is recoverable with
  `bw restore item <id>`; verify that rather than assuming deletion is permanent.
- The general lesson: a cache that answers confidently is more dangerous than one
  that errors, because the failure surfaces as a confident wrong conclusion far
  from its cause.
