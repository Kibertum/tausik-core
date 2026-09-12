---
slug: agents-skill-count-14
title: "Синхронизировать onboarding AGENTS с 14 core навыками"
status: active
epic: release-19-agent-effectiveness
story: release19-effective-context
complexity: simple
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: root-skill-count-14
scope: "Edit only the static AGENTS.md core-skill count; do not alter its dynamic state block; use the existing focused check-docs proof."
scope_exclude: "Do not alter generated constants, README, skills, bootstrap behavior, release/tag/push or user-owned .agents/."
relevant_files: []
scope_paths:
  - AGENTS.md
  - "tests/test_check_docs_hook.py"
  - "tausik/tasks/agents-skill-count-14.md"
  - "tausik/tasks/root-skill-count-14.md"
  - "tausik/stories/release19-effective-context.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Устранить static core-skill count drift в AGENTS.md, который блокирует check_docs после добавления /i-have-adhd.

## Acceptance Criteria

AC-1: AGENTS.md static repository structure describes 14 core skills, matching generated constants. AC-2: dynamic state block remains framework-generated rather than hand-edited. AC-3: negative boundary: check_docs still rejects a stale 13-core declaration. AC-4: focused check-docs test and signed verify pass.

## Plan

[{"step": "Confirm the stale static AGENTS count and preserve the dynamic block boundary.", "done": true}, {"step": "Correct only the static count to the canonical generated value.", "done": true}, {"step": "Run focused check-docs proof and signed verify, then unblock the dependent documentation tasks.", "done": false}]

## Rollback

Revert the one static onboarding count correction if canonical constants change.

## Journal

- 2026-09-12T10:25:20Z [implementation] — Corrected only AGENTS.md's static repository-tree count (13→14), leaving the DYNAMIC block untouched. Running the authoritative check-docs proof now.
- 2026-09-12T10:25:47Z [implementation] — Found and corrected both static AGENTS references: documentation-map label and repository-tree count, each 13→14. DYNAMIC region remains unchanged by this task.
