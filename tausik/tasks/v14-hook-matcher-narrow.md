---
slug: v14-hook-matcher-narrow
title: "Сузить task_done_verify hook matcher (убрать Bash)"
status: done
epic: v14-task-done-reliability
story: v14-defense-in-depth
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: ".claude/settings.json, bootstrap/bootstrap_generate.py, .qwen/settings.json — только matcher строка"
scope_exclude: "scripts/hooks/task_done_verify.py (логика не меняется), service_task.py, gate_runner.py"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T21:55:43Z"
---

## Goal

В .claude/settings.json и в bootstrap_templates.py PostToolUse hook task_done_verify.py имеет matcher "mcp__tausik-project__tausik_task_done|mcp__tausik-project__tausik_task_done_v2|Bash" — это значит hook fires на КАЖДЫЙ Bash call (не только task done через bash). На больших сессиях overhead +100-300ms × N bash calls. Сузить matcher до MCP tools + явного "Bash(.tausik/tausik task done*)". Hook сам делает is_task_done_invocation early-return, так что behavior не меняется, только overhead.

## Acceptance Criteria

1. .claude/settings.json: matcher hook task_done_verify сужен с «mcp__tausik-project__tausik_task_done|mcp__tausik-project__tausik_task_done_v2|Bash» до «mcp__tausik-project__tausik_task_done|mcp__tausik-project__tausik_task_done_v2».
2. bootstrap/bootstrap_generate.py:137-141 — то же сужение в источнике, чтобы новые проекты получили правильный matcher.
3. .qwen/settings.json — то же сужение если содержит этот hook.
4. Hook сам по-прежнему делает is_task_done_invocation early-return (поведение не меняется при invocation через MCP).
5. Negative: tests/test_bootstrap_hooks_parity.py + tests/test_task_done_verify_hook.py зелёные после правки.
6. Negative: CLI .tausik/tausik task done продолжает работать через встроенный verify-first gate в service_task (overhead на Bash hook убран; gate сохранён).
relevant_files: .claude/settings.json, bootstrap/bootstrap_generate.py, .qwen/settings.json

## Plan

## Rollback

## Journal

- 2026-05-02T21:55:43Z [implementation] — AC verified: 1. ✓ .claude/settings.json:97 matcher narrowed (Bash removed). 2. ✓ bootstrap/bootstrap_generate.py:137-141 matcher narrowed in source. 3. ✓ .qwen/settings.json:114 matcher narrowed. 4. ✓ Hook is_task_done_invocation early-return сохранён (logic не тронута). 5. ✓ pytest tests/test_bootstrap_hooks_parity.py + test_task_done_verify_hook.py = 24 passed in 0.55s. 6. ✓ Negative: CLI .tausik/tausik task done продолжает работать через service_task встроенный verify-first gate; hook overhead на каждом Bash убран.
