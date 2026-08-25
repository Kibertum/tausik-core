---
slug: v14c-snippet-detection-pereimenovan-v-epic-v15-snippet
task: null
date: "2026-05-07"
edges: []
---

## Decision

v14c-snippet-detection переименован в epic v15-snippet-system с декомпозицией на 5 sub-задач (classifier → table → ast-detect → mcp-search → brain-integration); оригинальная задача удалена.

## Rationale

/explore показал что 'snippet detection' в TAUSIK — пустой stub (brain_artifact_taxonomy.py:7-8). Оригинальный goal задачи (AST clone detection + dedicated table + MCP search + brain integration) — это 4-5 независимых фич, не одна 'complex' задача. Стандартная сложность 'complex' = одна сессия 180min ACTIVE; реальный scope требует 5 сессий. Переоценка с пользователем подтвердила: отложить целиком в 1.5 и сделать качественно по декомпозиции, а не пытаться запихнуть в 1.4 polish.
