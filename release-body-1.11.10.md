# TAUSIK 1.11.10

TAUSIK 1.11.10 fixes the final Cursor workflow break exposed after 1.11.9.

Closing a task as obsolete now atomically releases that task's package binding
from live execution leases and invalidates unused authorizations issued under
the old binding. The same Cursor thread can immediately create and start its
next task without `doctor --reconcile-execution-leases`, without reloading the
chat, and without losing session history. Leases belonging to other active
tasks remain unchanged.

Existing installations must update their framework copy, rerun the Cursor
bootstrap, and reload the Cursor window so the MCP server restarts on 1.11.10.
After that one runtime refresh, the same chat can continue; no owner reconcile
or new chat is required.

Read the full notes: [English](docs/en/whats-new-1.11.md) ·
[Русский](docs/ru/whats-new-1.11.md).

---

TAUSIK 1.11.10 исправляет последний сбой рабочего процесса Cursor, проявившийся
после 1.11.9.

Закрытие задачи как obsolete теперь атомарно освобождает её package-привязку у
живых execution leases и погашает неиспользованные авторизации старой привязки.
Тот же поток Cursor сразу может создать и запустить следующую задачу без
`doctor --reconcile-execution-leases`, перезагрузки чата и потери истории
сессии. Leases других активных задач остаются неизменными.

Для уже установленных проектов нужно обновить копию фреймворка, повторно
запустить bootstrap для Cursor и выполнить Reload Window, чтобы MCP-сервер
перезапустился на 1.11.10. После этого разового обновления runtime можно
продолжить тот же чат; owner reconcile и новый чат не нужны.

Полные заметки: [English](docs/en/whats-new-1.11.md) ·
[Русский](docs/ru/whats-new-1.11.md).
