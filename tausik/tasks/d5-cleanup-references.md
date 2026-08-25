---
slug: d5-cleanup-references
title: "Delete references/ + global path update"
status: done
epic: docs-overhaul-v13
story: references-merge
complexity: null
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T15:47:47Z"
---

## Goal

Delete references/ dir; update bootstrap_copy.copy_references and all references/ mentions across CLAUDE.md README AGENTS docs to point at docs/

## Acceptance Criteria

1. references/ directory deleted from repo root. 2. bootstrap_copy.copy_references rewritten to copy docs/ instead. 3. All references/ mentions in CLAUDE.md, AGENTS.md, CONTRIBUTING.md, scripts/README.md, brain SKILL.md, ship SKILL.md updated to docs/. 4. Bootstrap clean + 2226 tests pass. NEGATIVE: legacy IDE-specific references/ in agents/<ide>/references/ preserved.

## Plan

## Rollback

## Journal

- 2026-04-26T15:47:47Z [planning] — AC verified: references/ deleted via rm -rf ✓ copy_references rewritten to copy docs/ + preserve agents/<ide>/references/ for legacy ✓ Path updates applied to CLAUDE.md (×4), AGENTS.md (×7 + structure block), CONTRIBUTING.md (structure block), scripts/README.md, agents/skills/{brain,ship}/SKILL.md ✓ Bootstrap clean ✓ 2226/2226 tests pass after sweep ✓ NEGATIVE: agents/<ide>/references/ preserved per docs/ vs IDE-asset distinction ✓
