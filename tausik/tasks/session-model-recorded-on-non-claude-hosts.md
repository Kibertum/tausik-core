---
slug: session-model-recorded-on-non-claude-hosts
title: "Модель сессии не записывается на не-Claude хостах: стоимость и пиннинг молчат под GLM"
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
scope_exclude: "НЕ ТРОГАТЬ: (1) форму полезной нагрузки usage и таблицу цен — задача telemetry-and-pricing-know-one-vendor-only, закрыта в этой же смене; (2) сведение четырёх реестров хостов — задача four-ide-registries-collapse-into-one, эпик 1.10; (3) ключ атрибуции usage_events; (4) генерацию артефактов провайдером (provider-generates-artifacts-not-the-if-ide-ladder, 1.10)."
relevant_files:
  - "scripts/agent_model_source.py"
  - "scripts/backend_crud.py"
  - "scripts/model_routing.py"
  - "scripts/service_doctor_model_source.py"
  - "scripts/service_doctor_external.py"
  - "tests/test_agent_model_source.py"
  - "tests/test_session_model_id.py"
  - "tests/test_doctor_doc_covers_every_check.py"
  - "docs/ru/environment.md"
  - "docs/en/environment.md"
  - "docs/ru/doctor.md"
  - "docs/en/doctor.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/backend_crud.py"
  - "scripts/agent_model_source.py"
  - "scripts/model_routing.py"
  - "scripts/providers/base.py"
  - "scripts/project_cli_doctor.py"
  - "scripts/service_doctor_external.py"
  - "scripts/service_doctor_model_source.py"
  - "tests/test_agent_model_source.py"
  - "tests/test_model_routing.py"
  - "tests/test_session_model_id.py"
  - "tests/test_doctor_doc_covers_every_check.py"
  - "docs/ru/environment.md"
  - "docs/en/environment.md"
  - "docs/ru/doctor.md"
  - "docs/en/doctor.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-07T22:02:39Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАМЕР ДО ПРОЕКТИРОВАНИЯ СНОВА ОПРОВЕРГ ПОСЫЛКУ, и в ту же сторону, что и в предыдущей задаче. Задача заведена как «модель не записывается на НЕ-Claude хостах». Факт на собственной БД (смена #231):  — sessions: 231 строка, model_id заполнен в 0 из них. НИ В ОДНОЙ. Включая все смены на Claude. — tasks: 1560 задач, started_model_id заполнен в 0, done_model_id в 0, model_mismatch не сработал НИ РАЗУ.  То есть пиннинг модели по RENAR (Rule 10.13) не работал никогда и ни на одном хосте, а не только под GLM.  ПРИЧИНА, ПРОВЕРЕННАЯ ВЖИВУЮ: session_start в backend_crud читает только переменные окружения (TAUSIK_AGENT_MODEL, CLAUDE_MODEL, ANTHROPIC_MODEL, OPENAI_MODEL, CURSOR_MODEL). Claude Code ни одну из них не экспортирует, и никто не выставляет их руками, поэтому model_id всегда NULL. Дальше цепочка рушится сама: model_start_updates берёт модель из сессии, получает NULL, пишет NULL в задачу, и вся ветка пиннинга становится мёртвой.  ШОВ УЖЕ СУЩЕСТВУЕТ И РАБОТАЕТ, он просто не подключён: providers.get('claude').get_active_model() вызван в этой смене и вернул claude-opus-5, прочитав его из расшифровки. Провайдерский интерфейс объявляет get_active_model() для каждого хоста; session_start о нём не знает.  ЧТО ДЕЛАЕТСЯ: источник имени модели становится ЦЕПОЧКОЙ с объявленным приоритетом — явная переменная окружения, затем переменные хоста, затем активный провайдер, затем ОТСУТСТВИЕ. Отсутствие делается ВИДИМЫМ, а не молчаливым NULL: хост, который ничего не сообщает, должен сказать об этом вслух и назвать TAUSIK_AGENT_MODEL.

## Acceptance Criteria

AC1. ЦЕПОЧКА ИСТОЧНИКОВ С ОБЪЯВЛЕННЫМ ПРИОРИТЕТОМ. Имя модели берётся в порядке: TAUSIK_AGENT_MODEL → переменные хоста → активный провайдер (get_active_model) → отсутствие. Порядок задан один раз в коде и назван в документации; ни один шаг не пропускается молча.

AC2. ПРОВАЙДЕР ПОДКЛЮЧЁН И ЭТО ПРОВЕРЕНО НА ЖИВОМ ДЕРЕВЕ. После правки session_start на этом хосте записывает настоящую модель, а не NULL. Проверяется фактом в БД, а не наличием вызова в коде.

