---
slug: nested-codex-task-start-was-invalidated-but-then
title: "Nested Codex task start was invalidated but then reactivated by its successful tool output"
type: dead_end
tags: []
task: r111-cross-host-economy-acceptance
edges: []
---

Approach: Nested Codex task start was invalidated but then reactivated by its successful tool output
Reason: The conflict branch cleared active_task but left the pending start event alive. Drop the event on conflict so its output cannot create exact attribution.
