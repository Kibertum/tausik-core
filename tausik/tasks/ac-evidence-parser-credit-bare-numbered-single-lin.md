---
slug: ac-evidence-parser-credit-bare-numbered-single-lin
title: "AC evidence parser: credit bare-numbered single-line markers (1. ✓ 2. ✓)"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: fix-ac-evidence-parser-inline-numbered-single-line
scope: "scripts/service_ac_evidence.py (parse_evidence_lines + helper), tests/"
scope_exclude: "parse_ac_text (already fixed), gate_ac_check, AC storage format"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T09:16:31Z"
---

## Goal

Follow-up to fix-ac-evidence-parser-inline-numbered: parse_evidence_lines credits the canonical 'AC-N: ✓' inline format but NOT bare 'N. ✓' markers when several sit on ONE line (the natural shape of a one-line `task log` evidence entry) — proven: bare single-line evidence -> covered 0/3, canonical -> 3/3. Make parse_evidence_lines segment a line on AC_ITEM_BOUNDARY_RE and assign checkmark/test-ref signals PER SEGMENT, so both 'AC-N:' and bare 'N.' single-line evidence are credited, and per-segment checkmarking is more accurate than today's line-level over-credit.

## Acceptance Criteria

1. parse_evidence_lines segments a single line containing >=2 AC_ITEM_BOUNDARY_RE markers into per-marker segments; each segment yields its own EvidenceLine with ac_index from the segment's leading marker and checkmark/test_refs/manual/negative/domain computed within that segment. 2. Bare single-line evidence 'AC verified: 1. ✓ a. 2. ✓ b. 3. ✓ c.' -> build_report covered==3/3 (was 0/3); canonical 'AC-N: ✓' single-line still 3/3. 3. Per-segment accuracy: a line where only AC-2 carries ✓ credits ONLY criterion 2 (not 1 and 3) — no line-level over-credit. 4. Negative/boundary: a line with <2 boundary markers is processed whole (unchanged); inline 'AC-2' without a separator (e.g. 'checked AC-2 via tests') still detected via the existing inline path; prose numbers in a segment without a checkmark do NOT falsely credit. 5. All existing AC tests stay green (test_ac_evidence, test_qg2_gates, test_ac_parser_inline, test_domain_challenge); new tests cover bare single-line + per-segment selectivity. 6. ruff + mypy clean, bootstrap re-run.

## Plan

## Rollback

git revert — change isolated to parse_evidence_lines + new helper

## Journal

- 2026-06-14T09:15:58Z [implementation] — Root cause (category=incomplete-fix): parse_evidence_lines extracted ac_index only from a line-start 'N.' prefix or an inline 'AC-N' token, and computed checkmark at LINE level — so several bare 'N. ✓' markers packed on ONE line (the natural one-line task-log shape) were collapsed to a single index-less unit -> covered 0/N. Fix: _segment_evidence_line splits a line on AC_ITEM_BOUNDARY_RE (>=2 markers) and _evidence_lines_for_unit computes signals PER SEGMENT. Prevention: when a parser must read agent-authored evidence, test it against the literal one-line shape `task log` produces, not just the idealized multi-line form.
- 2026-06-14T09:16:06Z [implementation] — AC verified: AC-1: ✓ parse_evidence_lines segments line on AC_ITEM_BOUNDARY_RE, per-segment signals — tested via tests/test_ac_parser_inline.py::test_bare_numbered_single_line_evidence_credited. AC-2: ✓ bare single-line 'AC verified: 1. ✓ .. 2. ✓ .. 3. ✓' -> covered 3/3, canonical still 3/3 — test_bare_numbered_single_line_evidence_credited + test_canonical_inline_still_works_after_segmentation. AC-3: ✓ per-segment selectivity: only AC-2 with ✓ credits criterion 2, gaps=[1,3] — test_segment_checkmark_is_per_segment_not_line_level. AC-4: ✓ Negative/boundary: <2 markers processed whole, 'checked AC-2 via tests' still detected, prose number without ✓ not credited — existing test_inline_ac_reference_matches + test_parse_evidence_negative_scenario stay green. AC-5: ✓ 67 AC tests green across 5 files. AC-6: ✓ ruff + mypy clean, bootstrap re-run. Domain: validated on 3 REAL closed tasks — fix-ac-evidence(bare)=6/6, v34=7/7, mypy=6/6, all 0 bogus warnings.
