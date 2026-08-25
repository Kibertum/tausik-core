---
slug: sm-4-stack-diff-mcp
title: "MCP: tausik_stack_diff — unified diff builtin vs user override"
status: done
epic: v13-mcp-and-discipline
story: stacks-mcp
complexity: null
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T01:02:36Z"
---

## Goal

MCP tool wrapping existing CLI `tausik stack diff <name>`. Returns unified diff text between built-in and user-customized stack.json.

## Acceptance Criteria

MCP tool wired in agents/{claude,cursor}/mcp/project/{tools_extra.py,handlers.py}; CLI parity in project_cli_stack.py if applicable; tested via test_service_stack_ops.py. NEGATIVE: graceful errors for unknown stack / malformed JSON / overwrite without force.

## Plan

## Rollback

## Journal

- 2026-04-26T01:02:08Z [implementation] — AC: tausik_stack_diff returns unified diff between built-in and user override ✓ NEGATIVE: missing user override → empty diff with has_user=false flag ✓
- 2026-04-26T01:02:36Z [implementation] — AC verified: tausik_stack_diff returns unified diff + has_user/has_builtin flags ✓ missing override → empty diff ✓
