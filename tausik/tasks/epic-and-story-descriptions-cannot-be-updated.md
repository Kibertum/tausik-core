---
slug: epic-and-story-descriptions-cannot-be-updated
title: "Описание эпика и истории нельзя обновить: замысел группы задач устаревает молча"
status: done
epic: release-19-renar-conformance
story: evidence-primitives
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: "Схема БД не меняется (миграций нет): время последней правки описания берётся из события events, а не из новой колонки; doctor не трогается (489 строк, у предела) — отчёт устаревших описаний живёт в epic list / story list; гейта закрытия нет"
relevant_files:
  - "scripts/hierarchy_edit.py"
  - "scripts/project_cli.py"
  - "scripts/project_parser_hierarchy.py"
  - "harness/claude/mcp/project/handlers_hierarchy.py"
  - "harness/claude/mcp/project/tools.py"
  - "tests/test_hierarchy_update.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - "docs/ru/mcp.md"
  - "docs/en/mcp.md"
  - "docs/README.md"
  - "docs/_generated/constants.json"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/senar-compliance-matrix.md"
  - "docs/en/architecture.md"
  - "docs/ru/agent-contract.md"
  - README.md
  - README.ru.md
  - AGENTS.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/hierarchy_edit.py"
  - "scripts/project_cli.py"
  - "scripts/project_parser_hierarchy.py"
  - "harness/claude/mcp/project/handlers_hierarchy.py"
  - "harness/claude/mcp/project/tools.py"
  - "tests/test_hierarchy_update.py"
  - "tests/test_project_mcp.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - "docs/ru/mcp.md"
  - "docs/en/mcp.md"
  - "docs/README.md"
  - "docs/_generated/constants.json"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/senar-compliance-matrix.md"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "docs/en/agent-contract.md"
  - "docs/ru/agent-contract.md"
  - README.md
  - README.ru.md
  - AGENTS.md
  - CLAUDE.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-03T21:06:00Z"
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

НАЙДЕНО СОБСТВЕННОЙ РАБОТОЙ В #189, dogfooding. У команд `epic` и `story` есть только add, list, done, delete — ОБНОВИТЬ описание нельзя. За одну сессию это ударило дважды: описание эпика release-19-agent-effectiveness говорит про три слоя пути агента, тогда как эпик после перепланировки несёт ещё параллельную работу, контекст и кроссмодельность; описание истории github-primary-gitlab-mirror утверждало предпосылку, отменённую решением #267.
ПОЧЕМУ ЭТО НЕ КОСМЕТИКА: описание эпика и истории — это то, чем агент понимает ЗАМЫСЕЛ группы задач. Устаревшее описание есть ложное действующее утверждение ровно того класса, который лечит весь релиз: «сказанное шире сделанного». Обход, применённый сегодня, — держать замысел в решениях #269, #271, #273, #274 — работает только пока их кто-то читает.
ЧТО ДЕЛАЕТСЯ: `epic update` и `story update` с --title и --description, симметрично `task update`. Плюс проверка: эпик, состав которого изменился более чем на N задач с момента последней правки описания, попадает в отчёт устаревших описаний — не блокирует, но называет.
НЕГАТИВНОЕ: не превращать в гейт закрытия. Описание, обновлённое ради прохождения проверки, хуже честно устаревшего — предмет здесь видимость, а не принуждение.
СМЕЖНОЕ: то же ограничение у stories объясняет, почему сегодня приходилось УДАЛЯТЬ пустые истории вместо переименования.

## Acceptance Criteria

