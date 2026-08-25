---
slug: mixin-composition-vmesto-monolitnogo-service-hierarchymixin
task: null
date: "2026-03-14"
edges: []
---

## Decision

Mixin composition вместо монолитного Service: HierarchyMixin, TaskMixin, SessionMixin, KnowledgeMixin.

## Rationale

Каждый mixin < 200 строк. Можно тестировать изолированно. ProjectService наследует все миксины.
