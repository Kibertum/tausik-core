---
slug: decisions-have-no-lifecycle
title: "У решений нет жизненного цикла: неверное решение остаётся указанием навсегда, отвергнутое не ищется"
status: done
epic: release-110-deferred-from-19
story: release110-rag-and-memory-tell-the-truth
complexity: complex
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/decision_lifecycle.py"
  - "scripts/backend_migrations_v66.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_crud_knowledge.py"
  - "scripts/service_decide.py"
  - "scripts/service_knowledge.py"
  - "scripts/project_parser.py"
  - "scripts/project_cli.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/claude/mcp/project/handlers_knowledge.py"
  - "tests/test_decision_lifecycle.py"
scope_paths:
  - "scripts/**"
  - "harness/claude/mcp/project/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - memory-supersede-edges-are-data
completed_at: "2026-09-23T20:04:19Z"
---

## Goal

ЭТО ЯДРО ЖАЛОБЫ ПОЛЬЗОВАТЕЛЕЙ 1.8 «ФРЕЙМВОРК НЕ ЗАПИСЫВАЕТ ПЛОХИЕ РЕШЕНИЯ», ПЕРЕВЕДЁННОЕ В ЗАМЕР.
ЗАМЕР #189: решений 270, отвергнутые альтернативы называют 14 (5%) — и только ПРОЗОЙ внутри rationale, то есть запросом их не достать. У таблицы decisions колонки: id, decision, task_slug, rationale, created_at, slug. НИ ОДНОГО поля про отвергнутое и НИ ОДНОГО про жизненный цикл. Команда `tausik decisions` имеет ровно один флаг --limit: решения можно перечислить и больше ничего с ними сделать нельзя.
СЛЕДСТВИЕ ПЕРВОЕ: решение, оказавшееся неверным, остаётся действующим указанием НАВСЕГДА. Живые случаи этой же сессии: #267 разворачивает решение от 25.08 («GitHub — основное место разработки»), #269 сужает #256. Оба разворота выражены ПРОЗОЙ; машина по-прежнему считает старые решения действующими и втягивает их в блок наравне с новыми.
СЛЕДСТВИЕ ВТОРОЕ: отвергнутый вариант нельзя найти. Вопрос «а это уже пробовали?» — главный вопрос, ради которого ведут журнал решений, — сегодня отвечается только чтением 270 текстов подряд.
ЧТО ДЕЛАЕТСЯ: (1) `decide --rejected "вариант :: почему"` повторяемым флагом — отвергнутое становится полем, а не прозой, и ищется; (2) `decide --supersedes N --because "..."` — жизненный цикл через существующий memory_edges (source_type='decision'), без новой таблицы; (3) отменённое решение перестаёт втягиваться как действующее и показывается только вместе с отменившим; (4) `decisions` получает выборку: действующие, отменённые, по задаче, поиск по отвергнутому.
НЕГАТИВНОЕ: (а) отменённое решение НЕ УДАЛЯЕТСЯ — история разворотов есть главная ценность журнала; (б) нельзя требовать --rejected обязательным полем: решение без альтернатив бывает, и принуждение породит выдуманные альтернативы ради прохождения гейта — хуже, чем их отсутствие; (в) двусторонняя проверка: отменённое ушло из действующих И осталось в поиске.
СМЕЖНОЕ: memory-supersede-edges-are-data делает ту же работу для памяти и ту же подложку — не строить второй механизм.

## Acceptance Criteria

