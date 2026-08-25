---
slug: brain-skill-status
title: "Brain CLI/MCP: status — mirror freshness, registered projects, last sync error"
status: done
epic: shared-brain
story: brain-tausik-integration
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/brain_status.py (new), scripts/project_cli_ops.py, scripts/project_parser_ops.py, agents/skills/brain/SKILL.md, tests/test_brain_status.py (new)"
scope_exclude: "scripts/brain_init.py, agents/*/mcp/brain/handlers.py (MCP добавим отдельно если время)"
relevant_files:
  - "scripts/brain_status.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_parser_ops.py"
  - "tests/test_brain_status.py"
  - "agents/skills/brain/SKILL.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T10:42:37Z"
---

## Goal

Add `tausik brain status` CLI + matching `brain_status` MCP tool showing: enabled flag, mirror path + size + last modified, per-category row counts and last_pull_at / last_error from sync_state, registered projects (from brain_project_registry) with their project_hash, last WebFetch cache write time. Updates `/brain` skill to document the new subcommand.

## Acceptance Criteria

1. Новый scripts/brain_status.py с функцией collect_status() → dict с ключами: enabled, mirror_path, mirror_size_bytes, mirror_last_modified, categories (per-cat row_count + last_pull_at + last_error), projects (list of registered name+canonical+hash), last_web_cache_write
2. CLI: tausik brain status выводит human-readable отчёт
3. Регрессия: tausik brain init продолжает работать
4. Ошибка/граничный случай: brain не enabled → status выводит "Brain disabled" + minimal info без crash
5. Ошибка/граничный случай: mirror DB отсутствует / повреждена → graceful "Mirror missing/unreadable" с reason
6. Ошибка/граничный случай: registry file отсутствует → projects=[]
7. Тесты: collect_status disabled, enabled-empty, enabled-with-data, missing-mirror
8. Skill agents/skills/brain/SKILL.md документирует новый /brain status
9. pytest зелёный, ruff clean

## Plan

## Rollback

## Journal

- 2026-04-25T10:42:21Z [implementation] — AC verified: ✓1 scripts/brain_status.py с collect_status() — все 8 ключей включая categories per-cat (row_count + last_pull_at + last_error + last_error_at) ✓2 CLI tausik brain status: human markdown + --json flag ✓3 регрессия: brain init не тронут (smoke в этом проекте показал disabled-state корректно) ✓4 disabled → "Brain disabled" + минимум, без crash ✓5 missing mirror → mirror_size_bytes=None, error="mirror DB missing on disk" ✓6 пустой registry → projects=[] ✓7 9 тестов: disabled, config_load_error, missing_mirror, enabled_empty (zero rows), enabled_with_data (insert decision+sync_state+web_cache → counts assertion), registered_projects_listed, registry_missing, format_status disabled+with_data ✓8 SKILL.md: новый "/brain status" блок + удалён из Not-yet-implemented ✓9 pytest 9/9, ruff clean
