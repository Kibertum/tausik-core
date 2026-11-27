[English](../en/whats-new-1.16.md) | [Русский](../ru/whats-new-1.16.md)

# TAUSIK 1.16.2: reliable Codex chat completion

<!-- doc-map: reader=user; zone=release-notes -->

## 1.16.2 — 2026-11-27

TAUSIK 1.16 separates chat completion from authorization to change a project.
Codex Stop no longer forces another model turn because a task is unfinished or
a readiness request contains particular words. The phrase detector is removed
from Codex Stop. Old Stop registrations remain harmless until the IDE reloads.

Host context thresholds are advisory by default. They recommend a checkpoint
without revoking a lease or requiring a new chat. Projects that deliberately
need strict limits can set `host_context_budget.enforcement` to `hard`.
Older machine-generated checkpoint instructions follow the current policy when
read as the live handoff; explicit historical reads and owner content survive.

PreToolUse authorization, native identity, execution leases, memory preflight,
explicit task budgets and QG-0/QG-2 remain enforced. Completing a chat does not
grant permission to write or execute protected commands.

The release also fixes native Shell/PowerShell preflight binding, literal CLI
names inside search arguments, late native model attribution, and Windows
handling of bytecode belonging to WSL virtual environments.

## Upgrade

Update your framework checkout to `v1.16.2`, then rerun bootstrap for your
configured hosts. Reload the IDE once to load updated MCP modules and skills.
For a Codex-only checkout:

```powershell
py .tausik-lib/bootstrap/bootstrap.py --project-dir . --ide codex --no-detect
./.tausik/tausik.cmd doctor
```

For projects with multiple hosts, preserve the configured host list and update
each deployed profile. Do not discard local reviewed patches without checking
that the new release contains them.

## 1.16.0 — preliminary development tag

The development tag records the reviewed runtime changes. Public publication
uses 1.16.2 with completed release documentation; the earlier tag is unchanged.
