---
slug: plan-gate-on-task-completion
title: "Plan gate on task completion"
type: pattern
tags:
  - gate
  - plan
  - tasks
task: null
edges: []
---

Tasks with a plan cannot be marked done unless all steps are completed. Corrupted plan JSON raises ServiceError (not silently ignored). --force flag bypasses the gate. Plan is stored as JSON array: [{step: str, done: bool}].
