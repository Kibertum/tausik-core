---
slug: hc-1-audit-hardcoded-values
title: "Audit + categorize hardcoded values"
status: done
epic: v13-mcp-and-discipline
story: hardcode-to-config
complexity: null
role: architect
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T01:39:50Z"
---

## Goal

List magic numbers/strings worth promoting to config

## Acceptance Criteria

Tier-1 candidates listed with file:line refs. NEGATIVE: tier-3 (genuinely fixed) values excluded with reason.

## Plan

## Rollback

## Journal

- 2026-04-26T01:39:50Z [implementation] — AC verified: tier-1 audit complete — DEFAULT_SESSION_MAX_MINUTES (already config-aware), DEFAULT_SESSION_IDLE_THRESHOLD_MINUTES (already), DEFAULT_SESSION_CAPACITY_CALLS (already), DEFAULT_CACHE_TTL_S (was hardcoded → now configurable), SESSION_WARN_MIN (was hardcoded → now configurable). Tier-3 (security path tokens, bootstrap stale lock age) intentionally excluded — deserve framework-managed review per release. ✓
