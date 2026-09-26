---
slug: test-run-migrates-the-live-project-db
title: "Прогон тестов мигрирует ЖИВУЮ БД проекта, а два воркера xdist гоняются на одном ALTER"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/project_backend.py"
  - "scripts/backend_read_only.py"
  - "scripts/backend_migrations.py"
  - "scripts/gate_claudemd_state.py"
  - "tests/test_read_only_backend.py"
scope_paths:
  - "scripts/project_backend.py"
  - "scripts/backend_read_only.py"
  - "scripts/backend_migrations.py"
  - "scripts/gate_claudemd_state.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T20:43:37Z"
resolution: null
resolution_reason: null
---

## Goal

Замер смены #266: после подъёма SCHEMA_VERSION до 63 прогон tests/test_claudemd_state_gate.py::TestTheRealTreeIsIntact::test_the_gate_is_green_end_to_end_on_this_repository открыл .tausik/tausik.db через SQLiteBackend, init_schema мигрировал живую базу разработчика до v63 (бэкап tausik.db.bak.v62 создан тестом), а параллельный воркер упал на «duplicate column name: host_session_id» — гонка двух процессов на одной миграции. Следствие для пользователя: развёрнутая копия .claude/scripts (v62) после этого отказывает («Database schema v63 is newer than code v62») до bootstrap. Тест, читающий живое дерево, не имеет права писать в живую БД; и init_schema не защищён от параллельного апгрейда (нет блокировки, ALTER без проверки колонки).

## Acceptance Criteria

1. Воспроизведено: тест с подменой версии (фикстура-копия БД на v-1) показывает, что гейт состояния CLAUDE.md мигрирует базу при чтении.
2. Гейт и тесты живого дерева открывают БД только на чтение (mode=ro или отказ «база старше кода — нужен bootstrap»), никогда не мигрируют.
3. НЕГАТИВНЫЙ: два процесса, одновременно открывающие базу на старой схеме, не падают на duplicate column — миграция идёт под BEGIN IMMEDIATE с перечитыванием schema_version внутри блокировки (тест с двумя процессами).
4. CHANGELOG EN+RU.

## Plan

## Rollback

git revert

## Journal

- 2026-09-23T20:37:12Z [implementation] — AC-1: ✓ tests/test_read_only_backend.py::test_the_claudemd_gate_does_not_migrate_the_database_it_reads
- 2026-09-23T20:37:12Z [implementation] — AC-2: ✓ tests/test_read_only_backend.py::test_a_read_only_backend_refuses_a_schema_mismatch_and_writes_nothing
- 2026-09-23T20:37:12Z [implementation] — Воспроизведено тестами до правки: (1) гейт CLAUDE.md мигрировал базу v65→v66 при чтении; (2) два процесса на старой базе — второй падал 'database is locked' в run_migrations (не duplicate column: его уже снимает guard из задачи upgrade-from-1-8). Правка: backend_read_only.open_read_only (mode=ro, отказ при несовпадении версии со словами 'newer/older than code'), SQLiteBackend(read_only=True) — параметр, не новый член (храповик class_surface); гейт читает read_only; run_migrations — BEGIN IMMEDIATE и перечитывание версии под блокировкой. project_backend.py 491, backend_migrations.py 500 строк.
- 2026-09-23T20:37:13Z [implementation] — AC-2: ✓ tests/test_read_only_backend.py::test_a_read_only_backend_reads_a_current_database
- 2026-09-23T20:37:13Z [implementation] — AC-3: ✓ tests/test_read_only_backend.py::test_two_processes_upgrading_the_same_database_both_succeed (5 прогонов подряд зелёные)
- 2026-09-23T20:37:13Z [implementation] — AC-4: ✓ CHANGELOG EN+RU
- 2026-09-23T20:37:14Z [implementation] — NO-DEAD-END: красные прогоны — воспроизведение дефектов до правки и закреплённая тестом формулировка 'is newer than code', учтена
