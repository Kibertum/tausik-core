---
slug: v14-mypy-precommit-fix
title: "Fix pre-existing mypy errors blocking pre-commit (10 errors in 3 files)"
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
completed_at: "2026-05-03T09:58:50Z"
---

## Goal

Pre-commit hook (scripts/hooks/pre-commit) запускает strict mypy — блокирует commit'ы. 10 pre-existing errors из Composer batch: audit_pytest_dedupe.py (8 ast type issues), skill_profile.py (bootstrap_copy import), mcp_tool_counts.py (tools dynamic import). Все trivial fixes через type: ignore + isinstance().

## Acceptance Criteria

1. python -m mypy возвращает 0 errors.
2. scripts/audit_pytest_dedupe.py: добавить isinstance(node, ast.FunctionDef) checks или type: ignore[attr-defined,arg-type] для 8 errors.
3. scripts/skill_profile.py:14: type: ignore[import-not-found] на bootstrap_copy import.
4. scripts/mcp_tool_counts.py:26: type: ignore[import-not-found] на dynamic tools import.
5. Negative: pytest tests/ зелёный (no semantic change в логике).
6. Negative: ruff check всё ещё passes.
relevant_files: scripts/audit_pytest_dedupe.py, scripts/skill_profile.py, scripts/mcp_tool_counts.py

## Plan

## Rollback

## Journal

- 2026-05-03T09:58:50Z [implementation] — AC verified: 1. ✓ mypy: Success: no issues found in 115 source files. 2. ✓ audit_pytest_dedupe.py: добавлены isinstance(node, ast.FunctionDef) checks + type: ignore[arg-type, misc] на строки 121,130,137,138. 3. ✓ skill_profile.py: type: ignore[import-not-found] на bootstrap_copy. 4. ✓ mcp_tool_counts.py: type: ignore на оба dynamic 'import tools'. 5. ✓ ruff: All checks passed. 6. ✓ pytest: NO semantic change (только isinstance + type: ignore comments).
