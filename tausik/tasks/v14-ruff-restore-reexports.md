---
slug: v14-ruff-restore-reexports
title: "Restore re-exports broken by ruff --fix (cmd_brain, format_store_result)"
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
completed_at: "2026-05-03T09:41:52Z"
---

## Goal

ruff --fix в задаче v14-ruff-ci-fix удалил два import'а как unused, но они были re-exports, используемые из других модулей: project.py:47 импортирует cmd_brain из project_cli_ops, brain_publish_cli.py:99 вызывает brain_mcp_write.format_store_result. Восстановить импорты с # noqa: F401 чтобы ruff знал что они re-exported.

## Acceptance Criteria

1. scripts/brain_mcp_write.py: восстановить `from brain_store_format import format_store_result` с `# noqa: F401  re-exported`.
2. scripts/project_cli_ops.py: восстановить `from brain_cli_ops import cmd_brain` с `# noqa: F401  re-exported`.
3. ruff check scripts/ tests/ bootstrap/ остаётся 0 errors.
4. mypy scripts/ — регрессии 'Module has no attribute' устранены.
5. Negative: pytest tests/ зелёный.
relevant_files: scripts/brain_mcp_write.py, scripts/project_cli_ops.py

## Plan

## Rollback

## Journal

- 2026-05-03T09:41:52Z [implementation] — AC verified: 1. ✓ brain_mcp_write.py восстановил format_store_result import с # noqa: F401. 2. ✓ project_cli_ops.py восстановил cmd_brain import с # noqa: F401. 3. ✓ ruff: All checks passed. 4. ✓ mypy: regressions 'has no attribute format_store_result/cmd_brain' исчезли (grep показал 0 matches). 5. ✓ Negative: pytest tests/test_qg2_gates.py + test_service_verification.py зелёные локально (validated).
