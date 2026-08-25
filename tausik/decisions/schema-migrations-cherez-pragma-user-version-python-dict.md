---
slug: schema-migrations-cherez-pragma-user-version-python-dict
task: null
date: "2026-03-14"
edges: []
---

## Decision

Schema migrations через PRAGMA user_version + Python dict версий.

## Rationale

Простейший механизм, не требует Alembic. Каждая миграция — список SQL. Версия в meta таблице + PRAGMA. Откат не поддерживается — только forward.
