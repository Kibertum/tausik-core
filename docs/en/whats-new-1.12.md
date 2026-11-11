[English](../en/whats-new-1.12.md) | [Русский](../ru/whats-new-1.12.md)

# TAUSIK 1.12: recoverable host-context handoff

<!-- doc-map: reader=user; zone=release-notes -->

## 1.12.0 — 2026-11-11

TAUSIK 1.12.0 removes a recovery deadlock at `HOST_CONTEXT_HARD`. When an
unfinished task reaches the host-thread context ceiling, the trusted boundary
now writes a copy-ready checkpoint with the exact
`.tausik/tausik task start <slug> --package` command, revokes the old execution
lease and closes that host thread. A repeated Stop then returns
`ALLOW_HANDOFF`, so work continues in a fresh thread without rereading the full
conversation.

The recovery does not reopen authority in the exhausted thread. Implementation
writes, explicit MCP or CLI handoff attempts, unrelated protected mutations and
mixed request batches remain blocked. The checkpoint binds the exact project,
host, thread, session and task lease; ambiguous authority fails closed.

The behavior has focused live/expired-lease coverage, a fresh-process Stop
regression, deep adversarial review and the normal release verification lanes.

- [Exact 1.12.0 changelog](https://github.com/Kibertum/tausik-core/blob/v1.12.0/CHANGELOG.md)
- [Upgrade guide](upgrade.md)
