---
slug: review-iterate
title: "Итеративный review-цикл в /review"
status: done
epic: ralphex-inspired
story: review-overhaul
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "agents/claude/skills/review/SKILL.md"
scope_exclude: null
relevant_files:
  - "agents/claude/skills/review/SKILL.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-29T17:19:16Z"
---

## Goal

Review находит проблемы, фиксит их, и верифицирует фиксы повторным review — пока не останется 0 issues (CRITICAL+HIGH). Макс 5 итераций.

## Acceptance Criteria

1. /review с аргументом "iterate" запускает цикл review→fix→review. 2. Цикл останавливается при 0 issues (CRITICAL+HIGH) или после 5 итераций. 3. Каждая итерация логируется через task log. 4. Без "iterate" — поведение как раньше (однократный review). 5. При достижении лимита итераций выводится предупреждение с оставшимися issues. 6. Negative: если iterate запущен без активной задачи — предупреждение что логирование итераций невозможно, но цикл работает.

## Plan

[{"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0441\u0435\u043a\u0446\u0438\u044e Iterative Mode \u0432 SKILL.md \u043f\u043e\u0441\u043b\u0435 Algorithm", "done": true}, {"step": "\u041e\u043f\u0438\u0441\u0430\u0442\u044c \u0446\u0438\u043a\u043b: review \u2192 classify issues \u2192 fix CRITICAL+HIGH \u2192 re-review", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0443\u0441\u043b\u043e\u0432\u0438\u044f \u0432\u044b\u0445\u043e\u0434\u0430: 0 issues \u0438\u043b\u0438 max 5 \u0438\u0442\u0435\u0440\u0430\u0446\u0438\u0439", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0441\u0447\u0451\u0442\u0447\u0438\u043a \u0438\u0442\u0435\u0440\u0430\u0446\u0438\u0439 \u0438 \u043b\u043e\u0433\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u0447\u0435\u0440\u0435\u0437 task log", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043f\u0440\u0435\u0434\u0443\u043f\u0440\u0435\u0436\u0434\u0435\u043d\u0438\u0435 \u043f\u0440\u0438 \u0434\u043e\u0441\u0442\u0438\u0436\u0435\u043d\u0438\u0438 \u043b\u0438\u043c\u0438\u0442\u0430 \u0438\u0442\u0435\u0440\u0430\u0446\u0438\u0439", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c \u0441\u0435\u043a\u0446\u0438\u044e Arguments \u2014 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c iterate", "done": true}]

## Rollback

## Journal
