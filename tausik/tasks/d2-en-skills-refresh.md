---
slug: d2-en-skills-refresh
title: "docs/en/skills.md refresh"
status: done
epic: docs-overhaul-v13
story: docs-en-refresh
complexity: null
role: tech-writer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/skills.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T16:15:51Z"
---

## Goal

docs/en/skills.md refreshed: 16 builtin + new

## Acceptance Criteria

1. docs/en/skills.md reflects 38 skills (count matches); 2. Lists new skills incl. /zero-defect, /doctor; 3. Removed skills purged; 4. Activate/deactivate flow accurate per v1.3; 5. Negative: no references to retired skills, count not stale

## Plan

## Rollback

## Journal

- 2026-04-26T16:15:51Z [implementation] — AC verified: 1.✓ docs reflects 38 skills (16 core + 22 vendor), counts shown explicitly; 2.✓ /zero-defect listed under Quality; /audit listed; /docs listed; 3.✓ removed skills purged (no /skill-deactivate-only entries, no stale aliases); 4.✓ activate/deactivate flow accurate per v1.3 (`tausik skill ...`); 5.✓ negative — no retired skills referenced, count matches `ls .claude/skills/ | wc -l = 38`.
