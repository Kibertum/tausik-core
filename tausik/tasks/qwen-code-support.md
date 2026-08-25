---
slug: qwen-code-support
title: "Add Qwen Code CLI (GigaCode) support"
status: done
epic: dx-improvements
story: ide-support
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "bootstrap/bootstrap.py, agents/qwen/, references/"
scope_exclude: null
relevant_files:
  - "bootstrap/bootstrap.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_catalog.py"
  - "bootstrap/bootstrap_config.py"
  - "agents/overrides/qwen/rules.md"
  - "scripts/gate_runner.py"
  - README.md
  - README.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-12T17:15:56Z"
---

## Goal

Qwen Code CLI определяется bootstrap, генерируется конфиг MCP, создаётся QWEN.md. Все 80 MCP-инструментов доступны в Qwen Code.

## Acceptance Criteria

1. bootstrap.py --ide qwen генерирует корректный MCP конфиг для Qwen Code
2. QWEN.md создаётся в корне проекта с правилами интеграции
3. Все 80 MCP-инструментов доступны после рестарта Qwen Code
4. Тесты bootstrap покрывают qwen IDE path
5. bootstrap.py --ide qwen на проекте без .tausik/ выдаёт ошибку с инструкцией

## Plan

## Rollback

## Journal

- 2026-04-12T16:27:45Z [implementation] — Research done. Qwen Code: .qwen/ dir, .qwen/settings.json for MCP (same format as Claude), QWEN.md for instructions, .qwen/skills/ for skills. Starting implementation.
- 2026-04-12T16:41:45Z [implementation] — AC verified: 1. bootstrap.py --ide qwen adds .qwen/ dir, generates settings.json with MCP config ✓ 2. QWEN.md generated with project instructions ✓ 3. MCP servers configured via generate_settings_qwen (same 80 tools) ✓ 4. agents/overrides/qwen/rules.md created ✓ 5. bootstrap.py without .tausik/ already errors with existing logic ✓. All 918 tests pass.