1. Замер до правки: сколько решений, сколько называют отвергнутое прозой, сколько разворотов выражено прозой; числа в журнале.
2. decide --rejected "вариант :: почему" (повторяемый) пишет отвергнутое в поле decisions.rejected (миграция v66, JSON-массив); decisions --rejected QUERY находит решение по отвергнутому варианту; MCP tausik_decide принимает rejected.
3. decide --supersedes N (с причиной: --because или --rationale) пишет ребро supersedes через memory_edges, без новой таблицы; без причины — отказ; несуществующее N — отказ.
4. decisions --status active|superseded|all и --task; отменённое не показывается в active и в блоке памяти, но показывается в superseded вместе с отменившим (колонка superseded_by).
5. НЕГАТИВНЫЙ: отменённое решение не удаляется — строка на месте, ищется по --rejected и по all (двусторонняя проверка тестом).
6. НЕГАТИВНЫЙ: --rejected не обязателен — решение без альтернатив записывается как раньше; --rejected/--supersedes вместе с --global отказывают, а не теряются молча.
7. docs (cli, mcp) en/ru; CHANGELOG EN+RU.

## Plan

## Rollback

Колонка decisions.rejected (миграция v66, nullable) и рёбра supersedes в существующей memory_edges; откат — git revert, колонка остаётся с NULL, рёбра — данными без потребителя

## Journal

- 2026-09-23T19:55:35Z [implementation] — Замер ДО правки (read-only SQL над живой БД — команды для этого нет, отступление признаю): решений 384; упоминают отвергнутое/альтернативу прозой (эвристика по словам отверг/отклон/вместо/rejected/alternative/considered) — 100; выражают разворот прозой (разворачива/отменя/supersed/заменя/пересмотр/поправка к решению) — 33; рёбер supersedes от решений в memory_edges — 1. То есть жизненный цикл есть в подложке, но им почти не пользуются: нет команды, которая пишет ребро при записи решения.
- 2026-09-23T19:58:33Z [implementation] — Сделано: scripts/decision_lifecycle.py (normalize_rejected, rejected_of, supersede, check_before_write, listing); миграция v66 decisions.rejected (fresh — колонка последней); backend decision_add(rejected); service_decide.record(rejected, supersedes): проверка ДО записи, ребро supersedes в memory_edges после; decisions(n, status, task, rejected); CLI decide --rejected/--supersedes/--because, decisions --status/--task/--rejected с колонкой superseded_by; MCP tausik_decide rejected/supersedes (описание сокращено, поверхность в пределах ratchet). Живая миграция: schema 65→66, 384 решения, хэш содержимого до=после 5fb08f07fd628825; decisions --status superseded показывает #109 → 292.
- 2026-09-23T19:58:34Z [implementation] — AC-1: ✓ замер в журнале выше (384 / ~100 / 33 / 1 ребро)
- 2026-09-23T19:58:34Z [implementation] — AC-2: ✓ tests/test_decision_lifecycle.py::test_rejected_alternatives_are_a_field_and_are_searchable
- 2026-09-23T19:58:34Z [implementation] — AC-3: ✓ tests/test_decision_lifecycle.py::test_superseding_needs_a_reason_and_an_existing_target
- 2026-09-23T19:58:35Z [implementation] — AC-4: ✓ tests/test_decision_lifecycle.py::test_a_superseded_decision_leaves_active_and_stays_findable
- 2026-09-23T19:58:35Z [implementation] — AC-4: ✓ tests/test_decision_lifecycle.py::test_filters_by_task
- 2026-09-23T19:58:35Z [implementation] — AC-4: ✓ tests/test_decision_lifecycle.py::test_the_memory_block_does_not_carry_the_superseded_one
- 2026-09-23T19:58:36Z [implementation] — AC-5: ✓ tests/test_decision_lifecycle.py::test_a_superseded_decision_leaves_active_and_stays_findable (строка на месте, ищется по --rejected и all)
- 2026-09-23T19:58:36Z [implementation] — AC-6: ✓ tests/test_decision_lifecycle.py::test_a_decision_without_alternatives_is_recorded_as_before
- 2026-09-23T19:58:36Z [implementation] — AC-6: ✓ tests/test_decision_lifecycle.py::test_the_shared_store_refuses_what_it_cannot_hold
- 2026-09-23T19:58:36Z [implementation] — AC-7: ✓ docs cli/mcp en+ru, CHANGELOG EN+RU
