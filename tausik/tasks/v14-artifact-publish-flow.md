---
slug: v14-artifact-publish-flow
title: "CLI/MCP: propose → publish артефакта"
status: done
epic: v14-brain-snippets
story: v14-brain-snippets-workflow
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/brain_cli_ops.py"
  - "scripts/brain_mcp_write.py"
  - "scripts/brain_publish_cli.py"
  - "scripts/brain_publish_flow.py"
  - "scripts/brain_store_format.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_parser_ops.py"
  - "tests/test_brain_mcp_write.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T11:39:19Z"
---

## Goal

Поток публикации с аудитом и human gate при высоком риске.

## Acceptance Criteria

1. Черновик publish или MCP draft. 2. Audit-событие при успехе. 3. Negative: high-risk без явного подтверждения возвращает ошибку.

## Plan

## Rollback

## Journal

- 2026-05-01T11:37:53Z [implementation] — AC verified: 1. ✓ MCP brain_draft_artifact + CLI tausik brain draft/publish. 2. ✓ log_brain_event(write, artifact_publish:...) при успешном store patterns/gotchas. 3. ✓ risk_blocked без confirm_high_risk; scrub раньше risk; pytest tests/test_brain_mcp_write.py.
