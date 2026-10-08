---
slug: run-scoped-verify-before-formatting-and-profile-redeploy
title: "Run scoped verify before formatting and profile redeploy"
type: dead_end
tags:
  - scope
  - verification
task: r111-bounded-work-packet
edges: []
---

Approach: Run scoped verify before formatting and profile redeploy
Reason: Static gates correctly refused the receipt: five task Python files need ruff format, installed profile copies drift from source, and one task-start diff path is outside relevant_files. Format, redeploy generated profiles, identify the single diff path, then rerun the same scoped verify.
