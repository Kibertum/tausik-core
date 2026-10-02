---
slug: place-pytestmark-before-deferred-project-imports
title: "Place pytestmark before deferred project imports"
type: dead_end
tags: []
task: make-delegation-tests-host-deterministic-in-ci
edges: []
---

Approach: Place pytestmark before deferred project imports
Reason: Ruff E402: path injection requires the project imports to remain before module assignments.
