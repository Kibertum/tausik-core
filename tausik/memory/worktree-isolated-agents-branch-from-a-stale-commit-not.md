---
slug: worktree-isolated-agents-branch-from-a-stale-commit-not
title: "Worktree-isolated agents branch from a STALE commit, not current HEAD — patches unusable"
type: gotcha
tags:
  - git
  - gotcha
  - multiagent
  - swarm
  - wave2
  - worktree
task: null
edges: []
---

Spawning Agent-tool subagents with isolation:worktree (Wave 2 swarm, session #140) created worktrees branched from ce3a3d3 (2026-07-18), ~8 days and many commits BEHIND the session HEAD (6db6ea3). Consequence: the agents implemented on a stale base — bash_firewall.py diverged 78/66 lines and test_hooks.py was missing 328 lines vs HEAD, so `git diff HEAD..worktree-branch` was dominated by base divergence (344 files / 38008 deletions) and the patches could NOT be applied without silently reverting 8 days of work. Both agents also created their own active tasks in the SHARED .tausik/tausik.db (task-gate hook fired inside the worktree, which resolved .tausik up to the main repo), duplicating the planning slugs. **How to avoid:** (1) Do NOT use isolation:worktree for integration-bound patches in this environment — the worktree base is not the working HEAD. (2) Prefer NON-worktree agents that RETURN A SPEC (analysis + precise proposed diff as text), and implement on the correct base yourself. (3) If worktrees are used, verify `git merge-base HEAD <worktree-branch>` == HEAD before trusting any diff; extract only named new functions, never a blind apply. (4) Agents editing under isolation still write to the shared project DB via the task gate — expect stray tasks to clean up. Related: [[full-pytest-concurrent-with-tausik-cli-false-config-mutation]].
