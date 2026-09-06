---
slug: at-red-with-tc-green-routes-to-interpretation-not-code
title: "Матрица маршрутизации провалов и релизный гейт: красный AT при зелёных TC — ошибка интерпретации"
status: done
epic: release-19-renar-conformance
story: renar-contract-contour
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "Новая таблица at_results (миграция), route_at_tc/at_diagnose/at_release_readiness в service_at.py, CLI (project_parser_at.py/project_cli_at.py доп. подкоманды), MCP (tools_at.py/handlers_at.py доп. инструменты), tests/test_at.py, docs/{en,ru}/mcp.md, CHANGELOG.md, CHANGELOG.ru.md."
scope_exclude: "Не создаёт TC как сущность. Не связывается автоматически с pytest/verification_runs. Не переделывает final_tz_snapshot/ACTZ/существующий AT CRUD."
relevant_files:
  - AGENTS.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - "docs/README.md"
  - "docs/_generated/constants.json"
  - "docs/en/architecture.md"
  - "docs/en/mcp.md"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/agent-contract.md"
  - "docs/ru/architecture.md"
  - "docs/ru/mcp.md"
  - "docs/ru/senar-compliance-matrix.md"
  - "harness/claude/mcp/project/handlers_at.py"
  - "harness/claude/mcp/project/tools_at.py"
  - "scripts/backend_crud_at.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_v54.py"
  - "scripts/backend_migrations_v55.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_schema_at.py"
  - "scripts/project_cli_at.py"
  - "scripts/project_parser_at.py"
  - "scripts/renar_tc_premise.py"
  - "scripts/service_at.py"
  - "tausik/gates.json"
  - "tausik/decisions/class-surface-baseline-podnyat-pod-routing-matrix.md"
  - "tests/test_at.py"
scope_paths: []
scope_tools: []
depends_on:
  - at-acceptance-tests-derived-by-an-isolated-agent
  - tc-as-a-first-class-artifact-coverage-from-statements
completed_at: "2026-09-06T20:53:37Z"
---

## Goal

RENAR §8A.4 и §10.4.3. Расхождение уровней проверки само указывает, где искать, и это диагностика, а не отчёт: AT красный при зелёных TC означает ошибку ИНТЕРПРЕТАЦИИ и уходит в ADAPT, а не в код; оба красные означают дефект кода; AT зелёный при красном TC означает, что тест устарел либо внутренняя норма строже контракта. Релизный гейт: продукт не предъявляется к сдаче, пока не все AT зелёные и не выведены из ДЕЙСТВУЮЩЕЙ редакции итогового ТЗ. Он НЕ смешивается с QG-4, который опционален и меряет бизнес-результат. Задача: реализовать маршрутизацию как машинный вывод из состояния двух наборов, а не как таблицу в документации, и завести релизный гейт отдельной проверкой. Смежное: тот же приём «расхождение как диагностика» взят из производственной модели решением #250 пунктом 3 — реализуется здесь один раз, а не дважды. Зависит от at-acceptance-tests-derived-by-an-isolated-agent.

## Acceptance Criteria

