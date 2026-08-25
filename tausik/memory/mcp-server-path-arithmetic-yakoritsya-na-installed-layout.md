---
slug: mcp-server-path-arithmetic-yakoritsya-na-installed-layout
title: "MCP server path arithmetic якорится на installed layout (.claude/mcp/), не на source-tree (agents/)"
type: gotcha
tags:
  - bootstrap
  - brain
  - mcp
  - path-resolution
  - test-isolation
task: brain-mcp-path-fix
edges: []
---

Bootstrap копирует agents/<ide>/mcp/<name>/ в .claude/mcp/<name>/ один-в-один. Runtime path в .mcp.json указывает на .claude/mcp/<name>/server.py — т.е. installed layout авторитетен. Поэтому path arithmetic в server.py/handlers.py обязана быть 2·".." (от .claude/mcp/<name>/ к .claude/scripts/), а НЕ 4·".." (которая правильно резолвится только в source-tree agents/<ide>/mcp/<name>/ → repo root /scripts/).

Симптом бага при неправильной арифметике: 4·".." прыгает в родителя проекта → scripts/ не найден → ModuleNotFoundError на первом import brain_* в handlers.py → MCP сервер не стартует, клиент видит только "Server failed to start".

Тест-паттерн для регрессии (см. tests/test_brain_mcp_installed_layout.py): subprocess с PYTHONPATH="" + tmp_path/.claude/mcp/<name>/ + tmp_path/.claude/scripts/ со stub-модулями. Без subprocess-изоляции тесты тихо маскируют баг потому что sys.path уже содержит source-tree scripts/.
