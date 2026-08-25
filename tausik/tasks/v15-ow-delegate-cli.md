---
slug: v15-ow-delegate-cli
title: "task delegate — CLI primitive to mark a task for sub-agent delegation"
status: done
epic: v15-orchestrator-worker
story: v15-ow-core
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_cli (delegate handler), scripts/project_parser_task.py (subcommand), DB/state for delegation flag, tests/test_ow_delegate.py, docs/{en,ru}/cli.md"
scope_exclude: "No Agent-tool spawn from CLI; no hook changes (separate task v15-ow-hook-recognize)"
relevant_files:
  - "scripts/service_delegate.py"
  - "scripts/project_service.py"
  - "scripts/project_parser_task.py"
  - "scripts/project_cli_task.py"
  - "tests/test_ow_delegate.py"
  - README.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T20:37:58Z"
---

## Goal

Add `tausik task delegate <slug>` that records a task as delegated to a worker sub-agent: persists delegation intent (delegated flag + recommended model + parent session) so the orchestrator can spawn it and the hook layer can recognize it. Gate: only complexity<=medium tasks are delegable; complex tasks are refused with a clear message (they stay with the Opus coordinator). Stdlib-only, no Agent-tool call from CLI (the CLI marks intent; the orchestrator agent performs the actual spawn).

## Acceptance Criteria

AC1: `tausik task delegate <slug>` on a complexity<=medium task records delegation state (delegated=true, recommended model, parent session id) — verifiable via task show / DB. AC2: delegating a complexity=complex task is REFUSED with exit!=0 and a clear message (stays with coordinator). AC3: delegating an unknown/done task → clear error, no state change. AC4: idempotent — re-delegating an already-delegated task is a no-op-with-notice, not a crash. AC5: tests in tests/test_ow_delegate.py; filesize<400; stdlib-only.

## Plan

## Rollback

git revert the commit; delegation state is additive (a flag column/field) — drop/ignore on revert, no destructive migration.

## Journal

- 2026-06-14T20:37:40Z [implementation] — Implemented `tausik task delegate/undelegate <slug>`. Storage: meta kv (delegation:<slug> → JSON {model,display,parent_session,delegated_at}) — NO schema migration (lite, per #117). service_delegate.DelegateMixin (composed into ProjectService): task_delegate refuses complex (stays with coordinator) + done/unknown, idempotent no-op on re-delegate, recommended model via model_routing_matrix.suggest_model (fallback Sonnet 4.6); task_delegation reads; task_undelegate clears (empty meta). CLI dispatch in project_cli_task + delegated-line in task show. CLI-first (no MCP — avoids doc-count drift). 8 tests; CLI wiring verified (delegate subcommand recognized, reaches service). ruff/mypy clean, files <400.
- 2026-06-14T20:37:57Z [implementation] — AC1: ✓ delegate on complexity<=medium records {model,parent_session,delegated_at} in meta — test_medium_records_delegation, test_simple_is_delegable; verifiable via task show (delegated line) + task_delegation(). AC2: ✓ complex refused with exit!=0/ServiceError, nothing recorded — test_complex_refused + CLI. AC3: ✓ unknown/done task → clear error, no state change — test_unknown_task_refused, test_done_task_refused. AC4: ✓ idempotent re-delegate = no-op notice — test_idempotent_redelegate. AC5: ✓ 8 tests; service_delegate.py 95<400; stdlib-only; CLI wiring verified end-to-end. Domain: orchestrator marks a real medium task delegable; the recorded recommended model + parent session is what the agent passes to the Agent tool spawn. Negative: complex/done/unknown all refused; re-delegate no-ops; undelegate clears + no-ops when absent.
