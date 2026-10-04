---
slug: update-task-assurance-profiles-impact-and-relevant-files-in
title: "Update task assurance profiles, impact and relevant files in one PowerShell CLI call."
type: dead_end
tags:
  - cli
  - quoting
task: compare-project-version-model-economics
edges: []
---

Approach: Update task assurance profiles, impact and relevant files in one PowerShell CLI call.
Reason: Windows native argument quoting stripped the JSON string before the CLI parser. Apply the file scope separately; retain the conservative L2 fallback rather than spending more calls on metadata that does not change verification.
