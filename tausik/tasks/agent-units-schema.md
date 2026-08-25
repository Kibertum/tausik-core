---
slug: agent-units-schema
title: "Schema v17 + tier mapping для agent-native units"
status: done
epic: agent-native-planning
story: estimation-foundation
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/backend_schema.py (SCHEMA_VERSION + tasks DDL)\nscripts/backend_migrations.py (новая v17 migration)\nscripts/backend_crud.py (derive_tier_from_budget + task_set_call_budget + task_set_call_actual)\ntests/test_agent_units.py (новый файл)"
scope_exclude: "scripts/project_cli*.py (CLI — отдельная задача agent-units-cli-flags)\nscripts/service_*.py (recording логика — отдельная задача agent-units-recording)\nscripts/backend_queries.py (метрики — отдельная задача metrics-tier-calibration)\nagents/skills/plan/ (план skill — отдельная задача plan-skill-agent-aware)\nreferences/ (документация — после impl всех 6 задач)</scope_exclude>\n</invoke>\n<invoke name=\"TodoWrite\">\n<parameter name=\"todos\">[{\"content\": \"Start task agent-units-schema (QG-0)\", \"activeForm\": \"Starting task agent-units-schema\", \"status\": \"in_progress\"},\n{\"content\": \"Add v17 migration in backend_migrations.py\", \"activeForm\": \"Adding v17 migration\", \"status\": \"pending\"},\n{\"content\": \"Update SCHEMA_SQL + bump SCHEMA_VERSION to 17\", \"activeForm\": \"Updating schema snapshot\", \"status\": \"pending\"},\n{\"content\": \"Implement derive_tier_from_budget + task_set_call_budget + task_set_call_actual in backend_crud\", \"activeForm\": \"Implementing helpers\", \"status\": \"pending\"},\n{\"content\": \"Write tests in tests/test_agent_units.py\", \"activeForm\": \"Writing tests\", \"status\": \"pending\"},\n{\"content\": \"Run scoped pytest + mark task done with --ac-verified\", \"activeForm\": \"Running gates and closing task\", \"status\": \"pending\"}]"
relevant_files:
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_crud.py"
  - "tests/test_agent_units.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T11:43:28Z"
---

## Goal

Schema migration v17: добавить call_budget INTEGER, call_actual INTEGER, tier TEXT CHECK(tier IN ('trivial','light','moderate','substantial','deep')) к tasks table. Backend helpers task_set_call_budget, task_set_call_actual, derive_tier_from_budget. Маппинг порогов: trivial≤10, light 10-25, moderate 25-60, substantial 60-150, deep 150-400. Backwards-compat: старые tasks без call_budget работают как раньше.

## Acceptance Criteria

- [ ] Migration v17 добавляет колонки в tasks: call_budget INTEGER NULL, call_actual INTEGER NULL, tier TEXT NULL с CHECK(tier IS NULL OR tier IN ('trivial','light','moderate','substantial','deep'))
- [ ] backend_schema.py SCHEMA_VERSION = 17 + SCHEMA_SQL для tasks отражает новые колонки (fresh DBs не падают)
- [ ] Helper derive_tier_from_budget(budget: int|None) -> str|None в backend_crud: thresholds trivial≤10, light≤25, moderate≤60, substantial≤150, deep≤400, >400 → 'deep' (capped), None/0 → None
- [ ] task_set_call_budget(slug, budget: int|None): валидирует budget≥0 (или None для clear); auto-derives tier через derive_tier_from_budget; обновляет updated_at
- [ ] task_set_call_actual(slug, actual: int|None): валидирует actual≥0 (или None); НЕ меняет tier (tier — это план, actual — факт); обновляет updated_at
- [ ] Backwards-compat: существующие tasks без call_budget/call_actual/tier работают (NULL допустим, существующие SELECT не падают)
- [ ] Migration идемпотентна: повторный запуск не падает (проверка через "ALTER TABLE ADD COLUMN" — SQLite кинет на existing column, поэтому migration должна быть atomic — один запуск через MIGRATIONS)
- [ ] Negative scenario: попытка task_set_call_budget с budget=-1 → ValueError; попытка set с несуществующим slug → KeyError или возвращает False (consistent with existing helpers)
- [ ] Tests в tests/test_agent_units.py: (a) migration v17 применилась, колонки есть; (b) derive_tier_from_budget на boundary values 0,1,10,11,25,26,60,61,150,151,400,401,None; (c) task_set_call_budget успех + auto-derive tier; (d) task_set_call_actual без затрагивания tier; (e) negative budget rejected; (f) backwards-compat — fresh task без budget работает

## Plan

## Rollback

## Journal

- 2026-04-25T11:40:48Z [implementation] — Plan: 1) v17 migration adds call_budget+call_actual+tier with CHECK; 2) bump SCHEMA_SQL+SCHEMA_VERSION; 3) derive_tier_from_budget + task_set_call_budget/actual в backend_crud; 4) tests/test_agent_units.py. Стартую с migration.
- 2026-04-25T11:43:09Z [implementation] — Done. Evidence: - v17 migration: ALTER ADD call_budget+call_actual+tier (with CHECK) — backend_migrations.py - SCHEMA_VERSION=17, SCHEMA_SQL обновлён — backend_schema.py - derive_tier_from_budget + task_set_call_budget + task_set_call_actual — backend_crud.py - 30 новых тестов tests/test_agent_units.py — все PASS (boundaries 0,1,10,11,25,26,60,61,150,151,400,401,10000) - Существующие тесты не сломаны: test_migrations.py + test_tausik_backend.py 75/75 PASS - Live DB мигрировала v16→v17: все 3 колонки на месте - Backwards-compat: NULL допустим, существующие SELECT работают - Negative scenarios: budget=-1 / actual=-5 → ValueError; unknown slug → False (не KeyError, consistent с _ex semantics)
- 2026-04-25T11:43:23Z [implementation] — AC verified: 1. Migration v17 adds call_budget INTEGER, call_actual INTEGER, tier TEXT с CHECK ✓ (test_columns_present + test_tier_check_constraint PASSED) 2. SCHEMA_VERSION=17 + SCHEMA_SQL отражает новые колонки ✓ (test_schema_version_at_least_17 PASSED) 3. derive_tier_from_budget с правильными порогами (10/25/60/150/400, cap, None handling) ✓ (14 boundary cases PASSED) 4. task_set_call_budget валидирует, auto-derives tier, обновляет updated_at ✓ (5 tests PASSED) 5. task_set_call_actual без затрагивания tier, валидирует ✓ (4 tests PASSED) 6. Backwards-compat — существующие tasks без units работают ✓ (TestBackwardsCompat PASSED + 75/75 test_tausik_backend.py PASSED) 7. Migration идемпотентна — live DB мигрировала v16→v17 cleanly ✓ 8. Negative scenarios: budget=-1 → ValueError, unknown slug → False ✓ (4 tests PASSED) 9. Tests в tests/test_agent_units.py покрывают все AC ✓ (30 tests PASSED)
