---
slug: fix-ac-evidence-parser-inline-numbered-single-line
title: "fix AC-evidence parser: inline-numbered single-line AC undercounts criteria and markers"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/service_ac_evidence.py, scripts/gate_ac_check.py, tests/ (new test file)"
scope_exclude: "acceptance_criteria storage format (do not migrate stored AC); other gate logic"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T09:11:14Z"
---

## Goal

DOGFOODING defect hitting every task closure: acceptance_criteria is stored as a SINGLE line ('1. ... 2. ... N.'), so the line-anchored parsers in service_ac_evidence.parse_ac_text and gate_ac_check.verify_ac see only 1 item, and the marker regex r'\d+[.)].*✓' fails to recognise the canonical 'AC-N: ✓' format — producing the bogus 'N AC criteria, but only 0 have explicit evidence markers (✓)' warning on correctly-evidenced closes. Confirmed across 40 real tasks (all nl=0, old parser=1). Make parsing inline-aware: split single-line AC on the 1..N item boundaries (run-anchored to ignore stray numbers like 138/0/3.11), and count evidence via the structured build_report so 'AC-N: ✓' markers are credited.

## Acceptance Criteria

1. service_ac_evidence.parse_ac_text splits a single-line AC ('1. foo 2. bar 3. baz') into 3 item bodies via an inline run-anchored splitter, while multi-line AC keeps its existing line-based parse (>=2 items short-circuits before inline). 2. Run-anchoring: only boundaries continuing the sequence 1,2,3,... are honored, so stray numbers (Decision #138, 'returns 0', 'Python 3.11', 'v1.4') do NOT inflate the count or mis-split an item — asserted by tests using such strings. 3. gate_ac_check.verify_ac reports total_ac = real criteria count and counts 'AC-N: ✓' markers via build_report (covered==total when every criterion carries a ✓), so the spurious 'N AC criteria, but only 0 markers' warning disappears for well-formed single-line evidence. 4. Negative/boundary: empty AC -> []; free-prose AC with no numbered items -> splitlines fallback (no crash, no mis-split); AC with a single genuine criterion -> 1 item (inline not triggered). 5. Existing tests for service_ac_evidence + gate_ac_check stay green; new tests cover single-line multi-item AC parse + inline 'AC-N: ✓' marker counting + stray-number resistance. 6. ruff + mypy clean, bootstrap re-run.

## Plan

## Rollback

git revert — parser change is isolated to parse_ac_text + verify_ac

## Journal

- 2026-06-14T09:09:30Z [implementation] — AC verified: 1. ✓ parse_ac_text splits single-line '1. .. 2. .. 3. ..' into 3 items, multiline unchanged — tested via tests/test_ac_parser_inline.py::test_single_line_ac_splits_into_items + test_multiline_ac_unchanged. 2. ✓ run-anchored: Decision #138 / 'returns 0' / Python 3.11 / v1.4 don't inflate count — tested via test_stray_high_number_ignored + test_leading_zero_and_decimals_ignored. 3. ✓ verify_ac via build_report credits 'AC-N: ✓' markers, covered==total, no spurious warning — tested via test_inline_markers_full_coverage_no_warning + partial warns. 4. ✓ Negative/boundary: empty AC -> [], free prose -> splitlines fallback, single criterion -> 1 item — tested via test_empty_ac_returns_empty + test_free_prose_falls_back_to_splitlines + test_single_genuine_criterion_stays_one_item. 5. ✓ existing AC tests green (64 passed across test_ac_evidence/test_qg2_gates/test_domain_challenge/test_ac_evidence_json). 6. ✓ ruff + mypy clean, bootstrap re-run. Domain: validated on REAL closed-task data — test-v34 now items=7 covered=7 warnings=0 (was bogus '1 criteria/0 markers'), mypy-task 6/6 — the parser counts what a human reads.
- 2026-06-14T09:11:09Z [implementation] — AC verified: 1. ✓ parse_ac_text splits single-line into N items, multiline unchanged — tests/test_ac_parser_inline.py::test_single_line_ac_splits_into_items + test_multiline_ac_unchanged. 2. ✓ run-anchored ignores stray numbers (#138, returns 0, Python 3.11, v1.4) — test_stray_high_number_ignored + test_leading_zero_and_decimals_ignored. 3. ✓ verify_ac via build_report credits 'AC-N: ✓', covered==total, no spurious warning — test_inline_markers_full_coverage_no_warning + test_inline_markers_partial_coverage_warns. 4. ✓ Negative/boundary: empty AC -> [], free prose -> splitlines, single criterion -> 1 item — test_empty_ac_returns_empty + test_free_prose_falls_back_to_splitlines + test_single_genuine_criterion_stays_one_item. 5. ✓ 64 existing AC tests green (test_ac_evidence/test_qg2_gates/test_domain_challenge/test_ac_evidence_json). 6. ✓ ruff + mypy clean, bootstrap re-run. Domain: validated on real closed-task data — v34 items=7 covered=7 warnings=0 (was bogus 1/0), mypy-task 6/6.
