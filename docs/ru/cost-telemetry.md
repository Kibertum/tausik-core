# Телеметрия стоимости — атрибуция токенов по задачам

TAUSIK пишет LLM-телеметрию в две связанные таблицы:

| Таблица | Источник | Гранулярность | Когда |
|---|---|---|---|
| `session_usage_metrics` | `scripts/hooks/session_metrics.py` | per-session rollup | SessionEnd |
| `usage_events` | `scripts/hooks/posttool_usage.py` (v1.4) | per-tool-call | PostToolUse |

Session rollup отвечает на вопрос "сколько стоила сессия?" Per-tool ledger — на вопрос "сколько стоила *задача*?" — это нужно для баннера рекомендации модели, бюджетов задач и cost dashboard.

## Per-tool ledger

Каждый tool call (Read, Edit, Bash, MCP и т.д.) триггерит `posttool_usage.py`. Хук:

1. Читает harness payload из stdin.
2. Достаёт `tool_name` и (best-effort) `tool_response.usage.input_tokens` / `output_tokens` / `model`.
3. Ищет активную задачу — одна строка в `tasks WHERE status='active'`. При 0 или >1 — атрибуция `NULL`.
4. Считает `cost_usd` через `cost_pricing.calculate_cost_usd()`.
5. Пишет `usage_events` с `source='posttool'`.

Сбои никогда не блокируют harness. 5 graceful-degradation путей покрыты тестами:

- битый JSON в stdin,
- нет активной задачи (`task_slug=NULL`),
- неизвестный `model_id` (`cost_usd=0` + stderr warn),
- заблокирована БД (3 retry, затем stderr warn),
- нет `.tausik/tausik.db` (silent exit 0).

## Запросы

```bash
.tausik/tausik metrics cost                       # rollup по task_slug
.tausik/tausik metrics cost --since 2026-05-01    # окно
```

`metrics cost` исключает строки с `task_slug IS NULL`, чтобы события без атрибуции не загрязняли отчёт.

## Схема

`usage_events` (с v1.4 / миграция v24):

| колонка | тип | примечание |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | |
| `session_id` | INTEGER NOT NULL | FK → sessions(id) |
| `task_slug` | TEXT NULL | FK → tasks(slug); NULL при отсутствии/конфликте |
| `model_id` | TEXT NULL | canonical Anthropic id |
| `tokens_input` / `tokens_output` / `tokens_total` | INTEGER ≥ 0 | |
| `cost_usd` | REAL ≥ 0 | считается при insert |
| `tool_calls` | INTEGER ≥ 0 | всегда 1 для posttool строк |
| `source` | TEXT | `session_record` / `manual` / `posttool` |
| `recorded_at` | TEXT | ISO-8601 UTC |
| `tool_name` | TEXT NULL | `Read`, `Edit`, `Bash`, MCP-метод, … |

## Прайсинг

`scripts/cost_pricing.py` — единственный источник правды. При изменении цен Anthropic обновляйте и модуль, и `docs/{en,ru}/cost-telemetry.md`.

## Ограничения

- Подсчёт токенов работает только когда harness реально отдаёт `tool_response.usage`. Claude Code пока отдаёт это не для всех tool'ов; строки без usage пишутся с `tokens=0` чтобы сохранить count of calls.
- Multi-active-task проекты (редкость) теряют per-task атрибуцию — `task_slug=NULL`.
- Миграция v24 ребилдит `usage_events` через temp table (расширение `source` CHECK + добавление `tool_name`). Существующие строки сохраняются, `tool_name` back-fill в NULL.
