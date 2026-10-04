---
slug: import-usage-codex-report-as-a-package-without-adding
title: "Import usage_codex_report as a package without adding scripts to sys.path"
type: dead_end
tags:
  - codex
  - telemetry
task: r111-economy-hardening-acceptance
edges: []
---

Approach: Import usage_codex_report as a package without adding scripts to sys.path
Reason: The report module uses sibling absolute imports; invoke it with scripts on sys.path or through its public caller.
