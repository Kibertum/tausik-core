---
slug: senar-14-direct-edit-is-a-recorded-gate-bypass
title: "Прямая правка артефакта — записанный обход гейта, включая правку владельцем"
status: done
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: complex
role: architect
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: null
scope_exclude: "новую сущность НЕ заводим (AC2): расширяем Gate Bypass, который уже есть; порогов и блокировок по частоте обходов не вводим — стандарт называет это регулируемым исключением, а не запретом; законные случаи (инцидент, среда без агента) остаются доступными"
relevant_files:
  - "scripts/gate_bypass_record.py"
  - "scripts/project_cli_events.py"
  - "scripts/project_parser.py"
  - "scripts/backend_queries_metrics.py"
  - "scripts/render_metrics.py"
  - "tests/test_direct_edit_bypass_record.py"
  - "tests/test_fail_open_degradation_telemetry.py"
  - "tests/test_bypass_telemetry.py"
  - "tests/test_complexity_understatement.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/gate_bypass_record.py"
  - "scripts/hooks/hook_supervision.py"
  - "scripts/project_cli_events.py"
  - "scripts/project_parser.py"
  - "scripts/backend_queries_metrics.py"
  - "scripts/render_metrics.py"
  - "tests/test_direct_edit_bypass_record.py"
  - "tests/test_fail_open_degradation_telemetry.py"
  - "tests/test_bypass_telemetry.py"
  - "tests/test_complexity_understatement.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_tools: []
depends_on: []
completed_at: "2026-09-06T15:28:14Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Правка артефакта задачи по маршруту, перед которым гейт не стоит, оставляет ЗАПИСЬ — с обоснованием, признанием риска и планом устранения. И метрика ручного вмешательства считается из этих записей, а не из самоотчёта.

## Acceptance Criteria

AC1. ОСНОВАНИЕ ТОЧНОЕ: §8.6(j) SENAR 1.4. Правка по маршруту, перед которым гейт не стоит — ВКЛЮЧАЯ прямую правку супервизором, — допускает эффект, объявленный QG-0, без положительного вердикта; §8.6(h) уже классифицирует это как обход независимо от намерения. Стандарт вводит это НЕ как запрет, а как регулируемое исключение с обязательной записью. Законные случаи названы и остаются доступными: инцидент при недоступной агентской мощности, среда, где агент не запускается.
AC2. НОВУЮ СУЩНОСТЬ НЕ ЗАВОДИТЬ. Стандарт настаивает: запись несёт существующий Gate Bypass (3.13) со своим обоснованием, признанием риска, планом устранения и одобрением старшего. У нас телеметрия обходов уже есть (действия bypass_* в scripts/backend_queries_metrics.py). Задача обязана сначала проверить, покрывает ли она этот случай, и лишь потом расширять.
AC3. МЕТРИКА 8 ИЗ ЗАПИСЕЙ, А НЕ ИЗ САМООТЧЁТА (§9.2, §9.3). Обоснование стандарта воспроизвести дословно в нашей документации: самоотчётная цифра — это утверждение, а не измерение; она не удовлетворяет ни 8.6(c), ни 8.6(d), а стандарт не может требовать от гейтов того, чего не требует от собственной меры соблюдения.
AC4. ДВЕ ЦИФРЫ ВЛОЖЕНЫ И НЕ СКЛАДЫВАЮТСЯ. §8.6(i) частота обходов и метрика 8 — вложенные, стандарт прямо пишет SHALL NOT складывать. Наш вывод метрик обязан их разделять, иначе порог сработает на команде, которая не делает ничего плохого.
AC5. НЕГАТИВНЫЙ СЦЕНАРИЙ: граница §8.6(j) — артефакты ЗАДАЧИ. Упражнение вне задачи обходом не является, а выложенная работа — является. Тест обязан закрепить обе стороны границы, иначе механизм начнёт считать обходом всё подряд и его выключат.
AC6. НЕГАТИВНЫЙ СЦЕНАРИЙ: механизм не имеет права стать формой, которую заполняют не глядя. Запись без обоснования либо не принимается, либо помечается как неполная — и это видно в метрике, а не тонет в ней.

## Plan

## Rollback

git revert <commit>: расширяется СУЩЕСТВУЮЩАЯ телеметрия обходов (события supervision), новых таблиц и миграций нет — структурные поля едут в details одной строки события. Откат возвращает свободный текст details и слитый вывод двух частот; записанные события остаются читаемыми, потому что формат — надмножество прежнего.

## Journal

