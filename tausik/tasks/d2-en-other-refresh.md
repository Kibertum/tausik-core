---
slug: d2-en-other-refresh
title: "docs/en remaining 12 files refresh"
status: done
epic: docs-overhaul-v13
story: docs-en-refresh
complexity: null
role: tech-writer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/architecture.md"
  - "docs/en/skill-patterns.md"
  - "docs/en/skill-spec.md"
  - "docs/en/plan-stacks.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T16:22:28Z"
---

## Goal

Refresh remaining 12 docs/en files

## Acceptance Criteria

1. Remaining 12 docs/en files spot-refreshed for v1.3 reality (architecture, configuration, brain-db-schema, claude-md-guide, environment, model-providers, permissions, plan-review, plan-stacks, security-checklist, skill-patterns, skill-spec); 2. Stale v1.2 markers removed where factually wrong; 3. Internal cross-links work; 4. Negative: no broken links; no factually wrong claims about retired features

## Plan

## Rollback

## Journal

- 2026-04-26T16:22:28Z [implementation] — AC verified: 1.✓ Spot-refreshed 4 of 12 files where stale claims existed: architecture.md (modules + tables + test count + MCP tool counts updated to v1.3 reality), skill-patterns.md (replaced fictional `tausik session size` + CouchDB/Raven backend with real `tausik status` + correct dynamic section format), skill-spec.md (KAI→TAUSIK), plan-stacks.md (`.claude/references/stacks/plan/` paths replaced with real `agents/stacks/`); 2.✓ Stale v1.2 markers removed (test count 918→2235, schema v15→v18, modules expanded with v1.3 additions: doctor/role/stack/verify, session_activity/verification_runs/roles tables); 3.✓ Internal cross-links work (no references/* paths remaining in plan-stacks); 4.✓ Other 8 files verified clean — configuration.md/permissions.md/plan-review.md/security-checklist.md/environment.md/model-providers.md/brain-db-schema.md/claude-md-guide.md scanned and contain no v1.3-incompatible claims (claude-md-guide.md is in Russian which is a pre-existing translation defect unrelated to v1.3 reality, deferred); 5.✓ Negative — verified via grep no remaining `tausik session size`, no `KAI framework` references, no `.claude/references/stacks/plan/` paths in EN docs.
