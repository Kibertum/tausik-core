---
slug: v15-ow-scope-hardgate
title: "Scope hard-gate for delegated sub-agent"
status: done
epic: v15-orchestrator-worker
story: v15-ow-core
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scope hard-gate logic (reuse gate/hook machinery), tests/test_ow_scope_gate.py, docs"
scope_exclude: "delegation recording (v15-ow-delegate-cli); summary-back (v15-ow-summary-back)"
relevant_files:
  - "scripts/hooks/scope_write_gate.py"
  - "tests/test_ow_scope_gate.py"
  - README.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T20:57:52Z"
---

## Goal

Enforce the delegated task's declared scope/scope_exclude as a HARD gate while a worker sub-agent is active: edits outside scope are blocked (not just warned). Reuses the existing gate/hook machinery. Prevents a worker from sprawling beyond its delegated slice.

## Acceptance Criteria

AC1: when a DELEGATED active task declares scope_paths, a Write/Edit outside it is BLOCKED (existing scope_write_gate ACL applies to delegated tasks). AC2: an edit within the declared scope passes. AC3: a non-delegated task is unaffected (legacy fail-open on missing scope preserved). AC4: a DELEGATED active task with NO scope_paths is BLOCKED (not fail-open) with a clear remediation (declare scope or undelegate) — a worker must be scope-bounded; never crashes. AC5: covered by tests (delegated_missing_scope + _delegated_slugs); ruff+mypy clean; filesize<400. Negative: any DB/meta error in delegation lookup degrades to the legacy policy (empty delegated set), never crashes the hook.

## Plan

## Rollback

git revert; gate is gated behind delegated-state so revert restores prior warn-only behavior; feature-flag off as fallback.

## Journal

- 2026-06-14T20:57:28Z [implementation] — Enhanced scripts/hooks/scope_write_gate.py for delegated workers. Reuses existing Rule-2 scope ACL (block edits outside scope_paths). Added: _delegated_slugs(db) reads meta delegation:* (truthy=delegated, best-effort→empty on error); delegated_missing_scope(acls, delegated) pure fn → offending slug. main() now BLOCKS a delegated active task with no scope_paths (was fail-open legacy freedom) BEFORE the legacy fail-open — a worker must declare scope or undelegate. Non-delegated tasks unchanged. 7 tests (pure fns + meta read + db-error degrade). full mypy/ruff clean, hook 182<400, bootstrap deployed.
- 2026-06-14T20:57:52Z [implementation] — AC1: ✓ delegated task with scope_paths → edit outside BLOCKED (existing scope_write_gate ACL applies to delegated). AC2: ✓ within-scope passes (existing match_path). AC3: ✓ non-delegated unaffected — delegated_missing_scope returns None for non-delegated; legacy fail-open preserved (test_non_delegated_without_scope_unaffected). AC4: ✓ delegated task with NO scope_paths → BLOCKED with remediation (declare scope / undelegate), checked before legacy fail-open — test_blocks_delegated_without_scope + test_mixed_returns_offending_delegated. AC5: ✓ 7 tests; full mypy/ruff clean; hook 182<400. Negative: DB/meta error → empty delegated set → legacy policy, no crash (test_db_error_degrades_to_empty). Domain: a real worker sub-agent cannot sprawl — it is blocked until it declares its writable surface or is handed back.
