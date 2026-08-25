---
slug: brain-registry-stale-lock-recovery
title: "MEDIUM: stale-lock recovery в brain_project_registry"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: "scripts/brain_project_registry.py, tests/test_brain_project_registry.py"
scope_exclude: "scripts/brain_init.py, scripts/brain_config.py"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T09:09:26Z"
---

## Goal

O_EXCL lock без stale recovery: SIGKILL wizard → все будущие init'ы блокируются до manual delete projects.json.lock. Записывать pid+mtime, считать lock &gt;30s или с несуществующим pid как stale

## Acceptance Criteria

1. Добавлена helper _is_stale_lock(lock_path) возвращает True если (a) pid в файле не существует в системе, или (b) mtime файла старше _STALE_LOCK_AGE_S
2. Константа _STALE_LOCK_AGE_S = 30.0 (секунды) вверху модуля
3. _acquire_lock на FileExistsError проверяет _is_stale_lock → если True: unlink + retry O_EXCL (логгирует warning о recovered stale lock)
4. Регрессия: live lock (только что взятый, живой pid) ВСЁ ЕЩЁ вызывает RegistryLockError после timeout — test_register_lock_prevents_concurrent_write продолжает проходить
5. Ошибка/граничный случай: malformed lock file (empty / non-integer pid) — fall back на mtime-check, не crash
6. Ошибка/граничный случай: OSError при чтении lock (permission denied) — log warning, treat as NOT stale (безопасный default)
7. Ошибка/граничный случай: stale-lock delete fails (race с конкурентным процессом, perms) → continue retry loop (не падать)
8. Новые тесты: dead_pid_lock_reclaimed, expired_mtime_lock_reclaimed, live_lock_not_reclaimed, malformed_lock_reclaimed_after_ttl
9. pytest tests/test_brain_project_registry.py проходит; ruff clean

## Plan

## Rollback

## Journal

- 2026-04-24T20:07:11Z [implementation] — AC verified: _STALE_LOCK_AGE_S=30.0 + _pid_alive(pid) (os.kill(pid,0), OS-agnostic: ProcessLookupError→False, PermissionError→True, OSError→False, pid<=0→False) + _is_stale_lock(lock_path) (mtime > threshold, или dead pid, malformed falls back на mtime, read-error→False conservative). _acquire_lock: FileExistsError → if _is_stale_lock: unlink + log warning + retry (ровно 1 раз, reclaimed flag). 7 новых тестов: dead_pid_reclaimed, expired_mtime_reclaimed, live_fresh_not_reclaimed (regression), malformed_reclaimed_after_ttl, malformed_fresh_blocks (boundary), is_stale_lock_missing_returns_false, pid_alive_rejects_nonpositive. pytest 29/29. ruff clean.
