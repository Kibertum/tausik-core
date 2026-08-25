---
slug: v14b-token-t12-todo-reminder-geytit-todowrite-reminder-hook
title: "v14b-token-t12-todo-reminder: гейтить TodoWrite reminder hook условиями (>5 tool calls без update + "
type: dead_end
tags:
  - claude-code-harness
  - hooks
  - scope
task: null
edges: []
---

Approach: v14b-token-t12-todo-reminder: гейтить TodoWrite reminder hook условиями (>5 tool calls без update + список выглядит stale)
Reason: Reminder text 'The TodoWrite tool hasn't been used recently...' это builtin Claude Code system-reminder, а не TAUSIK hook. Grep 'TodoWrite' по всему репо — 0 матчей в scripts/hooks/. Парент-задача v14b-token-tier1-quick-wins T1.2 зафиксировала ложную гипотезу о существовании такого hook'а у нас. Контроль над текстом и условиями триггера на стороне Claude Code harness, не TAUSIK. Будущим агентам: НЕ пытайтесь делать новые TAUSIK hook'и для подавления builtin system-reminder'ов — они инжектятся harness'ом до наших хуков и нашими средствами не суппрессятся.
