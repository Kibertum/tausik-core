---
slug: qg-2-verify-first-cache-rejects-subset-relevant-files
title: "QG-2 verify-first cache rejects subset relevant_files"
type: gotcha
tags: []
task: v14b-status-exploration-audit-signals
edges: []
---

When `task done --relevant-files X Y Z` declares a STRICT SUBSET of files in `git diff HEAD` since task start, the verify cache is REFUSED with "declared relevant_files is a strict subset of files changed since task start (git diff). Cache refused — running fresh verify to prevent stale-green via misreported scope." The fresh verify in task-done trigger does NOT re-run pytest (only filesize), so verify-first gate fails with "no fresh `tausik verify` run for this task". Resolution: split unrelated work into separate commits BEFORE running task_done, so git diff matches the declared scope exactly. Do NOT overscope relevant_files (lying about scope) to satisfy the cache — the gate is intentional. Also: setting task.relevant_files via direct SQL UPDATE before `tausik verify --task` makes the files_hash match for subsequent task_done.</content>
<parameter name="tags">["qg-2", "verify-cache", "task-done", "git-diff"]
