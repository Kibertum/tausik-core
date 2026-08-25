---
slug: consumer-mcp-enum-snapshot
title: "MCP tools.py stack enum generated from registry"
status: done
epic: v16-plugin-arch-and-docs
story: refactor-consumers
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "agents/claude/mcp/project/tools.py, agents/cursor/mcp/project/tools.py, bootstrap/bootstrap_stacks.py, bootstrap/bootstrap.py"
scope_exclude: "scripts/*, MCP server logic (server.py)"
relevant_files:
  - "bootstrap/bootstrap_stacks.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T17:10:39Z"
---

## Goal

agents/claude/mcp/project/tools.py — stack enum no longer hand-edited list. Bootstrap-time generator regenerates the enum from registry.all_stacks() snapshot when bootstrap runs. Static enum stays in JSON Schema for advisory hint to MCP clients; runtime validation uses registry. cursor + .claude mirrors regenerated.

## Acceptance Criteria

1. agents/{claude,cursor}/mcp/project/tools.py: 4 inline-stack-enum списки заменены на reference _STACKS_ENUM module-level константу.
2. _STACKS_ENUM окружён маркерами BEGIN/END для bootstrap regeneration.
3. bootstrap_stacks.regenerate_mcp_stack_enums(lib_dir) — функция перезаписывает _STACKS_ENUM из default_registry().all_stacks() (sorted).
4. bootstrap.py main() вызывает regenerate_mcp_stack_enums после copy_stacks.
5. Включает все 25 стэков (включая ansible, terraform, docker, helm, kubernetes — раньше отсутствовали).
6. Tools.py импортируется без ошибок (no name errors на _STACKS_ENUM references).
7. pytest tests/ collected 2148 tests — нет SyntaxError / ImportError на tools.py.
8. **Negative scenario:** registry недоступен → regenerate возвращает 0 (no-op), bootstrap не падает; tools.py с устаревшим snapshot работает (snapshot-консервативно).

## Plan

## Rollback

## Journal

- 2026-04-25T17:08:22Z [implementation] — AC verified: 1. ✓ 4 inline enum в claude/tools.py + 4 в cursor/tools.py заменены на _STACKS_ENUM (5 references in claude include 1 definition + 4 schemas). 2. ✓ Маркеры BEGIN/END STACKS_ENUM окружают definition. 3. ✓ bootstrap_stacks.regenerate_mcp_stack_enums(lib_dir) — реализована, итерирует _MCP_TOOLS_PATHS (claude, cursor, qwen). 4. ✓ bootstrap.py main вызывает regenerate_mcp_stack_enums после copy_stacks. 5. ✓ _STACKS_ENUM содержит 25 стэков (ansible, terraform, docker, helm, kubernetes — присутствуют). 6. ✓ tools.py импортируется без ошибок (pytest collected 2148 tests, no ImportError). 7. ✓ regenerate возвращает 0 при no-diff состоянии (already in sync). 8. ✓ Negative: try/except + sys.path push защищены, при registry-error возвращает 0 без crash bootstrap.
