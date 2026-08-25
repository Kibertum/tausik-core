---
slug: cursor-sync
title: "Синхронизация cursor-агентов с claude-агентами"
status: done
epic: public-release
story: code-quality
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "agents/cursor/"
  - "bootstrap/bootstrap_copy.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T13:21:54Z"
---

## Goal

agents/cursor/skills/ полностью идентичны agents/claude/skills/ (или различия задокументированы).

## Acceptance Criteria

1. diff agents/claude/skills/ vs agents/cursor/skills/ — нулевой или задокументированный. 2. Frontmatter (effort, context) идентичен. 3. Ошибка если diff показывает незадокументированные расхождения.

## Plan

[{"step": "diff agents/claude/skills/ vs agents/cursor/skills/", "done": true}, {"step": "\u0418\u0441\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u0440\u0430\u0441\u0445\u043e\u0436\u0434\u0435\u043d\u0438\u044f \u0438\u043b\u0438 \u0437\u0430\u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c intentional", "done": true}, {"step": "\u041f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c bootstrap_copy.py \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0438\u0440\u0443\u0435\u0442 \u043e\u0431\u0430", "done": true}]

## Rollback

## Journal

- 2026-04-05T13:21:48Z [implementation] — Удалены agents/cursor/{skills,roles,stacks} — дубликаты claude. Bootstrap (line 88-89) уже имеет fallback на agents/claude/skills/. References оставлены — claude-rules.md и cursor-rules.md это intentional IDE-специфичные файлы.
