---
slug: a-task-s-scope-is-measured-from-a-git-anchor-stash-create
title: "A task's scope is measured from a git anchor (stash-create snapshot under refs/tausik/baseline/<slug>), not from started_at"
type: pattern
tags: []
task: scope-gate-baseline-never-moves-after-first-start
edges: []
---

Decision #390, session #272: scripts/task_baseline.py. git stash create records the working tree (committed + uncommitted) without touching it; update-ref keeps the object alive; git diff --name-only <anchor> is 'what this task changed', so work dirty before the task started stops counting. Resume re-anchors and journals BASELINE; close releases the ref. Pass -c user.name/user.email to stash create — a runner without git identity would otherwise fall back to HEAD silently. Tasks started before this landed have no anchor and keep the clock measure.
