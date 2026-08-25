---
slug: agent-units-cli-flags
title: "CLI: task_add/update принимают --call-budget и --tier"
status: done
epic: agent-native-planning
story: estimation-planning-integration
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_parser.py (CLI argparse)\nscripts/project_cli.py (cmd_task dispatcher)\nscripts/service_task.py (task_add signature расширение)\nscripts/project_backend.py (_TASK_FIELDS + backend.task_add)\nagents/claude/mcp/project/tools.py + handlers.py (MCP schema + handler)\n.claude/mcp/project/tools.py + handlers.py (mirror)\ntests/test_agent_units_cli.py (новый файл)"
scope_exclude: "scripts/project_cli_extra.py / project_cli_ops.py / project_cli_verify.py (не относятся к task add/update)\nagents/cursor/mcp/* (cursor-специфичные, отдельная среда)\nagents/skills/plan/ (отдельная задача plan-skill-agent-aware)\nbootstrap/ (не нужно править — задача не меняет hooks)</scope_exclude>\n</invoke>\n<invoke name=\"mcp__tausik-project__tausik_task_start\">\n<parameter name=\"slug\">agent-units-cli-flags"
relevant_files:
  - "scripts/project_parser.py"
  - "scripts/project_cli.py"
  - "scripts/service_task.py"
  - "scripts/project_backend.py"
  - "scripts/project_types.py"
  - "agents/claude/mcp/project/tools.py"
  - "agents/claude/mcp/project/handlers.py"
  - "scripts/gate_runner.py"
  - "tests/test_agent_units_cli.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T12:04:31Z"
---

## Goal

Расширить task_add + task_update + MCP analogs: --call-budget INTEGER (предпочтительно) или --tier {trivial,light,moderate,substantial,deep}. Если оба → --call-budget overrides --tier. Если ни одного → derive default tier='moderate' с warning. Auto-derive tier при наличии budget (по таблице из v17 schema). --complexity (старая story-points поле) deprecated с warning, но всё ещё работает для backwards compat.

## Acceptance Criteria

- [ ] `tausik task add ... --call-budget INT` принимается parser'ом, валидируется (>=0); сохраняет в БД через task_set_call_budget сразу после task_add; auto-tier
- [ ] `tausik task add ... --tier {trivial,light,moderate,substantial,deep}` принимается; если task_add пришёл без call_budget но с tier — записывается tier напрямую (call_budget остаётся NULL)
- [ ] Если переданы оба флага — call_budget overrides tier (warning в stderr "tier overridden by --call-budget", auto-derived tier)
- [ ] Если ни budget, ни tier — task создаётся как раньше (no warning — soft default; решение: warning слишком навязчив на 388 существующих flow, оставляем NULL/NULL)
- [ ] `tausik task update <slug> --call-budget X / --tier Y` работают через те же helpers
- [ ] backend.task_add принимает call_budget+tier параметры; _TASK_FIELDS включает 'call_budget','call_actual','tier' для task_update
- [ ] MCP tausik_task_add + tausik_task_update accept call_budget (integer) + tier (enum); validation в handlers
- [ ] MCP changes synced в .claude/mcp/project/ (обе копии: agents/claude + .claude)
- [ ] Negative scenarios: --call-budget=-5 → CLI exit 1 с error message; --tier=bogus → argparse choices error; --call-budget без числа → argparse type error
- [ ] Tests tests/test_agent_units_cli.py: (a) --call-budget add+update; (b) --tier add+update; (c) override behavior; (d) MCP handler accepts both fields; (e) negative cases (invalid budget, invalid tier); (f) backwards compat — task add без флагов работает

## Plan

## Rollback

## Journal

- 2026-04-25T11:59:18Z [implementation] — AC verified: 1. CLI task add --call-budget INT принимается, валидируется, auto-derives tier ✓ (test_budget_only_derives_tier, TestCliParser PASSED) 2. CLI task add --tier {...} принимается, не трогает call_budget ✓ (test_tier_only_no_budget PASSED) 3. Override behavior: --call-budget overrides --tier с notice ✓ (test_both_budget_overrides_tier PASSED — budget=200 → tier='deep' via auto-derive) 4. Без флагов NULL/NULL без warning ✓ (test_neither_leaves_nulls PASSED) 5. CLI task update --call-budget / --tier работают ✓ (test_update_budget_derives_tier, test_update_tier_directly, test_update_explicit_tier_overrides_auto PASSED) 6. backend.task_add сохраняет атрибуты + _TASK_FIELDS включает 'call_budget','call_actual','tier' ✓ 7. MCP tausik_task_add + tausik_task_update accept call_budget+tier ✓ (test_handler_passes_budget_through, test_handler_invalid_tier_rejected PASSED) 8. .claude/mcp/project mirror sync OK ✓ (cp agents/claude → .claude) 9. Negative scenarios: --call-budget=-1 → ServiceError ✓ (test_negative_budget_rejected, test_update_negative_budget_rejected PASSED); --tier=bogus → argparse rejects ✓ (test_invalid_tier_argparse_rejects PASSED); non-integer budget → argparse type error ✓ (test_non_integer_budget_argparse_rejects PASSED) 10. Tests tests/test_agent_units_cli.py 17/17 PASSED + смежные test_agent_units + test_agent_units_recording + test_tausik_service + test_tausik_backend 185/185 PASSED
