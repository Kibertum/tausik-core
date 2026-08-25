---
slug: r14-mcp-verify
title: "Align tausik_verify MCP with CLI (optional task, scope, structured output)"
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
completed_at: "2026-05-01T00:25:07Z"
---

## Goal

Release 1.4 readiness: r14-mcp-verify

## Acceptance Criteria

1. tausik_verify accepts optional task_slug (was required) - matches CLI parity. 2. tausik_verify accepts optional scope parameter (was missing). 3. Negative scenario - when neither task_slug nor scope is provided, behavior matches CLI verify with no --task (full-suite empty file scope, scope=manual default). 4. _handle_verify uses public ProjectService.run_verify_for_task method instead of private svc.be._conn (layering fix).

## Plan

## Rollback

## Journal

- 2026-05-01T00:25:07Z [implementation] — AC verified: 1. task_slug optional ✓ (test_tools_extra_schema_says_task_slug_optional). 2. scope+trigger optional ✓ (test_tools_extra_schema_lists_scope_and_trigger). 3. Negative scenario - missing task_slug runs full-suite without DB write ✓ (test_without_task_runs_full_suite_no_db_row). 4. _handle_verify uses public ProjectService.run_verify_for_task ✓ (test_no_be_conn_in_handle_verify_source).
- 2026-05-01T00:25:07Z [implementation] — Implemented: tools_extra schema relaxed (task_slug optional, scope+trigger added with enums); _handle_verify signature accepts kwargs; both claude+cursor MCP synced + .claude mirror updated.
