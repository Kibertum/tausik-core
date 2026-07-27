---
slug: tri-sloya-cli-service-backend-cli-formatiruet-service
task: null
date: "2026-03-14"
edges: []
---

## Decision

Три слоя: CLI → Service → Backend. CLI форматирует, Service валидирует, Backend = чистый SQL.

## Rationale

Разделение ответственности. Агент может заменить CLI на MCP без изменения бизнес-логики.
