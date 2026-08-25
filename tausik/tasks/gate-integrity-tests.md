---
slug: gate-integrity-tests
title: "Behavioral tests for gate_test_citation.py + gate_tdd_order.py"
status: done
epic: null
story: null
complexity: medium
role: qa
stack: null
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_gate_test_citation.py"
  - "tests/test_gate_tdd_order.py"
scope_paths:
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: "2026-07-27T12:46:38Z"
---

## Goal

Close the highest process-integrity coverage hole: gate_test_citation.py (Rule 5, anti-fabrication — decides whether a claimed test citation resolves to a real test) and gate_tdd_order.py (72L) are registered but have zero behavioral tests. Add tests that would catch a regression accepting a citation to a non-existent test / an inverted TDD-order verdict.

## Acceptance Criteria

1. gate_test_citation: a citation to a REAL test file+function resolves True; a citation to a NON-EXISTENT file resolves False (fail-closed) — a regression accepting an invented file reddens. 2. gate_test_citation anti-fabrication: an invented `::test_name` on a REAL file → False; a real `file::Class::method` node id and a parameterised `::test_x[case]` → True; path traversal `tests/../scripts/x.py` and a bare basename resolvable only inside tests/ → correct verdict (escape=False, in-tree basename=True). 3. gate_tdd_order: source changed without a test → (False, msg); source + test → (True); only non-code / empty file list → skipped (True) — an inverted verdict reddens. 4. gate_tdd_order pattern coverage: each _TEST_PATTERNS family recognised (test_, _test., .test., .spec., FooTest, tests/, __tests__/) + Windows backslash paths normalised + a code-ext file under tests/ counts as test. 5. Tests are behavioral (exercise the real functions against a tmp project tree, no mocking the unit under test) in tests/test_gate_test_citation.py + tests/test_gate_tdd_order.py. 6. Full scoped verify green; ruff + mypy clean.

## Plan

## Rollback

git revert — tests-only change, no production code touched; deleting the two new test files restores the prior state. Zero runtime risk (adds coverage, changes no behavior).

## Journal

- 2026-07-27T12:46:36Z [implementation] — AC verified: 1. ✓ tests/test_gate_test_citation.py::TestRefResolution::{test_real_file_and_function_resolves,test_nonexistent_file_fails_closed,test_file_only_citation_is_accepted,test_empty_path_fails_closed} — real→True, invented/nonexistent file→False (fail-closed). 2. ✓ TestAntiFabrication::{test_invented_function_on_real_file_fails,test_class_method_node_id_resolves,test_invented_method_under_real_class_fails,test_parameterised_id_strips_bracket,test_async_test_is_recognised,test_dotdot_traversal_out_of_tree_fails,test_bare_basename_resolves_only_inside_tests} — all four documented escapes pinned. 3. ✓ tests/test_gate_tdd_order.py::TestVerdict::{test_source_without_test_blocks(False),test_source_with_test_passes(True),test_only_non_code_files_skips,test_empty_file_list_skips,test_test_file_alone_is_not_source} — inverted verdict on any branch reddens. 4. ✓ TestPatternRecognition: parametrized over all 8 _TEST_PATTERNS families + test_windows_backslash_paths_normalised + test_code_ext_file_under_tests_dir_counts_as_test + test_non_code_extension_is_ignored_entirely. 5. ✓ Behavioral: tests call the real run_tdd_order_gate / _test_ref_exists / _named_test_defined / _project_root against a tmp_path project tree; no mocking of the unit under test. Files: tests/test_gate_test_citation.py, tests/test_gate_tdd_order.py. 6. ✓ tausik verify --task standard: pytest PASS scoped over the 2 files (31 tests). ruff clean on both. No production code changed (tests-only), no mypy target added.
