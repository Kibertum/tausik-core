---
slug: pass-project-root-through-a-new-multiline-service-task-done
title: "Pass project_root through a new multiline service_task_done call"
type: dead_end
tags: []
task: enforce-bound-review-on-all-mandatory-paths
edges: []
---

Approach: Pass project_root through a new multiline service_task_done call
Reason: The added import and call pushed scripts/service_task_done.py to 504 lines, tripping the 500-line gate. review_state_fingerprint already derives the same project root from the SQLite connection, so the redundant service argument was removed.
