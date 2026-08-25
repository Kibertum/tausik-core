---
slug: auto-format-hook-restores-blank-line-after-function-level
title: "Auto-format hook restores blank line after function-level imports"
type: gotcha
tags:
  - "ruff,filesize,gotcha,auto-format"
task: v14b-baseline-token-metrics
edges: []
---

ruff format (run via PostToolUse:Edit auto_format.py hook) re-inserts a blank line between an inline import and the next statement, even if you explicitly removed it to save lines for the filesize gate. To keep the file under 400 strict, extract the helper to a new file rather than inline-compactify — the formatter wins. Discovered while shrinking project_cli_ops.py during baseline-token-metrics close.
