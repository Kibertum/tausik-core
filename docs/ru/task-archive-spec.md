**Русский** | [English](../en/task-archive-spec.md)

# Soft-архив старых **done**-задач (hygiene)

<!-- doc-map: reader=user; zone=sessions -->

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

tausik hygiene unarchive --slug <slug>              # dry-run: что будет раскрыто
tausik hygiene unarchive --slug <slug> --confirm    # применить: снять archived_at
tausik hygiene unarchive --archived-within 1 --confirm   # откатить сегодняшнюю партию

tausik task list                       # по умолчанию: скрывает архивированные
tausik task list --include-archived    # opt-in: показать всё
```

MCP-инструмент `tausik_task_list` принимает тот же параметр `include_archived: bool`.

## Обратимость

`hygiene unarchive` снимает `archived_at`. **Это единственный путь, который это делает** —
два релиза этот раздел обещал обратимость «командой», а команды не было ни одной, так что
возврат партии потребовал бы прямого SQL, запрещённого проекту. Теперь обещание называет
команду, а `tests/test_hygiene_unarchive.py` проверяет, что команда существует: обещание
отката стоит читать только тогда, когда его кто-то проверяет.

Правила:

- **Селектор обязателен**: `--slug` или `--archived-within DAYS`. Голый `unarchive` раскрыл
  бы весь архив — это не восстановление.
- **`--archived-within`, а не «старше»**: откатывать надо ту партию, которую только что
  применили. Выбор самых старых архивных строк вернул бы ровно то, что должно было
  остаться скрытым, и оставил бы свежую ошибку на месте.
- **Двигаются только `archived_at` и `updated_at`.** `status` и `completed_at` остаются
  как были: архивация их не меняла, поэтому снятие признака раскрывает строку, а не
  оживляет работу.
- **Не зависит от `task_archive.enabled`.** Конфиг управляет операцией, которая СКРЫВАЕТ
  строки; путь восстановления, выключающийся вместе с ней, был бы недоступен ровно тогда,
  когда он нужен.

### Архивация памяти необратима, и это решение, а не пробел

Архивация записи **памяти** проставляет `valid_to` на её рёбрах графа
(`backend_graph.edges_invalidate_to`). Снятие признака рёбра не вернёт, поэтому
`memory unarchive` нет, и асимметрия намеренная. У задачи таких рёбер нет — раскрытие
ничего не теряет.

## Схема

Миграция v25 добавляет одну nullable-колонку:

```sql
ALTER TABLE tasks ADD COLUMN archived_at TEXT;  -- ISO8601 UTC timestamp
CREATE INDEX idx_tasks_archived_at ON tasks(archived_at);
```

## См. также

- [Принципы тестирования](testing-principles.md)
- [CLI — Задачи](cli.md#задачи)
