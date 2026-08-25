---
slug: v16r-model-pinning
title: "[P0] Model-version pinning per task"
status: done
epic: v16-renar-core
story: v16r-repro
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/backend_schema.py (SCHEMA_VERSION 32→33 + 5 колонок tasks), scripts/backend_migrations.py (миграция v33, аддитивные ALTER + индексы), scripts/project_backend.py (_TASK_FIELDS += новые колонки), scripts/model_pinning.py (NEW: session_model, model_start_updates, model_done_updates, compute mismatch, format_model_usage_section), scripts/backend_queries_usage.py (task_model_ids + usage_cost_rollup_by_model), scripts/service_task.py (task_start: started_model), scripts/service_task_done.py (task_done: done_model + mismatch + evidence msg), scripts/project_cli_ops.py (metrics by-model секция), scripts/project_cli_task.py (task_show поля), tests/test_model_pinning.py (NEW)."
scope_exclude: ".claude/.cursor/.qwen (generated). НЕ добавлять новый MCP-tool (без изменения tool count → без doc-count bump). НЕ менять posttool_usage hook (usage_events.model_id source уже работает). НЕ трогать gmcp/v2, reasoning_steps (v32). Логику mismatch/formatting держать в model_pinning.py, чтобы service_task_done.py и project_cli_ops.py не превысили 400 строк."
relevant_files:
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "scripts/project_backend.py"
  - "scripts/model_pinning.py"
  - "scripts/backend_queries_usage.py"
  - "scripts/service_task.py"
  - "scripts/service_task_done.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_cli_task.py"
  - "tests/test_model_pinning.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T15:12:22Z"
---

## Goal

Блокер №2 RENAR-релиза: фиксация model_id/version на task start и done (сейчас usage_events.model_id — best-effort, weak link). AC: task хранит started_model/done_model; маппинг usage_events↔task усилен; mismatch (смена модели mid-task) фиксируется в evidence; metrics показывают распределение по моделям.

## Acceptance Criteria

AC1: tasks хранит started_model_id/version (записаны на task_start из session_current) и done_model_id/version (на task_done). Тест: start→ поля = модель сессии; done → done-поля заполнены.
AC2 (mismatch + usage↔task): model_mismatch=1 когда >1 различных model_id среди {started, done} ∪ usage_events.model_id задачи; список моделей попадает в evidence/notes на task_done. NEGATIVE: задача, где usage_events содержит 2 разные модели → mismatch=1 И сообщение перечисляет обе; single-model задача → mismatch=0, без шумного сообщения.
AC3 (metrics): `tausik metrics` показывает распределение usage по model_id (usage_cost_rollup_by_model: model_id | events | tokens | cost). task show отображает started/done model + mismatch.
AC4 (gates): миграция v33 применяется чисто (foreign_key_check пуст); ruff+mypy+pytest зелёные; все затронутые файлы ≤400 строк; gen_doc_constants --check зелёный (test_count синхронизирован; MCP count НЕ меняется).

## Plan

## Rollback

Миграция v33 аддитивная (только ALTER TABLE ADD COLUMN + CREATE INDEX на tasks) — 0 влияния на существующие данные. Rollback: git revert; для локально-мигрированной БД колонки безвредны (NULL/0). SCHEMA_VERSION откатить к 32 при revert.

## Journal

- 2026-06-13T15:11:30Z [implementation] — AC1 ✓ test_started_model_pinned_on_task_start + test_session_model_helper; done-model в model_done_updates (test_done_updates_no_mismatch). AC2 ✓ test_task_model_ids_distinct (usage↔task link) + test_done_updates_flags_mismatch (NEGATIVE: 2 модели→mismatch=1, обе в msg) + test_task_done_persists_mismatch_in_evidence (notes); single-model→0. AC3 ✓ test_rollup_by_model_excludes_session_record (no double-count) + test_format_model_usage_section; task show рендерит started/done/version/mismatch. AC4 ✓ migration v33 чистая (проверено на ЖИВОЙ .tausik.db: v33, колонки+индексы есть), ruff+mypy(164) clean, FULL suite 3716 passed/0 failed, gen_doc_constants --check OK (3844, MCP count не менялся), все файлы ≤400. Review (tausik-reviewer): HIGH-1 TOCTOU→расчёт внутри tx; MED-2 WARNING-префикс; MED-3 version-поля; MED-4 NOT NULL убран из ALTER (SQLite<3.32); LOW-1 alias. Bug пойман verify: индекс на migration-колонку в INDEXES_SQL крашил init (gotcha #142). Knowledge: memory #142.
- 2026-06-13T15:12:21Z [implementation] — AC1 ✓ test_started_model_pinned_on_task_start + session_model helper; done-model в model_done_updates. AC2 ✓ test_task_model_ids_distinct (usage↔task) + test_done_updates_flags_mismatch (NEGATIVE 2 модели→1, обе в msg) + persists_in_evidence; single→0. AC3 ✓ rollup_by_model_excludes_session_record + format section; task show рендерит поля. AC4 ✓ migration v33 на ЖИВОЙ БД (v33+колонки+индексы), ruff+mypy(164), suite 3716/0 fail, --check OK 3844, ≤400. Review fixes: TOCTOU→tx, WARNING-prefix, version-поля, NOT NULL убран, alias. Verify поймал index-bug → gotcha #142. Knowledge: #142.
