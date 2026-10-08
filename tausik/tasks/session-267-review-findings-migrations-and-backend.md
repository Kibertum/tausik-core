---
slug: session-267-review-findings-migrations-and-backend
title: "Ревью смены #267 (миграции и бэкенд): перечитывание версии под BEGIN IMMEDIATE вне try держит блокировку при сбое; close() read-only делает WAL checkpoint; decisions --status/--task — N+1 запросов; supersede не атомарен с записью решения"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_migrations.py"
  - "scripts/project_backend.py"
  - "scripts/decision_lifecycle.py"
  - "scripts/service_decide.py"
  - "tests/test_review_267_fixes.py"
scope_paths:
  - "scripts/backend_migrations.py"
  - "scripts/project_backend.py"
  - "scripts/decision_lifecycle.py"
  - "scripts/service_decide.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T21:18:05Z"
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

CRITICAL, два HIGH и два MEDIUM из состязательного ревью миграций и бэкенда (смена #267) исправлены: любой путь после BEGIN IMMEDIATE снимает блокировку; read-only close без checkpoint; листинг решений одним запросом рёбер; запись решения и ребра supersedes — одна транзакция; проверка причины без фиктивного id.

## Acceptance Criteria

1. CRITICAL: сбой перечитывания schema_version после BEGIN IMMEDIATE (нет meta, мусор в значении) откатывает транзакцию — второе соединение затем пишет без 'database is locked'; тест.
2. HIGH: SQLiteBackend(read_only=True).close() не выполняет wal_checkpoint и не пишет предупреждение при живом писателе; тест.
3. HIGH: decisions с --task/--status/--rejected делает один запрос рёбер supersedes, а не запрос на строку; тест считает вызовы edge_list (ноль).
4. MEDIUM: решение с --supersedes и его ребро пишутся в одной транзакции; сбой ребра не оставляет решения; check_before_write проверяет причину сам, без фиктивного id=0; тест.
5. НЕГАТИВНЫЙ: существующие тесты миграций, решений и read-only зелёные; CHANGELOG EN+RU.

## Plan

## Rollback

git revert; правки локальны

## Journal

- 2026-09-23T21:02:47Z [implementation] — AC-1: ✓ tests/test_review_267_fixes.py::test_a_failed_version_reread_releases_the_write_lock
- 2026-09-23T21:02:47Z [implementation] — AC-2: ✓ tests/test_review_267_fixes.py::test_a_read_only_close_does_not_checkpoint
- 2026-09-23T21:02:47Z [implementation] — Сделано по ревью: run_migrations — перечитывание версии внутри try (ROLLBACK на любом сбое); SQLiteBackend хранит _read_only и не делает checkpoint при close; decision_lifecycle._superseder_map — один запрос рёбер, дешёвые фильтры раньше; service_decide — решение и ребро в svc.be.transaction(); _require_reason вместо вызова supersede с id=0. LOW про реэкспорт приватных помощников — не правлю: тест ссылается на них намеренно.
- 2026-09-23T21:02:48Z [implementation] — AC-3: ✓ tests/test_review_267_fixes.py::test_the_decision_listing_makes_no_per_row_graph_query
- 2026-09-23T21:02:48Z [implementation] — AC-4: ✓ tests/test_review_267_fixes.py::test_a_failed_edge_leaves_no_decision
- 2026-09-23T21:02:49Z [implementation] — AC-5: ✓ 1234 тестов миграций/решений/памяти/RAG зелёные; CHANGELOG EN+RU. NO-DEAD-END: находки ревью исправлены первым подходом
