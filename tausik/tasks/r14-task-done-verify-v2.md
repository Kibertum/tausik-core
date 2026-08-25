---
slug: r14-task-done-verify-v2
title: "task_done_verify hook matcher: include tausik_task_done_v2"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: simple
role: null
stack: null
tier: light
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T00:28:49Z"
---

## Goal

Release 1.4 readiness: r14-task-done-verify-v2

## Acceptance Criteria

1. matcher PostToolUse в bootstrap_generate содержит и task_done и task_done_v2. 2. Добавлен тест на парсинг payload v2.

## Plan

## Rollback

## Journal

- 2026-05-01T00:28:49Z [planning] — AC verified: 1. Matcher includes tausik_task_done_v2 ✓. 2. Bootstrap configs (claude+qwen) emit v2 in matcher ✓ (test_bootstrap_generate_mcp passes). 3. .claude/settings.json mirror updated ✓. 4. Docs row mentions v2 ✓ (docs/{en,ru}/hooks.md). 5. Negative scenario - unrelated tool names not matched ✓ (test_unrelated_tool_is_not_task_done).
- 2026-05-01T00:28:49Z [planning] — Docs aligned: docs/{en,ru}/hooks.md mention v2 + matcher pattern. New tests: tests/test_task_done_v2_matcher.py (5 tests) — 90/90 pass across bootstrap + verify hook + matcher suites.
- 2026-05-01T00:28:49Z [planning] — Extended PostToolUse matcher: scripts/hooks/_common.py _TASK_DONE_TOOL_NAMES now lists both tausik_task_done and tausik_task_done_v2. bootstrap_generate.py and bootstrap_qwen.py emit matcher 'tausik_task_done|tausik_task_done_v2|Bash'. .claude/settings.json updated for parity.
