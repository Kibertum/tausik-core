---
slug: fts5-optimize
title: "FTS OPTIMIZE, phrase search, field weighting"
status: done
epic: fts5-hardening
story: fts5-hardening
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
completed_at: "2026-03-22T12:25:50Z"
---

## Goal

Поиск поддерживает фразы, приоритет title над content, периодическая оптимизация индекса

## Acceptance Criteria

## Plan

[{"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c fts_optimize() \u043c\u0435\u0442\u043e\u0434 \u0432 backend \u0434\u043b\u044f \u0432\u0441\u0435\u0445 5 FTS \u0442\u0430\u0431\u043b\u0438\u0446", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c phrase search \u2014 \u043d\u0435 \u0441\u0442\u0440\u0438\u043f\u0430\u0442\u044c \u043a\u0430\u0432\u044b\u0447\u043a\u0438, \u0430 \u043e\u0431\u043e\u0440\u0430\u0447\u0438\u0432\u0430\u0442\u044c \u0432 FTS5 \u0441\u0438\u043d\u0442\u0430\u043a\u0441\u0438\u0441", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c column weighting \u0447\u0435\u0440\u0435\u0437 rank weight", "done": true}, {"step": "CLI \u043a\u043e\u043c\u0430\u043d\u0434\u0430 search --optimize \u0434\u043b\u044f \u0440\u0443\u0447\u043d\u043e\u0433\u043e \u0437\u0430\u043f\u0443\u0441\u043a\u0430", "done": true}, {"step": "\u0422\u0435\u0441\u0442\u044b", "done": true}]

## Rollback

## Journal
