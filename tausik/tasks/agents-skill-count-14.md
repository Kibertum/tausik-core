---
slug: agents-skill-count-14
title: "Синхронизировать onboarding AGENTS с 14 core навыками"
status: done
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
relevant_files:
  - AGENTS.md
  - "tests/test_check_docs_hook.py"
scope_paths:
  - AGENTS.md
  - "tests/test_check_docs_hook.py"
  - "tausik/tasks/agents-skill-count-14.md"
  - "tausik/tasks/root-skill-count-14.md"
  - "tausik/stories/release19-effective-context.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T12:12:40Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Устранить static core-skill count drift в AGENTS.md, который блокирует check_docs после добавления /i-have-adhd.

## Acceptance Criteria

AC-1: AGENTS.md static repository structure describes 14 core skills, matching generated constants. AC-2: dynamic state block remains framework-generated rather than hand-edited. AC-3: negative boundary: check_docs still rejects a stale 13-core declaration. AC-4: focused check-docs test and signed verify pass.

## Plan

[{"step": "Confirm the stale static AGENTS count and preserve the dynamic block boundary.", "done": true}, {"step": "Correct only the static count to the canonical generated value.", "done": true}, {"step": "Run focused check-docs proof and signed verify, then unblock the dependent documentation tasks.", "done": true}]

## Rollback

Revert the one static onboarding count correction if canonical constants change.

## Journal

- 2026-09-12T10:25:20Z [implementation] — Corrected only AGENTS.md's static repository-tree count (13→14), leaving the DYNAMIC block untouched. Running the authoritative check-docs proof now.
- 2026-09-12T10:25:47Z [implementation] — Found and corrected both static AGENTS references: documentation-map label and repository-tree count, each 13→14. DYNAMIC region remains unchanged by this task.
- 2026-09-12T10:52:33Z [implementation] — After the backlog-state commit, the real-repository check_docs test and pytest dedupe audit are rerun against the static 14-core onboarding correction.
- 2026-09-12T12:11:51Z [implementation] — Root cause (documentation): AGENTS.md carries two static core-skill counts (documentation-map row and repository-tree line) that are hand-maintained, and the skill-adding commit 4720e8e0 updated neither, so check_docs compared generated 14 against static 13. Prevention: the static count now matches generated constants; the check-docs real-repo test guards it, and the next skill addition must touch both static lines (they are named in this task's notes).
- 2026-09-12T12:11:52Z [implementation] — AC verified: AC-1 ✓ AGENTS.md:100 and :111 both read 14 core skills, equal to skills_core_count=14 in docs/_generated/constants.json. AC-2 ✓ exactly one DYNAMIC:START/END pair remains and git shows the block untouched by the two static edits in 6013fb2e. AC-3 ✓ TestDriftDetected::test_drifted_json_returns_1 still rejects a stale declaration. AC-4 ✓ tests/test_check_docs_hook.py 6/6 green, signed verify below. Domain: a fresh agent reading AGENTS.md sees the same catalog size that bootstrap actually deploys (14 + brain conditional).
