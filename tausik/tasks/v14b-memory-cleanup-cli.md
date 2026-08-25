---
slug: v14b-memory-cleanup-cli
title: "B9: tausik memory archive --before 90d + dedupe команды"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 100
defect_of: null
scope: "scripts/backend_schema.py, scripts/backend_migrations.py, scripts/service_knowledge.py, scripts/project_backend.py, scripts/project_parser.py (memory subparser), scripts/project_cli_*.py (memory dispatch), harness/{claude,cursor}/mcp/project/handlers.py + tools.py, tests/test_memory_cleanup_cli.py (new), tests/test_migrations.py, docs/{en,ru}/memory-merge-guidelines.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/brain_classifier.py (routing logic unrelated), brain layer (archive scoped to local memory only)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T23:16:23Z"
---

## Goal

Long-running проект накапливает память. Добавить tausik memory archive --before <duration> (помечает старые записи archived=1) и tausik memory dedupe (FTS5 similarity > 0.85 → suggest merge). Поддерживает спеку memory-merge-guidelines.md.

## Acceptance Criteria

1. Schema migration v26: ALTER TABLE memory ADD COLUMN archived_at TEXT (nullable, ISO8601). 2. Duration parser: parse_duration_to_days() поддерживает '90d'/'12w'/'1y'/'2m' (m=30d, y=365d). Невалидное → ValueError. 3. service_knowledge.memory_archive(before='90d') → int (count archived). UPDATE memory SET archived_at=now WHERE created_at < cutoff AND archived_at IS NULL. Идемпотентна. 4. service_knowledge.memory_dedupe(threshold=0.85) → list[dict] кандидатов на merge: для каждой пары memory с FTS5 hit и SequenceMatcher.ratio() > threshold возвращает {id_a, id_b, ratio, title_a, title_b}. Suggest-only — не удаляет. 5. memory_list/memory_search фильтруют archived_at IS NOT NULL по умолчанию; новый параметр include_archived=False; CLI флаг --include-archived. 6. CLI: tausik memory archive --before <duration> (требует подтверждения через --confirm; без --confirm = dry-run preview); tausik memory dedupe [--threshold 0.85] печатает таблицу suggested merges. 7. MCP tools tausik_memory_archive + tausik_memory_dedupe + include_archived в memory_list/memory_search. 8. Negative: повторный --confirm идемпотентен. 9. Negative: --threshold вне [0,1] → ValueError. 10. Negative: невалидный duration формат → ValueError. 11. Tests/test_memory_cleanup_cli.py: новый файл, ≥10 тестов. 12. tests/test_migrations.py: v26 миграция теста. 13. docs/{en,ru}/memory-merge-guidelines.md обновлены с новыми CLI. 14. CHANGELOG.md + CHANGELOG.ru.md. 15. ruff + mypy + pytest зелёные. 16. filesize gate pass.

## Plan

[{"step": "Migration v26: ALTER TABLE memory ADD COLUMN archived_at + idx", "done": true}, {"step": "Duration parser parse_duration_to_days() (d/w/m/y) in tausik_utils or new mem_dedupe module", "done": true}, {"step": "service_knowledge.memory_archive(before, dry_run) implementation", "done": true}, {"step": "service_knowledge.memory_dedupe(threshold) using FTS5 + SequenceMatcher", "done": true}, {"step": "memory_list/memory_search include_archived param + filter default", "done": true}, {"step": "CLI subparser: tausik memory archive --before --confirm + memory dedupe [--threshold]", "done": true}, {"step": "MCP wiring: tausik_memory_archive + tausik_memory_dedupe + include_archived on list/search", "done": true}, {"step": "tests/test_memory_cleanup_cli.py with archive/dedupe/duration/threshold/list-filter cases", "done": true}, {"step": "tests/test_migrations.py v26 case", "done": true}, {"step": "docs/{en,ru}/memory-merge-guidelines.md + CHANGELOG en+ru", "done": true}, {"step": "ruff + mypy + filesize + pytest green", "done": true}]

## Rollback

## Journal

- 2026-05-06T23:15:56Z [implementation] — AC verified: 1-16 ✓ migration v26 + duration parser + archive/dedupe service + CLI + MCP + filter + 18 tests + docs en/ru + CHANGELOG en+ru + ruff + mypy + pytest 2962 green + filesize
- 2026-05-06T23:16:23Z [implementation] — AC verified: 1-16 ✓ migration v26 + duration parser + archive/dedupe service + CLI + MCP + filter + 18 tests + docs en/ru + CHANGELOG en+ru + ruff + mypy + pytest 2962 green
