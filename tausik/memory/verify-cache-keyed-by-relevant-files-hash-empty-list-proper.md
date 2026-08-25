---
slug: verify-cache-keyed-by-relevant-files-hash-empty-list-proper
title: "verify cache keyed by relevant_files hash — empty list ≠ proper file set"
type: gotcha
tags:
  - cache
  - qg2
  - relevant_files
  - task_done
  - verify
task: null
edges: []
---

First `tausik verify --task X` ran with task.relevant_files=[] (had not been set yet). It cached an exit=0 run with empty files list. Second `tausik verify --task X --scope standard` reported "Cache HIT" using the empty-files cache, which had [SKIP] pytest because no test_files_for_files matched.

Then `task done --ac-verified --relevant-files A B` failed QG-2: "no fresh tausik verify run for this task" — because the cache lookup hashes the new file set [A, B] which doesn't match the cached empty-set hash.

Fix order:
1. `tausik task update X --relevant-files A B` (set on the task FIRST)
2. `tausik verify --task X --scope standard` (caches with proper files_hash)
3. `tausik task done X --ac-verified` (reads cache by same files_hash)

If you set relevant_files only on `task done`, the verify cache is from a different file set and you'll get the "no fresh verify run" rejection.
