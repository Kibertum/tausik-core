# TAUSIK 1.13.4

Softens execution-lease **package freshness** so ordinary agent work matches the spirit of 1.11.7 again.

## Highlights

- `PACKAGE_STALE` is **advisory** for ordinary Write/MCP mutations (warn and continue).
- **Fail-closed** package checks remain only for commit/push (`codex_protected_shell`).
- `tausik_task_update` rebinds the live lease package after a successful contract edit.
- Incomplete `complexity=complex` updates on an **active** task are refused **before write**, ending the `PACKAGE_STALE` ↔ `PACKAGE_INVALID` deadlock.
- Memory preflight tokens stay scoped to protected actions (commit/push and kin).
- Lease tables are **not** dropped; `TAUSIK_ENFORCE_EXECUTION_LEASE` stays on for identity/binding.

## Upgrade

Pin `.tausik-lib` to tag `v1.13.4`, then:

```powershell
py .tausik-lib\bootstrap\bootstrap.py --project-dir . --ide cursor --no-detect
.\.tausik\tausik.cmd doctor
```

Reload the IDE window after bootstrap so hooks and MCP pick up the soft gate.

Full notes:
[English](https://github.com/Kibertum/tausik-core/blob/v1.13.4/docs/en/whats-new-1.13.md) ·
[Русский](https://github.com/Kibertum/tausik-core/blob/v1.13.4/docs/ru/whats-new-1.13.md).
