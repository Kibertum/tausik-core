[English](../en/whats-new-1.13.md) | [Русский](../ru/whats-new-1.13.md)

# TAUSIK 1.13: live work follows real context

<!-- doc-map: reader=user; zone=release-notes -->

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
