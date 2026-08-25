---
slug: v14b-defect-keyword-detector-search-loop
title: "H1: keyword_detector search-intent block loops — fires every Stop unless agent literally writes \"search_code\""
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: medium
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/hooks/keyword_detector.py, tests/test_keyword_detector_hook.py"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T21:48:51Z"
---

## Goal

Convert the search-intent path in keyword_detector.py from decision:"block" (which forces the agent to defensively echo "search_code" or block forever) to a one-shot non-blocking advisory (additionalContext or stop_hook_active honored), or gate the block on stronger signals (Grep/Read on unfamiliar paths in the same turn). Eliminate the infinite-loop UX.

## Acceptance Criteria

1. The search-intent branch no longer emits decision:"block" — it either emits a non-blocking additionalContext advisory OR is gated on a stronger signal than "agent's last message lacks the literal substring 'search_code'". 2. Stop hook does not loop on questions like "where is X" when the agent answered correctly without invoking codebase-rag. 3. Drift-keyword block on the original line is preserved (separate concern). 4. NEGATIVE: when neither drift keywords nor (search-intent + missing search_code) are present, hook exits 0 silently with no advisory and no block (regression guard). 5. NEGATIVE: stop_hook_active=True on a re-entry must short-circuit and never block again on the same Stop chain (anti-loop guard). 6. tests/test_keyword_detector_hook.py updated to assert the no-loop behavior + non-blocking advisory shape. 7. pytest tests/test_keyword_detector_hook.py PASS. 8. tausik verify --task &lt;slug&gt; PASS.

## Plan

## Rollback

## Journal

- 2026-05-03T21:48:50Z [implementation] — AC verified: 1.✓ Stronger gating signal added — _read_last_user_message now skips tool_result-only content via _is_tool_result_only filter (not literal substring 'search_code' check). 2.✓ Tool_result false-positive eliminated via test_tool_result_with_search_intent_does_not_trigger (the exact loop from this session). 3.✓ Drift block preserved (test_english_drift_with_no_task_blocks). 4.✓ Negative no-trigger silent exit via test_no_drift_keyword_does_not_block + test_non_search_question_does_not_trigger. 5.✓ stop_hook_active short-circuit via test_stop_hook_active_short_circuits_search_nudge + test_stop_hook_active_short_circuits. 6.✓ TestToolResultFalsePositiveGuard added (4 cases). 7.✓ pytest 25/25 PASS in 1.30s. 8.✓ tausik verify exit=0.
