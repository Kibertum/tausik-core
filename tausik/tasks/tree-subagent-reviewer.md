---
slug: tree-subagent-reviewer
title: "Объявить предмет tree-итератора subagent reviewer"
status: done
epic: release-19-renar-conformance
story: release19-proof-integrity
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
completed_at: "2026-09-12T12:22:36Z"
resolution: null
resolution_reason: null
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
- 2026-09-12T12:22:03Z [implementation] — AC verified: AC-1 ✓ test_new_tree_iterator_must_declare_or_optout green. AC-2 ✓ CROSSCUTTING_SCOPE = [harness/claude/subagents/, bootstrap/bootstrap_copy.py] — exactly the tree os.listdir walks at line 164 and the copier it exercises. AC-3 ✓ selector and registry untouched (git log shows only tests/test_subagent_reviewer.py in 173f0249). AC-4 ✓ Negative: resolve_test_files_for_relevant([scripts/render_memory.py]) does not select test_subagent_reviewer; [harness/claude/subagents/tausik-reviewer.md] does. AC-5 ✓ 11/11 targeted, ruff clean, signed verify below. Domain: a change to a subagent Markdown now pulls the reviewer-deployment test into the scoped lane instead of only the full lane.
- 2026-09-12T12:22:03Z [implementation] — Unblocked: the nine uncommitted sibling paths that made receipt #2394 git-mismatch are all committed now (52097532…15f61052) and the tiered ownership resolver (42a87f8d) attributes committed sibling work; nothing in this task's scope changed.
