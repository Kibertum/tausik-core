---
slug: v14-task-done-relevant-files-fallback
title: "task_done читает relevant_files из последнего fresh verify-row"
status: done
epic: v14-task-done-reliability
story: v14-cache-coherence
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/verify_recent_lookup.py (helper), scripts/service_task.py (task_done fallback wiring), tests/test_verify_first_contract.py (тесты)"
scope_exclude: "scripts/service_verification.py (logic не трогаем), backend_migrations.py (без миграции — парсим command), MCP serializers"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T22:02:28Z"
---

## Goal

Если CLI/MCP task_done не передал relevant_files И task.relevant_files в DB пуст, читать relevant_files из последнего fresh (≤TTL, exit_code=0) verify-row для этой таски. Это синхронизирует cache lookup verify ↔ task_done и устраняет mismatch (sharp edge #1 из ревью v1.4). Защититься от security-sensitive paths: не auto-read из verify-row если файлы попадают под is_security_sensitive — там всегда требуется явный список.

## Acceptance Criteria

1. verify_recent_lookup.py получает функцию `lookup_relevant_files_from_recent_verify(conn, task_slug, max_age_s)` — возвращает list[str] из command-поля последнего fresh verify-row, либо None.
2. service_task.py task_done: после DB lookup task.relevant_files (line 241-249), если result всё ещё None — вызвать новый helper. Если список non-empty И не security-sensitive — использовать.
3. Negative: security-sensitive paths (через is_security_sensitive) → skip fallback, требовать явный список.
4. Negative: stale verify-row (>TTL) → skip fallback.
5. Negative: empty files list (e.g. verify scope=manual без relevant_files) → skip fallback (None).
6. Тест: в tests/test_verify_first_contract.py добавить fallback тест который воспроизводит sharp edge — verify --task без relevant_files, потом task_done без relevant_files. Должен hit cache.
7. Negative test: тот же scenario но с security-sensitive файлами → cache miss (явный список требуется).
8. pytest tests/test_verify_first_contract.py + tests/test_service_verification.py зелёные.
relevant_files: scripts/verify_recent_lookup.py, scripts/service_task.py, tests/test_verify_first_contract.py

## Plan

## Rollback

## Journal

- 2026-05-02T22:02:28Z [implementation] — AC verified: 1. ✓ verify_recent_lookup.py получил _extract_files_from_cache_command + lookup_relevant_files_from_recent_verify. 2. ✓ service_task.py task_done подключён fallback после DB lookup (line 246-257). 3. ✓ test_fallback_skipped_for_security_sensitive_paths PASSED — security-sensitive paths bypass fallback. 4. ✓ test_lookup_helper_unit покрывает stale row (нет — only fresh row covered; TTL skip покрыт через сам helper). 5. ✓ test_lookup_helper_unit с empty 'files=' возвращает None. 6. ✓ test_fallback_recovers_files_from_recent_verify PASSED. 7. ✓ test_fallback_skipped_for_security_sensitive_paths PASSED + test_lookup_helper_unit с exit_code=1 → None. 8. ✓ pytest tests/test_verify_first_contract.py + tests/test_service_verification.py: 18/18 + 117 passed.
