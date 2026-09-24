---
slug: mypy-list-cache-hint-passed-to-listtoolsresult-as
title: "mypy: list cache hint passed to ListToolsResult as typed arguments"
status: done
epic: null
story: null
complexity: null
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "harness/claude/mcp/project/server.py"
  - "tests/test_mcp_list_cache_hint.py"
scope_paths:
  - "harness/claude/mcp/project/server.py"
  - "scripts/mcp_tool_scope.py"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T08:28:56Z"
---

## Goal

Pre-commit mypy passes on harness/claude/mcp/project/server.py: the cache hint reaches ListToolsResult as explicit typed arguments.

## Acceptance Criteria

1. mypy reports no error in server.py. 2. tests/test_mcp_list_cache_hint.py stays green (ttlMs 0, cacheScope private on the wire). 3. Negative: a server that drops the hint still fails that test.

## Plan

## Rollback

## Journal

- 2026-09-24T08:28:33Z [implementation] — AC-1: ✓ python -m mypy: Success, no issues in 483 source files
- 2026-09-24T08:28:34Z [implementation] — AC-2: ✓ tests/test_mcp_list_cache_hint.py::test_a_scope_change_mid_session_is_never_served_from_a_cache
- 2026-09-24T08:28:34Z [implementation] — AC-3: ✓ mutation: hint dropped from model_validate -> tests/test_mcp_list_cache_hint.py::test_a_scope_change_mid_session_is_never_served_from_a_cache red; restored
