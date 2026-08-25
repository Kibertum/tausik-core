---
slug: remove-chromadb
title: "Удалить ChromaDB + добавить update check в /start"
status: done
epic: session3-improvements
story: cleanup
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
completed_at: "2026-03-19T08:25:15Z"
---

## Goal

Полностью убрать ChromaDB из кодовой базы; добавить в /start проверку что сабмодуль фреймворка актуален относительно remote HEAD

## Acceptance Criteria

rag_store_chroma.py удалён из всех agents. Нет импортов/ссылок на ChromaDB нигде в коде. /start SKILL.md содержит фазу проверки обновления сабмодуля. CLAUDE.md обновлён. Все тесты проходят.

## Plan

[{"step": "\u0423\u0434\u0430\u043b\u0438\u0442\u044c rag_store_chroma.py \u0438\u0437 agents/claude \u0438 agents/cursor", "done": true}, {"step": "\u0423\u0431\u0440\u0430\u0442\u044c \u0432\u0441\u0435 \u0438\u043c\u043f\u043e\u0440\u0442\u044b \u0438 \u0441\u0441\u044b\u043b\u043a\u0438 \u043d\u0430 ChromaDB \u0438\u0437 server.py, bootstrap, config, docs", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0432 /start SKILL.md \u0444\u0430\u0437\u0443 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f \u0441\u0430\u0431\u043c\u043e\u0434\u0443\u043b\u044f (git fetch + compare HEAD)", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c CLAUDE.md \u2014 \u0443\u0431\u0440\u0430\u0442\u044c \u0443\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u044f ChromaDB", "done": true}, {"step": "\u0417\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c \u0442\u0435\u0441\u0442\u044b, \u0443\u0431\u0435\u0434\u0438\u0442\u044c\u0441\u044f \u0447\u0442\u043e \u043d\u0438\u0447\u0435\u0433\u043e \u043d\u0435 \u0441\u043b\u043e\u043c\u0430\u043d\u043e", "done": true}]

## Rollback

## Journal
