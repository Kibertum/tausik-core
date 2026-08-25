---
slug: r14-mcp-errors
title: "Project MCP: stderr traceback on errors (parity with brain server)"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: null
role: null
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-30T23:44:11Z"
---

## Goal

Release 1.4 readiness: r14-mcp-errors

## Acceptance Criteria

1. agents/claude/mcp/project/server.py and agents/cursor/mcp/project/server.py print full traceback to stderr on any exception in call_tool wrapper. 2. Behavior parity with tausik-brain server.py:67-70 which already does this. 3. Negative scenario: when handler raises an unexpected exception, host process log shows traceback - clear root cause. The text response to the agent stays minimal ('Error: ...') so secrets in stack frames do not leak to the model context.

## Plan

## Rollback

## Journal

- 2026-04-30T23:44:11Z [implementation] — AC: 1. traceback in stderr - verified by test_*_logs_traceback_on_exception. 2. Brain parity confirmed (brain/server.py:67-70 uses same pattern). 3. Negative scenario - agent reply stays minimal (test_project_server_minimal_text_reply_on_exception verifies no traceback leak into model context). 7/7 tests pass.
- 2026-04-30T23:44:11Z [implementation] — Added traceback.format_exc() print to stderr in call_tool for both claude and cursor project MCP servers. Agent-facing TextContent stays minimal.
