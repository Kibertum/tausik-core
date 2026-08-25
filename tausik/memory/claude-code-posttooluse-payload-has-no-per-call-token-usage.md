---
slug: claude-code-posttooluse-payload-has-no-per-call-token-usage
title: "Claude Code PostToolUse payload has no per-call token usage"
type: gotcha
tags:
  - claude-code
  - hooks
  - payload-shape
  - telemetry
task: v14b-defect-token-metrics-no-realworld-write
edges: []
---

PostToolUse hook payload structure: {tool_name, tool_input, tool_response}. `tool_response` is the tool's RETURN VALUE (file content for Read, stdout/exit code for Bash, etc.) — it does NOT contain `usage` or `model`. API token usage is message-level only and surfaces in the transcript JSONL after each turn (`message.usage` with input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens). Any per-tool-call token telemetry MUST be derived from the transcript at SessionEnd, not from PostToolUse stdin. The original v14b-baseline-token-metrics design (scripts/hooks/token_metrics.py) failed silently in production for this reason — it was unit-tested with synthetic payloads that fabricated tool_response.usage. Replacement lives in scripts/hooks/session_metrics.py (extract_token_rows). Same caveat may apply to scripts/hooks/posttool_usage.py — audit before relying on it.
