---
slug: terse-answers-enforced-by-mechanism
title: "Terse answers enforced by mechanism: a Stop-hook check flags a bloated final answer and feeds back the budget"
status: done
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
relevant_files:
  - "scripts/answer_shape.py"
  - "scripts/hooks/user_prompt_submit.py"
  - "tests/test_user_prompt_submit_hook.py"
  - "tests/test_answer_shape.py"
scope_paths:
  - "scripts/answer_shape.py"
  - "scripts/hooks/user_prompt_submit.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T06:57:38Z"
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

Answer brevity stops being a wish in text: a mechanism measures each final answer against a budget and shape, and the agent sees the verdict; effect proven against the measured baseline.

## Acceptance Criteria

1. On every human prompt (UserPromptSubmit, shared by all hosts through build_hooks_dict) the hook scores the PREVIOUS final answer with answer_shape.score and, when it exceeds the budget (config answer_budget_words, default 200) or does not open with a verdict, injects one line naming the numbers and the shape to use. A Stop hook is not used: a blocked Stop swallows the turn's output (keyword-detector-self-trigger-loop). 2. The budget and the rule text live in one place (answer_shape). 3. NEGATIVE: the check never blocks and never rewrites; an answer within budget injects nothing; a missing or unreadable transcript injects nothing. 4. NEGATIVE: effectiveness is claimed only after a re-measurement with tausik metrics answers shows the median below the 396-word baseline; until then the CHANGELOG says 'measured baseline, effect pending'.

## Plan

## Rollback

git revert; the nudge leaves user_prompt_submit

## Journal

- 2026-09-24T06:56:36Z [implementation] — AC-1: ✓ tests/test_user_prompt_submit_hook.py::TestAnswerBudget::test_a_long_answer_is_named_with_its_numbers — user_prompt_submit reads transcript_path from the payload, scores the last assistant text (answer_shape.last_final_answer + budget_nudge), injects '[TAUSIK answer budget] ... N words, budget 200' — hosts share it through build_hooks_dict; config key answer_budget_words.
- 2026-09-24T06:56:37Z [implementation] — AC-2: ✓ review — budget default and rule text live in scripts/answer_shape.py only; docs/*/configuration.md and hooks.md describe them.
- 2026-09-24T06:56:37Z [implementation] — AC-3: ✓ tests/test_user_prompt_submit_hook.py::TestAnswerBudget::test_an_answer_within_budget_injects_nothing and tests/test_user_prompt_submit_hook.py::TestAnswerBudget::test_a_missing_transcript_injects_nothing — negative; mutation (word check disabled) -> 2 failed, 9 passed; restored.
- 2026-09-24T06:56:38Z [implementation] — AC-4: ✓ review — effectiveness NOT claimed: CHANGELOG says 'effect pending a re-measurement against the 396-word baseline'; re-measure with tausik metrics answers before 1.10 ships.
