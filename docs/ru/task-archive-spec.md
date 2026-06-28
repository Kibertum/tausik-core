**Русский** | [English](/docs/task-archive-spec)

# Soft-архив старых **done**-задач (hygiene)

Скрыть устаревшие завершённые задачи из `task list`, не теряя их. Активная работа не затрагивается.

## Цель

Держать рабочий набор сфокусированным: проставить `archived_at` на **done**-задачах, у которых `completed_at` старше **N** дней. Они остаются в БД (аудит, FTS, `task show` продолжают работать), но исчезают из `task list` по умолчанию.

## Конфиг (`.tausik/config.json`)

```json
{
  "task_archive": {
    "enabled": false,
    "done_age_days": 90,
    "note": "soft-delete only; status остаётся 'done', archived_at — маркер"
  }
}
```

| Ключ | Тип | По умолчанию | Смысл |
|------|-----|---------------|-------|
| `task_archive` | object | (нет) | Фича выключена при отсутствии блока или `enabled: false`. |
| `enabled` | bool | `false` | Должен быть `true`, чтобы `hygiene archive --confirm` что-либо записал. |
| `done_age_days` | int | `90` | В scope попадают только задачи `status = 'done'` и `completed_at ≤ сейчас − N дней`. Невалидное/0 клампится к `1`. |

`enabled: false` побеждает `--confirm` — команда печатает "disabled" и ничего не пишет.

## Условия попадания (positive)

- `task.status == 'done'`
- `task.completed_at` задан и **старше** `done_age_days` (UTC).
- `task.archived_at IS NULL` (уже архивированные пропускаются — `--confirm` идемпотентен).

## Запреты (hard)

- **Никогда** не включать `planning`, `active`, `blocked`, `review` — независимо от возраста и конфига.
- **Без удаления строк**: архив — soft-delete (`UPDATE ... SET archived_at = ?`). Сама строка `tasks`, FTS-индекс, логи, решения и участие в метриках сохраняются.

## CLI

```bash
tausik hygiene archive             # dry-run: показать кандидатов
tausik hygiene archive --confirm   # применить: проставить archived_at (идемпотентно)

tausik task list                       # по умолчанию: скрывает архивированные
tausik task list --include-archived    # opt-in: показать всё
```

MCP-инструмент `tausik_task_list` принимает тот же параметр `include_archived: bool`.

## Схема

Миграция v25 добавляет одну nullable-колонку:

```sql
ALTER TABLE tasks ADD COLUMN archived_at TEXT;  -- ISO8601 UTC timestamp
CREATE INDEX idx_tasks_archived_at ON tasks(archived_at);
```

## См. также

- [Принципы тестирования](testing-principles.md)
- [CLI — Задачи](cli.md#задачи)
