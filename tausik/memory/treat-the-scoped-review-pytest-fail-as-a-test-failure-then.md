---
slug: treat-the-scoped-review-pytest-fail-as-a-test-failure-then
title: "Treat the scoped review pytest FAIL as a test failure, then re-run with TAUSIK_VERIFY_FULL=1."
type: dead_end
tags:
  - gate
  - release-1.9
  - scoped-pytest
  - verification
task: session-rollup-window-attribution
edges: []
---

Approach: Treat the scoped review pytest FAIL as a test failure, then re-run with TAUSIK_VERIFY_FULL=1.
Reason: Both runs emitted 55 passed for the first scoped batch yet exited nonzero after later batches. The full marker override does not solve a batch that has no collected tests; no current-task source defect was demonstrated. The scoped-pytest gate must be investigated under its own scope rather than weakening or bypassing it here.
