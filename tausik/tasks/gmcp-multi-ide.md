---
slug: gmcp-multi-ide
title: "[P2] Multi-IDE: Cursor/Qwen глобальная регистрация или честный gap"
status: planning
epic: v2-global-mcp
story: v2gm-surfaces
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/cli_init.py"
  - "docs/en/multi-ide.md"
  - "docs/ru/multi-ide.md"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs:
  - "github#46"
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Глобальная регистрация для Cursor и Qwen: их MCP-конфиги живут в других местах (Cursor settings, qwen config). Либо дать tausik init/register путь под каждый IDE, либо честно задокументировать gap (MVP глобала = Claude, остальные — сабмодуль/manual). Решение через decide.

## Acceptance Criteria

1. tausik init/register умеет печатать user-scope MCP сниппет под Cursor и Qwen (пути их конфигов) ИЛИ док честно фиксирует, что глобал поддержан только для Claude. 2. Негативный: неизвестный IDE -> сообщение с поддерживаемым списком, без краша. 3. Матрица паритета IDE обновлена (docs multi-ide). 4. pytest/док-тест соответствия.

## Plan

## Rollback

git revert; затрагивает только регистрацию/доки, рантайм IDE не ломается

## Journal
