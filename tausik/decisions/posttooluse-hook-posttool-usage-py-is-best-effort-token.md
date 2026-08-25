---
slug: posttooluse-hook-posttool-usage-py-is-best-effort-token
task: v14b-usage-events-auto-write
date: "2026-05-03"
edges: []
---

## Decision

PostToolUse hook (posttool_usage.py) is best-effort token attribution: every tool call writes a usage_events row attributed to the single active task (NULL when 0 or >1). Token counts come from the harness payload when present, otherwise tokens=0/tool_calls=1 to keep the call count honest.

## Rationale

Claude Code does not currently expose per-tool token usage in the PostToolUse stdin schema for every tool. Two alternatives were considered and rejected: (1) inferring tokens by reading transcript JSONL on every tool call — rejected because it would race the harness writer and add I/O on the hot path; (2) skipping rows when tokens are unknown — rejected because the call count is itself useful for SENAR Rule 7 calibration drift. Writing tokens=0 rows preserves attribution while signalling "no usage data" to consumers. Cost rollup (tausik metrics cost) already excludes NULL slugs, so non-attributable events stay in the ledger for audit but don't pollute per-task numbers. Refuse-to-guess on multi-active-task is intentional: silently picking one would corrupt the calibration metric across tasks.
