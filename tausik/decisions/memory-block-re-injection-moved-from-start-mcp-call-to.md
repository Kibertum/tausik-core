---
slug: memory-block-re-injection-moved-from-start-mcp-call-to
task: update-claudemd-memory-tail
date: "2026-05-06"
edges: []
---

## Decision

memory_block re-injection moved from /start MCP call to CLAUDE.md via update_claudemd. New helper build_compact_memory_tail(be) in service_knowledge_aggregates.py renders 5 decisions + 5 conventions + 3 dead ends as one-line bullets inside DYNAMIC:START/END markers.

## Rationale

CLAUDE.md is loaded into agent context every turn. A separate tausik_memory_block MCP call duplicated content already accessible via CLAUDE.md. Embedding once amortises the cost across sessions and removes /start latency. Subsection is omitted on empty DB so cost is zero when no knowledge exists.
