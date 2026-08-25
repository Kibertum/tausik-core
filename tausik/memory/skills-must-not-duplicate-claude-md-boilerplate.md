---
slug: skills-must-not-duplicate-claude-md-boilerplate
title: "Skills must not duplicate CLAUDE.md boilerplate"
type: convention
tags:
  - audit
  - boilerplate
  - skills
  - tokens
task: skills-redundancy-audit
edges: []
---

Skills-redundancy-audit (2026-04-17): removed "Always respond in the user's language" from 12 SKILL.md files (checkpoint, commit, debug, end, explore, plan, review, ship, skill-test, start, task, test) — CLAUDE.md Response Language section covers this globally. Lint: tests/test_skills_no_boilerplate.py blocks regression.

Rationale: each skill is loaded every time it's invoked; duplicated instructions waste tokens and add noise. The generated CLAUDE.md already states "Always respond in the user's language" once as a hard constraint — skills don't need to repeat it.

Convention: any phrase that already lives in bootstrap_templates.py (Hard Constraints, Memory, SENAR Rules, Response Language) MUST NOT be repeated in individual skill files. Check existing CLAUDE.md template before adding boilerplate.
