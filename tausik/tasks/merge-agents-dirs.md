---
slug: merge-agents-dirs
title: "Объединить agents/claude и agents/cursor в единую структуру"
status: done
epic: public-release
story: cross-ide
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "agents/skills/"
  - "agents/overrides/"
  - "bootstrap/bootstrap_copy.py"
  - "scripts/ide_utils.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T13:34:32Z"
---

## Goal

Одна директория agents/ с общими скиллами + override-файлы для IDE-специфики. Нет дублирования 32 скиллов.

## Acceptance Criteria

1. agents/skills/ содержит 32 общих скилла (одна копия). 2. agents/overrides/{ide}/ содержит только IDE-специфичные отличия. 3. bootstrap_copy.py читает общие + мержит overrides. 4. Нет дублированных SKILL.md. 5. Ошибка если общий скилл отсутствует в agents/skills/.

## Plan

[{"step": "\u0421\u043f\u0440\u043e\u0435\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u043d\u043e\u0432\u0443\u044e \u0441\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u0443: agents/skills/ + agents/overrides/{ide}/", "done": true}, {"step": "\u041f\u0435\u0440\u0435\u043d\u0435\u0441\u0442\u0438 \u043e\u0431\u0449\u0438\u0435 \u0441\u043a\u0438\u043b\u043b\u044b \u0432 agents/skills/", "done": true}, {"step": "\u0421\u043e\u0437\u0434\u0430\u0442\u044c overrides \u0442\u043e\u043b\u044c\u043a\u043e \u0434\u043b\u044f \u0440\u0435\u0430\u043b\u044c\u043d\u044b\u0445 \u0440\u0430\u0437\u043b\u0438\u0447\u0438\u0439", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c bootstrap_copy.py \u2014 \u0447\u0438\u0442\u0430\u0442\u044c \u043e\u0431\u0449\u0438\u0435 + \u043c\u0435\u0440\u0436\u0438\u0442\u044c overrides", "done": true}, {"step": "\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u0434\u0443\u0431\u043b\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0435 agents/claude/skills/ \u0438 agents/cursor/skills/", "done": true}, {"step": "\u041f\u0440\u043e\u0433\u043d\u0430\u0442\u044c \u0442\u0435\u0441\u0442\u044b bootstrap", "done": true}]

## Rollback

## Journal

- 2026-04-05T13:34:25Z [implementation] — AC verified: 1. agents/skills/ содержит 32 скилла ✓ 2. agents/overrides/{claude,cursor}/ содержит rules ✓ 3. bootstrap_copy.py ищет shared → ide → claude ✓ 4. Нет дублей ✓ 5. 35 тестов прошли ✓
