---
slug: skills-hardening-review-language-improve-quality
title: "Skills hardening — review language, improve quality"
status: done
epic: null
story: null
complexity: null
role: architect
stack: null
tier: null
call_budget: null
defect_of: null
scope: "skills/*/SKILL.md"
scope_exclude: null
relevant_files:
  - "agents/skills/task/SKILL.md"
  - "agents/skills/plan/SKILL.md"
  - "agents/skills/ship/SKILL.md"
  - "agents/skills/commit/SKILL.md"
  - "agents/skills/end/SKILL.md"
  - "agents/skills/checkpoint/SKILL.md"
  - "agents/skills/explore/SKILL.md"
  - "agents/skills/review/SKILL.md"
  - "agents/skills/debug/SKILL.md"
  - "agents/skills/test/SKILL.md"
  - CLAUDE.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-07T19:38:06Z"
---

## Goal

Review all 31 skills: ensure English language, improve algorithm quality, fix terminology, strengthen instructions

## Acceptance Criteria

1. All SKILL.md files are in English
2. Algorithms are clear, actionable, and follow best practices
3. No broken references to CLI commands or MCP tools
4. Consistent terminology across all skills
5. No redundant or contradictory instructions
6. Skills with missing or empty algorithm sections are flagged and fixed

## Plan

## Rollback

## Journal

- 2026-04-07T16:47:19Z [implementation] — Review complete. All 34 skills read (11 core + 23 official). Issues found: 1) confluence/jira use old .frai/frai references instead of .tausik/tausik. 2) jira references 'frai' throughout. 3) run skill uses --force flag (removed in SENAR). 4) Several skills reference .tausik/tausik CLI where MCP-first is preferred. 5) All skills already in English — AC#1 met. 6) presale skill references project-specific tools/paths not in this repo.
- 2026-04-07T16:49:41Z [implementation] — All fixes applied: 1) confluence SKILL.md: .frai/frai → .tausik/tausik. 2) jira SKILL.md: all frai references → tausik (5 edits). 3) run SKILL.md: removed --force from task done. 4) All 34 SKILL.md files confirmed in English. 5) All CLI references verified against actual CLI help. 6) Bootstrap run — 32 skills synced to .claude/. Note: jira/bitrix24 MCP Python code still has frai references in DB schema/variables — separate task needed.
- 2026-04-07T19:15:43Z [implementation] — 5-agent review complete. Raw findings: Quality=26, Implementation=23, Simplification=19, Documentation=24, frai-plan=ready. Deduplicating and compiling consolidated report.
- 2026-04-07T19:26:09Z [implementation] — Step 2: Adding explicit MCP param names to all 11 core skills. Got exact schemas from ToolSearch for 14 MCP tools.
- 2026-04-07T19:30:50Z [implementation] — All core skill fixes applied: 1) roles/→agents/roles/ and stacks/→agents/stacks/ in CLAUDE.md + 5 skills. 2) Explicit MCP param names in task, plan, ship, end, checkpoint, explore. 3) /ship: swapped commit-before-close ordering, delegated commit to /commit skill. 4) /commit: added explicit git add step, documented gate_runner.py args. 5) Standardized subagent invocation pattern (inline contents, not file refs). 6) /explore: fixed param title not topic, added create_task param. 7) /end + /checkpoint: added handoff JSON structure example. 8) Bootstrap synced.
- 2026-04-07T19:36:51Z [implementation] — AC verified: all 10 core skills hardened — MCP params explicit, paths fixed, subagent patterns standardized, /ship commit flow fixed. Committed as b49d0dd.
