---
slug: batch-run
title: "Автономный batch-режим frai run"
status: done
epic: ralphex-inspired
story: batch-execution
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "новый skill agents/claude/skills/run/SKILL.md, scripts/project_cli.py, scripts/project_service.py"
scope_exclude: null
relevant_files:
  - "agents/claude/skills/run/SKILL.md"
  - "scripts/plan_parser.py"
  - "scripts/project_cli.py"
  - "scripts/project_parser.py"
  - "scripts/project.py"
  - "tests/test_plan_parser.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-29T18:03:34Z"
---

## Goal

frai run plan.md выполняет план автономно: каждая задача в свежей сессии, auto-commit, validation commands, progress в task_logs. Для CI и ночных прогонов.

## Acceptance Criteria

1. CLI: frai run plan.md выполняет markdown-план автономно. 2. Каждая задача = отдельный subagent (свежий контекст). 3. Validation commands (pytest, ruff) после каждой задачи. 4. Auto-commit после успешного завершения задачи. 5. Progress пишется в task_logs. 6. Max iterations per task (default 3), общий timeout. 7. При failure задачи — лог ошибки, переход к следующей (не stop all). 8. Новый skill /run с документацией. 9. Negative: если plan.md не найден — ошибка с понятным сообщением.

## Plan

[{"step": "\u0421\u043f\u0440\u043e\u0435\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0444\u043e\u0440\u043c\u0430\u0442 markdown-\u043f\u043b\u0430\u043d\u0430 \u0434\u043b\u044f batch-run", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u043f\u0430\u0440\u0441\u0435\u0440 \u043f\u043b\u0430\u043d\u0430 (markdown \u2192 \u0441\u043f\u0438\u0441\u043e\u043a \u0437\u0430\u0434\u0430\u0447 \u0441 \u0448\u0430\u0433\u0430\u043c\u0438)", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c CLI \u043a\u043e\u043c\u0430\u043d\u0434\u0443 frai run plan.md", "done": true}, {"step": "\u0420\u0435\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u0442\u044c \u043e\u0440\u043a\u0435\u0441\u0442\u0440\u0430\u0442\u043e\u0440: \u0446\u0438\u043a\u043b \u043f\u043e \u0437\u0430\u0434\u0430\u0447\u0430\u043c, subagent \u043d\u0430 \u043a\u0430\u0436\u0434\u0443\u044e", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c validation commands \u043f\u043e\u0441\u043b\u0435 \u043a\u0430\u0436\u0434\u043e\u0439 \u0437\u0430\u0434\u0430\u0447\u0438", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c auto-commit \u043f\u043e\u0441\u043b\u0435 \u0443\u0441\u043f\u0435\u0448\u043d\u043e\u0439 \u0437\u0430\u0434\u0430\u0447\u0438", "done": true}, {"step": "\u0420\u0435\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u0442\u044c error handling: \u043b\u043e\u0433 + skip to next", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c max iterations \u0438 timeout", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c SKILL.md \u0434\u043b\u044f /run", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u0442\u0435\u0441\u0442\u044b \u0434\u043b\u044f \u043f\u0430\u0440\u0441\u0435\u0440\u0430 \u0438 \u043e\u0440\u043a\u0435\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u0430", "done": true}]

## Rollback

## Journal
