---
slug: cache-bucket-separation-by-trigger
title: "Cache bucket separation by trigger"
type: gotcha
tags:
  - "verify-first,cache,security"
task: null
edges: []
---

When parameterizing run_gates_with_cache(trigger=...), the cache_command MUST include trigger as part of the key. Otherwise old task-done green could satisfy verify-first and bypass the contract. _build_cache_command(trigger, files) is the canonical helper.
