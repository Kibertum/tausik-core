---
slug: v16r-reasoning-steps-table
title: "[P0] reasoning_steps: схема + CLI/MCP tausik_reason_step"
status: done
epic: v16-renar-core
story: v16r-trace
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "scripts/backend_schema.py (SCHEMA_VERSION 31→32, reasoning_steps + fts_reasoning_steps + triggers + indexes в базовой схеме), scripts/backend_migrations.py (миграция v32, аддитивная), scripts/backend_init.py (fts_reasoning_steps в rebuild-цикл), scripts/backend_crud.py (reasoning_step_add/reasoning_step_list), scripts/service_task.py (reasoning_step_add/reasoning_steps + wire в task_show), scripts/project_parser_task.py + scripts/project_cli_task.py (CLI `task reason-step` + рендер trace в task show), harness/claude/mcp/project/{handlers,tools}.py + harness/cursor/mcp/project/{handlers,tools}.py (MCP tausik_reason_step), docs/_generated/constants.json + doc cross-refs (mcp tool count +1), tests/test_reasoning_steps.py (new)."
scope_exclude: ".claude/ .cursor/ .qwen/ (generated — bootstrap регенерит, НЕ редактировать). НЕ менять существующие таблицы (только аддитив). НЕ трогать gmcp/v2, .tausik/keys. Listing reasoning-шагов — через task show (НЕ отдельный MCP-list-tool), чтобы surface был минимальным (+1 MCP tool)."
relevant_files:
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_legacy.py"
  - "scripts/backend_crud.py"
  - "scripts/backend_crud_reasoning.py"
  - "scripts/service_task.py"
  - "scripts/service_reasoning.py"
  - "scripts/project_backend.py"
  - "scripts/project_parser_task.py"
  - "scripts/project_cli_task.py"
  - "tests/test_reasoning_steps.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T14:43:00Z"
---

## Goal

Блокер №1 RENAR-релиза (аудит §4.4): structured reasoning trace per task. Таблица reasoning_steps (task_slug, seq, kind: intent|premise|action|verification, content, ts) + миграция + CLI `tausik reason step` + MCP tausik_reason_step + FTS5 индексация. AC: запись/чтение шагов работает; task show отображает trace; типы — closed list; тесты.

## Acceptance Criteria

AC1 (migration): на v31-БД миграция v32 применяется чисто — reasoning_steps + fts_reasoning_steps + триггеры (ai/ad) + индексы созданы; PRAGMA foreign_key_check пуст; базовая схема (backend_schema) тоже их создаёт для свежей БД. Тест: run_migrations(conn,31)→32, assert таблицы+триггеры существуют.
AC2 (CRUD + closed types): reasoning_step_add(slug, kind, content[, seq]) пишет; reasoning_steps(slug) возвращает шаги в порядке seq; kind ∈ {intent,premise,action,verification} (CHECK). NEGATIVE: insert kind='foo' → IntegrityError (closed list реально enforced, не свободный текст).
AC3 (CLI/MCP/trace + FTS): `tausik task reason-step <slug> <kind> "txt"` и MCP tausik_reason_step пишут шаг; `task show <slug>` рендерит секцию reasoning trace; FTS5 поиск находит content шага. NEGATIVE: reason-step по несуществующему slug → ServiceError (не тихий no-op).
AC4 (gates): ruff + mypy + pytest (новый тест + существующие schema/migration) зелёные; gen_doc_constants --check зелёный (MCP tool count +1 синхронизирован в constants.json + doc cross-refs).

## Plan

## Rollback

Миграция v32 чисто аддитивная (CREATE reasoning_steps/fts_reasoning_steps/triggers/indexes) — 0 влияния на существующие данные/таблицы. Ни одна задеплоенная БД ещё не на v32. Rollback: git revert коммита; для локально-мигрированной БД — DROP TABLE fts_reasoning_steps; DROP TABLE reasoning_steps; UPDATE meta SET value='31' WHERE key='schema_version'.

