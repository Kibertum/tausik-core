---
slug: run-canonical-task-scoped-verify-after-focused-tests-and
title: "Run canonical task-scoped verify after focused tests and dedupe passed."
type: dead_end
tags:
  - filesize
  - verify
task: compare-project-version-model-economics
edges: []
---

Approach: Run canonical task-scoped verify after focused tests and dedupe passed.
Reason: Verify #3428 stopped before pytest because benchmark_compare.py reached 600 lines and project_parser_ops.py reached 515. Split comparison support into bounded modules and move parser registration out of the already-full parser module.
