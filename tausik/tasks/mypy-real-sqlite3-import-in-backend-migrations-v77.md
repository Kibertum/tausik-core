---
slug: mypy-real-sqlite3-import-in-backend-migrations-v77
title: "mypy: real sqlite3 import in backend_migrations_v77"
status: done
epic: null
story: null
complexity: null
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/backend_migrations_v77.py: import sqlite3 + аннотация без кавычек/noqa; без смены логики миграции"
scope_exclude: "всё, кроме scripts/backend_migrations_v77.py"
relevant_files:
  - "scripts/backend_migrations_v77.py"
  - "tests/test_task_block_question.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-07T18:42:54Z"
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

myPy commit-hook красный на backend_migrations_v77.py:36 (name-defined sqlite3) — заменить закавыченную аннотацию с noqa на реальный import sqlite3, вернуть коммит-лэйн задачи blocked-is-a-status в зелёный.

## Acceptance Criteria

1. `python -m mypy` чист по scripts/backend_migrations_v77.py — реальный `import sqlite3`, аннотация без кавычек и без `# noqa: F821`, как во всех соседних миграциях (v34/v42/v49/v76).
2. ruff и ruff format чисты по файлу; tests/test_task_block_question.py зелёный.
3. НЕГАТИВНЫЙ: закавыченная аннотация `"sqlite3.Connection"` без импорта НЕ проходит mypy — именно эту форму поймал commit-hook и отказался коммитить.

## Plan

## Rollback

git revert коммита с правкой; закавыченная аннотация возвращается одной строкой

## Journal

- 2026-10-07T18:42:37Z [implementation] — AC-1: AC-2: AC-3: NO — по-настоящему коротко:
- 2026-10-07T18:42:45Z [implementation] — PREV LINE IS NOISE - real evidence: AC-1: mypy clean on scripts/backend_migrations_v77.py (python -m mypy: Success, no issues; import sqlite3 real, annotation unquoted, noqa dropped). AC-2: ruff + ruff format clean; tests/test_task_block_question.py 12 passed. AC-3 NEGATIVE: the quoted-noqa form WAS refused by the mypy commit hook (migrations commit attempt 18:3x) - that is the negative proof, recorded in session journal. Verify run #3631 PASS (8/0/1, scoped 1 file, 12 passed), handle 3631.2742a3f0b6ba1a09a8135bfd207a7fca.
