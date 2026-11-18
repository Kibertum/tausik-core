# TAUSIK 1.14.0

Consumer day-0 **export-only**, out-of-tree QG-2 closes, and Windows shell hygiene.

## Highlights

- Bootstrap seeds `.tausik-lib/` (and IDE/harness copy paths) into `.gitignore` when
  the lib checkout is present; `harness_projection` refuses staging the lib itself and
  warns when the DB has state but the commit omits `tausik/`.
- QG-2 `--no-file-changes` pathspecs only `relevant_files`. Out-of-repo work uses
  `--external-evidence` (cannot combine with `--relevant-files`).
- Warn-only PostToolUse `windows_shell_hygiene` plus day-0 docs for nested quotes,
  EncodedCommand trailing args, `gh --jq` braces, and SSH heredocs.

## Upgrade

Pin `.tausik-lib` to tag `v1.14.0`, then:

```powershell
py .tausik-lib\bootstrap\bootstrap.py --project-dir . --ide cursor --no-detect
.\.tausik\tausik.cmd doctor
```

Reload the IDE window after bootstrap so hooks and MCP pick up the new gates.

Full notes:
[English](https://github.com/Kibertum/tausik-core/blob/v1.14.0/docs/en/whats-new-1.14.md) ·
[Русский](https://github.com/Kibertum/tausik-core/blob/v1.14.0/docs/ru/whats-new-1.14.md).
