---
slug: big-feature-umbrella-tasks-scope-down-spin-off-follow-ups
title: "Big \"feature umbrella\" tasks: scope down + spin off follow-ups instead of closing in one shot"
type: pattern
tags:
  - follow-ups
  - phase-b
  - scoping
  - task-management
task: null
edges: []
---

Several Phase B tasks (token-tier1-quick-wins, junk-audit-pass, skill-bundles-marketplace) had 6-10 sub-AC items spanning multiple subsystems. Trying to close them in one session burns the context window and produces shallow work on each piece.

Pattern that worked this session:
1. Update parent task AC to scope ONLY the most concrete 2-3 items achievable in remaining session budget.
2. Implement those items, with tests + verify + close.
3. For each deferred sub-AC, create a focused follow-up task via `task_add --story_slug <parent-story>`, naming it `<parent-slug>-<sub-id>` (e.g. token-tier1 → token-t12-todo-reminder, token-t13-prompt-caching-docs, token-t15-evidence-json).
4. Document the deferral explicitly in the parent's task_log so it's clear what's done vs. spun-off.

This gave 5 closed Phase B tasks + 6 follow-ups in one session vs. probably 1-2 partial closures otherwise. Use whenever a parent task has >5 ACs that touch independent subsystems.
