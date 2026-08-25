---
slug: skill-service-layer
title: "Route skill install/uninstall through ProjectService layer"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_service.py, scripts/project_cli_extra.py, agents/claude/mcp/project/handlers_skill.py"
scope_exclude: "skill_manager.py (keep as-is, service wraps it)"
relevant_files:
  - "scripts/project_cli_extra.py"
  - "agents/claude/mcp/project/handlers_skill.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-08T05:25:43Z"
---

## Goal

install_skill and uninstall_skill should go through ProjectService like activate/deactivate do, maintaining CLI→Service→Backend architecture. Add try/except for ImportError in CLI bare imports.

## Acceptance Criteria

1. ProjectService has install_skill and uninstall_skill static methods
2. CLI cmd_skill calls ProjectService.install_skill/uninstall_skill
3. MCP handlers call ProjectService.install_skill/uninstall_skill
4. CLI bare imports wrapped in try/except with user-friendly error
5. No regressions in tests

## Plan

## Rollback

## Journal

- 2026-04-08T05:17:55Z [implementation] — AC verified: 1. ProjectService.skill_install + skill_uninstall static methods added ✓ 2. CLI calls svc.skill_install/uninstall ✓ 3. MCP handlers call ProjectService ✓ 4. CLI imports wrapped in try/except ✓ 5. 879 tests pass ✓
