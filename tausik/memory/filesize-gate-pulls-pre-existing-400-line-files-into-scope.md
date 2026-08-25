---
slug: filesize-gate-pulls-pre-existing-400-line-files-into-scope
title: "filesize gate pulls pre-existing >400-line files into scope when you touch them"
type: gotcha
tags:
  - filesize-gate
  - qg2
  - refactor
  - tech-debt
task: v16r-task-replay
edges: []
---

The QG-2 filesize gate (max 400 lines) only checks files in the task's relevant_files. Pre-existing source files already over 400 are effectively grandfathered UNTIL you edit them — then task_done fails on them even if your addition was tiny. Example: backend_queries.py was already ~460 lines; adding a 15-line query method made task_done fail "backend_queries.py: 475 lines (max 400)". Fix pattern: don't grow an already-oversized module — put the new method in a smaller, thematically-cohesive sibling mixin instead. For RENAR/reasoning backend reads, backend_crud_reasoning.py (ReasoningCrudMixin, mixed into SQLiteBackend, ~70 lines) is the right home — verification_runs_for_task went there, leaving backend_queries.py untouched and out of relevant_files. backend_queries.py at 461 lines remains pre-existing tech debt (candidate for a future extract).
