---
slug: bootstrap-qwen-brain-mcp
title: "MEDIUM: bootstrap_qwen регистрирует brain MCP"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: "bootstrap/bootstrap_qwen.py, tests/test_bootstrap*.py"
scope_exclude: "bootstrap/bootstrap_generate.py"
relevant_files:
  - "bootstrap/bootstrap_qwen.py"
  - "tests/test_bootstrap_qwen.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T09:59:23Z"
---

## Goal

bootstrap_generate.py регистрирует tausik-brain для Claude/Cursor, но bootstrap_qwen.py только codebase-rag+tausik-project. Qwen users silently без brain. Добавить parallel brain_server block в generate_settings_qwen

## Acceptance Criteria

1. bootstrap_qwen.py регистрирует tausik-brain MCP server параллельно с tausik-project (если brain server.py существует в target_dir/mcp/brain/)
2. Регрессия: tausik-project + codebase-rag регистрация остаётся как было — Qwen users не теряют существующие MCP servers
3. Ошибка/граничный случай: если target_dir/mcp/brain/server.py не существует — brain не регистрируется (silent skip, как сейчас для других серверов)
4. Pattern параллелит bootstrap_generate.py:241-246 (claude/cursor): _p(python_exe) + ['--project', _p(project_dir)]
5. Тест в tests/test_bootstrap.py (или аналог): qwen settings содержит tausik-brain mcpServer entry когда brain server.py exists в target
6. pytest зелёный, ruff clean

## Plan

## Rollback

## Journal

- 2026-04-25T09:59:11Z [implementation] — AC verified: 1. brain_server block добавлен в generate_settings_qwen параллельно tausik-project ✓ 2. tausik-project + codebase-rag entries не тронуты — регрессия отсутствует ✓ 3. Silent skip когда target_dir/mcp/brain/server.py не существует ✓ 4. Pattern совпадает с bootstrap_generate.py:241-246 (_p(python_exe), [_p(brain_server), '--project', _p(project_dir)]) ✓ 5. Новый tests/test_bootstrap_qwen.py: registers_brain_when_server_present, skips_brain_when_server_missing (regression: project remains), preserves_user_added_servers ✓ 6. pytest 3/3 passed, ruff clean ✓
