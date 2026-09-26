---
slug: telemetry-and-pricing-know-one-vendor-only
title: "Телеметрия понимает одну форму полезной нагрузки и цены одного вендора: на другой модели пишутся нули"
status: done
epic: release-19-renar-conformance
story: guarantees-are-not-claude-only
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: "НЕ ТРОГАТЬ: (1) КЛЮЧ атрибуции usage_events (задача usage-attribution-is-keyed-by-task-not-session, эпик 1.10) — здесь только СОДЕРЖИМОЕ строки, не то, к чему она привязана; (2) механизм записи модели хостом (задача session-model-recorded-on-non-claude-hosts) — она следующая в очереди владельца и делается отдельно; (3) лента .tausik/token_metrics.jsonl и её покрытие; (4) четыре реестра хостов (эпик 1.10)."
relevant_files:
  - "scripts/hooks/posttool_usage.py"
  - "scripts/hooks/session_metrics.py"
  - "scripts/backend_migrations_v58.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_queries_usage.py"
  - "scripts/cost_pricing.py"
  - "scripts/service_recording.py"
  - "tests/test_usage_absence_is_not_zero.py"
  - "tests/test_cost_pricing.py"
  - "tests/test_posttool_usage_hook.py"
  - "tests/test_session_metrics_parse.py"
  - "tests/test_cost_budget_task.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/hooks/posttool_usage.py"
  - "scripts/backend_migrations_v58.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_queries_usage.py"
  - "scripts/cost_pricing.py"
  - "scripts/service_recording.py"
  - "scripts/hooks/task_cost_budget_check.py"
  - "scripts/render_metrics.py"
  - "scripts/project_cli_metrics.py"
  - "tests/test_usage_absence_is_not_zero.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on:
  - session-model-recorded-on-non-claude-hosts
completed_at: "2026-09-07T21:34:21Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАМЕР ДО ПРОЕКТИРОВАНИЯ ОПРОВЕРГ ПОСЫЛКУ ЗАДАЧИ. Задача заведена как «на другой модели пишутся нули». Замер на собственной БД проекта (смена #231, 55 583 события):  — 55 288 событий (99.5%) несут tokens_input=0, tokens_output=0 и model_id=NULL. Все они из source='posttool'. — cost_usd: 55 471 строка говорит 0, 113 говорят >0, NULL нет НИ ОДНОЙ. «Неизвестно» хранится как ноль. — tasks.cost_actual_usd > 0: НОЛЬ задач. 669 задач записали 0, 891 — NULL. — Единственный инструмент, чья полезная нагрузка PostToolUse вообще несёт usage, — Agent (75 строк). Bash (26 129), Read (7 385), Edit (6 346), Grep, Write, ToolSearch, MCP-инструменты — ни одной.  ПРИЧИНА, А НЕ СИМПТОМ: _extract_usage читает tool_response.usage. Результат ИНСТРУМЕНТА структурно не несёт usage — usage живёт в сообщении модели. То есть функция читает поле, которого в этой форме нет в принципе, и записывает ноль как измерение. Дефект не межвендорный: он на этом же вендоре, на этой же модели, в 99.5% строк.  СЛЕДСТВИЕ: продукт утверждает «эта работа стоила $0.00» 55 471 раз. Это нарушение решения #334 в собственной телеметрии, ровно того масштаба, ради которого решение и принималось.  ЧТО ДЕЛАЕТСЯ: отсутствие становится представимым. Колонки токенов и стоимости в usage_events перестают быть NOT NULL; неизмеренное пишется как NULL; уже записанные строки, о которых ДОКАЗУЕМО известно, что измерения не было, мигрируют в NULL. SUM в SQLite пропускает NULL и возвращает NULL, когда измерений нет вовсе, — то есть честный ответ получается сам. Извлечение токенов становится набором адаптеров по ФОРМЕ полезной нагрузки; неизвестная форма даёт явное отсутствие, а не ноль. Таблица цен отличает «цена неизвестна» от «бесплатно» на уровне данных.

## Acceptance Criteria