## Journal

- 2026-06-13T14:32:08Z [implementation] — RENAR reasoning_steps реализован: schema v32 (table+fts5+triggers+indexes) + аддитивная миграция v32, CRUD reasoning_step_add/list (seq auto-inc per-task, closed-list kind via CHECK), service + wire в task_show, CLI 'task reason-step' + trace-рендер, MCP tausik_reason_step (claude+cursor harness). 12 тестов (migration/CRUD/closed-types DB+service/FTS/task_show/parser/negatives). Full suite 3705 passed. Doc counts 104→105/97→98/111→112, test 3823→3835. Re-bootstrap .claude mirror (mirror-sync tests pass). gen_doc_constants --check green.
- 2026-06-13T14:32:58Z [implementation] — AC1 ✓: SCHEMA_VERSION=32; test_migration_v32_creates_table_triggers_clean (v31→32, reasoning_steps+fts+triggers, foreign_key_check пуст) + test_fresh_backend_has_reasoning_steps. AC2 ✓: test_add_and_list_steps_ordered (seq 1-4), test_seq_is_per_task; NEGATIVE test_invalid_kind_rejected_at_service (ServiceError) + test_invalid_kind_rejected_at_db (sqlite3.IntegrityError CHECK) + test_step_on_missing_task_raises. AC3 ✓: test_task_show_includes_reasoning_trace, test_fts_search_finds_step_content, test_cli_parser_accepts_reason_step/rejects_bad_kind; MCP tausik_reason_step→svc.reasoning_step_add (claude+cursor). AC4 ✓: ruff clean; mypy (pre-commit); FULL suite 3705 passed/8 skipped (12 новых reasoning-тестов); gen_doc_constants --check OK (counts 105/98/112, test 3835). Domain: reasoning trace персистится и searchable для реального RENAR-аудита (§4.4 blocker #1).
- 2026-06-13T14:42:24Z [implementation] — AC1 ✓: SCHEMA_VERSION=32; test_migration_v32_creates_table_triggers_clean (v31→32, reasoning_steps+fts+triggers ai/ad, foreign_key_check пуст) + test_fresh_backend_has_reasoning_steps. AC2 ✓: test_add_and_list_steps_ordered (seq 1-4), test_seq_is_per_task; NEGATIVE test_invalid_kind_rejected_at_service (ServiceError) + test_invalid_kind_rejected_at_db (sqlite3.IntegrityError CHECK) + test_step_on_missing_task_raises. AC3 ✓: test_task_show_includes_reasoning_trace, test_fts_search_finds_step_content, test_cli_parser_accepts/rejects; MCP tausik_reason_step→svc.reasoning_step_add (claude+cursor). AC4 ✓: ruff clean; mypy 163 files clean; FULL suite 3707 passed/8 skipped/0 failed; gen_doc_constants --check OK (105/98/112, test 3835). Filesize: extracted ReasoningCrudMixin+ReasoningMixin+seed_v18_roles→legacy, все <400. Domain: reasoning trace персистится+searchable для RENAR-аудита §4.4 blocker#1.
- 2026-06-13T14:42:59Z [implementation] — AC1 ✓ test_migration_v32_creates_table_triggers_clean + test_fresh_backend_has_reasoning_steps. AC2 ✓ test_add_and_list_steps_ordered/test_seq_is_per_task + NEGATIVE service(ServiceError)/db(IntegrityError CHECK)/missing-task. AC3 ✓ task_show trace + FTS search + CLI parser accept/reject; MCP tausik_reason_step (claude+cursor). AC4 ✓ ruff+mypy(163) clean, FULL suite 3707 passed/0 failed, gen_doc_constants --check OK (105/98/112, 3835). Filesize: extracted mixins+seed_v18→legacy, все <400. Knowledge: memory #141 (wiring-паттерн).
