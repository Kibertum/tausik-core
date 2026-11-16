# TAUSIK 1.13.2

TAUSIK 1.13.2 stabilizes upgrades of existing Cursor and Codex projects from
published v1.11.7 and later releases.

- Stateful upgrade journeys preserve tasks, dependencies, sessions, leases,
  turns, Stop state, and continuity where those records exist.
- Bootstrap refresh fails closed and preserves user-owned legacy Cursor rules.
- Windows paths, PowerShell, CRLF input, and host reloads have a mandatory native
  compatibility canary.
- Exact-SHA qualification separates trusted Linux evidence from the
  candidate-writable Windows report and uses a strict multi-platform hash lock.
- Codex `doctor` recovery stays lease-exempt alone; a trailing PowerShell write
  in the same shell command still hits write/scope gates.
- `ruff format` gate reads ruff 0.16 ANSI diagnostics and fails closed on
  unparsed nonzero checks.
- Unmanaged instruction files without DYNAMIC markers no longer abort bootstrap
  refresh.
- The bilingual upgrade guide includes WAL-safe backup and exact restore steps.

Full notes:
[English](https://github.com/Kibertum/tausik-core/blob/v1.13.2/docs/en/whats-new-1.13.md) ·
[Русский](https://github.com/Kibertum/tausik-core/blob/v1.13.2/docs/ru/whats-new-1.13.md).
