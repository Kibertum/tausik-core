---
slug: pytest-gate-drops-the-failing-test-names
title: "The pytest gate prints '=== FAILURES ===' and drops the names of the failing tests — a red verify does not say what is red"
status: planning
epic: release-110-deferred-from-19
story: release110-verification-is-cheap
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Measured three times in session #263: a scoped verify came back '[FAIL] pytest (block)' followed by the '=== FAILURES ===' banner and nothing else — the gate runner truncates the pytest output to a handful of lines and the short summary with the FAILED names is cut off. The agent found the red tests only by reproducing the selection through gate_command_runner.resolve_test_files_for_relevant and running pytest by hand; a user without that trick reruns the full lane, which is the pattern decision #371 forbids. Fix: the pytest gate always carries the 'short test summary info' block (the FAILED/ERROR lines) into the gate output and the verify report, whatever the truncation limit does to the rest; the same for the slow-only case — a scoped run that selects no test because every file is slow-marked says so and names TAUSIK_VERIFY_FULL=1 instead of CANNOT-RUN.

## Acceptance Criteria

## Plan

## Rollback

git revert; output shaping only

## Journal
