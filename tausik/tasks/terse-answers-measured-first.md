---
slug: terse-answers-measured-first
title: "Terse answers: measure answer length and shape on real sessions before any new rule"
status: done
epic: release-110-deferred-from-19
story: release110-terse-answers
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/answer_shape.py"
  - "scripts/project_parser_answers.py"
  - "scripts/project_parser_ops.py"
  - "scripts/project_cli_metrics.py"
  - "tests/test_answer_shape.py"
scope_paths:
  - "scripts/answer_shape.py"
  - "scripts/project_parser_answers.py"
  - "scripts/project_parser_ops.py"
  - "scripts/project_cli_metrics.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T06:54:56Z"
resolution: null
resolution_reason: null
---

## Goal

The 1.9 answer rules (i-have-adhd, response contract) are measured on transcripts: words per final answer, share of answers with a verdict first, filler rate; a baseline number exists before 1.10 changes anything.

## Acceptance Criteria

1. A repeatable script measures final assistant answers in session transcripts: word count, first-line verdict present, list-vs-prose share, filler phrases per answer. 2. Baseline recorded for the last 10 sessions with numbers. 3. NEGATIVE: the script refuses a transcript it cannot parse instead of reporting zeros.

## Plan

## Rollback

measurement only; nothing to revert

## Journal

- 2026-09-24T06:54:04Z [implementation] — AC-1: ✓ tests/test_answer_shape.py::test_the_final_answer_is_the_last_text_before_the_next_prompt — scripts/answer_shape.py (score/measure) + tausik metrics answers [--last N] [--json]; final answer = last assistant text before the next human prompt; words, verdict-first, list share, filler; interim words between tool calls.
- 2026-09-24T06:54:04Z [implementation] — AC-2: ✓ measurement — baseline, last 10 transcripts of this repo (65 answers): final_words_median 396, p90 915, verdict_first 95.4%, list_share_median 0.17, filler 0.08/answer, interim 52 words/turn. Finding: LENGTH is the problem, not filler or a missing verdict.
- 2026-09-24T06:54:04Z [implementation] — AC-3: ✓ tests/test_answer_shape.py::test_a_transcript_without_assistant_text_is_refused_not_zeroed — negative: unparseable transcript -> UnparseableTranscript, listed as SKIPPED, never counted as zero words.
