---
slug: create-test-and-recursively-remove-a-dynamically-named
title: "Create, test, and recursively remove a dynamically named temporary filtered snapshot in one PowerShe"
type: dead_end
tags:
  - public-snapshot
  - temp-cleanup
  - windows
task: public-snapshot-tests-read-excluded-files
edges: []
---

Approach: Create, test, and recursively remove a dynamically named temporary filtered snapshot in one PowerShell invocation.
Reason: The execution policy rejected the command before it ran because recursive cleanup targeted a computed path, despite the in-script temp-root guard. Split materialization from cleanup so the exact path can be read back and validated before a literal-path removal.