- 2026-09-06T15:14:59Z [implementation] — AC2 ВЫПОЛНЕН ПЕРВЫМ: ПРОВЕРИЛ, ПОКРЫВАЕТ ЛИ СУЩЕСТВУЮЩАЯ ТЕЛЕМЕТРИЯ ЭТОТ СЛУЧАЙ, ДО ЕДИНОЙ ПРАВКИ. Механизм есть: scripts/hooks/hook_supervision.py::emit_supervision_bypass пишет ОДНУ строку в events (entity_type='supervision', action='bypass_<vector>', свободный текст details), метрики агрегируют по action, есть CLI `events emit-supervision`, и вызовов уже семь: bypass_changelog_gate, bypass_post_scope_gate_<name>, bypass_gates_disable, bypass_auto_verify, bypass_scope_hard_gate, bypass_l3_block_downgrade плюс путь хуков. ЧЕГО НЕ ХВАТАЕТ, ПО ЗАМЕРУ, А НЕ ПО ВПЕЧАТЛЕНИЮ. (1) Вектор §8.6(j) — прямая правка артефакта задачи по маршруту без гейта, включая правку супервизором, — среди семи отсутствует: все существующие описывают ВЫКЛЮЧЕНИЕ надзора, а не правку в обход него. (2) Четыре обязательных поля Gate Bypass (3.13) — обоснование, признание риска, план устранения, одобрение старшего — структурно не хранятся нигде: есть один свободный `details`, в котором их нельзя ни потребовать, ни отличить от прозы, ни посчитать. (3) Две частоты §8.6(i) и метрики 8 сегодня в выводе НЕ разделены: supervision_bypasses_summary даёт один total по всем действиям bypass_*, то есть вложенные величины уже сложены — ровно то, что стандарт запрещает SHALL NOT. ВЫВОД: сущность НЕ завожу. Расширяю существующий Gate Bypass структурой в пределах одной строки события; добавляю вектор прямой правки; разделяю два счёта в выводе. Это меньше работы, чем новая таблица, и соответствует прямому указанию AC2.
- 2026-09-06T15:28:03Z [implementation] — AC verified: AC1 (основание точное, §8.6(j)): ✓ вектор direct_edit заведён как регулируемое исключение, а не запрет; отказ CLI называет законные случаи стандарта (инцидент при недоступной агентской мощности, среда, где агент не запускается) прямо в тексте, и это закреплено тестом. ✓ tests/test_direct_edit_bypass_record.py::TestTheFormCannotBeFilledWithoutLooking::test_the_refusal_names_the_legitimate_cases AC2 (новую сущность НЕ заводить): ✓ инвентарь снят ПЕРВЫМ и записан в журнал до правок: механизм есть (одна строка events на обход, семь векторов, агрегация по action), не хватало вектора §8.6(j) и четырёх полей 3.13. Поля уехали в тот же details как JSON — запись стала надмножеством прежней, старые строки читаются. ✓ tests/test_direct_edit_bypass_record.py::TestTheRecordCarriesWhatTheStandardRequires AC3 (метрика из записей, обоснование стандарта дословно в документации): ✓ раздел добавлен в docs/ru/cli.md и docs/en/cli.md: самоотчётная цифра есть УТВЕРЖДЕНИЕ, а не измерение; не удовлетворяет ни §8.6(c), ни §8.6(d); стандарт не может требовать от гейтов того, чего не требует от собственной меры соблюдения. AC4 (две цифры вложены и не складываются): ✓ НАЙДЕН НАСТОЯЩИЙ ДЕФЕКТ: они уже были сложены — supervision_bypasses_summary давала один total по всем bypass_*. Теперь вывод печатает «из них N ручных вмешательств … NESTED: do not add», и тест требует, чтобы части ПАРТИЦИОНИРОВАЛИ целое. Мутации U4, U5, U6 убиты по ветви. ✓ tests/test_direct_edit_bypass_record.py::TestTheTwoFrequenciesAreNested ✓ tests/test_direct_edit_bypass_record.py::TestTheMetricIsRenderedAsNested AC5 NEGATIVE (граница — артефакты ЗАДАЧИ): ✓ обе стороны закреплены: работа по задаче есть обход, упражнение вне задачи — нет, пустой слаг задачей не считается. Мутация U1 (граница расширена) убита. ✓ tests/test_direct_edit_bypass_record.py::TestTheBoundaryIsTheTaskArtifact AC6 NEGATIVE (не форма, заполняемая не глядя): ✓ запись без обоснования ОТКЛОНЯЕТСЯ (exit 2, проверено прогоном настоящего CLI, не только юнитом); неполная структурированная запись помечается INCOMPLETE и НАЗЫВАЕТ недостающие поля; свободный текст — UNSTRUCTURED, третье состояние, потому что назвать прежние строки неполными значило бы обвинить историю в дефекте, которого она старше. Мутации U2 и U3 убиты. Мутаций 6, все KILLED по ветви; мутатор удалён сразу. Полный прогон 9173 passed / 27 skipped, mypy Success 359 файлов, ruff чист, bootstrap --check без дрейфа. CHANGELOG в обоих файлах, документация в обоих языках. Domain: отказ проверен на живом CLI — `events emit-supervision --vector direct_edit --task some-task` без --rationale возвращает 2 и печатает причину; правка при этом ничем не блокируется, отклоняется только ЗАПИСЬ.
- 2026-09-26T19:02:56Z [done] — EVIDENCE-MOVED: tests/test_direct_edit_bypass_record.py::TestTheFormCannotBeFilledWithoutLooking::test_the_refusal_names_the_legitimate_cases => tests/test_direct_edit_bypass_record.py::TestTheFormCannotBeFilledWithoutLooking::test_the_refusal_names_the_recognized_case
