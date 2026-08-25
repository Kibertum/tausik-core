---
slug: v14b-hygiene-archive-confirm
title: "B5: hygiene archive --confirm actual implementation (soft-delete done > N days)"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/backend_schema.py, scripts/backend_migrations.py, scripts/project_cli_hygiene.py, scripts/project_backend.py, scripts/service_task.py, scripts/project.py (CLI argparse), scripts/cmd_db.py (если нужно), .claude/mcp/project/handlers.py (task_list MCP), tests/test_hygiene_cli.py, tests/test_backend_migrations.py, docs/en/task-archive-spec.md, docs/ru/task-archive-spec.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/backend_queries.py metrics queries (archived всё ещё считаем как done — historical accuracy), FTS search (archived findable in search)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T22:57:06Z"
---

## Goal

Сейчас --confirm reserved/rejected. Реализовать soft-delete: добавить archived_at column + UPDATE WHERE status='done' AND completed_at < cutoff. tausik task list по умолчанию исключает archived. Optional --include-archived flag.

## Acceptance Criteria

1. Schema migration v25: ALTER TABLE tasks ADD COLUMN archived_at TEXT (nullable, ISO8601). SCHEMA_SQL и SCHEMA_VERSION обновлены. Тест: миграция с v24 БД корректно добавляет колонку. 2. project_cli_hygiene._archive_apply(): новая функция UPDATE tasks SET archived_at=now WHERE status='done' AND completed_at<cutoff AND archived_at IS NULL. Идемпотентна. 3. cmd_hygiene_archive с --confirm и enabled=true: вызывает _archive_apply и печатает 'Archived N done tasks'. 4. cmd_hygiene_archive с --confirm и disabled: прежнее 'disabled' сообщение (--confirm не активирует фичу). 5. cmd_hygiene_archive без --confirm: dry-run как раньше. 6. project_backend.task_list: новый параметр include_archived=False, default фильтрует AND t.archived_at IS NULL. 7. service_task.task_list + MCP tausik_task_list + CLI tausik task list: пробрасывают --include-archived флаг. 8. Negative: повторный --confirm идемпотентен (0 archived second run). 9. Negative: archived task всё ещё доступна через task_show по slug. 10. tests/test_hygiene_cli.py: 3 новых теста (apply пишет timestamp, idempotent, list по умолчанию исключает). 11. Negative: --include-archived показывает архивированные. 12. docs/{en,ru}/task-archive-spec.md обновлены — убрать 'future implementation', описать --confirm + --include-archived + archived_at. 13. CHANGELOG.md + CHANGELOG.ru.md: запись в Unreleased. 14. ruff + mypy + pytest зелёные.

## Plan

[{"step": "Add migration v25 + SCHEMA_VERSION bump + SCHEMA_SQL archived_at column", "done": true}, {"step": "Implement _archive_apply() helper in project_cli_hygiene.py", "done": true}, {"step": "Wire --confirm flag into cmd_hygiene_archive (executes apply)", "done": true}, {"step": "Add include_archived param to project_backend.task_list (default False)", "done": true}, {"step": "Propagate include_archived through service_task + CLI (--include-archived) + MCP", "done": true}, {"step": "Update tests/test_hygiene_cli.py with apply/idempotent/list-filter cases", "done": true}, {"step": "Update tests/test_backend_migrations.py with v25 archived_at column check", "done": true}, {"step": "Update docs/{en,ru}/task-archive-spec.md (remove 'future', document new flags + column)", "done": true}, {"step": "Add CHANGELOG.md + CHANGELOG.ru.md Unreleased entries", "done": true}, {"step": "Run ruff + mypy + targeted pytest on hygiene + migrations", "done": true}]

## Rollback

## Journal