AC1 ОДНА РЕАЛИЗАЦИЯ, В МОДУЛЕ: scripts/hierarchy_edit.py::update(svc, kind, slug, title=None, description=None) — единственное место правки (валидация длины и однострочности как в add, _require_*, проекция в tausik/, событие epics|stories / slug / description_updated в events при изменении описания); CLI epic|story update и MCP tausik_epic_update / tausik_story_update зовут ровно эту функцию; ни один не несёт своей логики; ProjectService и SQLiteBackend не получают новых публичных членов (храповик class_surface только вниз).
AC2 НЕГАТИВНЫЙ СЦЕНАРИЙ (ошибки): update без единого поля — отказ с текстом «nothing to update»; неизвестный slug — та же ошибка, что у done/delete; title длиннее лимита — отказ validate_length; описание с переводом строки схлопывается в одну строку, как в add; мутации: событие не пишется — тест краснеет; CLI или MCP зовут backend напрямую мимо модуля — AST-тест краснеет.
AC3 ОТЧЁТ УСТАРЕВШИХ ОПИСАНИЙ, НЕ ГЕЙТ: epic list и story list получают колонку stale — число задач, созданных в эпике/истории ПОСЛЕ последней правки описания (события description_updated; если правок не было — created_at эпика/истории); порог из аргумента --stale-over N (по умолчанию 0 — печатается число, ничего не скрывается); закрытие эпика/истории/задачи от этого не зависит (тест: done проходит при любом stale).
AC4 Документация: docs/ru/cli.md и docs/en/cli.md, docs/ru/mcp.md и docs/en/mcp.md, спеки tools.py, счётчики MCP-инструментов во всех файлах, которые их несут (test_mcp_doc_tool_counts, gen_doc_constants --check); CHANGELOG.md и CHANGELOG.ru.md синхронно; bootstrap --ide all перед done (правится harness/ и scripts/), verify после него; память ДО done.

## Plan

## Rollback

git revert коммита: две подкоманды и два MCP-инструмента исчезают, описания остаются какими были; событий в events откат не удаляет (журнал append-only), они безвредны

## Journal

