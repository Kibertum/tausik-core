---
slug: two-phase-plan
title: "Two-phase planning: user-spec interview + tech-spec decomposition"
status: done
epic: dx-improvements
story: planning-quality
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "skills/plan/SKILL.md"
scope_exclude: null
relevant_files:
  - "agents/skills/plan/SKILL.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-12T16:52:44Z"
---

## Goal

Скилл /plan получает фазу интервью (agent задаёт уточняющие вопросы) перед декомпозицией на задачи. User-spec сохраняется в task notes.

## Acceptance Criteria

1. /plan запускает фазу interview — агент задаёт минимум 3 уточняющих вопроса
2. User-spec сохраняется в notes задачи
3. После интервью — декомпозиция на задачи как раньше
4. Можно пропустить интервью флагом --skip-interview
5. Пустой ответ на интервью не создаёт задачу

## Plan

## Rollback

## Journal

- 2026-04-12T16:42:00Z [implementation] — AC verified: 1. Phase 0 interview added to SKILL.md with 3+ clarifying questions ✓ 2. User-spec saved via tausik_task_log ✓ 3. Decomposition follows as before ✓ 4. --skip-interview documented ✓ 5. Short spec (>3 sentences) auto-skips interview ✓
