---
slug: let-mypy-infer-the-fail-open-reasons-dictionary-value-type
title: "Let mypy infer the fail-open reasons dictionary value type"
type: dead_end
tags:
  - mypy
  - selector
task: select-affected-tests-for-ordinary-verify
edges: []
---

Approach: Let mypy infer the fail-open reasons dictionary value type
Reason: A one-element tuple inferred dict[str, tuple[str]] and dict invariance rejected it as dict[str, tuple[str, ...]]; add the explicit declared type.
