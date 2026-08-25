---
slug: brain-skill-move
title: "Brain CLI/MCP: move record retroactively to-local / to-brain"
status: done
epic: shared-brain
story: brain-tausik-integration
complexity: medium
role: null
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/brain_move.py (new), scripts/project_cli_ops.py, scripts/project_parser_ops.py, agents/skills/brain/SKILL.md, tests/test_brain_move.py (new)"
scope_exclude: "scripts/brain_mcp_write.py, scripts/brain_init.py, agents/*/mcp/brain/handlers.py"
relevant_files:
  - "scripts/brain_move.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_parser_ops.py"
  - "tests/test_brain_move.py"
  - "agents/skills/brain/SKILL.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T10:47:13Z"
---

## Goal

Add `tausik brain move <id> --to-local` / `--to-brain` subcommand + matching MCP tool to reclassify a record that was filed in the wrong store. Reads source row, scrubs, writes to target, deletes from source on ok. Handles: scrub_blocked (abort, keep source), notion_error (abort), cross-project ownership check for to-local (source_project_hash must match current project). Updates `/brain` skill to document the new subcommand.</goal>
<parameter name="role">developer

## Acceptance Criteria

1. Новый scripts/brain_move.py с move_to_brain(local_id, kind, *, keep_source) и move_to_local(notion_page_id, category, *, force, keep_source) функциями
2. move_to_brain поддерживает kinds: decision (decisions table), pattern + gotcha (memory table). Вызывает brain_mcp_write.store_record с замапленными полями. На ok удаляет из local (если не keep_source)
3. move_to_local поддерживает categories: decisions, patterns, gotchas. Web_cache → refuse (no local counterpart)
4. Cross-project ownership check для to-local: source_project_hash != current project hash → refuse, разрешает с force=True
5. CLI: tausik brain move <id> --to-brain --kind X / --to-local --category X [--force] [--keep-source]
6. Регрессия: tausik brain init + status продолжают работать
7. Ошибка/граничный случай: scrub_blocked → keep source, return {status: 'skipped', reason: 'scrub_blocked'}
8. Ошибка/граничный случай: notion_error → keep source, return {status: 'failed', reason: 'notion_error'}
9. Ошибка/граничный случай: source_id не найден → return {status: 'not_found'}
10. Ошибка/граничный случай: kind/category invalid → return {status: 'bad_input'}
11. SKILL.md документирует /brain move
12. Тесты: 6+ unit для каждой ветки (happy paths + scrub + notion_error + ownership + bad_input)
13. pytest зелёный, ruff clean

## Plan

## Rollback

## Journal

- 2026-04-25T10:47:09Z [implementation] — AC verified: ✓1 brain_move.py с move_to_brain + move_to_local ✓2 to-brain поддерживает 3 kinds (decision/pattern/gotcha), маппинг fields → brain_mcp_write.store_record ✓3 to-local 3 categories (decisions/patterns/gotchas), web_cache → bad_input ✓4 cross-project ownership через _current_project_hash + brain_config.compute_project_hash, force=True override ✓5 CLI tausik brain move с --to-brain/--to-local mutually exclusive + --kind/--category + --force + --keep-source ✓6 регрессия brain init/status untouched ✓7 scrub_blocked → status='skipped', reason='scrub_blocked', source preserved ✓8 notion_error → status='failed', source preserved ✓9 source_id not found → status='not_found' ✓10 invalid kind/category → status='bad_input' ✓11 SKILL.md: новый /brain move + Subcommand status (все 5 implemented) ✓12 19 unit tests across 2 классов (TestMoveToBrain 10 + TestMoveToLocal 8 + helper) ✓13 pytest 19/19, ruff clean
