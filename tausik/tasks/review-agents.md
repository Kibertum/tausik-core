---
slug: review-agents
title: "Параллельные специализированные review-агенты"
status: done
epic: ralphex-inspired
story: review-overhaul
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "agents/claude/skills/review/SKILL.md, agents/claude/skills/review/agents/*.md (новые)"
scope_exclude: null
relevant_files:
  - "agents/claude/skills/review/SKILL.md"
  - "agents/claude/skills/review/agents/quality.md"
  - "agents/claude/skills/review/agents/implementation.md"
  - "agents/claude/skills/review/agents/testing.md"
  - "agents/claude/skills/review/agents/simplification.md"
  - "agents/claude/skills/review/agents/documentation.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-29T17:22:29Z"
---

## Goal

Review запускает 5 параллельных sub-agents (quality, implementation, testing, simplification, documentation), собирает и дедуплицирует результаты.

## Acceptance Criteria

1. Review запускает 5 параллельных sub-agents через Agent tool: quality, implementation, testing, simplification, documentation. 2. Каждый агент описан в отдельном .md файле в agents/claude/skills/review/agents/. 3. Результаты дедуплицируются (одна проблема от двух агентов = один issue). 4. Каждый finding верифицируется перед включением в отчёт. 5. Формат вывода совместим с текущим (severity levels, file:line). 6. Чеклист 28 items остаётся как часть quality agent. 7. Negative: если Agent tool недоступен — fallback на стандартный однопроходный review без агентов.

## Plan

[{"step": "\u0421\u043e\u0437\u0434\u0430\u0442\u044c agents/claude/skills/review/agents/ \u0434\u0438\u0440\u0435\u043a\u0442\u043e\u0440\u0438\u044e", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c quality.md \u2014 bugs, security, race conditions + 28-item checklist", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c implementation.md \u2014 goal achievement, AC coverage", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c testing.md \u2014 test quality, coverage gaps", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c simplification.md \u2014 over-engineering taxonomy", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c documentation.md \u2014 CLAUDE.md, README, docstrings", "done": true}, {"step": "\u041f\u0435\u0440\u0435\u0440\u0430\u0431\u043e\u0442\u0430\u0442\u044c SKILL.md: \u043e\u0440\u043a\u0435\u0441\u0442\u0440\u0430\u0446\u0438\u044f 5 \u0430\u0433\u0435\u043d\u0442\u043e\u0432 \u0447\u0435\u0440\u0435\u0437 Agent tool", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0434\u0435\u0434\u0443\u043f\u043b\u0438\u043a\u0430\u0446\u0438\u044e \u0438 \u0432\u0435\u0440\u0438\u0444\u0438\u043a\u0430\u0446\u0438\u044e findings", "done": true}, {"step": "\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c fallback \u043d\u0430 \u043e\u0434\u043d\u043e\u043a\u0440\u0430\u0442\u043d\u044b\u0439 review \u0431\u0435\u0437 \u0430\u0433\u0435\u043d\u0442\u043e\u0432", "done": true}]

## Rollback

## Journal
