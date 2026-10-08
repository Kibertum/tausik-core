---
slug: audit-trail-cherez-sqlite-triggers-ne-cherez-application
task: null
date: "2026-03-14"
edges: []
---

## Decision

Audit trail через SQLite triggers, не через application code.

## Rationale

Триггеры гарантируют запись ВСЕХ изменений, даже если вызвано напрямую через SQL. json_object() для безопасной JSON-сериализации.
