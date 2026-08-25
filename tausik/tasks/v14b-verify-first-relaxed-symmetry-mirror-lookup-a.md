---
slug: v14b-verify-first-relaxed-symmetry-mirror-lookup-a
title: "v14b-verify-first-relaxed-symmetry: mirror lookup_any_fresh_run into has_fresh_verify_run"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/verify_cache.py — has_fresh_verify_run; tests/test_verify_cache.py (или test_service_verification.py) — новые тесты; CHANGELOG.{md,ru.md} — запись."
scope_exclude: "scripts/verify_recent_lookup.py (lookup_any_fresh_run_for_task уже есть, не трогаем); scripts/service_verification.py (run_gates_with_cache работает корректно — НЕ дублировать его логику, переиспользовать)."
relevant_files:
  - "scripts/verify_cache.py"
  - "scripts/verify_recent_lookup.py"
  - "tests/test_verify_cache.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T18:51:22Z"
---

## Goal

Устранить STRICT vs relaxed asymmetry между run_gates_with_cache и has_fresh_verify_run (gotcha #111). После фикса task_done с явными relevant_files принимает свежий verify-run, записанный с files=[] (manual scope), без cache_status='git-mismatch'. Третья сессия подряд натыкаемся — структурный фикс убирает источник.

## Acceptance Criteria

1. has_fresh_verify_run(conn, slug, ['foo.py']) возвращает (True, row) когда STRICT lookup промахивается, но существует свежий exit_code=0 verify-run для slug, записанный с files=[] (manual scope, command содержит '|files='). Direction: manual→explicit accepted.
2. Reverse direction NOT auto-accepted: verify run, записанный с конкретными files=['bar.py'], НЕ удовлетворяет has_fresh_verify_run для тех же относительно других files=['foo.py'] через relaxed fallback (требуется strict files_hash match).
3. Strict hit по-прежнему приоритетнее: когда есть точное совпадение, relaxed-путь не активируется (нет лишних DB-запросов).
4. is_security_sensitive(files) → return False ДО любого relaxed lookup. Auth/payment пути никогда не получают session-level pass.
5. Новые unit-тесты в tests/test_verify_cache.py (или test_service_verification.py) покрывают: relaxed accept (manual→explicit), reverse reject, security-sensitive bypass, strict-priority.
6. Существующий full pytest зелёный (no regressions, baseline 2880).
7. CHANGELOG.md + CHANGELOG.ru.md: запись под Unreleased v1.4.0 polish Phase B (### Fixed) с упоминанием gotcha #111.

## Plan

## Rollback

## Journal

- 2026-05-06T18:35:59Z [implementation] — Explore done. Asymmetry confirmed: service_verification.run_gates_with_cache:223-239 уже имеет relaxed-fallback (one-direction: manual files=[] → explicit OK), а verify_cache.has_fresh_verify_run:74-104 — только strict. lookup_any_fresh_run_for_task + _extract_files_from_cache_command уже доступны в verify_recent_lookup.py (импортируются). План: расширить has_fresh_verify_run миррором логики, добавить unit-тесты в test_security_sensitive.py (соседство с TestVerifyFirstRegression) или новый test_verify_cache.py.
- 2026-05-06T18:44:00Z [implementation] — Implementation done: scripts/verify_cache.py получил relaxed-fallback с trigger=verify| фильтром (cache-bucket separation сохранена). Tests/test_verify_cache.py — 8 кейсов (manual→explicit, multi-file, strict-priority, reverse-reject, security-shortcut x2, no-row, red-row). Full pytest 2888 passed (was 2880, +8, 0 regressions). Ruff + mypy clean. CHANGELOG.md + CHANGELOG.ru.md обновлены под Unreleased v1.4.0 polish Phase B Fixed. Bootstrap прогнан — .claude/scripts/verify_cache.py синхронизирован.
- 2026-05-06T18:44:40Z [implementation] — AC verified: 1. ✓ tests/test_verify_cache.py::TestRelaxedAcceptManualToExplicit::test_relaxed_hit_when_strict_misses + test_relaxed_hit_with_multiple_explicit_files — manual files=[] verify-row satisfies has_fresh_verify_run with explicit relevant_files 2. ✓ tests/test_verify_cache.py::TestReverseDirectionRejected::test_explicit_verify_does_not_match_different_explicit_files — explicit verify row with files=['scripts/a.py'] rejected for has_fresh_verify_run with files=['scripts/b.py'] via relaxed path (returns False) 3. ✓ tests/test_verify_cache.py::TestStrictPriorityOverRelaxed::test_strict_hit_returns_strict_row_not_manual — both rows present, strict wins by id; relaxed branch not reached 4. ✓ tests/test_verify_cache.py::TestSecurityShortCircuit (2 cases) — is_cache_allowed=False for src/auth/login.py short-circuits before any DB lookup; relaxed branch never reached 5. ✓ tests/test_verify_cache.py — 8 new test cases all pass (pytest tests/test_verify_cache.py: 8 passed in 0.18s) 6. ✓ Full pytest: 2888 passed, 7 skipped, 120 deselected (was 2880 baseline → +8 new, 0 regressions). Includes test_verify_first_contract.py::test_task_done_bucket_does_not_satisfy_verify_first which initially failed and led to adding the trigger=verify| filter 7. ✓ CHANGELOG.md (### Fixed under [Unreleased] v1.4.0 polish Phase B) + CHANGELOG.ru.md (### Исправлено) entry mentioning gotcha #111, manual→explicit acceptance, reverse-direction reject, cache-bucket separation, security short-circuit, 8 new tests, 2888/2880 baseline
- 2026-05-06T18:51:22Z [implementation] — AC verified: 1. PASS — TestRelaxedAcceptManualToExplicit (2 cases): manual files=[] verify-row satisfies has_fresh_verify_run with explicit relevant_files. 2. PASS — TestReverseDirectionRejected: explicit verify row rejected for different file set via relaxed path. 3. PASS — TestStrictPriorityOverRelaxed: both rows present, strict wins by id. 4. PASS — TestSecurityShortCircuit (2): is_cache_allowed=False short-circuits before DB. 5. PASS — TestBucketSeparationInterleaved: task-done rows do NOT shadow verify row when interleaved (SQL trigger filter). 6. PASS — Full pytest: 2889 passed, 7 skipped, 120 deselected (was 2880 baseline, +9 new, 0 regressions). 7. PASS — CHANGELOG.md + CHANGELOG.ru.md entries under v1.4.0 polish Phase B Fixed mention gotcha #111, all behaviors, 9 new tests, 2889/2880 baseline. Live dogfood: verify recorded files=[] row, task_done with explicit relevant_files now hits relaxed path.
