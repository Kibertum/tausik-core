---
slug: r14-mcp-docs
title: "Sync MCP docs (tool counts, brain fields, stack name, verify API) with schemas"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: null
role: null
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T00:21:45Z"
---

## Goal

Release 1.4 readiness: r14-mcp-docs

## Acceptance Criteria

1. Tool count synced: 96+stub → 97 actual (91 project + 6 brain). 2. Brain field schemas synced: title/body → name/decision/url/content per category. 3. tausik_verify entry honestly documents current API (task_slug required) and points to v1.4 Verify-First Contract section. 4. Verify-First Contract section added to both EN and RU mcp.md with workflow. 5. Negative scenario - if user reads docs and tries to use brain_store_decision with body (old schema) they get clear MCP error from server about required fields. Doc no longer misleads them.

## Plan

## Rollback

## Journal

- 2026-05-01T00:21:45Z [implementation] — AC verified: 1. Tool count synced (97 actual, was misreported 96) ✓ 2. Brain field schemas synced (name/decision/description/content) ✓ 3. tausik_verify documented honestly (task_slug required) ✓ 4. Verify-First Contract section present in both EN and RU mcp.md ✓ 5. Negative scenario - misleading old schema removed; new docs match real input schemas ✓
- 2026-05-01T00:21:45Z [implementation] — docs/{en,ru}/mcp.md updated: tool count 96→97 (91 project + 6 brain), brain_store_* fields title/body → name/decision per actual tools.py schema, brain_get adds category required, brain_cache_web adds url, version 1.3→1.4, Verify-First Contract section added with MCP workflow.
