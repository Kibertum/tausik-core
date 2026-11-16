# TAUSIK 1.11.12

TAUSIK 1.11.12 keeps Cursor work running after a command is rejected before
execution.

`PostToolUseFailure` no longer puts the whole project into
`LEASE_MAINTENANCE` when the write gate already rejected a malformed command.
The exception is limited to structurally confirmed pre-execution denials;
executed actions and genuine audit inconsistencies remain fail-closed.

The candidate replayed the original unmatched-quote failure against two
independently deployed consumer projects. Both existing Cursor threads then
resumed their original tasks and performed real task/tool activity without
returning to maintenance.

Existing installations must update their framework copy, run
`python .tausik-lib/bootstrap/bootstrap.py --project-dir . --ide cursor`, then
run **Developer: Reload Window** so the hook and capability digest use 1.11.12.

Read the full notes:
[English](https://github.com/Kibertum/tausik-core/blob/v1.11.12/docs/en/whats-new-1.11.md) ·
[Русский](https://github.com/Kibertum/tausik-core/blob/v1.11.12/docs/ru/whats-new-1.11.md).
