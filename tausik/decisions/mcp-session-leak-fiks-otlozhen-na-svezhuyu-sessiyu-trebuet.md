---
slug: mcp-session-leak-fiks-otlozhen-na-svezhuyu-sessiyu-trebuet
task: null
date: "2026-07-17"
edges: []
---

## Decision

mcp-session-leak: фикс отложен на свежую сессию — требует архитектурного выбора auto-reap vs ручной reap

## Rationale

Авто-reaping протухших MCP-серверов при старте рискует убить ЖИВЫЕ сиблинг-сессии (пользователь явно предупредил 'не поубивай лишнего'), и не верифицируется без многопроцессного стенда. Безопасная альтернатива — явная команда reap + жёсткое предупреждение в /start при sibling_count>N. Решение auto-vs-manual — за пользователем; не убивать процессы автономно.
