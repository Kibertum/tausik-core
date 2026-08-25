---
slug: v14c-defect-mcp-tool-handler-drift
title: "DEFECT: test_every_tool_name_has_handler fail — TOOLS/handlers drift"
status: done
epic: v14-polish-followup
story: v14-polish-c-followup
complexity: simple
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T16:55:18Z"
---

## Goal

test_mcp_integration.py::TestMCPHandlerDispatch::test_every_tool_name_has_handler падает (pre-existing, не от v14c-mass-parametrize-batch-1). Проверяет что каждый инструмент в TOOLS list имеет handler в handlers.py. Failure означает drift: либо tool добавлен в TOOLS не зарегистрирован handler, либо handler удалён без удаления из TOOLS. Локализовать и исправить для 1.4 polish (не переносить в 1.4.1).

## Acceptance Criteria

AC-1: Локализована причина drift'а — точный список tools/handlers с описанием mismatch'а в notes.
AC-2: Test passes (`pytest tests/test_mcp_integration.py::TestMCPHandlerDispatch::test_every_tool_name_has_handler` → 0).
AC-3: Если был добавлен handler — covered tests pass для этого tool. Если был убран tool из TOOLS — соответствующая ссылка в docs/{en,ru}/mcp.md обновлена.
AC-4: Negative scenario — если tool отсутствует в реальном MCP server (sibling-process artifact), фактическое поведение пишется в notes как "no fix needed, sibling drift" и тест адаптируется (skip/parametrize по active TOOLS list).
AC-5: ruff + mypy чистые.

## Plan

## Rollback

## Journal

- 2026-05-07T16:54:06Z [implementation] — Localised drift: tausik_memory_archive added to TOOLS (handlers.py:501 + tools.py:587, required:[before]) but missing from skip_tools in test_every_tool_name_has_handler. MCP framework + CLI argparse both validate args in production — only this direct-handler test was broken. Fix: 1-line addition to skip_tools (alphabetic with other memory_* skips). Test class is pytestmark=slow (line 12), excluded from fast lane — drift slipped past CI default.
- 2026-05-07T16:55:14Z [implementation] — AC verified: 1. ✓ Drift локализован — tausik_memory_archive (handlers.py:501, tools.py:587 with required:[before]) добавлен в TOOLS но missing в test skip_tools. 2. ✓ pytest -m '' tests/test_mcp_integration.py::TestMCPHandlerDispatch::test_every_tool_name_has_handler → 1 passed in 1.95s. 3. ✓ Handler существует и работает в production (MCP schema validation + CLI argparse делают валидацию до handler reach), не нужно править docs/mcp.md. 4. N/A — fix реальный, не sibling drift. 5. ✓ ruff clean; mypy errors = baseline (11 pre-existing union-attr/import-not-found в файле, не от правки).
