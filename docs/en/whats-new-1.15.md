[English](../en/whats-new-1.15.md) | [Русский](../ru/whats-new-1.15.md)

# TAUSIK 1.15: Cursor failClosed unfreeze

<!-- doc-map: reader=user; zone=release-notes -->

## 1.15.0 — 2026-11-21

TAUSIK 1.15.0 unfreezes Cursor managing-agent PreToolUse **failClosed** (timeout
floor + exit map + durable lease rebind) and lands the TauX dogfood fixes that
blocked honest L3, QG-2 close, and scoped verify on consumer trees.

### Cursor failClosed and durable lease

Bootstrap emits a 45s PreToolUse timeout floor. `cursor_hook.map_exit` never
returns bare exit 1 for Claude-style warnings — policy deny stays exit 2.
Recovery is `bootstrap --ide cursor`, not a human external unblock. `task update`
authorizes as `cli_task_update` and rebinds the live package fingerprint so
`PACKAGE_STALE` does not strand the thread until another `task start`.

### Codex L3 read-only path

Capability preflight plus `review cohort-infrastructure-blocked` preserve repair
rounds when the host cannot offer a mechanically read-only reviewer. Docs:
[codex-l3-readonly](codex-l3-readonly.md).

### Dogfood QG-2 and verify honesty

Phantom STALE after a green verify is gone (TB-016). Empty `testing.roots=[]`
no longer discovers tests (TB-005). Lockfiles are not authored filesize (TB-014).
`--relevant-files` refuses `.` and directories; `NoTestRoots` fails fast; cohort
readiness uses the shared AC evidence parser. Post-bootstrap refresh skips
markerless / `hand_maintained` instruction files instead of aborting the upgrade.

- [Exact 1.15.0 changelog](https://github.com/Kibertum/tausik-core/blob/v1.15.0/CHANGELOG.md)
- [Upgrade guide](upgrade.md)
