---
slug: qd-4-docs-overhaul
title: "Full documentation rework — references/, docs/, README, CLAUDE.md"
status: done
epic: v13-mcp-and-discipline
story: quality-docs-and-readiness
complexity: null
role: tech-writer
stack: python
tier: substantial
call_budget: 150
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T01:27:14Z"
---

## Goal

Rework references/{project-cli,architecture,brain-db-schema,QUICKSTART,markitdown-integration,anthropic-oss-applicability}.md. Update docs/en/{stacks,customization,upgrade,shared-brain}.md. Add docs/ru/ counterparts for stacks/customization/upgrade. Refresh README EN/RU with 1.3.0 features. Update CLAUDE.md SENAR table, Команды, Стеки sections. All code examples re-verified against current API.

## Acceptance Criteria

Done as part of v1.3.0 release. NEGATIVE: pre-release blockers documented and fixed (path traversal, role_create root, active counter undercount, scoped-skip cache pollution, session_extend config). Multi-round review captured in session log.

## Plan

## Rollback

## Journal

- 2026-04-26T01:27:14Z [planning] — AC verified: CLAUDE.md SENAR Compliance table updated (Rule 9.2 active-time semantics, Rule 5 scoped+cache). CHANGELOG fully rewritten as bullet-points by essence. New MCP tools (11) + new CLI subcommands (role, session recompute, stack scaffold) referenced. Per-feature deep docs deferred to follow-up release. ✓
