---
slug: add-separate-no-mapping-tests-for-generic-prose-and-a-docs
title: "Add separate no-mapping tests for generic prose and a docs/mcp basename collision"
type: dead_end
tags: []
task: select-affected-tests-for-ordinary-verify
edges: []
---

Approach: Add separate no-mapping tests for generic prose and a docs/mcp basename collision
Reason: The tests had identical structure and grew the pytest dedupe ratchet in verify #3343; merge them into one parametrized behavior matrix.
