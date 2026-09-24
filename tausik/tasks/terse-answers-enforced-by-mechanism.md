---
slug: terse-answers-enforced-by-mechanism
title: "Terse answers enforced by mechanism: a Stop-hook check flags a bloated final answer and feeds back the budget"
status: planning
epic: release-110-deferred-from-19
story: release110-terse-answers
complexity: complex
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

Answer brevity stops being a wish in text: a mechanism measures each final answer against a budget and shape, and the agent sees the verdict; effect proven against the measured baseline.

## Acceptance Criteria

1. A hook measures the final answer (words, verdict-first, filler) against a configured budget and feeds a one-line verdict back to the agent when it is exceeded. 2. Budget and rules live in one place, shared by hosts via build_hooks_dict. 3. NEGATIVE: effectiveness is claimed only if a re-measurement shows answers shorter than the terse-answers-measured-first baseline. 4. NEGATIVE: the check never blocks a turn and never rewrites the answer.

## Plan

## Rollback

git revert; the hook is removed from the shared declaration

## Journal
