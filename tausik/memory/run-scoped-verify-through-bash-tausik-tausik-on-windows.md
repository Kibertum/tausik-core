---
slug: run-scoped-verify-through-bash-tausik-tausik-on-windows
title: "Run scoped verify through bash .tausik/tausik on Windows"
type: dead_end
tags:
  - verify
  - windows
task: guard-host-context-budget-before-session-reopen
edges: []
---

Approach: Run scoped verify through bash .tausik/tausik on Windows
Reason: The wrapper mixed a WSL-style cwd with Windows Python and resolved .claude/scripts/project.py under D:\mnt\d; use the native Windows entrypoint instead.
