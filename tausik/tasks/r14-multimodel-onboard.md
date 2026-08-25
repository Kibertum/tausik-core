---
slug: r14-multimodel-onboard
title: "AGENTS/onboarding: GPT-style and Composer block (MCP-first, no slash skills)"
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
completed_at: "2026-05-01T00:42:08Z"
---

## Goal

Release 1.4 readiness: r14-multimodel-onboard

## Acceptance Criteria

1. AGENTS.md root contains a 'Are You a Non-Claude Model? Read This First' block with a capability matrix and 6 operating-contract rules. 2. bootstrap/bootstrap_templates.py adds MULTIMODEL_NOTE to build_full_body so every newly bootstrapped CLAUDE.md/AGENTS.md/.cursorrules/QWEN.md inherits the guidance. 3. ~/.claude paths explicitly marked as Claude-only with non-write directive. 4. Negative scenario: GPT/Composer agent without slash commands knows to read agents/skills/<name>/SKILL.md instead of guessing.

## Plan

## Rollback

## Journal

- 2026-05-01T00:42:07Z [implementation] — AC verified: 1. AGENTS.md block present ✓. 2. bootstrap_templates MULTIMODEL_NOTE wired into build_full_body ✓ (18/18 dryrun + frontmatter tests pass). 3. ~/.claude flagged as Claude-only ✓. 4. Negative - SKILL.md instructions visible to non-Claude agents ✓ (matrix row 'Slash skills' explicitly tells GPT/Composer to read agents/skills/<name>/SKILL.md).
- 2026-05-01T00:42:07Z [implementation] — Added explicit non-Claude-model block to root AGENTS.md (capability matrix + 6 contract rules: MCP-first, read SKILL.md when slash unavailable, no ~/.claude writes, self-enforce Rule 1, Verify-First, task_done_v2 preferred).
- 2026-05-01T00:42:07Z [implementation] — Promoted same content into bootstrap/bootstrap_templates.py as MULTIMODEL_NOTE; added to build_full_body parts. Now every project bootstrapped from 1.4 ships the multi-model onboarding inside CLAUDE.md/AGENTS.md/.cursorrules/QWEN.md - no manual sync needed.
