---
slug: import-bootstrap-bootstrap-templates-directly-to-measure
title: "Import bootstrap.bootstrap_templates directly to measure ANSWER_SHAPE and load harness/stacks/python"
type: dead_end
tags:
  - bootstrap
  - python
  - stack
task: controlled-prose-for-user-facing-answers
edges: []
---

Approach: Import bootstrap.bootstrap_templates directly to measure ANSWER_SHAPE and load harness/stacks/python.md
Reason: bootstrap_templates uses sibling imports and requires bootstrap on PYTHONPATH; this repository has no harness/stacks tree. Measure with PYTHONPATH=bootstrap and use the deployed .tausik stack guide instead.
