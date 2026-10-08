---
slug: dekompozitsiya-backend-crud-v-project-backend-py-360
task: null
date: "2026-03-14"
edges: []
---

## Decision

Декомпозиция backend: CRUD в project_backend.py (360), сложные запросы в backend_queries.py (191)

## Rationale

project_backend.py превышал лимит 400 строк (534). BackendQueriesMixin наследуется через MRO, все методы доступны на SQLiteBackend.
