---
slug: treat-a-repository-without-tests-as-having-no-applicable
title: "Treat a repository without tests/ as having no applicable pytest lane"
type: dead_end
tags:
  - consumer
  - selector
  - verify
task: prune-low-value-tests-by-behavioral-evidence
edges: []
---

Approach: Treat a repository without tests/ as having no applicable pytest lane
Reason: A consumer may declare a root-level test file explicitly; the selector rejected that valid changed-test edge and broke the first-close E2E.
