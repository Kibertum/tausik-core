---
slug: run-task-closure-after-refreshing-only-the-default-claude
title: "Run task closure after refreshing only the default Claude profile"
type: dead_end
tags: []
task: prepare-exact-1-11-1-release-inputs
edges: []
---

Approach: Run task closure after refreshing only the default Claude profile
Reason: The 1.11.1 version bump left five other deployed profiles stale, so bootstrap_drift correctly failed. Resolved with bootstrap/bootstrap.py --ide all before canonical verify.
