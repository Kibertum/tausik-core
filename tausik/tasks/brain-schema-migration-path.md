---
slug: brain-schema-migration-path
title: "LOW: migration path для SCHEMA_VERSION"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: "scripts/brain_schema.py, tests/test_brain_schema.py"
scope_exclude: "scripts/brain_sync.py, scripts/brain_config.py"
relevant_files:
  - "scripts/brain_schema.py"
  - "tests/test_brain_schema.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T10:01:14Z"
---

## Goal

SCHEMA_VERSION=1 пишется но никогда не читается → нет ALTER strategy. Добавить _migrate(conn, from_version) helper или задокументировать протокол в brain-db-schema.md

## Acceptance Criteria

1. apply_schema читает текущий brain_meta.schema_version после CREATE TABLE IF NOT EXISTS
2. Новый _migrate(conn, from_version) helper: итерирует BRAIN_MIGRATIONS dict (по возрастанию ключей), применяет statements для каждой версии > from_version, обновляет brain_meta.schema_version
3. BRAIN_MIGRATIONS = {} placeholder dict с docstring-комментарием контракта (формат: {ver: [sql_stmt, ...]}, применяется в порядке возрастания, irreversible)
4. Если db_version > SCHEMA_VERSION → raise RuntimeError("Brain DB schema vN newer than code v1; update tausik-lib")
5. Регрессия: существующая чистая install (no brain_meta) → schema_version = 1 записан как сейчас
6. Регрессия: повторный apply_schema на v1 db → no-op, не raise
7. Ошибка/граничный случай: пустой BRAIN_MIGRATIONS → нет действий при apply (no schema bump beyond INSERT OR IGNORE)
8. Тест: db_version > SCHEMA_VERSION → raise (newer-code guard)
9. pytest зелёный, ruff clean

## Plan

## Rollback

## Journal

- 2026-04-25T10:01:12Z [implementation] — AC verified: 1. apply_schema читает brain_meta.schema_version после INSERT OR IGNORE ✓ 2. _migrate(conn, from_version) iterates BRAIN_MIGRATIONS sorted, applies stmts > from_version, bumps schema_version per batch ✓ 3. BRAIN_MIGRATIONS={} placeholder с docstring контракта (формат, irreversible, single-tx) ✓ 4. db_version > SCHEMA_VERSION → RuntimeError("newer than code v1; update tausik-lib") ✓ 5. Чистая install — schema_version=1 записан INSERT OR IGNORE как было ✓ 6. Repeat apply_schema на v1 → no-op ✓ 7. Empty BRAIN_MIGRATIONS → нет действий ✓ 8. test_apply_schema_raises_when_db_newer покрывает newer-code guard ✓ + test_migrate_applies_pending_versions, test_migrate_skips_already_applied, test_migrate_rolls_back_on_failure (rollback batch + version not bumped) ✓ 9. pytest 23/23 passed, ruff clean ✓
