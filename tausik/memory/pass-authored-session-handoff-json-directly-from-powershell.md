---
slug: pass-authored-session-handoff-json-directly-from-powershell
title: "Pass authored session handoff JSON directly from PowerShell as a native CLI argument"
type: dead_end
tags: []
task: prepare-exact-1-11-1-release-inputs
edges: []
---

Approach: Pass authored session handoff JSON directly from PowerShell as a native CLI argument
Reason: Windows native argument quoting stripped or split embedded JSON quotes and spaces. Passing the JSON through an environment variable to Python subprocess with an argv list preserved it exactly.
