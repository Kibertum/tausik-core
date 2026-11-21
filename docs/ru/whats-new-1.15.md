[English](../en/whats-new-1.15.md) | [Русский](../ru/whats-new-1.15.md)

# TAUSIK 1.15: разморозка Cursor failClosed

<!-- doc-map: reader=user; zone=release-notes -->

## 1.15.0 — 2026-11-21

TAUSIK 1.15.0 размораживает Cursor managing-agent PreToolUse **failClosed**
(timeout floor + карта exit + долгий lease rebind) и закрывает dogfood TauX,
который блокировал честный L3, закрытие QG-2 и scoped verify на consumer-деревьях.

### Cursor failClosed и долгий lease

Bootstrap ставит floor timeout PreToolUse 45s. `cursor_hook.map_exit` не отдаёт
голый exit 1 на Claude-style warning — policy deny остаётся exit 2. Восстановление
— `bootstrap --ide cursor`, не внешний unblock человека. `task update`
авторизуется как `cli_task_update` и перепривязывает fingerprint пакета, чтобы
`PACKAGE_STALE` не держал поток до следующего `task start`.

### Read-only путь L3 на Codex

Preflight возможности и `review cohort-infrastructure-blocked` сохраняют
repair-раунды, когда хост не даёт механически read-only reviewer. Docs:
[codex-l3-readonly](codex-l3-readonly.md).

### Dogfood QG-2 и честность verify

Фантомный STALE после зелёного verify убран (TB-016). Пустой `testing.roots=[]`
больше не уходит в discovery (TB-005). Lockfile не authored filesize (TB-014).
`--relevant-files` отвергает `.` и каталоги; `NoTestRoots` fail-fast; готовность
когорты использует общий парсер AC evidence.

- [Точный changelog 1.15.0](https://github.com/Kibertum/tausik-core/blob/v1.15.0/CHANGELOG.ru.md)
- [Руководство по обновлению](upgrade.md)
