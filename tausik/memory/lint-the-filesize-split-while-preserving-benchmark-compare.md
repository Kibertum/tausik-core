---
slug: lint-the-filesize-split-while-preserving-benchmark-compare
title: "Lint the filesize split while preserving benchmark_compare public re-exports."
type: dead_end
tags:
  - lint
  - refactor
task: compare-project-version-model-economics
edges: []
---

Approach: Lint the filesize split while preserving benchmark_compare public re-exports.
Reason: Ruff treated persist_snapshot and render_comparison imports as unused. Declare the module public surface with __all__ so existing callers keep one import path.
