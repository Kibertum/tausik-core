---
slug: verify-first-relaxed-symmetry-manual-files-satisfies
title: "verify-first relaxed symmetry: manual files=[] satisfies explicit task_done"
type: pattern
tags: []
task: v14b-verify-first-relaxed-symmetry-mirror-lookup-a
edges: []
---

After v14b-verify-first-relaxed-symmetry-mirror-lookup-a (CHANGELOG v1.4.0 polish Phase B Fixed): has_fresh_verify_run now mirrors run_gates_with_cache's one-direction relaxed fallback. Workflow: `tausik verify --task <slug>` (no --relevant-files, records files=[] manual scope) → `task done <slug> --relevant-files X Y Z --ac-verified` works. Strict miss falls back to relaxed lookup that filters by `command LIKE 'trigger=verify|%'` in SQL (so interleaved task-done bucket rows with higher ids don't shadow the verify row). Reverse direction stays strict — explicit verify with files=[A] does NOT auto-satisfy task_done with files=[B]. Security-sensitive paths short-circuit before relaxed branch via existing is_cache_allowed check. Supersedes gotcha #111 (workaround "always pass relevant_files=[]" no longer needed).</content>
<parameter name="tags">["verify-first", "qg-2", "cache", "task-done"]
