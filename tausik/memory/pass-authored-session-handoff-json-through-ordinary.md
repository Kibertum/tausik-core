---
slug: pass-authored-session-handoff-json-through-ordinary
title: "Pass authored session-handoff JSON through ordinary PowerShell quoting"
type: dead_end
tags:
  - checkpoint
  - powershell
task: add-memory-only-governance-profile
edges: []
---

Approach: Pass authored session-handoff JSON through ordinary PowerShell quoting
Reason: The Windows native-command boundary stripped JSON quotes; use an argv-preserving caller or equivalent escaping.
