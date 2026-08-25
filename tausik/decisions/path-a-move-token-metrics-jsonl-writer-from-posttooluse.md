---
slug: path-a-move-token-metrics-jsonl-writer-from-posttooluse
task: v14b-defect-token-metrics-no-realworld-write
date: "2026-05-06"
edges: []
---

## Decision

Path A — move token_metrics.jsonl writer from PostToolUse hook to SessionEnd transcript-parser. Per-tool attribution: split message-level usage across tool_use blocks in the same assistant entry. Drop the broken PostToolUse hook entirely.

## Rationale

Claude Code PostToolUse payload contains tool_name/tool_input/tool_response (return value of the tool), NOT API usage. Token usage is message-level only — known from the transcript JSONL after a turn completes. Path A reuses the existing scripts/hooks/session_metrics.py SessionEnd hook (which already parses transcripts) and extends it with one additional emitter that writes rows to .tausik/token_metrics.jsonl with the schema service_token_metrics.aggregate() expects (session_id, tool_name, input_tokens, output_tokens, cache_read, cache_create, model, ts). Per-tool attribution = message-level usage / count of tool_use blocks in that assistant entry — best approximation possible given message-level granularity. Path B (deprecate per-tool granularity) was rejected because service_token_metrics.aggregate() already produces per-tool p50/p90 output, and the v14b-subagent-reviewer Gate A decision needs that breakdown to know which tools dominate context cost.
