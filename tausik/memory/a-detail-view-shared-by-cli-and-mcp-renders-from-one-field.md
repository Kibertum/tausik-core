---
slug: a-detail-view-shared-by-cli-and-mcp-renders-from-one-field
title: "A detail view shared by CLI and MCP renders from ONE field tuple module, never two lists"
type: pattern
tags: []
task: mcp-task-show-hides-the-fields-the-agent-is-judged-by
edges: []
---

Session #269: MCP tausik_task_show listed 6 fields, CLI task show 26 — scope_paths and rollback_plan, the fields gates judge by, were invisible over MCP. Fix shape: scripts/task_detail_fields.py (TASK_DETAIL_FIELDS + detail_lines) called by both; a test greps both callers for detail_lines and refuses a second literal list. Same class as mcp-update-claudemd-erases-the-memory-tail.
