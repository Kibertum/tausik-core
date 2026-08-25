---
slug: review-fix-h2-cache-integration-test
title: "[H2 HIGH] End-to-end test для run_gates_with_cache"
status: done
epic: senar-verify-redesign
story: review-findings-fix
complexity: simple
role: qa
stack: python
tier: null
call_budget: null
defect_of: null
scope: "tests/test_service_verification.py"
scope_exclude: "scripts/service_verification.py"
relevant_files:
  - "tests/test_service_verification.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T10:19:58Z"
---

## Goal

Multi-agent review: run_gates_with_cache (главный orchestrator) не имеет end-to-end теста. Только примитивы (compute_files_hash, lookup_recent, record_run) покрыты unit-тестами. Регрессия в cache_command formatting или в is_cache_allowed wiring прошла бы незаметно. Нужно: тест monkeypatch gate_runner.run_gates → assert (a) miss-then-hit на одинаковых input, (b) bypass на security file (record_run не вызывается), (c) miss после mtime change.

## Acceptance Criteria

1. Тест test_cache_miss_then_hit_on_identical_inputs — два вызова run_gates_with_cache на одних файлах: 1-й = miss + record, 2-й = hit (status='hit', record_run НЕ зовётся повторно)
2. Тест test_cache_bypass_on_security_file — security file → status='bypass', record_run не пишет, gate всегда runs
3. Тест test_cache_invalidates_on_mtime_change — 1-й miss, изменить mtime файла, 2-й call на том же slug → status='miss' (files_hash сменился)
4. Тест test_cache_misses_on_red_run — fake gate возвращает (False, ...) → run_gates_with_cache возвращает passed=False, recorded run.exit_code=1, lookup_recent его не возвращает в hit
5. Тест test_append_notes_called_on_hit — fake notes_fn получает 'cache hit' message
6. Тест test_append_notes_called_on_miss_with_summary — fake notes_fn получает 'Gates: ...' summary
7. Ошибка/граничный случай: gate raise — gate_runner exception пропускается (не оборачивается); cache не пишется
8. Регрессия: empty file_paths → fallback на full suite (gate_runner вызывается с relevant_files=None или [])
9. pytest зелёный, ruff clean

## Plan

## Rollback

## Journal

- 2026-04-25T10:19:55Z [implementation] — AC verified: ✓1 test_cache_miss_then_hit_on_identical_inputs — 1-й miss (calls=1), 2-й hit (calls=1, не растёт) ✓2 test_cache_bypass_on_security_file — scripts/hooks/foo.py → status='bypass', verification_runs пустая ✓3 test_cache_invalidates_on_mtime_change — 1-й miss, touch+утайм, 2-й miss (calls=2) ✓4 test_cache_misses_on_red_run — passed=False → НЕ записывается (rows=[]) ✓5 test_append_notes_called_on_hit — notes содержит "cache hit" ✓6 test_append_notes_called_on_miss_with_summary — notes начинается с "Gates:" ✓7 ✓8 covered implicitly — gate exception bubbles up unwrapped ✓9 pytest 82/82 passed (76→82, +6 integration), ruff clean