AC1. ОТСУТСТВИЕ ПРЕДСТАВИМО В ХРАНИЛИЩЕ. tokens_input, tokens_output, tokens_total и cost_usd в usage_events перестают быть NOT NULL. Миграция несёт ЗАМОРОЖЕННЫЙ ЛИТЕРАЛ DDL, а не чтение живой схемы: чтение сделало бы позднюю правку задним числом меняющей историю.

AC2. ИЗВЛЕЧЕНИЕ ВОЗВРАЩАЕТ ОТСУТСТВИЕ, А НЕ НОЛЬ. _extract_usage на полезной нагрузке без usage возвращает None, а не 0. Ноль возвращается ТОЛЬКО когда в нагрузке действительно стоит ноль — это разные утверждения, и тест проверяет оба случая раздельно.

AC3. ФОРМЫ РАЗБИРАЮТСЯ АДАПТЕРАМИ. Известные формы (tool_response.usage, tool_response.message.usage) читаются как раньше; форма, которой адаптер не знает, даёт явное отсутствие. Двусторонняя проверка: неизвестная форма НЕ даёт нуля И известная форма по-прежнему читается.

AC4. УЖЕ ЗАПИСАННАЯ ЛОЖЬ ИСПРАВЛЕНА РОВНО ТАМ, ГДЕ ОНА ДОКАЗУЕМА. Миграция переводит в NULL только строки source='posttool' с нулями и без модели — те, о которых известно, что измерения не было. Строка с настоящим нулём не трогается. Число затронутых строк печатается, а не подразумевается.

AC5. ПОТРЕБИТЕЛИ ПОКАЗЫВАЮТ «НЕ ИЗМЕРЕНО», А НЕ НОЛЬ. Роллап по задаче без единого измерения даёт NULL и печатается как «не измерено»; роллап с измерениями считает по ним. Бюджет по стоимости не срабатывает на неизмеренном и НЕ считает его нулём.

AC6. ЦЕНА НЕИЗВЕСТНА И БЕСПЛАТНО — РАЗНЫЕ ЗАПИСИ. В таблице цен различие выражено данными, а не надеждой: модель без цены даёт отсутствие стоимости, модель с ценой 0 даёт ноль, и снаружи они различимы.

AC7 (НЕГАТИВНЫЙ). НОЛЬ НЕ ПОДМЕНЯЕТСЯ ОТСУТСТВИЕМ В ОБРАТНУЮ СТОРОНУ. Событие, где модель действительно вернула 0 токенов, остаётся нулём и попадает в суммы. Тест доказывает, что миграция и новый код не стирают настоящие нули.

AC8 (НЕГАТИВНЫЙ). МЕТРИКИ НЕ ПАДАЮТ НА NULL. Каждый потребитель колонок прогоняется на строке с NULL: ни исключения, ни молчаливого приведения к нулю. Прогон полного набора тестов — часть критерия.

AC9 (БЕЗОПАСНОСТЬ ДАННЫХ). МИГРАЦИЯ ПЕРЕСТРАИВАЕТ ТАБЛИЦУ СО СТОИМОСТЬЮ — поверхность угрозы здесь не сеть, а необратимая потеря учётных данных. Требования: (а) CHECK, запрещающий отрицательные токены и стоимость, СОХРАНЯЕТСЯ и лишь допускает NULL — ослабление ограничения не является побочным эффектом послабления обязательности; (б) перенос строк идёт одним оператором INSERT ... SELECT внутри транзакции, частичный результат невозможен; (в) число строк до и после совпадает, и это проверяется тестом, а не глазом; (г) ни одна строка с ненулевыми токенами или ненулевой стоимостью не изменяется.

## Plan

## Rollback

Адаптеры извлечения плюс записи цен. Откат — git revert; собранные события остаются, повторный разбор не требуется.

## Journal

