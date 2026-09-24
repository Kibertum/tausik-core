---
slug: tools-list-otdaet-ttlms-0-i-cachescope-private-skrytie-po
task: mcp-tools-list-caching-conflicts-with-scope-hiding
date: "2026-09-24"
edges: []
---

## Decision

tools/list отдаёт ttlMs=0 и cacheScope=private, скрытие по scope_tools сохраняется (github#91)

## Rationale

Скрытие даёт замеренные −56% поверхности (памятка #327), а сменить кэш-подсказку стоит одну строку. Список зависит от состояния задачи, и SEP-2567 требует, чтобы list не зависел от соединения: кэш запрещён, приватен, и свежий запрос всегда отражает текущий scope. SDK 1.27 не моделирует поля, но ListToolsResult принимает extra-ключи, поэтому апгрейд SDK не нужен.
