---
slug: terse-answers-measured-first
title: "Terse answers: measure answer length and shape on real sessions before any new rule"
status: planning
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
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

The 1.9 answer rules (i-have-adhd, response contract) are measured on transcripts: words per final answer, share of answers with a verdict first, filler rate; a baseline number exists before 1.10 changes anything.

## Acceptance Criteria

1. A repeatable script measures final assistant answers in session transcripts: word count, first-line verdict present, list-vs-prose share, filler phrases per answer. 2. Baseline recorded for the last 10 sessions with numbers. 3. NEGATIVE: the script refuses a transcript it cannot parse instead of reporting zeros.

## Plan

## Rollback

measurement only; nothing to revert

## Journal
