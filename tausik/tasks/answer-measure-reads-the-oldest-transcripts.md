---
slug: answer-measure-reads-the-oldest-transcripts
title: "The answer measure and its ratchet read the OLDEST ten transcripts, not the last ten"
status: done
epic: release-110-deferred-from-19
story: release110-owner-priorities
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/hooks/transcript_locator.py"
  - "scripts/answer_budget_ratchet.py"
  - "scripts/project_parser_answers.py"
  - "tausik/gates.json"
  - "tests/test_answer_window_is_the_newest.py"
  - "tests/test_answer_budget_ratchet.py"
  - "changelog.d/answer-measure-reads-the-oldest-transcripts.md"
scope_paths:
  - "scripts/"
  - "tests/"
  - "changelog.d/"
  - "tausik/"
  - "tausik/gates.json"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T21:43:07Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Found session #279: project_transcripts() is oldest-first and both metrics answers and answer_budget_ratchet slice [:last]. The window is frozen on the first transcripts: [:10] gives 27 answers p90 1325; [-10:] gives 238 answers p90 453, median 198. Two tasks waited on a measure that could not move.

## Acceptance Criteria

AC-1 metrics answers and the ratchet read the NEWEST N transcripts. AC-2 NEGATIVE: a test with three transcripts of known mtimes fails if the oldest ones are read. AC-3 The baseline is re-measured on the corrected window and the number and its window are logged; it is not raised.

## Plan

## Rollback

git revert

## Journal

- 2026-09-29T21:41:17Z [implementation] — AC-1: ✓ tests/test_answer_window_is_the_newest.py::test_newest_returns_the_last_n_oldest_first; both readers use transcript_locator.newest_project_transcripts. AC-2 Negative: ✓ tests/test_answer_window_is_the_newest.py::test_the_ratchet_reads_the_newest_not_the_oldest. AC-3: ✓ re-measured on newest 10: 238 answers, median 198.0, p90 453 (was 522.5/923 on the oldest window); baseline LOWERED in tausik/gates.json with provenance; tests/test_answer_budget_ratchet.py green.
