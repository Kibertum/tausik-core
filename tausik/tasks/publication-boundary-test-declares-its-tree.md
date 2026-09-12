---
slug: publication-boundary-test-declares-its-tree
title: "Property-тест границы публикации обходит дерево, не объявив CROSSCUTTING_SCOPE"
status: done
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: 8
defect_of: unify-the-four-privacy-checks-into-one-publication-boundary
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_publication_boundary.py"
  - "tests/test_crosscutting_registry.py"
scope_paths:
  - "tests/test_publication_boundary.py"
  - "tausik/tasks/publication-boundary-test-declares-its-tree.md"
  - "tausik/stories/release19-proof-integrity.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T15:15:39Z"
---

## Goal

Полный прогон (смена #247): test_crosscutting_registry::test_new_tree_iterator_must_declare_or_optout красный — tests/test_publication_boundary.py обходит scripts/ и harness/ по AST, но не объявляет CROSSCUTTING_SCOPE, и scoped pytest слеп к нему при изменениях в этих деревьях.

## Acceptance Criteria

AC-1: tests/test_publication_boundary.py declares CROSSCUTTING_SCOPE = ['scripts/', 'harness/'] — exactly the trees _modules() walks. AC-2: test_crosscutting_registry.py::TestCrosscuttingVisibility::test_new_tree_iterator_must_declare_or_optout green and the baseline shrink-only rule untouched. AC-3 (negative): resolve_test_files_for_relevant(['docs/en/cli.md']) does not select the boundary test; ['scripts/knowledge_export.py'] does. AC-4: focused pytest + signed verify.

## Plan

## Rollback

git revert одной строки.

## Journal

- 2026-09-12T15:15:01Z [implementation] — Root cause (missing-validation): the new property test walked scripts/ and harness/ without the CROSSCUTTING_SCOPE declaration the registry demands from every tree iterator, so the scoped lane could not select it for changes in those trees; the boundary task's own scoped verify did not map to test_crosscutting_registry. Prevention: the declaration names exactly the two trees the walk reads; the full lane's visibility test caught it the same day.
- 2026-09-12T15:15:02Z [implementation] — AC verified: AC-1 ✓ CROSSCUTTING_SCOPE = ['scripts/', 'harness/'] in tests/test_publication_boundary.py. AC-2 ✓ tests/test_crosscutting_registry.py 22/22 incl. test_new_tree_iterator_must_declare_or_optout and the shrink-only baseline. AC-3 ✓ Negative: resolve_test_files_for_relevant(['docs/en/cli.md']) does not select the file; ['scripts/knowledge_export.py'] does. AC-4 ✓ signed verify below.
