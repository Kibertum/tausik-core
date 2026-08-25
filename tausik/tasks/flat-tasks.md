---
slug: flat-tasks
title: "Flat tasks: task add без обязательного story, story_id nullable"
status: done
epic: v2-simplify-core
story: v2-simplify-core
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-22T15:14:00Z"
---

## Goal

task add 'title' работает без epic/story, --group опционален

## Acceptance Criteria

## Plan

[{"step": "\u0421\u0434\u0435\u043b\u0430\u0442\u044c story_id nullable \u0432 backend task_add", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c parser: task add \u043f\u0440\u0438\u043d\u0438\u043c\u0430\u0435\u0442 title \u043a\u0430\u043a \u043f\u0435\u0440\u0432\u044b\u0439 arg, story \u043e\u043f\u0446\u0438\u043e\u043d\u0430\u043b\u0435\u043d \u0447\u0435\u0440\u0435\u0437 --group", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c service: task_add \u0431\u0435\u0437 \u043e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c\u043d\u043e\u0433\u043e story_slug", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c CLI: \u043d\u043e\u0432\u044b\u0439 \u0444\u043e\u0440\u043c\u0430\u0442 task add", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c \u0442\u0435\u0441\u0442\u044b", "done": true}]

## Rollback

## Journal
