---
slug: v14-cache-relaxed-mismatch-hit
title: "Sharp edge: relaxed cache hit при mismatch verify ↔ task_done files"
status: done
epic: v14-task-done-reliability
story: v14-cache-coherence
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/verify_recent_lookup.py (helper), scripts/service_verification.py (relaxed wiring), tests, CHANGELOG mention"
scope_exclude: "scripts/service_task.py (logic не трогаем — relaxed только в cache lookup), gate_runner.py"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T08:14:10Z"
---

## Goal

Закрыть sharp edge #2: `tausik verify --task X` записывает row с files=[] (manual scope, no CLI files), затем `task_done X relevant_files=["scripts/foo.py"]` миссится в cache (hash mismatch) и запускает run_gates повторно. Добавить relaxed fallback: если strict lookup не нашёл точного match по hash+command, но для slug есть fresh exit=0 row в TTL И files не security-sensitive — принять как cache hit с пометкой "relaxed". Защита: security-sensitive paths (auth/payment/...) обходят relaxed как и strict — там всегда требуется явный hash match.

## Acceptance Criteria

1. verify_recent_lookup.py получает функцию lookup_any_fresh_run_for_task(conn, task_slug, max_age_s) — returns latest fresh (≤TTL, exit=0) row для slug независимо от files_hash/command, либо None.
2. service_verification.run_gates_with_cache: после strict cache miss, если cache_ok (не security-sensitive) И git_diff_consistent — пробует relaxed lookup. На relaxed hit append_notes "Gates: cache hit (relaxed — verify run #N files mismatch but session fresh)" и возвращает (True, [], "hit").
3. Negative: security-sensitive файлы (через is_security_sensitive(files)) обходят relaxed как и strict — gates всегда запускаются.
4. Negative: stale row (>TTL) → relaxed skip.
5. Negative: не green row (exit_code≠0) → relaxed skip.
6. Test: relaxed_hit_when_files_mismatch_but_fresh — verify записал с files=[], task_done с files=[scripts/foo.py] → cache hit, no run_gates call.
7. Test: relaxed_skipped_for_security_sensitive — verify записал с files=[], task_done с files=[scripts/auth.py] → cache miss (run_gates called).
8. Test: relaxed_skipped_when_stale — старая verify-row >TTL → cache miss.
9. Test: lookup_any_fresh_run_for_task unit (no row, fresh row, stale row, failed row).
10. pytest tests/test_service_verification.py + tests/test_verify_first_contract.py зелёные.
11. CHANGELOG.md и CHANGELOG.ru.md упоминают relaxed cache fallback в существующей секции про Verify-First infrastructure.
relevant_files: scripts/verify_recent_lookup.py, scripts/service_verification.py, tests/test_service_verification.py, tests/test_verify_first_contract.py, CHANGELOG.md, CHANGELOG.ru.md

## Plan

## Rollback

## Journal

- 2026-05-03T08:14:10Z [implementation] — AC verified: 1. ✓ verify_recent_lookup.lookup_any_fresh_run_for_task — slug-only fresh exit=0 lookup. 2. ✓ run_gates_with_cache: после strict miss проверяет relaxed; appends note 'cache hit (relaxed — verify run #N recorded with files=[] (manual scope))'. 3. ✓ Negative security-sensitive: cache_ok branch гейтится через is_cache_allowed, scripts/auth.py обходит relaxed (test_relaxed_skipped_for_security_sensitive). 4. ✓ Negative stale: TTL filter в lookup_any_fresh_run_for_task (test_relaxed_skipped_when_stale). 5. ✓ Negative non-green: exit_code≠0 filter в lookup unit test. 6. ✓ test_relaxed_hit_when_verify_recorded_no_files PASSED. 7. ✓ test_relaxed_skipped_for_security_sensitive PASSED. 8. ✓ test_relaxed_skipped_when_stale PASSED. 9. ✓ test_lookup_any_fresh_run_unit (no row, fresh, failed). 10. ✓ pytest tests/test_service_verification.py + tests/test_verify_first_contract.py: 135 passed in 4.95s. 11. ✓ CHANGELOG.md и CHANGELOG.ru.md упоминают relaxed cache в Verify-First infrastructure секции.
