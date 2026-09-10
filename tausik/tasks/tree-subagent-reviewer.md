---
slug: tree-subagent-reviewer
title: "Объявить предмет tree-итератора subagent reviewer"
status: blocked
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "tests/test_subagent_reviewer.py; tests/test_crosscutting_registry.py; task metadata only"
scope_exclude: "Do not change resolver policy, weaken the visibility registry, alter CI, release metadata, tag, push or publish."
relevant_files:
  - "tests/test_subagent_reviewer.py"
  - "tests/test_crosscutting_registry.py"
scope_paths:
  - "tests/test_subagent_reviewer.py"
  - "tests/test_crosscutting_registry.py"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Устранить красный full-lane дефект: tests/test_subagent_reviewer.py обходится по дереву исходников, но не имеет требуемого CROSSCUTTING_SCOPE или явного opt-out, из-за чего scoped verification не может честно включать его при затронутых файлах.

## Acceptance Criteria

1. Reproduced test_crosscutting_registry::TestCrosscuttingVisibility::test_new_tree_iterator_must_declare_or_optout is green. 2. tests/test_subagent_reviewer.py declares the exact tree it traverses through CROSSCUTTING_SCOPE, or a justified explicit [] only if it guards no tree. 3. The declaration does not widen selection beyond the actual traversal, does not alter the selector, and does not weaken the registry. 4. Negative boundary: a sibling change outside the declared guarded path does not select test_subagent_reviewer. 5. Targeted pytest and ruff are green; signed verify runs before closure.

## Plan

[{"step": "Inspect the tree traversal in test_subagent_reviewer and determine its exact guarded paths.", "done": true}, {"step": "Add the narrow truthful CROSSCUTTING_SCOPE declaration or explicit reviewed opt-out.", "done": true}, {"step": "Run the registry regression, subagent-reviewer tests and ruff.", "done": true}, {"step": "Run signed verify and close only on a certifying receipt.", "done": true}]

## Rollback

git revert the CROSSCUTTING_SCOPE declaration.

## Journal

- 2026-09-10T12:54:35Z [implementation] — Declared the actual subject narrowly: harness/claude/subagents/ and bootstrap/bootstrap_copy.py. Behavior check: changing the canonical reviewer source selects test_subagent_reviewer; scripts/unrelated.py does not. Registry + reviewer tests: 17 passed serially; ruff clean.
- 2026-09-10T12:55:29Z [implementation] — Signed verify #2394 ran real ruff+pytest successfully (11/521 scoped tests, 12.6s), but status=git-mismatch because nine files from other unfinished tasks are dirty and cannot truthfully be declared here. Handle is deliberately not used for closure.
