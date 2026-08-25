---
slug: review-mlow-brain-safety
title: "[B2+B6+B7 MED] Brain migration FK envelope + docstrings + lock contract"
status: done
epic: senar-verify-redesign
story: review-findings-mlow-fix
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/brain_schema.py, scripts/brain_project_registry.py"
scope_exclude: "tests/ (no behavior change requiring new tests)"
relevant_files:
  - "scripts/brain_schema.py"
  - "scripts/brain_project_registry.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T10:26:09Z"
---

## Goal

3 связанных safety improvements в brain/registry. B7: brain_schema._migrate не использует PRAGMA foreign_keys=OFF/ON envelope (latent bug когда добавятся FK). B6: _migrate per-batch irreversibility не документирована (контракт implicit). B2: brain_project_registry._acquire_lock контракт "1 reclaim per call" не задокументирован + TOCTOU window. Все три — defensive docs/PRAGMA, чистые improvements без поведенческих изменений.

## Acceptance Criteria

1. brain_schema._migrate docstring добавляет явный "Migrations are irreversible — failures only roll back the failing batch; previously committed migrations remain"
2. brain_schema._migrate использует PRAGMA foreign_keys=OFF/ON envelope (как backend_migrations.py:run_migrations) — insurance для будущих FK-touching migrations
3. brain_schema._migrate добавляет PRAGMA foreign_key_check после COMMIT (raise если violations)
4. brain_project_registry._acquire_lock docstring документирует "single reclaim per call (reclaimed flag)" контракт
5. brain_project_registry._acquire_lock docstring acknowledge небольшой TOCTOU window между _is_stale_lock и os.unlink
6. Регрессия: existing tests все зелёные (нет behavior change в этой задаче, только docs + insurance pragma)
7. Ошибка/граничный случай: PRAGMA foreign_key_check показывает violations → raise RuntimeError с диагностикой
8. pytest зелёный, ruff clean

## Plan

## Rollback

## Journal

- 2026-04-25T10:26:02Z [implementation] — AC verified: ✓1 brain_schema._migrate docstring добавляет "Migrations are irreversible — failed batch only rolls back current; previously committed migrations stay applied" ✓2 PRAGMA foreign_keys=OFF/ON envelope обернул весь loop через try/finally (matches backend_migrations.py) ✓3 PRAGMA foreign_key_check после COMMIT, raise RuntimeError если violations ✓4 brain_project_registry._acquire_lock docstring документирует "single reclaim per call (reclaimed flag)" ✓5 acknowledge небольшой TOCTOU window между _is_stale_lock и os.unlink ✓6 регрессия: pytest 52/52 passed (test_brain_schema 23 + test_brain_project_registry 29) ✓7 violations → RuntimeError ✓8 ruff clean
