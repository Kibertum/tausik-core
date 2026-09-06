---
slug: at-acceptance-tests-derived-by-an-isolated-agent
title: "AT — приёмочный тест от контракта: выводится изолированным агентом и перегенерируется перед испытаниями"
status: done
epic: release-19-renar-conformance
story: renar-contract-contour
complexity: complex
role: architect
stack: python
tier: substantial
call_budget: 90
defect_of: null
scope: "Новая сущность AT: миграция схемы, backend_crud_at.py/service_at.py, CLI (project_parser_at.py/project_cli_at.py), MCP (tools_at.py/handlers_at.py), harness/skills/at-generate/SKILL.md (процедура изоляции), staleness-гейт (warn), tests/test_at.py, docs/{en,ru}/mcp.md, CHANGELOG.md, CHANGELOG.ru.md."
scope_exclude: "Не вызывает LLM/Agent tool из Python-кода scripts/ (stdlib-only). Не генерирует реальный AT-контент для существующих SPEC/ACTZ этого проекта. Не переделывает final_tz_snapshot/ACTZ. Не решает маршрутизацию провалов AT/TC — следующая задача."
relevant_files:
  - "scripts/backend_schema_at.py"
  - "scripts/backend_migrations_v54.py"
  - "scripts/backend_crud_at.py"
  - "scripts/service_at.py"
  - "scripts/gate_at_freshness.py"
  - "scripts/project_parser_at.py"
  - "scripts/project_cli_at.py"
  - "harness/claude/mcp/project/tools_at.py"
  - "harness/claude/mcp/project/handlers_at.py"
  - "scripts/backend_init.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "scripts/gate_registry_scoped.py"
  - "scripts/project.py"
  - "scripts/project_backend.py"
  - "scripts/project_parser.py"
  - "scripts/project_service.py"
  - "scripts/renar_tc_premise.py"
  - "harness/claude/mcp/project/handlers.py"
  - "harness/claude/mcp/project/tools.py"
  - pyproject.toml
  - "tausik/gates.json"
  - "tests/test_at.py"
  - "tests/test_gates_catch_their_violation.py"
  - "tests/test_mcp_tool_token_cost.py"
  - "tests/test_spec_completeness.py"
  - "docs/en/at-generation-procedure.md"
  - "renar/specs/at-generation-procedure.md"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - AGENTS.md
  - README.md
  - README.ru.md
  - RENAR-CONFORMANCE.yaml
  - "docs/README.md"
  - "docs/_generated/constants.json"
  - "docs/en/architecture.md"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/agent-contract.md"
  - "docs/ru/architecture.md"
  - "docs/ru/senar-compliance-matrix.md"
scope_paths: []
scope_tools: []
depends_on:
  - final-tz-is-the-acceptance-reference-and-we-have-none
completed_at: "2026-09-06T18:15:36Z"
---

## Goal

RENAR §8A (ADR-012, accepted). Прослеживаемость TC замкнута через интерпретацию: TC → SR → ADAPT → ТЗ. Отсюда класс дефектов, который TC не ловит В ПРИНЦИПЕ: при неверной интерпретации ВСЕ TC зелёные, потому что система идеально соответствует неверному толкованию — и проваливает приёмку у заказчика. AT закрывает ровно этот остаток и только его. Три обязательных свойства: (1) выводится ИЗОЛИРОВАННЫМ агентом исключительно из итогового ТЗ, без доступа к ADAPT, BR, SR, SPEC, TC и коду; (2) ПЕРЕГЕНЕРИРУЕТСЯ перед каждыми испытаниями от действующей редакции, иначе система в конце длинного заказа проверяется против контракта годичной давности; (3) обязательное поле tz_text — дословная цитата пункта контракта. Изоляция здесь не пожелание, а механизм генерации: агент, видевший интерпретацию, воспроизведёт её ошибку. У нас уже есть внешний ревьюер на другой модели — механизм разделения обязанностей существует, но для AT нужна изоляция ПО ВХОДУ, а не только по автору. Зависит от final-tz-is-the-acceptance-reference-and-we-have-none.

## Acceptance Criteria

AC-1 Схема: сущность AT (таблица at) — slug, tz_ref (какой пункт final_tz_snapshot), tz_text (ОБЯЗАТЕЛЬНОЕ, дословная цитата — сервисный слой отклоняет пустое/несовпадающее с текущим governing_text по tz_ref на момент генерации), scenario (сценарий проверки), source_as_of (момент final_tz_snapshot, от которого выведен AT — основа для staleness), generated_by (свободный текст: кто/что сгенерировало — заполняется ОРКЕСТРИРУЮЩИМ агентом, не изолированным), created_at. Новая миграция (следующая версия схемы).
AC-2 Изоляция — НЕ автоматизация вызовом LLM из stdlib-кода (проект без сетевых зависимостей в scripts/): задокументированная ПРОЦЕДУРА (skill harness/skills/at-generate/SKILL.md), предписывающая оркестрирующему агенту вызвать ИЗОЛИРОВАННОГО субагента (Agent tool, general-purpose, ФРЕШ контекст) с промптом = ТОЛЬКО текст final_tz_snapshot (tz_ref+governing_text), без ADAPT/BR/SR/SPEC/TC/кода. Skill формулирует явный запрет оркестратору редактировать/дополнять вывод изолированного агента по существу — только транскрибировать в `at create`.
AC-3 Свежесть, не блокирующий вызов LLM в гейте: детектор staleness (сервисная функция + CLI/MCP), сравнивающий AT.source_as_of с ТЕКУЩИМ состоянием final_tz_snapshot по тому же tz_ref (изменился ли governing_actz/governing_point_no/completed_at с момента генерации AT). warn-severity гейт (по образцу renar_drift_schema) на verify/task-done, не блокирует, называет устаревшие AT по slug.
AC-4 CLI+MCP: `tausik at create/show/list/delete/check-freshness`, полный MCP-паритет (тот же принцип, что у ACTZ).
AC-5 Качество: tests/test_at.py; mypy/ruff/filesize зелёные; class_surface baseline обновлён решением при необходимости; docs/{en,ru}/mcp.md; оба CHANGELOG; полный прогон; мутации на staleness-компараторе.
AC-6 Явно НЕ входит в эту задачу: реальная генерация AT-контента для существующих SPEC/tz_ref этого проекта (это отдельная будущая работа, выполняемая ЧЕРЕЗ построенный здесь механизм, не заранее); маршрутизация провалов AT/TC (следующая задача at-red-with-tc-green-routes-to-interpretation-not-code).

