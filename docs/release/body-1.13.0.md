# TAUSIK 1.13.0

TAUSIK 1.13.0 keeps live work in the current host thread while real context is
available.

Estimated `call_budget` and `checkpoint_calls` values are now advisory at every
value. They no longer force a new chat, restrict a live task to recovery
commands, or create a `CONTINUITY_BLOCKED` / `PACKAGE_STALE` deadlock. Persisted
call-count recovery state from earlier builds is retired on the next protected
action, including in unattended mode.

Native host-context ceilings, execution-lease correlation and stale-package
protection remain fail-closed. Explicit autonomous composition also keeps its
separate `2×` budget check between tasks.

From the consumer project root, update `.tausik-lib`, then run
`python .tausik-lib/bootstrap/bootstrap.py --project-dir . --ide codex` and
`.tausik/tausik doctor`.

Read the full notes:
[English](https://github.com/Kibertum/tausik-core/blob/v1.13.0/docs/en/whats-new-1.13.md) ·
[Русский](https://github.com/Kibertum/tausik-core/blob/v1.13.0/docs/ru/whats-new-1.13.md).
