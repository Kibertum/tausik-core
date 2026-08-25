---
slug: adversarial-review-fixes-ac-evidence-segmentation-
title: "adversarial-review fixes: AC evidence segmentation false-positive + gate verified-bypass + colon body"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/service_ac_evidence.py, scripts/gate_ac_check.py, tests/test_ac_parser_inline.py"
scope_exclude: "backend_migrations_v34.py (separate task), parse_ac_text body-collision (count correct, display-only — out of scope)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T09:28:47Z"
---

## Goal

Adversarial reviewer (tausik-reviewer, separate model) found in this session's AC-parser work: (HIGH-2) _segment_evidence_line segments evidence on ANY two numbered markers with no sequence filter, so prose like 'see 3. tests/x.py ... section 7. output' falsely credits AC-3 with a test-ref — a false POSITIVE that hides missing evidence. (MED) gate_ac_check.verify_ac has_marker accepts a bare 'verified' substring anywhere in notes, bypassing the QG-2 hard gate; my switch to build_report made this the only hard-gate path. (MED) AC_NUMBER_PREFIX_RE omits ':' from its separator class, so 'AC-1: foo' stores body ': foo' with a leading colon. Fix all three + add the missing adversarial tests + minor regex-clarity polish.

## Acceptance Criteria

1. _segment_evidence_line only segments a line when its boundary markers are EITHER all AC-prefixed OR the bare indices are contiguous from 1 — so prose 'see 3. tests/x.py ... 7. output' is processed whole and does NOT credit AC-3 (false-positive killed), while legitimate 'AC-1: ✓..' and bare '1. ✓ 2. ✓ 3. ✓' still segment. 2. gate_ac_check.verify_ac has_marker no longer accepts a bare 'verified' substring: it requires 'ac verified'/'verified ac', a checkmark, OR report.covered>0 — a note like 'git identity verified' with no AC evidence raises the QG-2 ServiceError again. 3. AC_NUMBER_PREFIX_RE separator class includes ':' so 'AC-1: foo' parses body 'foo' (no leading colon). 4. Negative/boundary: bare non-contiguous evidence ('1. ✓ 3. ✓') and prose-number lines do not over-credit; existing partial-coverage and negative-scenario tests stay green. 5. New tests: prose-collision non-credit, verified-bypass now raises, colon-stripped body, content assertions on inline AC-prefix parse. All AC test files green. 6. Regex polish: replace dead '(?<=^)' arm with '(?:^|(?<=[\\s;(]))'. ruff + mypy clean, bootstrap re-run.

## Plan

## Rollback

git revert — changes isolated to the two parser functions + regex

## Journal

- 2026-06-14T09:28:37Z [implementation] — AC verified: AC-1: ✓ _segment_evidence_line now segments only when all boundaries AC-prefixed OR bare indices contiguous-from-1; prose '3. tests/x.py .. 7. output' processed whole, AC-3 not credited — tested via tests/test_ac_parser_inline.py::test_prose_numbers_do_not_falsely_credit_criteria + test_bare_non_contiguous_evidence_not_segmented. AC-2: ✓ has_marker drops bare 'verified', adds report.covered>0; 'git identity verified by CI' raises QG-2 — test_bare_verified_word_does_not_bypass_gate + test_covered_evidence_satisfies_gate_without_verified_word. AC-3: ✓ AC_NUMBER_PREFIX_RE separator now [.):]; 'AC-1: foo' -> body 'foo' no colon — test_single_line_ac_with_ac_prefix asserts. AC-4: ✓ bare non-contiguous not over-credited, negative/partial tests green. AC-5: ✓ 71 AC tests green across 5 files; new tests added. AC-6: ✓ boundary regex polished to (?:^|(?<=[\\s;(])); ruff + mypy clean (198 files), bootstrap re-run. Domain: real-data revalidation unchanged (fix-ac=6/6, v34=7/7, bare=6/6) — hardening killed false positives without dropping true positives.
