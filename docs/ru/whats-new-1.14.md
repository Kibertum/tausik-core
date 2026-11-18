[English](../en/whats-new-1.14.md) | [Русский](../ru/whats-new-1.14.md)

# TAUSIK 1.14: consumer git остаётся export-only

<!-- doc-map: reader=user; zone=release-notes -->

## 1.14.0 — 2026-11-18

TAUSIK 1.14.0 делает consumer git **export-only** на day-0, позволяет закрывать
QG-2 для out-of-tree работы без dirty дерева хоста и предупреждает о кавычках
в Windows shell без блокировки.

### Consumer export-only на day-0

Если есть `.tausik-lib`, bootstrap сеет `.tausik-lib/` (и пути IDE/harness) в
`.gitignore`. `harness_projection` отказывает стейдж самого checkout lib и пишет
в stderr, когда в DB есть state, а в коммите нет `tausik/`. Quickstart EN/RU:
durable tracked = продукт + `tausik/`.

### QG-2 для out-of-tree

`--no-file-changes` смотрит только pathspec `relevant_files` — чужой dirty вне
области не блокирует. Для работы вне репозитория хоста `--external-evidence`
пропускает dirty-check дерева; нельзя сочетать с `--relevant-files`.

### Windows shell hygiene

Docs EN/RU и warn-only PostToolUse `windows_shell_hygiene` ловят вложенные
кавычки, EncodedCommand, `gh --jq` braces и SSH heredoc. Хук не блокирует.

### MCP tip scripts без Reload Window

Memory preflight предпочитает живой `project/scripts` и перезагружает tip
modules на каждый `issue_preflight`. Правка mid-release больше не требует
Reload Window или рестарта MCP; deployed IDE-копии остаются fallback.

- [Точный changelog 1.14.0](https://github.com/Kibertum/tausik-core/blob/v1.14.0/CHANGELOG.ru.md)
- [Руководство по обновлению](upgrade.md)
