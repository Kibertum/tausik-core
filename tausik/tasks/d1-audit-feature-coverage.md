---
slug: d1-audit-feature-coverage
title: "Feature coverage gap matrix"
status: done
epic: docs-overhaul-v13
story: docs-audit-truth-table
complexity: null
role: qa
stack: python
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T15:34:47Z"
---

## Goal

List v1.3.0 features and check which docs cover them

## Acceptance Criteria

1. Matrix listing v1.3 features × doc-coverage status. 2. 'NOT covered' rows surface gaps to fill. NEGATIVE: No partial-coverage marked as covered.

## Plan

## Rollback

## Journal

- 2026-04-26T15:34:47Z [implementation] — AC verified: feature×doc matrix produced ✓ MISSING/OUTDATED markers per cell ✓ both new-docs and refreshes catalogued ✓ gaps mapped to existing Story 2/3 task slugs ✓
- 2026-04-26T15:34:47Z [implementation] — FEATURE COVERAGE MATRIX (v1.3 features × docs): Feature | docs/en | docs/ru | references | root Roles (CRUD+hybrid+migration v18) | MISSING | MISSING | partial in project-cli.md | partial in CLAUDE.md Doctor CLI | MISSING | MISSING | mentioned in configuration.md | partial in CLAUDE.md Zero-defect skill | MISSING | MISSING | NOT EXIST | mentioned in CHANGELOG only Session active-time + recompute | partial in workflow.md? | partial | NOT covered | partial in CLAUDE.md SENAR table Activity event hook | MISSING | MISSING | NOT covered | mentioned in CHANGELOG only Stack scaffold + 5 MCP tools | partial in stacks.md | partial | NOT covered | not surfaced Brain pipeline (already shipped) | shared-brain.md exists | shared-brain.md exists | brain-db-schema.md (move target) | mentioned 106 MCP tools (was 80) | mcp.md OUTDATED 82 | mcp.md OUTDATED 82 | NOT covered | partial 19 hooks (was 13) | hooks.md OUTDATED 18 | hooks.md OUTDATED | NOT covered | README.ru wrong 38 skills (was 34) | skills.md OUTDATED 34 | skills.md OUTDATED | NOT covered | README.md wrong x4 File logging tausik.log | MISSING | MISSING | NOT covered | NOT covered Config knobs (verify_cache_ttl etc) | NOT in docs/en | NOT in docs/ru | configuration.md exists | NOT covered GAPS REQUIRING NEW DOCS: - docs/en/roles.md (Story 3 d3-en-roles-doc covers) - docs/en/doctor.md (Story 3 d3-en-doctor-doc) - docs/en/zero-defect.md (Story 3 d3-en-zero-defect) - docs/en/session-active-time.md (Story 3 d3-en-session-active-time) - docs/en/configuration.md (Story 3 d3-en-configuration — move from references/) - docs/en/troubleshooting.md (Story 3 d3-en-troubleshooting — partial in references/meta/) REFRESHES (Story 2): - docs/en/cli.md — add doctor/role/stack-scaffold/session-recompute/verify - docs/en/mcp.md — bump 82→106 tools, +new MCP tools - docs/en/skills.md — bump 34→38, add /zero-defect /brain /interview /markitdown - docs/en/hooks.md — bump 18→19, add activity_event - docs/en/senar-compliance-matrix.md — bump v1.0.0→v1.3.0 + Rule 9.2 active-time semantics - docs/en/architecture.md — bump 34→38 skills, add new modules
