---
slug: treat-the-pre-existing-parse-error-test-as-still-asserting
title: "Treat the pre-existing parse-error test as still asserting the current contract"
type: dead_end
tags: []
task: select-affected-tests-for-ordinary-verify
edges: []
---

Approach: Treat the pre-existing parse-error test as still asserting the current contract
Reason: Verify #3344 showed it pinned the superseded fail-closed behavior; rewrite it to prove fail-open runs the full lane and preserves pytest's real red verdict.
