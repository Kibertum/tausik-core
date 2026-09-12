---
slug: scoped-pytest-empty-late-batch
title: "Не считать пустой поздний pytest-batch провалом уже доказанного scoped run"
status: blocked
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: scoped-pytest
scope: "Change only scoped pytest batch aggregation in scripts/gate_command_runner.py, with behavioral tests in tests/test_gate_command_runner.py; update CHANGELOG.md and CHANGELOG.ru.md plus generated task/story state."
scope_exclude: "Do not raise timeouts, widen test selection, weaken scope honesty, turn a wholly empty run green, release, tag, push or modify user-owned .agents/."
relevant_files:
  - "scripts/gate_command_runner.py"
  - "tests/test_gate_command_runner.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/gate_command_runner.py"
  - "tests/test_gate_command_runner.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/tasks/scoped-pytest-empty-late-batch.md"
  - "tausik/tasks/session-rollup-window-attribution.md"
  - "tausik/stories/release19-proof-integrity.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Исправить scoped pytest batching: когда один или несколько ранних batches реально прошли, а поздний batch содержит только deselected tests и pytest возвращает 5, общий run не должен ложно считаться FAIL. При этом run с нулём выполненных tests остаётся non-evidence.

## Acceptance Criteria

AC-1: a sequence with one passing pytest batch followed by exit 5 is PASS and discloses that the late batch collected no tests. AC-2: a first/only exit-5 pytest batch remains COULD_NOT_RUN/non-evidence, never PASS. AC-3: a nonzero failure after a passing batch remains FAIL. AC-4: shellless sequencing, timeout and no-test semantics outside scoped batching remain unchanged. AC-5: focused pytest, ruff, dedupe and signed verify pass.

## Plan

[{"step": "Reproduce the aggregate exit-code path with a passing pytest batch followed by a no-tests-collected batch and capture the current false FAIL.", "done": true}, {"step": "Implement the smallest aggregate semantics that preserves a fail-closed wholly empty run and a real failure.", "done": true}, {"step": "Add behavioral regression tests for pass-plus-empty, empty-only and pass-plus-failure.", "done": true}, {"step": "Run focused quality checks and signed verify; then unblock the affected rollup task only if the receipt is presentable.", "done": false}]

## Rollback

Revert the dedicated commit; retain the existing fail-closed result when no batch executes a test.

## Journal

- 2026-09-12T10:19:15Z [implementation] — Started after reproducing the real run: 55 tests pass in the first scoped batch, then a later all-deselected batch returns pytest exit 5 and incorrectly collapses the aggregate to FAIL. Next: add a direct runner-level red regression before changing aggregate semantics.
- 2026-09-12T10:20:32Z [implementation] — Implemented explicit scoped-pytest batch aggregation: prior passing batches establish evidence; a later exit-5/no-tests batch is disclosed and neutral, while empty-only and real failures remain non-passing. TAUSIK_VERIFY_FULL now reaches every batch. Red regression passed after fix: 11 focused tests plus ruff.
- 2026-09-12T10:22:17Z [implementation] — After batching fix, the real 59-file scoped gate advances past the empty-batch symptom but still fails on two unrelated crosscutting failures: tests/test_hook_encoding.py names test_verify_commit_ownership.py:23 without encoding='utf-8', and tests/test_check_docs_hook.py reports docs/_generated/constants.json drift. A direct crosscutting run reproduced 989 passed, 2 failed. These must not be excluded or attributed to batching.
