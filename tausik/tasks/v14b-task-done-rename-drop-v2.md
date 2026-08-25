---
slug: v14b-task-done-rename-drop-v2
title: "Rename: drop _v2 suffix from task_done — single tausik_task_done returning structured JSON"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/service_task.py, agents/claude/mcp/project/{handlers,tools,tools_extra,self_check}.py, agents/cursor/mcp/project/{handlers,tools,tools_extra,self_check}.py, bootstrap/bootstrap_hooks.py, tests/test_*.py, agents/skills/{task,ship}/**, docs/{en,ru}/{mcp,troubleshooting,quickstart,hooks}.md, AGENTS.md, QWEN.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/project_cli.py (CLI keeps using svc.task_done str-returning method — backward compat), bootstrap_templates.py (already unifined)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-04T11:26:27Z"
---

## Goal

Eliminate the confusing parallel pair of tausik_task_done (legacy str) + tausik_task_done_v2 (dict). Keep ONE MCP tool name `tausik_task_done` that returns the structured JSON dict (the v2 behavior). Drop _v2 from all references: tools, handlers, hooks matcher, tests, skills, docs.

## Acceptance Criteria

1. scripts/service_task.py: task_done_v2() method dropped. task_done() (CLI-facing) keeps str-returning legacy contract. 2. agents/{claude,cursor}/mcp/project/handlers.py: _do_task_done is the SOLE handler — calls _task_done_report() and returns json.dumps(result). _do_task_done_v2 dropped. _DISPATCH no longer has tausik_task_done_v2 entry. 3. agents/{claude,cursor}/mcp/project/tools.py: tausik_task_done_v2 tool definition dropped. tausik_task_done description updated to mention structured JSON response. 4. bootstrap/bootstrap_hooks.py: PostToolUse matcher drops |tausik_task_done_v2 — only tausik_task_done. 5. tests/test_task_done_v2_matcher.py renamed → test_task_done_matcher.py + content updated to assert only tausik_task_done is in matcher. 6. tests/test_project_mcp.py / test_mcp_integration.py / test_verify_first_contract.py: update references — call tausik_task_done (not _v2). 7. Skills (agents/skills/task,ship/SKILL.md + variants/{haiku,sonnet}.md): strip "v2 vs v1" / "fallback to legacy task_done" guidance. tausik_task_done IS the structured response. 8. docs/{en,ru}/mcp.md: drop tausik_task_done_v2 separate section, update tausik_task_done to mention structured JSON return. 9. docs/{en,ru}/troubleshooting.md + quickstart.md + hooks.md: strip _v2 references. 10. AGENTS.md + QWEN.md: drop _v2 from spine description. 11. agents/{claude,cursor}/mcp/project/self_check.py + tools_extra.py: update doc strings to drop _v2 reference. 12. agents/{claude,cursor}/mcp/project/handlers.py: keep both removed and clean. 13. CHANGELOG bilingual ### Changed entry: BREAKING for any agent that parsed tausik_task_done as a string — now returns JSON-encoded dict (structured-response). Migration: parse JSON from response. 14. pytest fast lane GREEN; ruff GREEN. 15. tausik verify --task + task done --ac-verified.

## Plan

## Rollback

## Journal

- 2026-05-04T11:26:27Z [implementation] — AC verified: 1. ✓ scripts/service_task.py: task_done_v2() method dropped. task_done() (CLI-facing) keeps str-returning legacy contract. 2. ✓ agents/{claude,cursor}/mcp/project/handlers.py: _do_task_done now calls _task_done_report() directly + json.dumps. _do_task_done_v2 dropped. _DISPATCH no longer has tausik_task_done_v2 entry. 3. ✓ agents/{claude,cursor}/mcp/project/tools.py: tausik_task_done_v2 tool definition dropped. tausik_task_done description updated to mention structured JSON. 4. ✓ bootstrap/bootstrap_hooks.py: PostToolUse matcher → mcp__tausik-project__tausik_task_done only. 5. ✓ tests/test_task_done_v2_matcher.py renamed → test_task_done_matcher.py + asserts no _v2 alias remains. 6. ✓ tests/test_project_mcp.py: test_task_done_v2_returns_structured_json → test_task_done_returns_structured_json (canonical name). test_mcp_integration.py: tausik_task_done_v2 dropped from skip list. 7. ✓ tests/test_verify_first_contract.py: switched to _task_done_report() direct call. 8. ✓ Skills (task,ship/SKILL.md + variants/{haiku,sonnet}.md): stripped 'v2 vs v1' fallback prose. 9. ✓ docs/{en,ru}/mcp.md: dropped duplicate tausik_task_done_v2 row + section. AGENTS.md + QWEN.md + READMEs: updated tool counts (100→99, 107→106). 10. ✓ CHANGELOG.md/ru.md bilingual ### Changed entry with Breaking note + full migration guidance. 11. ✓ pytest fast lane: 2741 passed, 7 skipped, 118 deselected (78s). Ruff clean on all changed files (1 pre-existing F841 NOT mine). 12. ✓ Bootstrap deployed; gen_doc_constants regenerated; verify recorded. Migration: agents calling mcp__tausik-project__tausik_task_done_v2 → switch to mcp__tausik-project__tausik_task_done (same input schema, same structured-JSON return).
