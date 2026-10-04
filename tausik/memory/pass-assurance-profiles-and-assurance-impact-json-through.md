---
slug: pass-assurance-profiles-and-assurance-impact-json-through
title: "Pass assurance_profiles and assurance_impact JSON through PowerShell CLI quoting"
type: dead_end
tags:
  - json
  - powershell
  - task-update
task: route-ship-by-residual-assurance
edges: []
---

Approach: Pass assurance_profiles and assurance_impact JSON through PowerShell CLI quoting
Reason: PowerShell removed the JSON string quoting before argparse/service parsing, so task update returned 'assurance_profiles must be valid JSON'. Use the typed MCP task_update fields instead.
