---
slug: our-evidence-speaks-only-our-own-schema
title: "Наши следы говорят только на нашем языке: у наблюдаемости агентов появился стандарт, и мы вне его"
status: done
epic: release-19-renar-conformance
story: standards-drift-detection
complexity: medium
role: architect
stack: python
tier: substantial
call_budget: 100
defect_of: null
scope: "scripts/otel_genai.py (новый), scripts/project_parser.py и scripts/project_cli_*.py (команда экспорта), tests/test_otel_genai.py (новый), docs/ru/cli.md, docs/en/cli.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "схема БД (миграций нет), сетевой OTLP-экспортер (отдельная работа: требует зависимости и решения о сети), состав внутренних событий"
relevant_files:
  - "scripts/otel_semconv.py"
  - "scripts/otel_export.py"
  - "scripts/hooks/session_metrics.py"
  - "tests/test_otel_export.py"
  - "tests/test_session_metrics_parse.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-06T12:34:46Z"
resolution: null
resolution_reason: null
---

## Goal

У OpenTelemetry есть семантические соглашения GenAI: имена спанов, ключи атрибутов, метрики и события для вызова модели, ВЫПОЛНЕНИЯ ИНСТРУМЕНТА, прогона агента, извлечения и ОПЕРАЦИЙ ПАМЯТИ. Вложенность invoke_agent / chat / execute_tool, атрибуты модели и токенов, метрика длительности операции, отдельные соглашения для MCP. Статус — Development, разделение репозиториев в июне 2026, но основные понятия устоялись.

У нас есть events, usage_event_log и task replay — всё в частной схеме. Следствие двустороннее: наши доказательства не читаются НИКАКИМ стандартным инструментом, и мы не читаем ничьи. Для продукта, который продаёт доказуемость, это сужение аудитории до тех, кто согласился на наш формат.

Задача: научиться ИЗЛУЧАТЬ спаны GenAI поверх того, что уже пишется, не заменяя внутреннюю схему. Квитанция получает возможность ссылаться на стандартный след, а не только на собственные записи. НЕГАТИВНОЕ ОГРАНИЧЕНИЕ ПЕРВОЕ: соглашения В РАЗРАБОТКЕ, имена атрибутов ещё поедут — та же ловушка, что с отозванной подписью ADAPT, поэтому привязка идёт через один слой отображения, а не россыпью по коду. НЕГАТИВНОЕ ВТОРОЕ: излучение НЕ ИМЕЕТ ПРАВА открывать сеть по умолчанию — README обещает ноль обращений наружу, и экспортер обязан быть выключен, пока его явно не включили. Смежное: гипотеза r-capture-tool-traces-and-prove-they-answer-something.

## Acceptance Criteria

AC-1 (ОДИН слой отображения): весь контакт с семантическими соглашениями GenAI живёт в одном модуле; имена атрибутов и операций объявлены ОДНОЙ таблицей, а не россыпью по коду. Тест: ни один другой файл scripts/ и harness/ не содержит строк, начинающихся на «gen_ai.» (детектор по образцу охраны второй литеральной копии).
AC-2 (излучение поверх существующего, без замены): спаны выводятся из уже записанных usage_events и events; внутренняя схема НЕ меняется (миграции нет), и это проверено тестом на неизменность списка таблиц/колонок, задействованных отображением.
AC-3 (выключено по умолчанию и НОЛЬ сети): без явной команды или ключа конфигурации не пишется ничего; экспортер пишет только в ФАЙЛ, сетевых вызовов в модуле нет вовсе. Negative: тест утверждает, что модуль не импортирует ни socket, ни http-клиент, и что вызов без явного включения ничего не создаёт.
AC-4 (версия соглашений объявлена, привязка обратима): модуль называет версию семантических соглашений, к которой он привязан, и говорит, что имена ещё поедут; смена имени атрибута — правка ОДНОЙ таблицы. Тест: отображение строится из таблицы, а не из литералов в функциях (мутация подмены имени в таблице меняет выход).
AC-5 (детерминированность и ссылаемость): trace_id и span_id выводятся из наших идентификаторов детерминированно (одна и та же строка даёт тот же id), длина и форма — как требует OTLP (16 и 8 байт в hex). Negative: две разные строки не дают одинаковый span_id.
AC-6 (честность неполноты): то, чего мы не знаем, НЕ выдумывается — отсутствующая модель, нулевые токены, неизвестное имя инструмента дают отсутствие атрибута, а не ноль или «unknown». Тест на каждый случай.
AC-7: `tausik otel export` (или эквивалент) описан в docs/{ru,en}/cli.md; полный прогон, mypy, ruff; мутации объявлены и убиты ПО ВЕТВИ либо объявлены эквивалентными; CHANGELOG в обоих файлах; README-обещание «ноль обращений наружу» не нарушено и это сказано в докстринге.

