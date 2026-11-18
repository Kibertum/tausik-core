[English](../en/whats-new-1.14.md) | [Русский](../ru/whats-new-1.14.md)

# TAUSIK 1.14: consumer git stays export-only

<!-- doc-map: reader=user; zone=release-notes -->

## 1.14.0 — 2026-11-18

TAUSIK 1.14.0 makes consumer git **export-only** on day-0, lets QG-2 close
out-of-tree work without a dirty host tree, and warns on Windows shell quote
pitfalls without blocking.

### Consumer export-only on day-0

When `.tausik-lib` is present, bootstrap seeds `.tausik-lib/` (plus IDE and
harness copy paths) into `.gitignore`. `harness_projection` refuses staging the
lib checkout itself and prints stderr when the DB has state but the commit omits
`tausik/`. Quickstart EN/RU name product + `tausik/` as the durable tracked
surface.

### QG-2 out-of-tree closes

`--no-file-changes` pathspecs only `relevant_files`, so unrelated dirty files
outside the declared scope no longer block. For work that lives outside the host
repo, `--external-evidence` skips the host-tree dirty check; it cannot be
combined with `--relevant-files`.

### Windows shell hygiene

Day-0 docs EN/RU and a warn-only PostToolUse `windows_shell_hygiene` hook catch
nested quotes, EncodedCommand trailing args, `gh --jq` braces, and SSH heredocs.
The hook does not block.

- [Exact 1.14.0 changelog](https://github.com/Kibertum/tausik-core/blob/v1.14.0/CHANGELOG.md)
- [Upgrade guide](upgrade.md)
