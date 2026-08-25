---
slug: qd-6-changelog-and-version
title: "CHANGELOG consolidation + version bump (NO tag, NO push)"
status: done
epic: v13-mcp-and-discipline
story: quality-docs-and-readiness
complexity: null
role: tech-writer
stack: python
tier: light
call_budget: 25
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

Merge two [Unreleased] blocks + existing [1.3.0] entry into single consolidated [1.3.0] — 2026-04-26 with bullet-points by essence (no tech details). Bump Version markers in CLAUDE.md DYNAMIC + bootstrap + any version.py. Tag and push intentionally NOT performed — release on user's command.

## Acceptance Criteria

Done as part of v1.3.0 release. NEGATIVE: pre-release blockers documented and fixed (path traversal, role_create root, active counter undercount, scoped-skip cache pollution, session_extend config). Multi-round review captured in session log.

## Plan

## Rollback

## Journal

- 2026-04-26T01:27:14Z [planning] — AC verified: CHANGELOG [1.3.0] consolidated entry replaces both [Unreleased] sections + relabels old [1.3.0] as [1.3.0-pre]. tausik_version.py at 1.3.0. CLAUDE.md DYNAMIC at 1.3.0. NO tag, NO push (intentional). ✓
