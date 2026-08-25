---
slug: missing-global-rules
title: "Создать или удалить references/global-rules.md"
status: done
epic: public-release
story: docs-audit
complexity: simple
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
completed_at: "2026-04-05T13:20:25Z"
---

## Goal

Нет битых ссылок: global-rules.md либо существует с содержимым, либо все ссылки на него удалены.

## Acceptance Criteria

1. Файл global-rules.md либо создан с содержимым, либо все ссылки на него удалены. 2. Ошибка если grep по репо находит битую ссылку на несуществующий global-rules.md.

## Plan

[{"step": "Grep \u0432\u0441\u0435 \u0441\u0441\u044b\u043b\u043a\u0438 \u043d\u0430 global-rules.md", "done": true}, {"step": "\u0420\u0435\u0448\u0438\u0442\u044c: \u0441\u043e\u0437\u0434\u0430\u0442\u044c \u0444\u0430\u0439\u043b \u0438\u043b\u0438 \u0443\u0434\u0430\u043b\u0438\u0442\u044c \u0441\u0441\u044b\u043b\u043a\u0438", "done": true}, {"step": "\u0420\u0435\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u0442\u044c \u0440\u0435\u0448\u0435\u043d\u0438\u0435", "done": true}, {"step": "\u041f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u2014 \u043d\u0435\u0442 \u0431\u0438\u0442\u044b\u0445 \u0441\u0441\u044b\u043b\u043e\u043a", "done": true}]

## Rollback

## Journal

- 2026-04-05T13:20:16Z [implementation] — AC verified: grep по всему репо не находит ни файла global-rules.md, ни ссылок на него. Проблема не существует — false positive от агента-разведчика.