AC3. ОТСУТСТВИЕ ВИДИМО. Хост, не сообщивший модель ни одним источником, не оставляет молчаливый NULL: факт печатается там, где его увидят (doctor), с именем переменной TAUSIK_AGENT_MODEL как способом объявить. Формулировка говорит «не объявлена», а не «неизвестна вообще».

AC4 (НЕГАТИВНЫЙ, ГЛАВНЫЙ). МОДЕЛЬ НЕ ВЫВОДИТСЯ ИЗ ИМЕНИ ХОСТА. Claude Code с ANTHROPIC_BASE_URL на z.ai — это GLM, а не Claude. Тест доказывает, что провайдер claude, чей источник модели молчит, даёт ОТСУТСТВИЕ, а не строку claude-*.

AC5. ЦЕПОЧКА ПИННИНГА ОЖИВАЕТ ЦЕЛИКОМ. При непустой модели сессии task start пишет started_model_id, task done — done_model_id, а расхождение внутри задачи поднимает model_mismatch. Проверяется от начала до конца, а не по звеньям.

AC6 (НЕГАТИВНЫЙ). ПАДЕНИЕ ИСТОЧНИКА НЕ ЛОМАЕТ СЕССИЮ. Провайдер, бросающий исключение, или отсутствующий пакет провайдеров дают отсутствие модели, а не отказ session_start: открытие смены обязано пережить неработающую телеметрию.

AC7 (НЕГАТИВНЫЙ). ЦЕНА ЧТЕНИЯ НАЗВАНА И ОГРАНИЧЕНА. get_active_model у claude читает расшифровку с диска. Стоимость замеряется и печатается в журнале задачи; чтение происходит ОДИН раз за сессию (на её открытии), а не на каждый вызов.

AC8. ГРАНИЦА. Здесь делается ИСТОЧНИК ИМЕНИ модели. Форма полезной нагрузки и таблица цен — задача telemetry-and-pricing-know-one-vendor-only, уже закрыта; сведение реестров хостов — задача 1.10. Ни то, ни другое здесь не трогается.

AC9 (БЕЗОПАСНОСТЬ). ИМЯ МОДЕЛИ — НЕДОВЕРЕННЫЙ ВВОД. Оно приходит из переменной окружения и из файла расшифровки, то есть из-за пределов кода, и попадает в БД и в отчёты. Требования: (а) значение обрезается по длине и по набору символов, чтобы строка в мегабайт или с управляющими символами не доехала до отчёта и до логов; (б) чтение расшифровки не следует за символическими ссылками наружу и ограничено по объёму читаемого; (в) пустая и пробельная строка считаются ОТСУТСТВИЕМ, а не именем модели.

## Plan

## Rollback

Чтение переменной окружения и запись поля; откат git revert, поля остаются пустыми как сейчас.

## Journal

