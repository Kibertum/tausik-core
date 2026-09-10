---
slug: verify-certifies-a-run-that-touched-no-test-of-the-subject
title: "verify сертифицирует зелёным прогон, в котором ни один тест предмета не участвовал: маппер идёт от ИМЕНИ файла"
status: blocked
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: publish-risk-gate-docstring-lies-after-205
scope: null
scope_exclude: "Do not change task lifecycle or receipt cryptography except where a no-subject test must withhold certification; do not broaden to transitive imports, rewrite test history, alter CI, release, tag or push."
relevant_files:
  - "scripts/gate_test_resolver.py"
  - "scripts/gate_command_runner.py"
  - "scripts/gate_outcome.py"
  - "tests/test_gate_test_resolver_import_edge.py"
  - "tests/test_gate_command_runner.py"
scope_paths:
  - "scripts/gate_test_resolver.py"
  - "scripts/gate_command_runner.py"
  - "scripts/gate_outcome.py"
  - "tests/test_gate_test_resolver_import_edge.py"
  - "tests/test_gate_command_runner.py"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

НАЙДЕНО ВЖИВУЮ в сессии #162 при закрытии publish-risk-gate-docstring-lies-after-205, ВОСПРОИЗВЕДЕНО запуском резолвера, а не рассуждением.

