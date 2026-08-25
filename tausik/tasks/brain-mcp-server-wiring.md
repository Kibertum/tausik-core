---
slug: brain-mcp-server-wiring
title: "Регистрация tausik-brain MCP-сервера в .mcp.json"
status: done
epic: shared-brain
story: brain-mcp-server
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "agents/claude/mcp/brain/server.py (new), agents/cursor/mcp/brain/{server.py,handlers.py,tools.py} (new), bootstrap/bootstrap_generate.py (extend generate_mcp_json), tests/test_bootstrap_generate_mcp.py (new)"
scope_exclude: "agents/claude/mcp/brain/handlers.py + tools.py (stable, from prev task), scripts/brain_*.py (stable), bootstrap/bootstrap_copy.py (copy_mcp already handles the dir), any SSE/HTTP transport (future)"
relevant_files:
  - "agents/claude/mcp/brain/server.py"
  - "agents/cursor/mcp/brain/server.py"
  - "agents/cursor/mcp/brain/handlers.py"
  - "agents/cursor/mcp/brain/tools.py"
  - "bootstrap/bootstrap_generate.py"
  - "tests/test_bootstrap_generate_mcp.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-23T09:27:00Z"
---

## Goal

Thin MCP server for tausik-brain (agents/claude/mcp/brain/server.py mirrored into agents/cursor/mcp/brain/) + bootstrap registration in .mcp.json. Server mimics project/server.py shape: argparse --project, loads stdio transport, lists TOOLS from brain/tools.py, dispatches via brain/handlers.handle_tool. generate_mcp_json gains a `tausik-brain` entry when the server file exists. Brain not configured is NOT a bootstrap concern — tools themselves return the setup hint at call time (keeps the wiring idempotent regardless of brain.enabled flag).

## Acceptance Criteria

1) agents/claude/mcp/brain/server.py (new) — thin launcher: argparse, import TOOLS+handle_tool, stdio_server run loop. Shape matches project/server.py; ≤80 lines.
2) agents/cursor/mcp/brain/server.py + handlers.py + tools.py — copies of the claude variants so the cursor IDE also gets the brain server.
3) bootstrap/bootstrap_generate.py.generate_mcp_json registers "tausik-brain" when brain/server.py exists. Uses same python_exe as other servers.
4) Server does not crash when brain.enabled=false — tools themselves return setup hint; no config read happens at server startup.
5) Tests in tests/test_bootstrap_generate_mcp.py (or similar) verify: empty .mcp.json → brain server added; existing .mcp.json with user server → user entry preserved; brain server added.
6) mypy + ruff clean; full pytest passes; no regressions.
7) Out of scope: brain init wizard (brain-init-wizard), SSE/HTTP transport (noted in task but deferred to future — stdio only in v1).

## Plan

[{"step": "Create agents/claude/mcp/brain/server.py from project/server.py template", "done": true}, {"step": "Mirror agents/cursor/mcp/brain/ (server + handlers + tools)", "done": true}, {"step": "Extend bootstrap/bootstrap_generate.generate_mcp_json to register tausik-brain", "done": true}, {"step": "Write tests/test_bootstrap_generate_mcp.py", "done": true}, {"step": "Run mypy + ruff + full pytest", "done": true}, {"step": "Log AC evidence; task done", "done": true}]

## Rollback

## Journal

- 2026-04-23T09:23:17Z [implementation] — AC verified: 1. agents/claude/mcp/brain/server.py created (79 lines, thin launcher) ✓ 2. agents/cursor/mcp/brain/ mirrored with server.py + handlers.py + tools.py ✓ 3. generate_mcp_json registers tausik-brain when server exists ✓ test_registers_brain_when_server_present 4. no config read at startup ✓ server.py has no brain_config import; tools return setup hint lazily ✓ 5. 5 tests for generate_mcp_json: registers/skips/preserves/updates/forward-slashes ✓ 6. mypy scripts/ clean, ruff clean, 1401 pass / 2 skip ✓ 7. SSE/HTTP deferred, noted in task ✓
