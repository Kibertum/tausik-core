---
slug: release-verify-3512-after-final-l3-approval
title: "Release verify #3512 after final L3 approval"
type: dead_end
tags: []
task: release-tausik-1-11-1
edges: []
---

Approach: Release verify #3512 after final L3 approval
Reason: ruff formatting expanded the target-project L3 call and raised service_task_done.py to 503 lines, so filesize blocked before pytest; factored the project root local to restore headroom without behavior change.