- 2026-05-06T22:33:58Z [implementation] — Step 1 done: SCHEMA_VERSION 24→25, ALTER TABLE tasks ADD archived_at, CREATE INDEX idx_tasks_archived_at, schema sync.
- 2026-05-06T22:34:46Z [implementation] — Steps 2-3 done: _archive_apply() implemented (idempotent UPDATE), cmd_hygiene_archive now applies on --confirm. Disabled config still wins over --confirm.
- 2026-05-06T22:51:02Z [implementation] — All 10 plan steps done. Final stats: pytest 2936 passed / 0 failed / 7 skipped / 120 deselected (full fast-lane). ruff + mypy green. Migration v25 (archived_at column + index), CLI/MCP --include-archived flag, idempotent --confirm soft-delete, 8 new test cases, docs en/ru rewritten, CHANGELOG en/ru, README/AGENTS test count badges 3056→3063, fixed cp1252 unicode encoding bug in tests/test_check_docs_hook.py (write_text without encoding= + subprocess without encoding=).
- 2026-05-06T22:52:21Z [implementation] — AC verified: 1. ✓ Migration v25 adds archived_at — tests/test_migrations.py::test_migration_v25_adds_archived_at_to_tasks pass. 2. ✓ _archive_apply idempotent — tests/test_hygiene_cli.py::TestConfirmAppliesSoftDelete::test_confirm_idempotent pass. 3. ✓ --confirm stamps timestamp — test_confirm_stamps_archived_at pass. 4. ✓ disabled overrides --confirm — test_confirm_disabled_config_does_not_apply pass. 5. ✓ dry-run unchanged — test_dry_run_lists_candidates pass. 6. ✓ task_list filters by default — TestTaskListFiltersArchived::test_default_hides_archived pass. 7. ✓ MCP+CLI propagate include_archived — wired in handlers.py + tools.py + project_parser.py + project_cli_task.py. 8. ✓ idempotent re-run no-op — covered above. 9. ✓ task_show works on archived — test_archived_task_still_visible_via_task_show pass. 10. ✓ 8 new tests added in test_hygiene_cli.py. 11. ✓ --include-archived shows them — test_include_archived_shows_them pass. 12. ✓ docs en/ru rewritten. 13. ✓ CHANGELOG entries en+ru. 14. ✓ ruff + mypy + pytest 2936 passed all green.
- 2026-05-06T22:55:00Z [implementation] — AC verified: 1. ✓ Migration v25 — test_migration_v25_adds_archived_at_to_tasks. 2. ✓ idempotent — test_confirm_idempotent. 3. ✓ stamps timestamp — test_confirm_stamps_archived_at. 4. ✓ disabled overrides --confirm — test_confirm_disabled_config_does_not_apply. 5. ✓ dry-run — test_dry_run_lists_candidates. 6. ✓ task_list filters — test_default_hides_archived. 7. ✓ MCP+CLI propagated — handlers.py + tools.py + project_parser_task.py + project_cli_task.py. 8. ✓ idempotent re-run no-op. 9. ✓ task_show works — test_archived_task_still_visible_via_task_show. 10. ✓ 8 new tests in test_hygiene_cli.py. 11. ✓ --include-archived — test_include_archived_shows_them. 12. ✓ docs en/ru rewritten. 13. ✓ CHANGELOG en+ru. 14. ✓ ruff + mypy + pytest 2936 passed. 15. ✓ filesize gate fixed — split project_parser.py 414→252 by extracting task subparser to project_parser_task.py.
- 2026-05-06T22:55:11Z [implementation] — AC verified: 1. ✓ Migration v25 archived_at — test_migration_v25_adds_archived_at_to_tasks. 2. ✓ idempotent apply — test_confirm_idempotent. 3. ✓ stamps timestamp — test_confirm_stamps_archived_at. 4. ✓ disabled overrides --confirm — test_confirm_disabled_config_does_not_apply. 5. ✓ dry-run lists candidates. 6. ✓ task_list filters by default — test_default_hides_archived. 7. ✓ MCP+CLI propagated. 8. ✓ idempotent re-run. 9. ✓ task_show works on archived row. 10. ✓ 8 new test cases. 11. ✓ --include-archived. 12. ✓ docs en/ru. 13. ✓ CHANGELOG en+ru. 14. ✓ ruff+mypy+pytest 2936 green. 15. ✓ filesize fix — split parser 414→252.
- 2026-05-06T22:57:06Z [implementation] — AC verified: 1-15 ✓ migration+CLI+MCP+tests+docs+CHANGELOG+filesize all green