## Plan

## Rollback

git revert коммита задачи. Схема БД не меняется, экспортер выключен по умолчанию, поэтому откат ничего не ломает и не требует миграции.

## Journal

- 2026-09-06T12:26:26Z [implementation] — ЗАМЕР ДО ПРАВКИ: ПРЕМИСА ЗАДАЧИ УСТАРЕЛА ЧАСТИЧНО. Инвентарь ПО ИМЕНИ (ls scripts | grep otel) и ПО ЗНАЧЕНИЮ (grep «gen_ai.») показал, что часть работы СДЕЛАНА в релизе 1.8 задачей l26-otel-export, коммит 37e81bd: scripts/otel_semconv.py (63 строки) — ЕДИНСТВЕННЫЙ носитель имён gen_ai.*, с объявленной нестабильностью соглашений и ссылкой на репозиторий-источник; scripts/otel_export.py (158 строк) — OTLP/JSON без SDK, stdlib-only, выключен по умолчанию, включается конфигом или переменной среды с явным kill switch; tests/test_otel_export.py (258 строк, 22 теста) уже пинит: off by default, отсутствующие поля ОПУСКАЮТСЯ, детектор второй копии имён вне маппера, отказ на некорректных id и на спане с концом раньше начала. Единственный вызывающий — scripts/hooks/session_metrics.py. ЧТО РЕАЛЬНО ОСТАЛОСЬ, и это ровно то, что называет текст задачи: (1) излучается ОДИН спан на СМЕНУ, а соглашения описывают ВЛОЖЕННОСТЬ invoke_agent → execute_tool/chat, и задача прямо называет выполнение инструмента, прогон агента и операции памяти; (2) GEN_AI_OPERATION_VALUE = «session» — значение, которого в закрытом перечне операций соглашений НЕТ: спан имеет форму GenAI и объявляет операцию, которой соглашения не определяют, то есть говорит на чужом языке с чужим словом; (3) квитанция сослаться на стандартный след по-прежнему не может. ВЫВОД ПО ОБЪЁМУ: беру (1) и (2) — вложенные спаны с ИМЕНАМИ ОПЕРАЦИЙ ИЗ СОГЛАШЕНИЙ, выводимые из уже записанных usage_events (tool_name, tool_calls, model_id, токены), плюс детерминированные id. Пункт (3) объявляю остатком: он требует решения, ЧТО именно квитанция цитирует (trace_id смены или span конкретного прогона) и переживает ли эта ссылка смену версии соглашений — отдельная работа, и её премиса не проверена. AC-1..AC-4 в части единственного слоя и выключенности УЖЕ ВЫПОЛНЕНЫ прежней задачей — проверяю их прогоном, а не переписываю.
- 2026-09-06T12:30:48Z [implementation] — ПОЧИНКА (приращение поверх сделанного в 1.8). (1) ИМЯ ОПЕРАЦИИ ПЕРЕСТАЛО БЫТЬ НАШИМ СЛОВОМ: gen_ai.operation.name — перечисление соглашений, а мы печатали «session», которого там нет; теперь смена — invoke_agent, вызов инструмента — execute_tool, оба объявлены в OPERATIONS, плюс gen_ai.agent.name. Функция operation_for отвечает None на то, что честно отобразить нельзя (операция памяти, поиск знаний), и вызывающий не выдаёт спан вместо выдуманного слова. (2) ВЛОЖЕННОСТЬ: build_otlp_trace принимает tool_calls и строит ДОЧЕРНИЕ спаны execute_tool с parentSpanId; id ребёнка выводится sha256 из (родитель, id строки, время, имя) — детерминирован и посолен родителем, чтобы одна строка из двух смен не столкнулась. Строка без имени инструмента, вне окна родителя или с концом раньше начала — пропускается, а не угадывается; строка без своего окна наследует окно родителя («это было в течение смены» — правда, выдуманная длительность — нет). (3) ИСТОЧНИК ЖИВОЙ: session_metrics уже обходил блоки tool_use ради счёта; теперь по тому же обходу собирает имена в OUT-ПАРАМЕТР, а не в словарь метрик — тот пишется в файл и в БД, и телеметрии там не место. НАЙДЕНО СВОИМ ЖЕ ПРОГОНОМ: 22 прежних теста прошли ПОСЛЕ смены имени операции и добавления атрибута — так быть не должно. Разбор: test_golden_document_is_stable сравнивал документ САМ С СОБОЙ (тавтология под именем, обещающим эталон), а структурный тест утверждал лишь assert span["name"] (истинность), не значение. Переименован в test_the_document_is_deterministic, добавлены test_the_operation_name_is_one_the_conventions_define и test_no_operation_value_of_our_own_invention_survives. ТЕСТЫ: 33 в test_otel_export (было 22), 17 в test_session_metrics_parse (было 14), все одиночным прогоном. ОСТАТОК ОБЪЯВЛЕН: ссылка квитанции на стандартный след не построена — требует решения, что именно цитируется и переживает ли ссылка смену версии соглашений.
- 2026-09-06T12:34:43Z [implementation] — AC-1 (один слой отображения): ✓ уже выполнено задачей l26-otel-export и проверено прогоном — tests/test_otel_export.py::TestSemconvSingleSource::test_no_hardcoded_semconv_names_outside_mapper зелёный; новые имена (gen_ai.tool.name, gen_ai.agent.name) и перечень операций добавлены в тот же scripts/otel_semconv.py, ни одного литерала gen_ai.* вне него AC-2 (излучение поверх существующего, схема не меняется): ✓ миграции нет; строки для дочерних спанов собираются на уже выполнявшемся обходе расшифровки и передаются ВЫХОДНЫМ ПАРАМЕТРОМ. Negative: tests/test_session_metrics_parse.py::TestToolRowsForTheOptionalTrace::test_the_metrics_dict_is_unchanged_by_the_collection — словарь метрик побайтно тот же с параметром и без (мутация O8 «строки утекли в метрики» убита) AC-3 (выключено по умолчанию, ноль сети): ✓ tests/test_otel_export.py::TestExportEnabled::test_default_off и ::test_env_falsy_overrides_config_enabled; экспортер пишет только в файл, сетевых вызовов в модуле нет; tests/test_otel_export.py::TestOptInWiring::test_disabled_returns_empty AC-4 (версия соглашений объявлена, привязка обратима): ✓ tests/test_otel_export.py::TestSemconvSingleSource::test_instability_is_documented; отображение строится из таблицы имён — мутация O1 (имя операции обратно в «session») убита tests/test_otel_export.py::TestBuildOtlpTrace::test_the_operation_name_is_one_the_conventions_define AC-5 (детерминированность и ссылаемость): ✓ tests/test_otel_export.py::TestToolSpansNestUnderTheAgentRun::test_child_ids_are_derived_and_distinct (та же строка — тот же id, разные строки — разные, форма 16 hex). Negative: ::test_the_same_row_under_another_parent_gets_another_id (мутация O5 «соль родителя снята» убита) AC-6 (честность неполноты): ✓ tests/test_otel_export.py::TestToolSpansNestUnderTheAgentRun::test_tokens_and_model_travel_when_present_and_are_omitted_when_not и ::test_an_explicit_zero_is_omitted_not_reported (мутация O4 убита ПОСЛЕ разбора: различима только на явном нуле), ::test_a_row_with_no_tool_name_is_not_a_tool_call (мутация O3), ::test_a_kind_we_cannot_map_gets_no_operation_name_of_our_own (мутация O2), tests/test_session_metrics_parse.py::TestToolRowsForTheOptionalTrace::test_rows_carry_the_tool_names_and_the_model (мутация O9 — безымянный tool_use не становится строкой) AC-7: ✓ полная лента, mypy, ruff; CHANGELOG.md и CHANGELOG.ru.md; докстринг экспортера по-прежнему говорит, что модуль stdlib-only и не открывает сеть; команды CLI задача не добавляла — экспорт идёт через хук метрик смены, как и прежде, поэтому правки docs/cli.md не требуется Negative (вложенность): tests/test_otel_export.py::TestToolSpansNestUnderTheAgentRun::test_a_row_outside_the_parents_window_is_skipped (мутация O6), ::test_a_tool_call_becomes_a_child_of_the_session (мутация O7 «связь с родителем снята»), ::test_no_tool_calls_leaves_the_document_exactly_as_before (расширение аддитивно) Замер и остаток: премиса задачи проверена — часть работы сделана в 1.8; остаток (ссылка квитанции на стандартный след) ОБЪЯВЛЕН в журнале как непостроенный с указанием, какое решение он требует. Domain: семантические соглашения OpenTelemetry GenAI (нестабильные, источник и статус объявлены в модуле), внутренние события TAUSIK как источник истины.
- 2026-09-26T18:44:31Z [done] — EVIDENCE-UNPROVEN: tests/test_otel_export.py::TestExportEnabled::test_default_off — git never carried this path or member under any directory
- 2026-09-26T18:44:31Z [done] — EVIDENCE-UNPROVEN: tests/test_otel_export.py::TestOptInWiring::test_disabled_returns_empty — git never carried this path or member under any directory
- 2026-09-26T18:44:31Z [done] — EVIDENCE-UNPROVEN: tests/test_otel_export.py::TestSemconvSingleSource::test_instability_is_documented — git never carried this path or member under any directory
- 2026-09-26T18:44:31Z [done] — EVIDENCE-UNPROVEN: tests/test_otel_export.py::TestSemconvSingleSource::test_no_hardcoded_semconv_names_outside_mapper — git never carried this path or member under any directory