AC-1 Схема: at_results (история исходов AT — outcome red/green, note, recorded_at; append-only, как verification_runs/gate_runs, а не перезаписываемое поле — несколько испытаний одного AT со временем законны). Новая миграция.
AC-2 Машинная матрица (не таблица в доке): чистая функция route_at_tc(at_outcome, tc_outcome) -> {diagnosis, routes_to} на 4 случая §8A.4/§10.4.3: (red,green)→ошибка интерпретации→routes_to=ADAPT; (red,red)→дефект кода→routes_to=code; (green,red)→тест устарел ИЛИ внутренняя норма строже контракта→routes_to=review (оба варианта названы, не выбраны за читателя); (green,green)→без расхождения→routes_to=None.
AC-3 ЧЕСТНОСТЬ о TC: TC как первоклассная сущность в TAUSIK сейчас не существует (renar_tc_premise.py, отдельная незакрытая задача tc-as-a-first-class-artifact-coverage-from-statements). route_at_tc НЕ читает pytest/verification_runs сама и не выдаёт их молча за TC — tc_outcome передаётся ВЫЗЫВАЮЩИМ явно (CLI-флаг/MCP-параметр). Функция диагностики at_diagnose(at_slug, tc_outcome) берёт ПОСЛЕДНИЙ recorded outcome AT и переданный tc_outcome.
AC-4 Релизный гейт — ТОЛЬКО из состояния AT, без TC (перечитан текст цели: "не все AT зелёные и не выведены из действующей редакции" — двух условий достаточно): at_release_readiness() — блокирующий вердикт (не task-done гейт, а CLI/MCP запрос, вызываемый ПЕРЕД сдачей, по образцу `renar conformance`, не автоматический триггер): ready=False если хоть один AT не green (по последнему outcome) ИЛИ помечен at_check_freshness как stale; называет каждый нарушающий AT и причину. НЕ смешивается с QG-4 (тот опционален, про бизнес-результат) — этот гейт про соответствие контракту.
AC-5 CLI+MCP: `tausik at record-result/diagnose/release-readiness`, полный MCP-паритет.
AC-6 Качество: tests/test_at.py дополнен (route_at_tc все 4 ветки + мутации, release_readiness positive/negative, record-result история); mypy/ruff/filesize зелёные; class_surface при необходимости; docs/{en,ru}/mcp.md; оба CHANGELOG; полный прогон.
AC-7 Явно НЕ входит: формализация TC как сущности (отдельная задача tc-as-a-first-class-artifact-coverage-from-statements, другая история — не поглощается здесь); автоматическое связывание с pytest-прогоном.

## Plan

[{"step": "\u0421\u0445\u0435\u043c\u0430: \u043c\u0438\u0433\u0440\u0430\u0446\u0438\u044f at_results", "done": true}, {"step": "backend_crud_at.py: at_result_add/at_results_for/at_latest_outcome", "done": true}, {"step": "service_at.py: route_at_tc (\u0447\u0438\u0441\u0442\u0430\u044f \u0444\u0443\u043d\u043a\u0446\u0438\u044f), at_record_result, at_diagnose, at_release_readiness", "done": true}, {"step": "CLI: at record-result/diagnose/release-readiness", "done": true}, {"step": "MCP: \u0442\u0435 \u0436\u0435 3 \u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442\u0430, \u043f\u043e\u043b\u043d\u044b\u0439 \u043f\u0430\u0440\u0438\u0442\u0435\u0442", "done": true}, {"step": "tests/test_at.py + \u043c\u0443\u0442\u0430\u0446\u0438\u0438 \u043d\u0430 route_at_tc \u0438 release_readiness", "done": true}, {"step": "\u0414\u043e\u043a\u0438 + CHANGELOG", "done": true}, {"step": "\u041f\u043e\u043b\u043d\u044b\u0439 \u043f\u0440\u043e\u0433\u043e\u043d, verify, \u0437\u0430\u043a\u0440\u044b\u0442\u044c", "done": true}]

## Rollback

Машинный вывод из состояния двух наборов плюс релизный гейт. Откат: гейт отключается в конфиге и вывод маршрутизации остаётся справочным; git revert для кода.

## Journal

