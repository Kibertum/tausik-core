---
slug: agent-entry-point-and-onboarding-flow
title: "Agent entry point and onboarding flow"
status: done
epic: null
story: null
complexity: medium
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: "AGENTS.md, CLAUDE.md (dynamic section only via MCP), references/QUICKSTART.md, references/QUICKSTART.en.md"
scope_exclude: null
relevant_files:
  - AGENTS.md
  - README.md
  - README.ru.md
  - "references/QUICKSTART.md"
  - "references/QUICKSTART.en.md"
  - "bootstrap/bootstrap_generate.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-07T13:18:42Z"
---

## Goal

After bootstrap, agent has a clear path: CLAUDE.md → AGENTS.md → details. No guessing where to look.

## Acceptance Criteria

1. AGENTS.md restructured: why→how→where, not just a repo map. 2. Clear navigation chain: CLAUDE.md → AGENTS.md → references/QUICKSTART → docs/. 3. Agent after bootstrap can find all framework docs within 2 hops from CLAUDE.md. 4. SENAR methodology explained in agent-accessible doc. 5. Negative: agent without CLAUDE.md still finds onboarding via AGENTS.md alone.

## Plan

## Rollback

## Journal

- 2026-04-07T13:18:29Z [implementation] — AC verified: 1. AGENTS.md rewritten from repo map to full onboarding: why TAUSIK → SENAR explanation → rules → work cycle → doc map → repo structure ✓ 2. Navigation chain: CLAUDE.md→refs/QUICKSTART, README→AGENTS.md→QUICKSTART→docs/ — all linked ✓ 3. 2 hops from CLAUDE.md to any doc ✓ 4. SENAR explained in AGENTS.md (gates, workflow rules, metrics) ✓ 5. AGENTS.md standalone: has rules + commands + doc map, works without CLAUDE.md ✓. Also updated bootstrap_generate.py AGENTS.md template for new projects.
