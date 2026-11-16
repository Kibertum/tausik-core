[English](../en/whats-new-1.13.md) | [Русский](../ru/whats-new-1.13.md)

# TAUSIK 1.13: live work follows real context

<!-- doc-map: reader=user; zone=release-notes -->

## 1.13.3 — 2026-11-17

TAUSIK 1.13.3 makes protected memory preflight usable from skills without opening
`memory_preflight.py`, and keeps GitHub release bodies under
`docs/release/body-<version>.md`.

- [Exact 1.13.3 changelog](https://github.com/Kibertum/tausik-core/blob/v1.13.3/CHANGELOG.md)
- [Upgrade guide](upgrade.md)

## 1.13.2 — 2026-11-15

TAUSIK 1.13.2 is a stabilization release for existing Cursor and Codex projects.
It adds a published-version upgrade matrix beginning at v1.11.7, preserves task,
dependency, session, lease, turn, Stop, and continuity state across the schema
boundaries that own those records, and executes the commands installed in each
host's real SessionStart-to-Stop lifecycle.

Bootstrap refresh now fails closed with a bounded diagnostic. It updates every
existing host projection and removes legacy `.cursorrules` only when its
ownership digest proves that TAUSIK generated it and the replacement MDC rule
exists. The upgrade guide now uses a SQLite online backup so committed WAL
frames are part of the recoverable set.

Once the protected activation dry run succeeds, official publication will
require exact-SHA release qualification. Linux produces isolated trusted
evidence, native Windows is a mandatory Cursor/Codex compatibility canary, and
the protected verifier binds the successful Windows job identity without
trusting candidate-writable JUnit as signed evidence.

The qualification controller lock now carries every published wheel hash
for each exact dependency pin. Native Windows, macOS, and Linux lanes retain
strict `--require-hashes` verification without inheriting the maintainer's
platform-specific wheel choice.

- [Exact 1.13.2 changelog](https://github.com/Kibertum/tausik-core/blob/v1.13.2/CHANGELOG.md)
- [Upgrade guide](upgrade.md)

## 1.13.0 — 2026-11-11

TAUSIK 1.13.0 stops treating estimated tool-call counts as a reason to freeze a
live task. `call_budget` and `checkpoint_calls` remain useful planning and
checkpoint signals, but they never force a new chat or restrict the current
task to a recovery allowlist. The host's native context telemetry remains the
only authority that can require a fresh host thread.

The upgrade also retires persisted `call_budget_exhausted` and
`checkpoint_required` state from earlier builds, including unattended mode.
This removes the deadlock where `CONTINUITY_BLOCKED` demanded recovery while a
stale context package prevented that recovery. `task start <slug> --package`
can still rebind the package, and ordinary protected mutations still fail
closed while their package is stale.

Explicit autonomous release composition keeps its separate `2×` budget guard
between tasks through `TAUSIK_AUTONOMOUS_BUDGET_BLOCK`. It does not interrupt a
task that is already in progress.

- [Exact 1.13.0 changelog](https://github.com/Kibertum/tausik-core/blob/v1.13.0/CHANGELOG.md)
- [Upgrade guide](upgrade.md)
