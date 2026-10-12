[English](../en/cost-telemetry.md) | **Русский**

# Телеметрия стоимости — атрибуция токенов по задачам

<!-- doc-map: reader=user; zone=quality -->

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

`metrics cost` исключает строки с `task_slug IS NULL` из таблицы по задачам, чтобы события без
атрибуции не загрязняли её и не удваивали суммы. Но с v48 они не пропадают из вида: под таблицей
печатается явная корзина «вне задачи» — сколько таких событий, сколько токенов и стоимости, и
сколько из них не имели даже сессии. Корзина печатается и когда таблица по задачам пуста.

## Схема

`usage_events` (с v1.4 / миграция v24; `session_id` ослаблен миграцией v48):

| колонка | тип | примечание |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | |
| `session_id` | INTEGER NULL | FK → sessions(id) ON DELETE SET NULL; NULL, если сессия не открыта (v48) |
| `task_slug` | TEXT NULL | FK → tasks(slug) ON DELETE SET NULL; ОСНОВНАЯ атрибуция события (v48) |
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

## Цена задачи в ходах

```bash
python scripts/turn_economy.py          # отчёт
python scripts/turn_economy.py --json   # то же машинно
```

**Почему единица — ХОД, а не запрос.** На 5964 строках телеметрии входная сторона на 99,5%
`cache_read`: 2 876 911 173 токена против 22 099 свежего входа. Префикс пересылается целиком на
каждом вызове, поэтому лишний ВЫЗОВ стоит около 482 000 токенов, а укорачивание запроса экономит
сотни. Правка, сокращающая запрос ценой лишнего хода, проигрывает примерно сто к одному.

**Что показал замер** (1230 закрытых задач с записанным `call_actual`): медиана 20 ходов, p90 78,
максимум 1900. По месяцам: 2026-04 медиана 6 → 2026-09 медиана 32, p90 35 → 114. В токенах —
9,6 млн на медианную задачу и 37,6 млн на p90.

**Куда уходят ходы** (8195 измеренных вызовов): `Bash` 87,6% и 3,64 из 4,07 млрд `cache_read`,
`Write` 7,7%, `Edit` 2,7%, всё остальное вместе меньше 2%.

Обе половины ЛОКАЛЬНЫ: `call_actual` лежит в базе этого проекта, сайдкар пишет хук этой машины.
Ни то ни другое не ездит, поэтому на свежем клоне отчёт говорит об отсутствии словами, а не
выдаёт ноль.

## Нативные отчёты Codex и Kilo (1.11)

```bash
tausik metrics tokens --host codex --json
tausik metrics tokens --host kilo --json
```

CLI и `tausik_metrics({"host": "codex" | "kilo"})` вызывают одну реализацию
отчёта. Если источник отсутствует, ответ содержит `source_available: false` и
неизвестные счётчики вместо нулей.

Адаптер Codex следует явным границам `task start` / успешного `task done` в
порядке нативных ответов. Неудачные попытки закрытия и переделка остаются в
стоимости окна, а в `accepted_task_cost` задача попадает только при статусе
`done` в проектной базе. Для задачи выводятся ходы модели,
input/cached/output/reasoning, attempts/retries и наблюдённая идентичность
model/reasoning/speed. История форка, вложенные и незаконченные окна и ответы вне
границ остаются без атрибуции. Команды и tool output просматриваются только для
проверки успеха границы и не сохраняются в кэше.

Адаптер Kilo открывает документированную локальную SQLite-базу только для чтения.
Он выбирает лишь идентификатор ответа, provider/model/version и пять токенных
счётчиков; промпты, tool payload, учётные данные и исходные пути проекта не попадают
в проектный кэш. Kilo хранит обычный input, cache read, cache write, обычный output
и reasoning раздельно, поэтому TAUSIK сначала восстанавливает общие input/output.
Инкрементальное чтение опирается на идентификатор и время обновления ответа, а
агрегаты сессии дают независимую сверку.
Завершённые ответы и ошибки считаются отдельно, поэтому API error с нулевым расходом
нельзя принять за успешный запуск GLM.

В этой базе нет квоты подписки Kilo. Отчёт оставляет `account_quota: null`, не
применяет прайс и не заявляет экономию. Документация API провайдера о cached tokens
не доказывает, что конкретный хост передал тот же счётчик. Атрибуция к задаче тоже
неизвестна: ответ Kilo не содержит slug задачи TAUSIK.

## Естественные когорты проекта (1.11.1)

`tausik metrics cohorts` и `tausik_metrics({"view":"cohorts"})` показывают
инвентарь реальной принятой работы до любого сравнения. Чтение нативных источников
Codex/Kilo записывает в `benchmark_observations` только нормализованные счётчики и
identity. Повторное чтение сходится по непрозрачному хэшу ответа, а завершённый
нативный ответ заменяет свои прежние частичные счётчики. Промпты, ответы,
tool payload, credentials и исходные пути транскриптов не сохраняются.

Версию TAUSIK доказывают совпадающие границы старта и завершения задачи. Строки с
отсутствующими или разными границами остаются `legacy/unclassified`: импортёр не
угадывает, по какую сторону обновления появился ответ. Смена
host, provider, model, reasoning effort или speed mode разделяет когорты. Принятой
считается только доставленная `done`-задача без obsolete-resolution. Неудачные
попытки и все прогоны review/verification остаются в evidence задачи. Если работа
охватывает несколько identity, task-level evidence показывается один раз в unsplit-корзине,
а не начисляется каждой когорте. Неатрибутированная и ещё не принятая
работа показываются отдельными корзинами.

