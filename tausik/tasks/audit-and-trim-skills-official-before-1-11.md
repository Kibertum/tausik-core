---
slug: audit-and-trim-skills-official-before-1-11
title: "Audit and trim skills-official before 1.11"
status: done
epic: null
story: null
complexity: medium
role: release-engineer
stack: python
tier: moderate
call_budget: null
defect_of: null
scope: "skills-official inventory, its bootstrap/runtime/docs consumers, and focused tests required by any removal"
scope_exclude: "No changes to supported host behavior, no external tracker mutation, commit, push, tag, release or site deployment"
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - QWEN.md
  - "bootstrap/bootstrap.py"
  - "bootstrap/bootstrap_templates.py"
  - "harness/skills/run/SKILL.md"
  - "docs/en/skills.md"
  - "docs/ru/skills.md"
  - "docs/en/skill-bundles.md"
  - "docs/ru/skill-bundles.md"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "docs/en/adding-new-ide.md"
  - "docs/ru/adding-new-ide.md"
  - "docs/en/skill-spec.md"
  - "docs/ru/skill-spec.md"
scope_paths:
  - skills-official
  - bootstrap
  - scripts
  - docs
  - tests
  - harness
scope_tools: []
depends_on: []
completed_at: "2026-10-02T13:01:10Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: gpt-6-astra
started_model_version: null
done_model_id: gpt-6-astra
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Determine which bundled official skills are required by TAUSIK 1.11, remove only redundant or stale material, and document the repository map without weakening supported bootstrap profiles.

## Acceptance Criteria

AC-1 Every skills-official entry is classified by purpose, consumer and release relevance. AC-2 Any removal has no live bootstrap/runtime/docs reference and focused tests remain green; uncertain entries are retained. AC-3 The final report explains each top-level repository directory and the role of root files. Negative: supported host bootstrap must not lose a referenced skill.

## Plan

[{"step": "Inventory every entry and find all consumers", "done": true}, {"step": "Classify keep/remove with evidence and remove only dead material", "done": true}, {"step": "Run focused verification and deliver the repository map", "done": true}]

## Rollback

Restore removed paths and references from the current Git worktree/base revision

## Journal

- 2026-10-02T12:58:01Z [implementation] — Catalog audit: origin manifest has 42 entries, 12 exact duplicates of core and 16 additional overlap/org/internal candidates; local nested checkout has unrelated history, is 6 ahead/21 behind and dirty, so destructive edits are unsafe. Core default deploy remains 14 skills; catalog stubs are excluded.
- 2026-10-02T12:58:01Z [implementation] — Removed stale catalog counts and copied inventory from core docs/generated guidance; per-skill install is now canonical and full-catalog exposure is legacy only. Kept external repo untouched; fixed invalid core /run effort metadata (deep -> slow).
- 2026-10-02T13:00:54Z [implementation] — AC-1: ✓ origin manifest classified: 42 entries; 12 exact core duplicates, 10 functional duplicates, 5 organization-specific, 1 maintainer-only, 14 keep candidates. AC-2: ✓ tests/test_bootstrap_skills_coverage.py::TestBootstrapSkillsCoverage::test_default_excludes_official_stubs. AC-3: ✓ repository top-level map inspected against tracked paths. Negative: bootstrap --ide all deployed 14 core skills and no official stubs; external dirty checkout was not modified. Domain: public core remains usable without skills-official and recommends per-skill installation. Verification: #3382.
- 2026-10-02T13:00:54Z [implementation] — Focused validation: 389 passed; affected-test verify #3382 selected 58/656 files and passed 1,181 with 16 skipped and 51 deselected. Repository map prepared for owner handoff.
- 2026-10-02T13:01:09Z [implementation] — NO-DEAD-END: verify #3381 stopped at the formatter because bootstrap/bootstrap.py had pre-existing unformatted edits; ruff formatted the declared file and identical verify #3382 passed.
