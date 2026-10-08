---
slug: qwen-hook-matchers-equalised-with-claude-1-10-qwen-hooks
task: qwen-hooks-are-a-second-copy-of-the-declaration
date: "2026-09-23"
edges: []
---

## Decision

QWEN HOOK MATCHERS EQUALISED WITH CLAUDE (1.10, qwen-hooks-are-a-second-copy-of-the-declaration); the four accepted differences in gate_cross_model_parity.DECLARED_DIFFERENCES are withdrawn. Qwen now registers activity_event, task_call_counter and the truncation nudge on Claude's matchers instead of every tool, and task_done_verify runs on the MCP tool AND the shell on every host. Consequence, stated: Qwen's gap-based active time and call counts shrink to Claude's unit from this release — Qwen numbers before and after are not comparable. Accepted because since #376/#380 session time and call capacity are signals, not gates, so no refusal rests on the old Qwen unit; the same work now yields the same number on both hosts; and the 1.9 economy baseline (#338) was fixed against Claude, whose matchers did not change.

## Rationale
