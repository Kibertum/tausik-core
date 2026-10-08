---
slug: pre-flight-workspace-scan-to-prevent-agent-hallucinated
title: "Pre-flight workspace scan to prevent agent-hallucinated duplicates"
type: pattern
tags:
  - agent-safety
  - anti-hallucination
  - architecture
  - brain
  - notion
  - wizard
task: v133-impl
edges: []
---

When a setup wizard creates global / workspace-level resources (Notion DBs, S3 buckets, Slack channels, etc.) that are meant to be singletons across projects, do NOT rely on docs alone to prevent agents from creating duplicates. Add a pre-flight scan that calls the relevant search/list API, matches by canonical title/name, and refuses to proceed when an existing resource is detected. Combine with: (a) explicit `--join-existing` flag that auto-discovers + verifies before writing config, (b) explicit `--force-create` escape hatch with extra confirmation prompt + audit log, (c) defensive degradation when the scan API itself fails (warn + proceed, rather than block). The pre-flight runs BEFORE prompting for create-time inputs (parent page id, etc.) so users in --join-existing mode never have to answer create-only prompts.
