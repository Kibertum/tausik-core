# Базовый замер экономики Cursor для 1.11.7

[English](../en/cursor-economy-baseline.md) | **Русский**

<!-- doc-map: reader=maintainer; zone=reference -->

Решение #433: слой экономики 1.11.7 для Cursor — это **раунды + поверхность**,
а не полировка кэша. Здесь — как считать раунды на playbook memory-only и что
остаётся **unknown**, если у хоста нет журнала.

## Правила честности

- **Не** переклеивать числа Codex ([codex-economy-baseline](codex-economy-baseline.md))
  как экономию Cursor.
- **Не** заявлять API-USD или % подписки без датированной публичной таблицы цен
  в том же абзаце.
- Лучше «unknown», чем выдуманный before/after.

## Фиксированный сценарий (memory-only)

Модель, план Cursor и набор MCP не менять. В проекте
`governance_profile=memory-only`. Сценарий:

1. `tausik_memory_brief` (один раз)
2. `tausik_memory_search` или `tausik_decisions_list` (поиск до записи)
3. `tausik_decide` **или** `tausik_memory_add` (одна долговечная запись)
4. Опционально лёгкая задача: `tausik_task_quick` → `tausik_task_done` **без**
   `session_start` / `verify`

Стоп, когда запись долговечна. SENAR-сессию не открывать.

## Как считать раунды

| Сигнал | Как | Когда доступен |
|---|---|---|
| Раунды агента/инструментов | Считать ходы модели с ≥1 tool call или пакеты tool-call в транскрипте Cursor | Всегда вручную по чату |
| Premium requests | Дельта «premium requests» в UI/биллинге Cursor за окно, если счётчик есть | Только если UI показывает датированный счётчик для этого чата |

Записать: дату, model id, имена включённых MCP, число раундов (или дельту
premium) и факт, что сценарий прошёл без `session_start`/`verify`.

## Статус релиза 1.11.7

**Замеренные before/after раунды для этого сценария: unknown.**

Блокирующий сигнал: Cursor не отдаёт проектный журнал tool-раундов, который
TAUSIK мог бы читать так же, как журналы Codex для `tausik metrics --host codex`.
Релиз несёт метод и чеклист выше, а не числовой claim.

Ручной чеклист:

1. Новый чат агента Cursor на fixture-проекте memory-only.
2. Отключить non-TAUSIK MCP (см. [context-economy](context-economy.md)).
3. Пройти четыре шага; записать раунды в журнал задачи или датированную
   research-заметку.
4. Повторить после деплоя playbook (`tausik_memory_brief` + lite skills) во
   втором чате; сравнивать только раунды — никогда USD.

Когда появится ledger хоста — заполнить ячейки before/after здесь, не переписывая
этот раздел честности.