- 2026-08-29T13:57:38Z [planning] — [#189] ПЕРЕСЕЧЕНИЕ: ext-p1-provider-refactor, пункт G6 — «session model recording for non-Claude hosts (TAUSIK_AGENT_MODEL) so cost/pinning survive under GLM». Это ровно половина данной задачи (запись модели на не-Claude хосте), и она заведена там раньше. Не дублировать: здесь делается разбор ФОРМЫ полезной нагрузки и таблица цен по вендорам, там — механизм записи модели хостом. При взятии любой из двух свериться со второй. Дополнительно замерено, что задача zai-claude-code-firstclass закрылась со строкой cost: actual=$0.0000 / tokens: actual=0 — то есть нули писались уже тогда, в задаче ПРО GLM.
- 2026-08-29T14:22:55Z [planning] — [#189] ПОПРАВКА К ССЫЛКЕ: задача ext-p1-provider-refactor, упомянутая выше, УДАЛЕНА 29.08 после расщепления на четыре оценённые задачи (provider-generates-artifacts-not-the-if-ide-ladder, four-ide-registries-collapse-into-one, session-model-recorded-on-non-claude-hosts, bundled-root-separate-from-vendored-copy). Ссылка сохранена как происхождение формулировок, а не как указатель на живую задачу — искать её в базе бесполезно. Найдено собственной проверкой плана: это ровно тот класс сгнившей ссылки, который чинит audit evidence.
- 2026-09-07T21:33:06Z [implementation] — ЗАМЕР ДО ПРОЕКТИРОВАНИЯ ОПРОВЕРГ ПОСЫЛКУ. Задача: «на другой модели пишутся нули». Факт на собственной БД: 55 288 из 55 583 событий (99.5%) несут нули И NULL-модель, все из source=posttool; cost_usd=0 в 55 471 строке, NULL нет ни одной; задач с cost_actual_usd>0 — НОЛЬ. Дефект не межвендорный: он здесь, на этом вендоре. Причина структурная: _extract_usage читал tool_response.usage, а результат ИНСТРУМЕНТА usage не несёт — usage принадлежит сообщению модели. Bash 26 129 строк, Read 7 385, Edit 6 346 — ни одной с usage. Единственный инструмент, который его несёт, — Agent, 75 строк.
- 2026-09-07T21:33:24Z [implementation] — AC verified: 1. ✓ схема v58: tokens_input/tokens_output/tokens_total/cost_usd допускают NULL, миграция несёт ЗАМОРОЖЕННЫЙ ЛИТЕРАЛ (tests/test_usage_absence_is_not_zero.py). 2. ✓ _extract_usage возвращает None при отсутствии usage и (0,0) когда в нагрузке действительно ноль — test_the_shape_that_never_carried_usage_yields_absence и test_a_real_zero_in_the_payload_is_a_measurement. 3. ✓ четыре известные формы читаются (параметризованный test_every_known_shape_is_still_read), неизвестная даёт отсутствие. 4. ✓ миграция тронула ровно доказуемое: на живой БД 55 307 строк перешли в NULL, 295 измеренных сохранены, 2 настоящих нуля остались нулями. 5. ✓ роллап без измерений даёт None и несёт measured_event_count как знаменатель; бюджет пропускает сравнение на неизмеренном; CLI печатает cost NOT MEASURED. 6. ✓ get_pricing различает отсутствие цены (None) и цену ноль ({input:0,output:0}) — test_a_free_model_and_an_unpriced_model_are_told_apart. 7. ✓ настоящий ноль сохранён в обе стороны: test_a_measured_zero_stays_zero, test_a_priced_model_with_zero_tokens_really_does_cost_zero, строки source=manual и session_record не тронуты. 8. ✓ потребители на NULL не падают: найдено и исправлено реальное падение session_metrics (TypeError на форматировании None); полный набор 9825 passed, mypy 419 файлов чисто. 9. ✓ CHECK на неотрицательность сохранён и проверен параметризованным test_nonsense_is_still_refused; перенос строк — один INSERT ... SELECT; число строк совпадает (test_no_row_is_lost_or_gained); индексы восстановлены (test_the_indexes_survive_the_table_swap). Domain: миграция прогнана на НАСТОЯЩЕЙ базе проекта, а не на фикстуре: 55 602 строки, из них 55 307 перешли в NULL, 295 измеренных сохранились, индексы на месте, doctor чист, tausik metrics печатается. Negative: AC7 и AC8 — негативные — прогнаны: настоящий ноль остаётся нулём (три отдельных теста), а падение потребителя на NULL было найдено тестом и исправлено, а не обойдено.
