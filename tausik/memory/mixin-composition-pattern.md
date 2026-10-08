---
slug: mixin-composition-pattern
title: "Mixin composition pattern"
type: convention
tags:
  - architecture
  - mixins
task: null
edges: []
---

ProjectService composes 4 mixins: HierarchyMixin (epic/story CRUD), TaskMixin (task lifecycle + cascade), SessionMixin (session start/end/handoff), KnowledgeMixin (memory/web-cache/decisions/plans). All mixins access self.be: SQLiteBackend. New domain logic = new mixin file (service_*.py), not expansion of existing.
