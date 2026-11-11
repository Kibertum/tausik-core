# TAUSIK 1.11.13

TAUSIK 1.11.13 lets a fully verified task close after its Codex thread reaches
the hard host-context ceiling.

An exact `tausik_task_done` call with `ac_verified=true` now reaches the normal
execution-lease and QG-2 checks instead of being preempted by
`HOST_CONTEXT_HARD`. The exception does not authorize unfinished work:
implementation writes and all other protected mutations remain blocked and
require a fresh host thread.

When Stop already returned `CONTINUE` earlier in the turn, its retry now
re-evaluates durable state. It returns `ALLOW_DONE` after successful closure
and an actionable `CONTINUE` while work remains unfinished.

From the consumer project root, update `.tausik-lib`, then run
`python .tausik-lib/bootstrap/bootstrap.py --project-dir . --ide codex` and
`.tausik/tausik doctor`. Restart Codex or open a fresh trusted Codex thread so
the hook capability digest uses 1.11.13.

Read the full notes:
[English](https://github.com/Kibertum/tausik-core/blob/v1.11.13/docs/en/whats-new-1.11.md) ·
[Русский](https://github.com/Kibertum/tausik-core/blob/v1.11.13/docs/ru/whats-new-1.11.md).
