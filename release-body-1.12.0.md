# TAUSIK 1.12.0

TAUSIK 1.12.0 makes unfinished work recoverable after a Codex thread reaches
the hard host-context ceiling.

`HOST_CONTEXT_HARD` now persists a trusted copy-ready checkpoint with the exact
fresh-thread `task start <slug> --package` command before it revokes the old
execution lease and closes the exhausted thread. A repeated Stop returns
`ALLOW_HANDOFF` instead of trapping the task in a `CONTINUE` loop.

The boundary remains fail-closed: implementation writes, explicit MCP or CLI
handoff attempts, unrelated protected mutations and mixed request batches do
not renew authority in the exhausted thread.

From the consumer project root, update `.tausik-lib`, then run
`python .tausik-lib/bootstrap/bootstrap.py --project-dir . --ide codex` and
`.tausik/tausik doctor`. Continue the unfinished task in a fresh trusted thread
with the exact command stored in the checkpoint.

Read the full notes:
[English](https://github.com/Kibertum/tausik-core/blob/v1.12.0/docs/en/whats-new-1.12.md) ·
[Русский](https://github.com/Kibertum/tausik-core/blob/v1.12.0/docs/ru/whats-new-1.12.md).
