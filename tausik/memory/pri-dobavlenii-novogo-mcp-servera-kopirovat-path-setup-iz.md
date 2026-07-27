---
slug: pri-dobavlenii-novogo-mcp-servera-kopirovat-path-setup-iz
title: "При добавлении нового MCP сервера — копировать path-setup из agents/<ide>/mcp/project/server.py (reference impl)"
type: convention
tags:
  - convention
  - diagnostics
  - mcp
  - path-resolution
task: brain-mcp-path-fix
edges: []
---

В agents/claude/mcp/project/server.py:14-19 и handlers.py:10-13 уже рабочая форма path-setup: 2·"..", os.path.isdir guard перед sys.path.insert. Новый MCP (brain, future) должен копировать её 1:1 — не переизобретать. Инварианты:
1. scripts_dir = normpath(os.path.join(this_dir, "..", "..", "scripts")) — 2·"..".
2. sys.path.insert обёрнут в os.path.isdir(scripts_dir); при отсутствии писать stderr-диагностику с именем сервера ("[tausik-<name>] scripts dir missing: ...").
3. call_tool exception branch обязан печатать traceback.format_exc() в stderr перед возвратом Error TextContent — без этого debug в MCP-среде невозможен (stderr MCP-клиента либо не видим, либо виден только при включённом verbose).
4. import asyncio и import traceback — на верхнем уровне модуля, не внутри main() (убирает L3-класс warnings).
