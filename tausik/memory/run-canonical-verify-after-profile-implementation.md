---
slug: run-canonical-verify-after-profile-implementation
title: "Run canonical verify after profile implementation"
type: dead_end
tags: []
task: add-memory-only-governance-profile
edges: []
---

Approach: Run canonical verify after profile implementation
Reason: The cross-cutting rule-generator parity detector defined a writer only as direct open/write calls and therefore saw zero generators after writes moved behind write_generated_rules. Extend the detector to recognize the shared writer as the stronger warning-owning boundary; do not reintroduce five direct warning/write copies.
