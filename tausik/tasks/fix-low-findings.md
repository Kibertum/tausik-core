---
slug: fix-low-findings
title: "Исправить все LOW findings из 4 ревью-агентов"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/plan_parser.py"
  - "scripts/cq_client.py"
  - "agents/claude/mcp/project/handlers.py"
  - "agents/cursor/mcp/project/handlers.py"
  - "tests/test_cq_client.py"
  - "tests/test_qg2_gates.py"
  - "tests/test_skills_maturity.py"
  - "tests/test_cli_smoke_extra.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T20:09:23Z"
---

## Goal

Ноль open findings. Все LOW из ревью закрыты: тесты усилены, docs консистентны, stale references убраны.

## Acceptance Criteria

1. test_cq_client: добавлен тест confirm(), убран мёртвый status в mock. 2. test_qg2_gates: test_gates_skipped проверяет mock not called. 3. test_skills_maturity: ui-ux в ROLES, test_dead_end assert task add rc=0. 4. plan_parser.py: stale agents/claude/skills reference убрана. 5. cq_client confirm(): unit_id URL-encoded. 6. handlers.py: exception в counter логируется а не глотается. 7. Ошибка если grep находит agents/claude/skills в scripts/.

## Plan

## Rollback

## Journal

- 2026-04-05T20:09:14Z [implementation] — AC verified: 1. confirm() тест + status убран из mock ✓ 2. test_gates_skipped assert_not_called ✓ 3. ui-ux в ROLES + task add assert ✓ 4. plan_parser stale ref fixed ✓ 5. confirm() URL-encoded ✓ 6. counter logged not swallowed ✓ 7. grep agents/claude/skills в scripts/ = 0 ✓ 751/751 тестов
