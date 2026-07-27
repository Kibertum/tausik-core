---
slug: stdlib-only-nikakih-vneshnih-zavisimostey-v-yadre-freymvorka
task: null
date: "2026-03-14"
edges: []
---

## Decision

stdlib only — никаких внешних зависимостей в ядре фреймворка.

## Rationale

Фреймворк встраивается в любой проект без конфликтов версий. pip install не нужен. mcp — единственное опциональное исключение для MCP серверов.