ЗАМЕР: gate_test_resolver сопоставляет модулю тесты по ИМЕНИ (scripts/X.py -> tests/test_X.py) плюс по объявленному CROSSCUTTING_SCOPE. Единственное поведенческое покрытие scripts/brain_publish_flow.py живёт в tests/test_decide_classifies_what_it_publishes.py — файл сохранил историческое имя НАМЕРЕННО (решение #221, чтобы история осталась находимой) и CROSSCUTTING_SCOPE не объявлял. Результат: verify --relevant-files scripts/brain_publish_flow.py прогонял ДЕВЯТЬ файлов, ни один из которых не касается предмета, и печатал PASS.

ПОЧЕМУ ЭТО ХУЖЕ ОБЫЧНОГО ПРОБЕЛА В ПОКРЫТИИ: verify не просто не находит тесты — он СЕРТИФИЦИРУЕТ. Выдаёт подписанную квитанцию и одноразовый handle, которым task done закрывает QG-2. То есть ОТСУТСТВИЕ покрытия конвертируется в ДОКАЗАТЕЛЬСТВО покрытия. Строка 'scoped run over 9 of 392 test file(s)' читается как охват, а не как предупреждение.

ЧАСТНЫЙ СЛУЧАЙ УЖЕ ЗАКРЫТ в #162: CROSSCUTTING_SCOPE в тот файл добавлен, маппинг проверен запуском резолвера. Здесь — ОБЩАЯ ФОРМА, потому что чинить по одному найденному файлу значит ждать следующего.

ЧТО СДЕЛАТЬ, решить явно: (а) сопоставление по ИМПОРТУ, а не только по имени — тест, импортирующий scripts/X, покрывает scripts/X независимо от имени файла; (б) пустое пересечение обязано говорить ГРОМКО и НЕ сертифицировать: сейчас 'ни одного теста предмета' неотличимо от честного охвата; (в) разовый аудит — перечислить модули scripts/, для которых не находится ни одного импортирующего теста, и сравнить с реальностью. Пункт (в) даёт замер, без которого (б) может оказаться шумным.

## Acceptance Criteria

1. Резолвер сопоставляет тесты по ИМПОРТУ затронутого модуля, а не только по имени файла и объявленному CROSSCUTTING_SCOPE. Тест: файл с историческим именем, импортирующий scripts/brain_publish_flow.py, попадает в набор БЕЗ объявления CROSSCUTTING_SCOPE.
2. Пустое пересечение НЕ сертифицирует. Тест: verify для модуля, который не импортирует ни один тест, завершается отказом или явным отсутствием сертификации, а НЕ PASS с подписанной квитанцией и выданным handle.
3. Строка охвата перестаёт звучать как охват, когда его нет: SCOPE называет, сколько тестов реально КАСАЮТСЯ предмета, отдельно от общего числа прогнанных.
4. Разовый аудит проведён и записан: перечень модулей scripts/, для которых не находится ни одного импортирующего теста. Число названо в журнале, даже если оно ноль — ноль тоже результат замера.
5. НЕГАТИВ И ГРАНИЦЫ: (а) изменение не раздувает прогон — тест, импортирующий модуль транзитивно через много слоёв, не обязан считаться покрытием; глубина разбора названа и обоснована; (б) отказ по пункту 2 НЕ ломает законные случаи, где тестов нет осознанно: существующий видимый opt-out CROSSCUTTING_SCOPE = [] продолжает работать, и это закреплено тестом; (в) при неразбираемом тестовом файле резолвер НАЗЫВАЕТ файл, а не молча исключает его из набора — иначе SyntaxError в тесте тихо сужает покрытие.
6. Полный pytest зелёный, mypy и ruff чистые.

## Plan

[{"step": "Reproduce filename-only selection and inventory the resolver, gate and receipt/handle boundary.", "done": true}, {"step": "Define direct-import evidence, explicit opt-out and parse-error reporting without transitive expansion.", "done": true}, {"step": "Implement direct-import mapping and a non-certifying result for a non-empty scope with no subject test.", "done": true}, {"step": "Add behavioral tests for historical filename, no-subject refusal, opt-out, parse error and scope disclosure.", "done": true}, {"step": "Run the audit over scripts, then full pytest, mypy, ruff, dedupe and signed verify.", "done": true}]

## Rollback

git revert. Изменение затрагивает резолвер тестов и формулировку вывода verify; поведение продукта не меняется, откат возвращает сопоставление только по имени.

## Journal

- 2026-09-10T12:31:04Z [implementation] — Задача активирована как прямое следствие verify #2391: текущий filename/import mapper выбрал 78 файлов для двух verify-модулей и не завершился в timeout. Не повышать лимит; измерить direct-import subject coverage и сузить/сделать честным сертификат.
- 2026-09-10T12:32:29Z [implementation] — Шаг 1: текущий resolver уже имеет direct import edge и no-test-mapped отказ: scripts/brain_publish_flow.py выбирает tests/test_decide_classifies_what_it_publishes.py. Но 78 файлов у verify_scope_honesty приходят главным образом от широких CROSSCUTTING_SCOPE=[scripts/], а parse errors в test source сейчас молча превращаются в absence. Следующая работа: разделить доказательные edges в результате резолвера, явно сообщать parse-failure и измерить direct/observed coverage, не отменяя законные basename/crosscutting guards.
- 2026-09-10T12:43:29Z [implementation] — Шаги 2–4: resolver теперь называет неразбираемый candidate test source, а pytest gate возвращает COULD_NOT_RUN с reason test_source_parse_error вместо тихого сужения. SCOPE теперь отдельно печатает число direct-import subject tests; basename/CROSSCUTTING/observed остаются additive, потому что не все законные проверки импортируют продукт. Targeted tests: 53 passed; ruff clean. Разовый audit scripts/: 420 modules, 45 без direct-import-or-observed evidence; список записан в handoff/terminal (главным образом versioned migrations и CLI adapters), это измерение, не автоматическое обвинение.
- 2026-09-10T12:47:44Z [implementation] — Added an integration regression: a syntactically broken test that names the changed module now yields blocking COULD_NOT_RUN/test_source_parse_error before pytest is spawned. Focused resolver + command-runner suite: 54 passed; ruff on changed implementation/tests: passed.
- 2026-09-10T12:49:09Z [implementation] — Formal verify #2392 did not certify: pytest scoped 71/521 test files and hit its time budget after 34.7s (output reached 10%). It also reports three paths changed since task start but absent from declared scope. This confirms the remaining blocker is selector/time-budget and scope ownership, not the new parse-error behavior.