Пропуски identity, счётчиков, task linkage и quality evidence остаются `null` и
снижают coverage. Cached input — подмножество input, reasoning output — подмножество
output; их не прибавляют к родительским итогам. Инвентарь показывает даты, размер
выборки, coverage, attempts/retries, verification outcome и review depth/invocations.
Эта задача не считает API-эквивалент USD и не заявляет экономию: цены применяет
следующая задача сравнения.
Время от старта до завершения не считается active duration: без прямого измерения
active duration остаётся неизвестной.

### Сравнение двух естественных когорт

Работайте как обычно на одной версии TAUSIK, обновитесь и продолжайте обычную
работу. Когда по обе стороны накопится достаточно принятых задач, сравните
естественные когорты. Не заказывайте платные повторы, не воспроизводите
промпты, не запускайте синтетический корпус и не заполняйте матрицу
версия×модель.

```bash
# Одна наблюдаемая модель до и после обновления.
tausik metrics compare \
  --left-label before --left-version 1.11.0 --left-model gpt-5 \
  --right-label after --right-version 1.11.1 --right-model gpt-5 \
  --minimum-sample 5 --save .tausik/reports/1.11.0-vs-1.11.1.json

# Одна версия TAUSIK и две модели, реально использованные проектом.
tausik metrics compare \
  --left-version 1.11.1 --left-model gpt-5 \
  --right-version 1.11.1 --right-model gpt-6
```

`tausik_metrics` выполняет ту же операцию при `view="comparison"` и объекте
`compare` с селекторами `left`/`right`. Селектор принимает `tausik_version`, `provider`,
`model`, `reasoning_effort`, `speed_mode`, `since`, `until` и отображаемый
`label`. Полная декартова матрица не требуется.

Отчёт сначала агрегирует ответы по задаче, затем считает median и p90. Он
показывает покрытие для раундов ответа, вызовов инструментов, измеренной
активной длительности, попыток/повторов, всего входа, кэшированного и
некэшированного входа, выхода, reasoning-подмножества и общих токенов
(`input + output`). Кэшированный вход входит во вход, а reasoning — в выход;
эти подмножества повторно не суммируются.

API-эквивалент USD необязателен и не означает расход подписки, credits или
остаток квоты. Укажите датированную таблицу провайдера в
`.tausik/config.json`:

```json
{
  "api_equivalent_usd_rate_card": {
    "source": "https://provider.example/pricing/2026-10-01",
    "as_of": "2026-10-01",
    "valid_until": "2026-12-31",
    "unit": "usd_per_million_tokens",
    "models": {
      "openai/gpt-5": {
        "uncached_input": 1.25,
        "cached_input": 0.125,
        "output": 10.0
      }
    }
  }
}
```

Берите датированные ставки провайдера; числа выше показывают только схему.
Отсутствующая, неверная, просроченная или неподходящая таблица даёт `null`, а
не ноль. Credits подписки и включённая квота остаются отдельными неизвестными.

Качество показано рядом со стоимостью: доли неуспешных/повторных verify,
распределение L1/L2/L3/deep review, вызовы ревьюеров, подтверждённые
critical/high находки и дефекты после объявленного окна созревания. Отчёт
стратифицирует сложность, assurance profiles и impact. Разный состав задач
даёт предупреждение. Малые выборки, смешанные настройки модели или
одновременная смена версии и модели делают результат `inconclusive`.
Наблюдаемая разница не превращается в причинную экономию или универсальный
коэффициент эффективности.

Сохранённый snapshot содержит запрос, покрытие, происхождение цен, точные
версии/модели, непрозрачные хэши состава когорт и время генерации. Имена задач
и сырой диалог в него не попадают.

## Ограничения

- **Токены сессий, записанные до 1.10, завышены и не пересчитываются**. Claude Code пишет одно сообщение API с N блоками как N записей транскрипта с одинаковым usage, и счётчик складывал его N раз: 1,81× на replay-транскрипте смены #263. С 1.10 usage считается один раз на message id. Завышение зависит от числа блоков, поэтому старые строки не делятся на константу; сравнивать их с новыми нельзя.
- **`tausik metrics tokens` НЕ атрибутирует стоимость по инструментам и
  сообщает об этом до того, как что-либо покажет.** Расход API отчитывается на
  *сообщение*, а не на вызов инструмента — собирающий хук сам об этом говорит.
  В `.tausik/token_metrics.jsonl` попадает message-level величина,
  проставленная тому инструменту, который случился рядом: поэтому `in_p50` и
  `in_p90` выходят почти одинаковыми у всех инструментов, `in_total`
  отслеживает количество вызовов, а сумма `cache_read` пересчитывает один
  кэшированный контекст на каждом вызове. Читайте таблицу как **объём
  вызовов** — это она меряет честно. Атрибуция затрат по инструментам требует
  парсера уровня транскрипта, которого пока нет. По этой же причине вопрос о
  токенах саб-агентов не был отвечаем никогда: вызовы `Agent` записываются как
  ~2 входных токена, то есть собственный расход саб-агента здесь невидим.
- Подсчёт токенов работает только когда harness реально отдаёт `tool_response.usage`. Claude Code пока отдаёт это не для всех tool'ов; строки без usage пишутся с `tokens=0` чтобы сохранить count of calls.
- Multi-active-task проекты (редкость) теряют per-task атрибуцию — `task_slug=NULL`.
- Миграция v24 ребилдит `usage_events` через temp table (расширение `source` CHECK + добавление `tool_name`). Существующие строки сохраняются, `tool_name` back-fill в NULL.
