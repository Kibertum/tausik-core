---
slug: update-assurance-metadata-through-powershell-with-inline
title: "Update assurance metadata through PowerShell with inline JSON and mark the plan through a guessed to"
type: dead_end
tags: []
task: add-cli-version-flag-and-block-session-start-on-a
edges: []
---

Approach: Update assurance metadata through PowerShell with inline JSON and mark the plan through a guessed top-level reason command
Reason: The first JSON form did not survive native argument parsing, and reason is a task subcommand rather than a top-level command; use PowerShell stop-parsing for JSON, task step for plan progress, and task reason-step only for RENAR.
