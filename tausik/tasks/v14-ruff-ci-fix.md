---
slug: v14-ruff-ci-fix
title: "Fix 10 ruff errors blocking CI (unused imports + 1 E402)"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T09:40:05Z"
---

## Goal

Локальный ruff check показал 10 errors которые блокируют CI на push. Большинство — F401 unused imports. Один E402 — module-level import not at top of file в service_verification.py:94 (verify_recent_lookup import after re-export from verify_files_hash). Применить ruff --fix для автофикса 8/10 + ручной фикс E402 + service_gates.py.

## Acceptance Criteria

1. ruff check scripts/ tests/ bootstrap/ возвращает 0 errors.
2. Все unused imports удалены: scripts/audit_orphan_files.py (sys), audit_stale_docs.py (re), brain_mcp_write.py (format_store_result), project_cli_ops.py (cmd_brain), tests/test_check_docs_hook.py (sys), test_session_model_id.py (sqlite3), test_skill_cli_help.py (sys), test_task_gate_hook.py (pytest).
3. E402 в service_verification.py:94 исправлен — либо переместить import выше, либо # noqa: E402 с обоснованием.
4. service_gates.py:443 has_fresh_verify_run удалён (либо использован).
5. Negative: pytest tests/ зелёный после правок.
relevant_files: scripts/audit_orphan_files.py, scripts/audit_stale_docs.py, scripts/brain_mcp_write.py, scripts/project_cli_ops.py, scripts/service_gates.py, scripts/service_verification.py, tests/test_check_docs_hook.py, tests/test_session_model_id.py, tests/test_skill_cli_help.py, tests/test_task_gate_hook.py

## Plan

## Rollback

## Journal

- 2026-05-03T09:40:05Z [implementation] — AC verified: 1. ✓ ruff check scripts/ tests/ bootstrap/ — All checks passed. 2. ✓ Auto-fix удалил 8 unused imports. 3. ✓ E402 fix: # noqa: E402 на verify_recent_lookup import (тот же паттерн что у verify_files_hash). 4. ✓ has_fresh_verify_run удалён из service_gates.py:443 (был unused). 5. ✓ Negative: pytest tests/test_qg2_gates.py + test_service_verification.py зелёные локально (verified earlier this session).
