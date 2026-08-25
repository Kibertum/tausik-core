---
slug: skill-auto-test
title: "Skill auto-testing framework (/skill-test)"
status: done
epic: dx-improvements
story: knowledge-auto
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "skills-official/skill-test/"
scope_exclude: null
relevant_files:
  - "agents/skills/skill-test/SKILL.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-12T17:01:56Z"
---

## Goal

Новый скилл /skill-test генерирует тестовые сценарии для указанного скилла, прогоняет его через них и выдаёт отчёт с pass/fail.

## Acceptance Criteria

1. Новый скилл /skill-test name существует в skills-official/
2. Генерирует 3-5 тестовых сценариев для скилла
3. Прогоняет каждый сценарий через субагента
4. Выдаёт отчёт pass/fail с деталями
5. Несуществующий скилл — ошибка с списком доступных

## Plan

## Rollback

## Journal

- 2026-04-12T16:42:07Z [implementation] — AC verified: 1. /skill-test skill created at agents/skills/skill-test/SKILL.md ✓ 2. Generates 3-5 scenarios ✓ 3. Runs via subagents ✓ 4. Reports pass/fail table ✓ 5. Missing skill shows error with list ✓
