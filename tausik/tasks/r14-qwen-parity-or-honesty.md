---
slug: r14-qwen-parity-or-honesty
title: "Qwen settings hooks parity with Claude OR remove same-as-Claude claim"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: null
role: null
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T00:44:14Z"
---

## Goal

Release 1.4 honesty about Qwen non-parity

## Acceptance Criteria

1. Either bootstrap_qwen.py contains identical hooks block with brain_search_proactive plus brain_post_webfetch plus task_call_counter plus activity_event. 2. Or README and docs honestly enumerate missing hooks and consequences (active time, brain cache, calibration). 3. Regression test test_bootstrap_hooks_parity compares hook command lists between generate_settings_claude and generate_settings_qwen.

## Plan

## Rollback

## Journal

- 2026-05-01T00:44:13Z [implementation] — AC verified: 1. Identical hooks block - bootstrap_qwen.py now lists all 16 hooks parity-tested in test_bootstrap_hooks_parity.py ✓ (Path A chosen over Path B). 2. Regression test compares command lists between Claude and Qwen settings ✓. 3. Negative scenario - if either generator regresses, test_qwen_has_every_claude_hook or test_qwen_does_not_invent_hooks fails with explicit script-name diff ✓.
- 2026-05-01T00:44:13Z [implementation] — Achieved hooks parity: bootstrap/bootstrap_qwen.py now emits brain_search_proactive (PreToolUse on WebSearch/WebFetch), brain_post_webfetch (PostToolUse on WebFetch), task_call_counter and activity_event (PostToolUse on every tool). Doc-comment updated to acknowledge the v1.4 closure of the four-hook gap.
- 2026-05-01T00:44:13Z [implementation] — Added regression test tests/test_bootstrap_hooks_parity.py with 3 cases: (a) Qwen has every Claude hook, (b) Qwen does not invent hooks Claude lacks, (c) 16 critical hooks are present in both. Tests run isolated via tmp_path. 13/13 pass across qwen + parity + mcp_generate suites.
