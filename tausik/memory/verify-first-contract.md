---
slug: verify-first-contract
title: "Verify-First Contract"
type: pattern
tags:
  - "verify-first,architecture"
task: null
edges: []
---

Heavy gates (pytest, tsc, cargo, phpstan etc.) run on 'verify' trigger, not 'task-done'. task_done becomes a cache lookup instead of synchronous subprocess. Cache key includes trigger so verify and task-done buckets never cross-satisfy. Opt-out: config.task_done.auto_verify=true.
