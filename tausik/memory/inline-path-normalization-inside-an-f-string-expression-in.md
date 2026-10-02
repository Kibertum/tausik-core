---
slug: inline-path-normalization-inside-an-f-string-expression-in
title: "Inline path normalization inside an f-string expression in affected_test_selection.py"
type: dead_end
tags:
  - python
  - selector
task: select-affected-tests-for-ordinary-verify
edges: []
---

Approach: Inline path normalization inside an f-string expression in affected_test_selection.py
Reason: Python 3.11 rejects backslashes inside f-string expressions; normalize the path before the predicate instead.
