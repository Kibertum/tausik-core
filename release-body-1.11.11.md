# TAUSIK 1.11.11

TAUSIK 1.11.11 restores uninterrupted Cursor work after the 1.11.10 regression.

`tausik_task_add` accepts the standard QG-0 fields in one authorized MCP call.
Every terminal close path now atomically releases the task-package lease
binding: ordinary QG-2 close, memory-only light close, hierarchy receipt close,
and obsolete. The same Cursor thread can immediately start its next task. A
failed close rolls back both task and lease state; stale and cross-thread
leases remain fail-closed.

The candidate completed two consecutive full MCP task lifecycles in the same
live Cursor thread in both naproksen and BotAdminPanel without losing existing
chats or application work.

Existing installations must update their framework copy, rerun the Cursor
bootstrap, and reload the Cursor window so the MCP server starts on 1.11.11.

Read the full notes: [English](docs/en/whats-new-1.11.md) ·
[Русский](docs/ru/whats-new-1.11.md).

---

TAUSIK 1.11.11 восстанавливает непрерывную работу Cursor после регрессии
1.11.10.

`tausik_task_add` принимает стандартные поля QG-0 одним авторизованным
MCP-вызовом. Каждый терминальный путь закрытия теперь атомарно освобождает
task-package-привязку lease: обычный QG-2 close, memory-only light close,
hierarchy receipt close и obsolete. Тот же поток Cursor сразу запускает
следующую задачу. При сбое закрытия откатываются и задача, и lease; stale и
cross-thread leases остаются fail-closed.

Кандидат выполнил два последовательных полных MCP-lifecycle задач в одном
живом потоке Cursor отдельно в naproksen и BotAdminPanel, не потеряв
существующие чаты и работу над приложениями.

Для уже установленных проектов нужно обновить копию фреймворка, повторно
запустить bootstrap для Cursor и выполнить Reload Window, чтобы MCP-сервер
стартовал на 1.11.11.

Полные заметки: [English](docs/en/whats-new-1.11.md) ·
[Русский](docs/ru/whats-new-1.11.md).
