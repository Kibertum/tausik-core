---
slug: r14-mcp-verify-private-attr
title: "MCP _handle_verify: stop using svc.be._conn (use service method, fix layering)"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: medium
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
completed_at: "2026-05-01T00:25:08Z"
---

## Goal

Release 1.4 readiness: r14-mcp-verify-private-attr

## Acceptance Criteria

1. ProjectService gains run_verify_for_task(slug, relevant_files, scope, trigger) public method that wraps run_gates_with_cache. 2. _handle_verify in MCP handlers no longer touches svc.be._conn. 3. Negative scenario - if service-side method raises ServiceError (task not found, etc), MCP returns Error: ... cleanly without leaking private internals.

## Plan

## Rollback

## Journal

- 2026-05-01T00:25:08Z [implementation] — AC verified: 1. ProjectService.run_verify_for_task added ✓ (test_with_task_returns_structured_dict). 2. _handle_verify no svc.be._conn ✓ (test_no_be_conn_in_handle_verify_source for both IDEs). 3. Negative scenario - ServiceError on unknown task → MCP returns clean Error: ✓ (test_unknown_task_raises_service_error).
- 2026-05-01T00:25:08Z [implementation] — Implemented: GatesMixin.run_verify_for_task public method (service_gates.py:80-130) wraps run_gates_with_cache. Both claude+cursor MCP _handle_verify rewritten to use svc.run_verify_for_task instead of svc.be._conn. Static test_no_be_conn_in_handle_verify_source enforces no regression.
