---
slug: verify-cache-invalidates-when-relevant-files-changes
title: "Verify cache invalidates when relevant_files changes"
type: gotcha
tags:
  - "verify,cache,workflow"
task: v14b-baseline-token-metrics
edges: []
---

tausik verify --task caches by hash of (task_slug, relevant_files set). Updating task_update --relevant-files invalidates the cache, forcing a re-run on next task_done. Order matters: set relevant_files FIRST, then verify, then task done. Hit during baseline-token-metrics close (added bootstrap_qwen.py post-verify, had to re-verify before task done).
