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

## Per-task cost / token budget (v14c-token-budget-task)

Сестра `call_budget` — защита от runaway: лимит USD spend или token total на задачу.

```bash
# План: 1.20 USD и 50k токенов на complex рефактор.
tausik task add "Token-budget feature" --slug v14c-token-budget-task \
    --cost-budget 1.20 --token-budget 50000 --complexity complex

# Скорректировать позже.
tausik task update v14c-token-budget-task --cost-budget 2.50

# Детальный вид показывает actual / budget когда usage_events накопится.
tausik task show v14c-token-budget-task
# → cost: actual=$0.4321 / budget=$1.2000
# → tokens: actual=12000 / budget=50000
```

**Схема (v27):** четыре nullable колонки в `tasks`:

| Колонка | Тип | Пишется | Читается |
|---|---|---|---|
| `cost_budget_usd` | REAL | `task add/update --cost-budget` | hook + `task_done` |
| `cost_actual_usd` | REAL | `record_cost_actual` на `task_done` | `task show` |
| `token_budget` | INTEGER | `task add/update --token-budget` | hook + `task_done` |
| `tokens_actual` | INTEGER | `record_cost_actual` на `task_done` | `task show` |

**Две точки enforcement:**

1. **`task_done`** — `service_recording.record_cost_actual` роллапит `usage_events` для `task_slug = <slug>` с `started_at`, пишет `cost_actual_usd` / `tokens_actual` в строку, эмитит `WARNING:` в done-сообщение когда actual превышает 1.5× budget (cost ИЛИ tokens — независимые триггеры).
2. **PostToolUse hook `task_cost_budget_check.py`** — после каждого tool call; тот же rollup; эмитит одну stderr строку на tool call при пересечении порога:
   - `[TAUSIK cost-budget WARN]` при ≥ 1.5× AND < 2.0× — мягкий cap, advisory.
   - `[TAUSIK cost-budget BLOCKER]` при ≥ 2.0× — жёсткий cap. Агент читает строку следующим turn'ом и должен остановиться, перепланировать или поднять budget через `tausik task update --cost-budget`. (Hooks не могут физически блокировать Claude Code; это soft refuse.)

   Каждая `(slug, level)` пара дросселируется до 1 emission per 30 секунд через atomic write в `.tausik/.cost_budget_throttle.json`. Hook молчит когда:
   - `TAUSIK_SKIP_HOOKS=1`
   - 0 active задач (некому атрибутировать)
   - ≥ 2 active задач (multi-agent неоднозначность — та же политика что в `task_call_counter`)
   - У единственной active задачи не задан ни `cost_budget_usd`, ни `token_budget`
   - DB отсутствует или залочена

**Out of scope (отдельные задачи):** session-level token cap (зеркало `session_capacity_calls`), HUD/status display tokens-vs-budget, token-tier mapping в `/plan` SKILL.md.

## Ограничения

- Подсчёт токенов работает только когда harness реально отдаёт `tool_response.usage`. Claude Code пока отдаёт это не для всех tool'ов; строки без usage пишутся с `tokens=0` чтобы сохранить count of calls.
- Multi-active-task проекты (редкость) теряют per-task атрибуцию — `task_slug=NULL`.
- Миграция v24 ребилдит `usage_events` через temp table (расширение `source` CHECK + добавление `tool_name`). Существующие строки сохраняются, `tool_name` back-fill в NULL.
