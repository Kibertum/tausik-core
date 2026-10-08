---
slug: powershell-does-not-support-bash-heredoc-redirection-for
title: "PowerShell does not support Bash heredoc redirection for inline Python"
type: dead_end
tags: []
task: read-lever-chosen-and-measured
edges: []
---

Approach: PowerShell does not support Bash heredoc redirection for inline Python
Reason: The read-only DB timestamp query used Bash heredoc syntax and failed before execution. Use a PowerShell here-string piped to Python.