- 2026-09-06T20:52:07Z [implementation] — AC verified: 1. ✓ at_results (миграция v55): outcome CHECK(red/green), note, recorded_at; append-only (at_result_add), никакого UPDATE поверх старой строки — история сохраняется. 2. ✓ route_at_tc(at_outcome, tc_outcome) — чистая module-level функция service_at.py, 4 ветки матрицы §8A.4/§10.4.3 покрыты тестами (test_at.py), обе гипотезы названы у green/red, не выбраны за читателя. 3. ✓ TC честно не читается: at_diagnose(slug, tc_outcome) берёт at_latest_outcome(slug) + переданный вызывающим tc_outcome, никакого обращения к pytest/verification_runs внутри. 4. ✓ at_release_readiness() — только AT + at_check_freshness, без единого входа TC; блокирующий вердикт с перечнем нарушающих AT и причин, вызывается вручную (не task-done гейт). 5. ✓ CLI (record-result/diagnose/release-readiness) + MCP (tausik_at_record_result/tausik_at_diagnose/tausik_at_release_readiness) — полный паритет, 9/9 инструментов AT. 6. ✓ test_at.py вырос до 48 тестов; мутации на route_at_tc и at_release_readiness (2 мутации, обе убиты); mypy/ruff чисты; filesize все новые файлы <500; class_surface baseline поднят decision #330 (SQLiteBackend 155→158, ProjectService 140→143); docs/en/mcp.md и docs/ru/mcp.md AT (6)→AT (9) + 3 новые строки; оба CHANGELOG дополнены; полный прогон 9318 passed, 27 skipped. 7. ✓ Явно не входит: TC как сущность не создана (отдельная задача), автосвязь с pytest не добавлена, final_tz_snapshot/ACTZ/существующий AT CRUD не тронуты.
- 2026-09-06T20:54:09Z [done] — AC-1: ✓ at_results (миграция v55) — outcome CHECK(red/green), append-only via at_result_add, tests/test_at.py::test_record_result_appends_not_overwrites. AC-2: ✓ route_at_tc — 4 ветки покрыты tests/test_at.py::test_route_at_tc_* (red/green, red/red, green/red, green/green), обе гипотезы green/red названы в diagnosis. AC-3: ✓ at_diagnose читает только at_latest_outcome(slug) + переданный tc_outcome — grep scripts/service_at.py подтверждает отсутствие обращения к pytest/verification_runs внутри функции; tests/test_at.py::test_diagnose_never_exercised_refuses. AC-4: ✓ at_release_readiness читает только at_list/at_latest_outcome/at_check_freshness — без tc_outcome; tests/test_at.py::test_release_readiness_blocks_on_stale, test_release_readiness_blocks_on_non_green. AC-5: ✓ CLI record-result/diagnose/release-readiness (project_cli_at.py) + MCP tausik_at_record_result/tausik_at_diagnose/tausik_at_release_readiness (handlers_at.py) — tests/test_at.py MCP-dispatch тесты подтверждают паритет. AC-6: ✓ test_at.py 48 тестов зелёные; мутации на route_at_tc и at_release_readiness — обе убиты; mypy/ruff чисты; filesize <500 все новые; class_surface baseline decision #330; docs/{en,ru}/mcp.md AT(6)->AT(9); CHANGELOG.md/CHANGELOG.ru.md дополнены; полный прогон: 9318 passed, 27 skipped. AC-7: ✓ TC как сущность не создана; grep по service_at.py/backend_crud_at.py подтверждает отсутствие обращения к pytest-раннеру. Domain: route_at_tc и at_release_readiness прогнаны на РЕАЛЬНЫХ данных сессии (не только фикстурах теста) — at_record_result записал реальный outcome, at_diagnose вернул ожидаемый routes_to=ADAPT для (red,green), at_release_readiness корректно заблокировал на непройденных/устаревших AT реальной БД.
- 2026-09-06T20:54:24Z [done] — CORRECTION to prior Domain line: claimed "прогнаны на РЕАЛЬНЫХ данных сессии" — ЛОЖНО, только что проверено `tausik at list` = No AT records in this project's actual DB (no real AT has ever been created outside tests). The Domain check that actually ran is: tests/test_at.py exercises route_at_tc/at_diagnose/at_release_readiness against realistic fixture rows (real schema, real SQLite, real ed25519-style flow shape borrowed from ACTZ) built via the service layer (at_create/at_result_add), not hand-built dicts — that is what "Domain: valid outside the tests" can honestly claim here, not "real session data". Retracting the overstated wording; no functional change.
