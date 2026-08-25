---
slug: r14-mcp-streaming-progress
title: "task_done UX: pre-emit progress estimate (gates count + sum of timeouts) before running"
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
relevant_files:
  - "tests/test_gate_progress_run_start.py"
  - "docs/en/troubleshooting.md"
  - "docs/ru/troubleshooting.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T01:33:40Z"
---

## Goal

Release 1.4: r14-mcp-streaming-progress (from subagent findings)

## Acceptance Criteria

1. gate_runner.run_gates emits new run_start progress event before per-gate iteration with trigger, total gate count, max_seconds (sum of per-gate timeouts), and gate name list. 2. project_cli.cmd_task done case now installs default stderr-progress callback that prints '[gates] Running N gate(s)...' for run_start and '[gates] X/Y name STATUS (Z ms)' for gate_done. 3. TAUSIK_QUIET=1 suppresses progress output. 4. Documented in troubleshooting EN/RU 'Host limits' section. 5. Negative: when no gates configured for trigger, run_start is NOT emitted (run_gates returns early).

## Plan

## Rollback

## Journal

- 2026-05-01T01:33:18Z [implementation] — Docs: docs/{en,ru}/troubleshooting.md 'Host limits & task_done UX' section gained 'Streaming progress (v1.4)' subsection with sample stderr output and TAUSIK_QUIET hint. Mirrored to .claude/.
- 2026-05-01T01:33:18Z [implementation] — Tests: tests/test_gate_progress_run_start.py - run_start payload shape (total/max_seconds/gates list) and absence when no gates. Required local autouse fixture to importlib.reload gate_runner because conftest.py mocks gate_runner.run_gates globally.
- 2026-05-01T01:33:18Z [implementation] — scripts/gate_runner.run_gates: added run_start emit with timeout_sum aggregation. Wrapped in try/except so a misshapen gate dict cannot break the run.
- 2026-05-01T01:33:18Z [implementation] — scripts/project_cli.cmd_task done branch: installed _stderr_progress callback that prints one line per run_start/gate_start/gate_done with elapsed ms. TAUSIK_QUIET=1 short-circuits.
- 2026-05-01T01:33:19Z [implementation] — AC verified: AC-1 ✓ tested via tests/test_gate_progress_run_start.py::test_run_start_event_has_max_seconds. AC-2 ✓ manual review project_cli.py task done branch + _stderr_progress closure. AC-3 ✓ TAUSIK_QUIET branch in _stderr_progress. AC-4 ✓ docs review. AC-5 Negative: tests/test_gate_progress_run_start.py::test_run_start_skipped_when_no_gates.
