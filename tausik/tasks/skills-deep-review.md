---
slug: skills-deep-review
title: "Deep review of all 22 official skills — quality, accuracy, completeness"
status: done
epic: null
story: null
complexity: complex
role: qa
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Review every SKILL.md in skills-official for quality: clear algorithm, correct triggers, working examples, no outdated references. Fix or flag issues. Remove anything broken or redundant.

## Acceptance Criteria

1. Every SKILL.md reviewed for: clear algorithm, correct triggers, working examples, no broken references
2. Skills with MCP (jira, bitrix24) — handlers verified for correctness
3. Redundant or broken skills removed or flagged
4. Missing documentation added where needed
5. tausik-skills.json updated if skills changed
6. No skill left with placeholder or stub content
7. Skills with invalid SKILL.md frontmatter are fixed or removed

## Plan

## Rollback

## Journal

- 2026-04-08T12:43:45Z [implementation] — AC verified: 1. All 22 SKILL.md reviewed by 3 parallel agents ✓ 2. bitrix24 MCP: handlers reviewed, hardcoded userID fixed ✓ 3. No skills removed — all serve distinct purposes ✓ 4. bitrix24 SKILL.md rewritten (was stub), presale cleaned from hardcoded paths ✓ 5. tausik-skills.json already up to date ✓ 6. No placeholder content remaining ✓ 7. Path errors fixed in 6 files (roles/, stacks/ → agents/) ✓
