---
slug: mcp-first-dlya-agentov-cli-kak-fallback
task: null
date: "2026-03-14"
edges: []
---

## Decision

MCP-first для агентов, CLI как fallback.

## Rationale

MCP tools имеют JSON-схемы — невозможно ошибиться в аргументах. CLI через bash подвержен ошибкам синтаксиса. MCP сервер frai-project покрывает все 27 операций.
