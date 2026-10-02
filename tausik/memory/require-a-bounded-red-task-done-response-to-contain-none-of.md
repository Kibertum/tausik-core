---
slug: require-a-bounded-red-task-done-response-to-contain-none-of
title: "Require a bounded red task_done response to contain none of the failing tool's text"
type: dead_end
tags: []
task: bound-agent-validation-output-to-durable-artifacts
edges: []
---

Approach: Require a bounded red task_done response to contain none of the failing tool's text
Reason: The contract intentionally keeps up to four actionable failure lines; the correct boundary is that the complete repeated body is absent and the returned excerpt stays capped.
