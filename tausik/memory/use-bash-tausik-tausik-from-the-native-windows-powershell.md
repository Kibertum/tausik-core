---
slug: use-bash-tausik-tausik-from-the-native-windows-powershell
title: "Use bash .tausik/tausik from the native Windows PowerShell execution host"
type: dead_end
tags:
  - cli
  - windows
task: r111-bounded-work-packet
edges: []
---

Approach: Use bash .tausik/tausik from the native Windows PowerShell execution host
Reason: bash resolved the repository as /mnt/d while invoking Windows Python, producing D:\mnt\d\... and file-not-found. Use python scripts/project.py for fresh CLI fallback here.
