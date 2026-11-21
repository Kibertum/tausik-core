# TAUSIK 1.15.0

Cursor PreToolUse **failClosed** unfreeze, durable CLI lease rebind, and TauX
dogfood (L3 Codex path, QG-2 phantom STALE, verify honesty).

## Highlights

- Bootstrap PreToolUse timeout floor 45s; `cursor_hook.map_exit` never returns
  bare exit 1 for Claude-style warnings (policy deny stays exit 2). Recovery is
  `bootstrap --ide cursor`, not a human external one-liner.
- `task update` authorizes as `cli_task_update` and rebinds the live package
  fingerprint so `PACKAGE_STALE` does not strand the thread.
- Codex L3: capability preflight + `review cohort-infrastructure-blocked`
  without burning repair rounds. Docs: `docs/en/codex-l3-readonly.md`.
- Dogfood: TB-005…016 (empty testing.roots, phantom STALE, lockfile filesize,
  NoTestRoots, shared AC readiness, supplementary L1/L2 below route, …).

## Upgrade

Pin `.tausik-lib` to tag `v1.15.0`, then:

```powershell
py .tausik-lib\bootstrap\bootstrap.py --project-dir . --ide cursor --no-detect
.\.tausik\tausik.cmd doctor
```

After bootstrap, reload the IDE once so new hooks load.

Full notes:
[English](https://github.com/Kibertum/tausik-core/blob/v1.15.0/docs/en/whats-new-1.15.md) ·
[Русский](https://github.com/Kibertum/tausik-core/blob/v1.15.0/docs/ru/whats-new-1.15.md).
