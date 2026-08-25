---
slug: task-lifecycle-cascade
title: "Task lifecycle cascade"
type: pattern
tags:
  - cascade
  - lifecycle
  - tasks
task: null
edges: []
---

task start -> auto-activates parent story (open->active) and epic. task done -> auto-closes parent story if all sibling tasks done, then auto-closes epic if all stories done. Cascade is one-way up: child completion triggers parent check.
