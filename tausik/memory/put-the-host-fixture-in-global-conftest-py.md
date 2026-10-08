---
slug: put-the-host-fixture-in-global-conftest-py
title: "Put the host fixture in global conftest.py"
type: dead_end
tags: []
task: make-delegation-tests-host-deterministic-in-ci
edges: []
---

Approach: Put the host fixture in global conftest.py
Reason: It made affected-test selection correctly fail open across all 654 test files and exposed unrelated private historical task data; local per-module fixtures keep the contract bounded.