- 2026-09-03T20:42:44Z [planning] — ИНВЕНТАРЬ ДО ОЦЕНКИ (по вызову и по классу, включая tests/): backend epic_update/story_update(**fields) уже есть (project_backend.py:332/368); службы нет (service_hierarchy.py, 93 строки); CLI cmd_epic/cmd_story в project_cli.py:129-155 + парсер project_parser_hierarchy.py; MCP — handlers_hierarchy.py HIERARCHY_HANDLERS (9 записей) + спеки в harness/claude/mcp/project/tools.py:495-570; docs: cli.md ru/en:44-52, mcp.md ru/en таблица иерархии; тесты: tests/test_project_mcp.py (MCP), tests/test_mcp_integration.py пиннит len(TOOLS) >= 26 (нижняя граница, не закрытый список). События: backend_crud.event_add. Схема epics/stories: description есть, updated_at НЕТ — время правки описания берём из events (без миграции). Doctor 489 строк — отчёт кладём в epic list/story list. Несущих файлов 5 (служба, CLI, парсер, handlers, tools) + 4 docs + тесты — сложность ПЕРЕОЦЕНЕНА simple -> medium (память #523).
- 2026-09-03T20:48:12Z [implementation] — ПОЧИНКА: HierarchyMixin._hierarchy_update — единственная реализация (валидация как в add, _require_*, событие description_updated при правке описания, проекция); epic_update/story_update; description_staleness через backend.last_event_at + tasks_created_after (без миграции); epic_list_with_staleness/story_list_with_staleness. CLI: epic|story update, list --stale-over N, колонка stale. MCP: tausik_epic_update/tausik_story_update в HIERARCHY_HANDLERS и tools.py; списки печатают (stale: N). Docs: cli.md ru/en, mcp.md ru/en. Тесты: tests/test_hierarchy_update.py — 19 passed (служба, ошибки, AST «одна реализация» для CLI и MCP, парсер, отчёт, done при 25 stale). Потребители (test_project_mcp, test_mcp_tool_scope, test_mcp_integration, test_tausik_cli) 57 passed. ruff/mypy чисто. МУТАЦИИ 6/6 УБИТЫ (базовый 19 passed, убито только rc=1): (a) событие не пишется -> journaled+resets красные; (b) CLI зовёт svc.be напрямую -> AST-тест красный; (c) MCP-обработчик зовёт svc.be -> красный; (d) счётчик игнорирует событие -> resets красный; (e) epic_done отказывает при stale -> never_blocks красный; (f) правка заголовка пишет событие -> два теста красные. Память #546 записана до done.
- 2026-09-03T21:04:28Z [implementation] — ПЕРЕДЕЛКА ПО ГЕЙТУ class_surface (полная лента 5 failed): первая версия добавила ProjectService 5 публичных членов (118 -> 123) и SQLiteBackend 2 (129 -> 131) — храповик поверхности классов «только вниз» (baseline в tausik/gates.json), и он прав: это те самые god-классы. Реализация вынесена в МОДУЛЬ scripts/hierarchy_edit.py — update(svc, kind, slug, title, description), staleness(svc, kind, slug), list_with_staleness(svc, kind, epic_slug); служба и backend не тронуты (git checkout), запросы через svc.be._q1 как в brain_move.py. CLI и MCP зовут hierarchy_edit.update / list_with_staleness; AST-тест проверяет вызов именно модуля и отсутствие .be./epic_update у вызывающих; отдельный тест: у ProjectService нет epic_update/story_update/description_staleness, у SQLiteBackend нет last_event_at/tasks_created_after. ДОКИ СО СЧЁТЧИКАМИ MCP (119+7=126 -> 121+7=128): docs/en/mcp.md, docs/ru/mcp.md, README.md, README.ru.md (и три ячейки таблицы), docs/README.md, AGENTS.md, docs/en/senar-compliance-matrix.md, docs/ru/senar-compliance-matrix.md, docs/en/architecture.md (там же старый дрейф «= 124» исправлен на 128), docs/ru/agent-contract.md; docs/_generated/constants.json перегенерирован (gen_doc_constants --check OK; это job doc-constants в CI). test_mcp_doc_tool_counts 6 passed, test_gate_class_surface зелёный.
- 2026-09-03T21:04:43Z [implementation] — МУТАЦИИ 7/7 УБИТЫ на модульной версии (базовый 21 passed, убито только rc=1): (a) событие не пишется; (b) CLI зовёт svc.be.epic_update мимо модуля — AST-тест; (c) MCP-обработчик мимо модуля — AST-тест + round-trip; (d) счётчик игнорирует событие правки; (e) epic_done отказывает при stale — never_blocks; (f) правка заголовка пишет событие; (g) update без полей принимается молча — nothing_to_update. AC1 переписан под модуль (hierarchy_edit.update), CHANGELOG ru/en — тоже.
- 2026-09-03T21:05:56Z [implementation] — AC-1: ✓ tests/test_hierarchy_update.py::test_each_caller_calls_the_one_implementation_and_nothing_below_it (AST: CLI cmd_epic/cmd_story и MCP-обработчики зовут hierarchy_edit.update и list_with_staleness, никто не лезет в .be./epic_update) и tests/test_hierarchy_update.py::test_nothing_public_was_added_to_the_god_classes; tests/test_hierarchy_update.py::TestUpdate::test_a_description_edit_is_journaled_as_an_event. AC-2: ✓ tests/test_hierarchy_update.py::TestUpdate::test_nothing_to_update_is_refused, tests/test_hierarchy_update.py::TestUpdate::test_an_unknown_slug_fails_like_done_does, tests/test_hierarchy_update.py::TestUpdate::test_an_overlong_title_is_refused, tests/test_hierarchy_update.py::TestUpdate::test_a_multiline_description_collapses_like_add; мутации 7/7 в журнале. Negative: update без полей — отказ «nothing to update» (живой CLI на реальной БД); CLI/MCP мимо модуля — AST-тест красный; done при 25 stale проходит. AC-3: ✓ tests/test_hierarchy_update.py::TestStaleness::test_the_lists_carry_the_number, tests/test_hierarchy_update.py::TestStaleness::test_an_edit_resets_the_count, tests/test_hierarchy_update.py::TestStaleness::test_stale_never_blocks_closing; живой отчёт: epic list --stale-over 20 назвал 10 эпиков (landscape-2026-h2: 155), story list --epic release-19-renar-conformance --stale-over 5 — все шесть историй релиза (6–27). AC-4: ✓ docs cli.md/mcp.md ru+en; счётчики 126->128 в 10 файлах, tests/test_mcp_doc_tool_counts.py 6 passed, gen_doc_constants --check OK, tests/test_gate_class_surface.py зелёный; tools.py спеки; CHANGELOG.md + CHANGELOG.ru.md синхронно; bootstrap --ide all выполнен, verify после него; память #546 до done. Domain: замысел группы задач правится одной командой на любом канале, а его устаревание видно числом и никого не блокирует.
- 2026-09-03T21:06:24Z [done] — ПРИЗНАНИЕ ПРИ ЗАКРЫТИИ: гейт зафиксировал COMPLEXITY UNDERSTATED — заявлено medium, тронуто 13 несущих файлов из 21 (complex). Переоценка simple -> medium после инвентаря была, но инвентарь не учёл: (1) храповик class_surface, вынудивший переделку в модуль; (2) десять файлов документации со счётчиком MCP-инструментов (126 -> 128) и constants.json. Четвёртая смена подряд с занижением (память #523): считать в инвентаре и ФАЙЛЫ-НОСИТЕЛИ ЧИСЕЛ, которые меняет добавление инструмента/гейта, — они несут поведение тестов.
