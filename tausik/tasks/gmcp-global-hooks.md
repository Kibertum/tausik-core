---
slug: gmcp-global-hooks
title: "[P1] Глобальные хуки из установленной библиотеки"
status: planning
epic: v2-global-mcp
story: v2gm-surfaces
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_qwen.py"
  - "scripts/hooks/_common.py"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Хуки (task_gate, scope_write_gate, memory_pretool_block, secret_scan, bash_firewall и пр.) работают из глобально установленной либы, регистрируются в user-scope settings.json и резолвят проект через CLAUDE_PROJECT_DIR (его прокидывает хост). Вне TAUSIK-проекта — тихий no-op (is_tausik_project уже есть). Bootstrap-hooks генерит user-scope команды на установленный tausik-hook entry.

## Acceptance Criteria

1. Хук-команды резолвятся к глобальной либе (entry-point или python -m), без зависимости от .claude/scripts/hooks копий. 2. Хук в TAUSIK-проекте срабатывает; вне TAUSIK-проекта exit 0 no-op. 3. Негативный: CLAUDE_PROJECT_DIR не задан/проект не резолвится -> fail-open (allow) кроме явного FAIL_SECURE, без краша хоста. 4. Parity: bootstrap_hooks и bootstrap_qwen дают согласованный набор (parity-тест зелёный). 5. pytest: глобальный путь хука, no-op вне проекта, fail-open.

## Plan

## Rollback

git revert + re-bootstrap; per-project хуки в .claude/settings.json остаются рабочими на переходный период

## Journal