## Plan

[{"step": "\u0421\u0445\u0435\u043c\u0430: \u043c\u0438\u0433\u0440\u0430\u0446\u0438\u044f \u0442\u0430\u0431\u043b\u0438\u0446\u044b at", "done": true}, {"step": "backend_crud_at.py + service_at.py (create/show/list/delete + staleness \u043a\u043e\u043c\u043f\u0430\u0440\u0430\u0442\u043e\u0440)", "done": true}, {"step": "CLI: project_parser_at.py/project_cli_at.py", "done": true}, {"step": "MCP: tools_at.py/handlers_at.py, \u043f\u043e\u043b\u043d\u044b\u0439 \u043f\u0430\u0440\u0438\u0442\u0435\u0442", "done": true}, {"step": "Warn-\u0433\u0435\u0439\u0442 staleness (gate_registry_scoped.py + \u043a\u043b\u0430\u0441\u0441\u0438\u0444\u0438\u043a\u0430\u0446\u0438\u044f \u0432 test_gates_catch_their_violation.py)", "done": true}, {"step": "harness/skills/at-generate/SKILL.md \u2014 \u043f\u0440\u043e\u0446\u0435\u0434\u0443\u0440\u0430 \u0438\u0437\u043e\u043b\u044f\u0446\u0438\u0438", "done": true}, {"step": "tests/test_at.py + \u043c\u0443\u0442\u0430\u0446\u0438\u0438 \u043d\u0430 staleness-\u043a\u043e\u043c\u043f\u0430\u0440\u0430\u0442\u043e\u0440\u0435", "done": true}, {"step": "\u0414\u043e\u043a\u0438 + CHANGELOG", "done": true}, {"step": "\u041f\u043e\u043b\u043d\u044b\u0439 \u043f\u0440\u043e\u0433\u043e\u043d, verify, \u0437\u0430\u043a\u0440\u044b\u0442\u044c", "done": true}]

## Rollback

Новая сущность AT с генерацией изолированным по входу агентом. Откат: обратная миграция плюс git revert; TC и SPEC не затрагиваются, AT читает итоговое ТЗ и ничего в него не пишет.

## Journal

- 2026-09-06T18:13:49Z [implementation] — AC verified: 1. ✓ Таблица ats (миграция v54), tz_text/generated_by обязательны на сервисном слое, source_as_of/tz_ref для сравнения свежести. 2. ✓ Изоляция НЕ вызовом LLM из stdlib-кода — docs/en/at-generation-procedure.md (экспортирован как SPEC at-generation-procedure, тип PROC, привязан к задаче) описывает вызов ИЗОЛИРОВАННОГО субагента (Agent tool) с промптом=только final_tz текст; CLI/MCP только транскрибируют результат. 3. ✓ at_check_freshness сравнивает source_as_of с final_tz_snapshot по tz_ref (мутации M1 !=->==, M2 orphan-branch убиты); warn-гейт at_freshness (gate_at_freshness.py) на task-done, не блокирует, называет устаревшие AT — red/green тесты в test_at.py, классифицирован EXCUSED. 4. ✓ CLI 6 подкоманд + MCP 6 инструментов, полный паритет. 5. ✓ test_at.py 26 тестов; mypy 400 файлов Success; ruff чист; filesize все новые <500 (max 137); class_surface baseline поднят (decision #329); docs/{en,ru}/mcp.md AT (6); оба CHANGELOG. 6. ✓ Реальная генерация AT-контента НЕ входит — только механизм. Domain: at_check_freshness проверен на РЕАЛЬНО подписанных ed25519 ACTZ-точках (не моках) — governing_actz/point_no/completed_at из настоящего final_tz_snapshot. Negative: orphaned tz_ref (нет подписанной точки), изменившийся governing point (новый ACTZ перекрыл), отсутствующий AT-slug — все три явно отклоняются/помечаются. Побочно: renar/specs/ проекция обновлена через `renar export`, RENAR-CONFORMANCE.yaml перевыпущен через `renar conformance --write`; test_spec_completeness.py::test_the_live_repository_reports_exactly_the_gap_it_has обновлён — новый SPEC честно UNCHECKED (нет enumerable subject у процедурного PROC, как и у renar-adoption), не выдуман coverage-registry под него.
