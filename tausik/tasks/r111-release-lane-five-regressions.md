---
slug: r111-release-lane-five-regressions
title: "1.11 release lane: resolve five full-suite regressions"
status: done
epic: release-111-economy-draft
story: release111-release-proof
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_codex_write_gate.py"
  - "tests/test_usage_codex.py"
  - "scripts/usage_observation.py"
  - "scripts/enforcement_evidence.py"
  - "scripts/service_token_metrics.py"
  - "scripts/project_cli_task.py"
  - "tausik/gates.json"
  - "tests/test_subagent_model_hints.py"
  - "harness/claude/mcp/project/handlers_status.py"
  - "harness/claude/mcp/project/tools.py"
  - "scripts/default_gates.py"
  - "scripts/gate_stack_dispatch.py"
  - "scripts/render_verify.py"
  - "scripts/verify_prepare.py"
  - "tests/test_verify_prepare.py"
  - "changelog.d/verify-prepare-python-only-111.md"
  - "docs/ru/research/release111-economy-results.md"
scope_paths:
  - "tests/test_codex_write_gate.py"
  - "tests/test_usage_codex.py"
  - "scripts/usage_observation.py"
  - "scripts/enforcement_evidence.py"
  - "scripts/service_token_metrics.py"
  - "scripts/project_cli_task.py"
  - "tausik/gates.json"
  - "tests/test_subagent_model_hints.py"
  - "harness/claude/mcp/project/handlers_status.py"
  - "harness/claude/mcp/project/tools.py"
  - "scripts/default_gates.py"
  - "scripts/gate_stack_dispatch.py"
  - "scripts/render_verify.py"
  - "scripts/verify_prepare.py"
  - "tests/test_verify_prepare.py"
  - "changelog.d/verify-prepare-python-only-111.md"
  - "docs/ru/research/release111-economy-results.md"
scope_tools: []
depends_on: []
completed_at: "2026-10-01T20:23:01Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Make the current 1.11 tree pass the full non-slow pytest lane without weakening the five failing contracts.

## Acceptance Criteria

AC-1 DDL fixtures use canonical schema and hook behavior remains covered. AC-2 mypy reports zero errors in the declared tree. AC-3 formatted legacy ratchet only shrinks and cross-host model-route test matches the approved routing contract. AC-4 Negative: no test, type check, or gate is disabled; full non-slow pytest passes.

## Plan

[{"step": "Replace handwritten DDL fixtures with canonical schema", "done": true}, {"step": "Fix the four mypy source errors without ignores", "done": true}, {"step": "Shrink format ratchet and align the stale routing assertion", "done": true}, {"step": "Run focused checks and the full non-slow lane", "done": true}]

## Rollback

Revert only the bounded fixture, typing, ratchet and routing-test corrections; retain the failing full-suite evidence.

## Journal

- 2026-10-01T20:08:12Z [implementation] — Focused release lane isolated remaining failures: canonical task fixtures need required timestamps; cmd_task package branches can keep the existing None-returning contract because dispatcher ignores results; format ratchet exposed six additional changed files and scope was widened before formatting.
- 2026-10-01T20:09:04Z [implementation] — Focused validation green: 110 passed; mypy reports zero issues across 540 source files; ruff check green; six current-tree format divergences were formatted and the legacy list now only shrinks.
- 2026-10-01T20:10:55Z [implementation] — Root cause of verify #3299: verify preparation passed non-Python task scope to ruff format; gates.json was rewritten with trailing commas, so baseline readers correctly refused. Restored JSON mechanically, constrained formatter preparation to .py/.pyi, and added negative coverage. 62 preparation/ratchet tests pass.
- 2026-10-01T20:19:22Z [implementation] — AC-4 release lanes green without disabling checks: default 12733 passed, 35 skipped, 143 deselected in 153.19s; separate slow lane 143 passed, 12768 deselected in 126.23s. Evidence logs stored under .tausik/planning/release-111/. Release report records engineering readiness and economic HOLD.
- 2026-10-01T20:22:46Z [implementation] — AC-1 PASS: canonical DDL fixtures plus 110 focused tests. AC-2 PASS: mypy zero issues across 540 source files. AC-3 PASS: format ratchet shrank and cross-host route assertion passed. AC-4 PASS: default lane 12733 passed, 35 skipped, 143 deselected; separate slow lane 143 passed; scoped verify #3302 green. Negative PASS: no gate, type check, or test was disabled.
- 2026-10-01T20:23:01Z [implementation] — AC-1 PASS: canonical DDL fixtures plus 110 focused tests. AC-2 PASS: mypy zero issues across 540 source files. AC-3 PASS: format ratchet shrank and cross-host route assertion passed. AC-4 PASS: default lane 12733 passed, 35 skipped, 143 deselected; separate slow lane 143 passed; scoped verify #3302 green. Negative PASS: no gate, type check, or test was disabled.
- 2026-10-01T20:23:12Z [done] — AC-1: ✓ tests/test_ddl_fixture_parity.py plus tests/test_codex_write_gate.py and tests/test_usage_codex.py; canonical schema and hook behavior pass. AC-2: ✓ python -m mypy; zero issues in 540 source files. AC-3: ✓ tests/test_gate_ruff_format.py plus tests/test_subagent_model_hints.py; ratchet and route contract pass. AC-4: ✓ default pytest 12733 passed with 143 slow deselected; ✓ separate slow lane 143 passed. Domain: real task-scoped verify #3302 passed 68 of 650 mapped test files and both release lanes exercised all collected default and slow tests; gates.json remained valid JSON after preparation. Negative: no test, gate, or type check disabled; hadolint remained explicitly skipped and is not claimed.
