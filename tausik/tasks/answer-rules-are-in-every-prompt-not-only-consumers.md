---
slug: answer-rules-are-in-every-prompt-not-only-consumers
title: "Answer rules reach consumers but not this repo, and the hook speaks only after a long answer"
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
  - "scripts/answer_shape.py"
  - "scripts/hooks/user_prompt_submit.py"
  - "tests/test_answer_rules_every_prompt.py"
  - "tests/test_user_prompt_submit_hook.py"
  - CLAUDE.md
scope_paths:
  - CLAUDE.md
  - AGENTS.md
  - "scripts/"
  - "harness/"
  - "tests/"
  - "docs/"
  - "changelog.d/"
  - "bootstrap/"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T22:44:58Z"
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

Owner, session #279: the ADHD answer rules are still not applied. Cause measured: ANSWER_SHAPE (776 chars) ships only into generated consumer CLAUDE.md; this repo's CLAUDE.md carries one line. The UserPromptSubmit hook speaks only AFTER an over-budget answer. Rules must be in front of the agent before every answer.

## Acceptance Criteria

AC-1 This repo's CLAUDE.md carries the ANSWER_SHAPE rules. AC-2 UserPromptSubmit injects the rules on every human prompt, before the answer, not only after an over-budget one. AC-3 NEGATIVE: a test fails if the injected text drifts from ANSWER_SHAPE. AC-4 MOVED to answer-rules-remeasured-after-three-sessions (1.11): the re-measure needs three sessions.

## Plan

## Rollback

git revert

## Journal

- 2026-09-29T21:14:15Z [implementation] — NO-DEAD-END: heredoc ate the backslash in \n (known shared gotcha), fixed by Edit. AC-1: ✓ tests/test_answer_rules_every_prompt.py::test_this_repository_s_own_rules_file_carries_them. AC-2: ✓ ::test_the_hook_injects_the_rules_on_a_prompt_with_no_prior_answer. AC-3: ✓ ::test_the_injected_rules_are_the_shipped_rules_byte_for_byte. AC-4: pending, re-measure after 3 sessions.
- 2026-09-29T22:43:53Z [implementation] — AC-4 split out to answer-rules-remeasured-after-three-sessions. Evidence for AC-1..3 logged earlier (tests/test_answer_rules_every_prompt.py); CLAUDE.md trimmed to stay under its 4096B static cap (tests/test_claude_md_size.py green); hook tests updated to the new always-inject contract (tests/test_user_prompt_submit_hook.py).