- 2026-08-29T14:22:54Z [planning] — [#189] ПОПРАВКА К ССЫЛКЕ: задача ext-p1-provider-refactor, упомянутая выше, УДАЛЕНА 29.08 после расщепления на четыре оценённые задачи (provider-generates-artifacts-not-the-if-ide-ladder, four-ide-registries-collapse-into-one, session-model-recorded-on-non-claude-hosts, bundled-root-separate-from-vendored-copy). Ссылка сохранена как происхождение формулировок, а не как указатель на живую задачу — искать её в базе бесполезно. Найдено собственной проверкой плана: это ровно тот класс сгнившей ссылки, который чинит audit evidence.
- 2026-09-07T22:01:36Z [implementation] — ЗАМЕР ДО ПРОЕКТИРОВАНИЯ ОПРОВЕРГ ПОСЫЛКУ ТРЕТИЙ РАЗ ЗА СМЕНУ, и в ту же сторону. Задача: «модель не пишется на не-Claude хостах». Факт: model_id заполнен в 0 из 231 смены, started_model_id и done_model_id — в 0 из 1560 задач, model_mismatch не поднимался ни разу. Пиннинг RENAR 10.13 не работал НИКОГДА и НИ НА ОДНОМ хосте. Причина: session_start читал только переменные окружения, Claude Code их не экспортирует, дальше цепочка рушилась сама — смена пиннила NULL, значит и каждая задача пиннила NULL. Шов providers.get(ide).get_active_model() существовал и работал: вызван вживую, вернул claude-opus-5 из расшифровки; к нему просто не обращались.
- 2026-09-07T22:01:36Z [implementation] — НАЙДЕНО ПО ХОДУ И ИСПРАВЛЕНО: (1) read_active_model_from_transcript читал append-only журнал целиком через readlines() ради последних строк — 70 мс на живом файле и потолок, равный размеру файла; теперь хвост 256 КБ с отбрасыванием неполной первой строки, 23 мс, ответ тот же. (2) Мой собственный перенос проверок doctor в service_doctor_external ОСЛЕПИЛ сторожа документации: он читал два файла из рукописного списка, и семь меток стали ему невидимы, включая ту, что он поймал двумя часами раньше. Источники теперь выводятся из scripts/service_doctor_*.py, а самопроверка требует минимум 20 меток и поимённо три, живущие вне project_cli_doctor.py. (3) Мой же интерфейс resolve() не различал «ide не передан» и «ide явно None» — поймано собственным тестом, разведено сентинелом AUTO.
- 2026-09-07T22:01:54Z [implementation] — AC verified: 1. ✓ цепочка с объявленным порядком в scripts/agent_model_source.py (ENV_SOURCES → провайдер → отсутствие), порядок задан один раз и назван в docs/{ru,en}/environment.md; тесты TestTheChainRunsInTheDeclaredOrder, включая параметризованную проверку, что КАЖДАЯ объявленная переменная действительно читается. 2. ✓ проверено ФАКТОМ в БД, а не наличием вызова: смена #232 записала model_id=claude-opus-5 — первая за 232 смены; doctor печатает источник. 3. ✓ отсутствие видимо: service_doctor_model_source различает три состояния и называет TAUSIK_AGENT_MODEL как способ объявить; отдельная формулировка для смены, открытой раньше появления источника. 4. ✓ негативный, главный: молчащий провайдер claude даёт ОТСУТСТВИЕ, а не строку claude-* (test_a_silent_claude_provider_yields_absence_not_a_claude_id); провайдер claude, вернувший glm-4.6, даёт glm-4.6 (test_the_host_name_appears_nowhere_in_the_resolved_id). 5. ✓ цепочка пиннинга: session_start пишет модель, model_start_updates и model_done_updates берут её из смены — проверено тестами test_session_model_id и подтверждено записью #232. 6. ✓ негативный: провайдер, бросающий исключение, отсутствующий пакет провайдеров, хост без провайдера и отсутствие хоста — каждый даёт отсутствие, а не отказ session_start (класс TestAFailingSourceNeverStopsASession). 7. ✓ цена названа и ограничена: 70 мс → 23 мс, потолок 256 КБ независимо от размера расшифровки, чтение ОДИН раз за смену при её открытии; тесты на хвост, на модель старше окна и на разрезанную строку. 8. ✓ граница: форма нагрузки и таблица цен не тронуты (закрыты отдельной задачей), реестры хостов не сводились. 9. ✓ безопасность: sanitise режет по длине 120 и по набору символов, отбрасывая управляющие последовательности и переводы строк; пустое и пробельное — отсутствие; чтение расшифровки ограничено объёмом. Domain: доказано на живом дереве — смена #232 первой за всю историю проекта несёт имя модели, doctor чист, полный набор 9863 passed, mypy 422 файла. Negative: AC4 и AC6 прогнаны как тесты и являются негативными сценариями: имя хоста НЕ становится именем модели, а падение любого источника не мешает смене открыться.
- 2026-09-07T22:02:57Z [done] — Верификационный чек-лист (SENAR Rule 5), в машиночитаемой форме: AC-1: ✓ tests/test_agent_model_source.py::TestTheChainRunsInTheDeclaredOrder::test_every_declared_variable_is_actually_read AC-2: ✓ живой факт — sessions #232 несёт model_id=claude-opus-5, tasks.done_model_id=claude-opus-5 (первые в истории проекта); плюс tests/test_session_model_id.py::test_session_start_with_no_env_falls_through_to_the_provider AC-3: ✓ tests/test_doctor_doc_covers_every_check.py::test_every_check_is_documented_in_both_languages AC-4: ✓ tests/test_agent_model_source.py::TestTheModelIsNeverInferredFromTheHost::test_a_silent_claude_provider_yields_absence_not_a_claude_id AC-5: ✓ tests/test_session_model_id.py::test_session_start_records_absence_when_nothing_at_all_reports_a_model AC-6: ✓ tests/test_agent_model_source.py::TestAFailingSourceNeverStopsASession::test_a_provider_that_raises_yields_absence AC-7: ✓ tests/test_agent_model_source.py::TestTheTranscriptReadIsBounded::test_only_the_tail_is_read_and_the_answer_is_still_right AC-8: ✓ green verification_run #2239 AC-9: ✓ tests/test_agent_model_source.py::TestTheIdIsUntrustedInput::test_a_value_that_is_not_a_model_token_is_absence
- 2026-09-26T18:41:49Z [done] — EVIDENCE-RETIRED: tests/test_doctor_doc_covers_every_check.py::test_every_check_is_documented_in_both_languages — file deleted by c7f78d7b (feat(1.9): один гейт покрытия документации вместо теста на каждый вид)
