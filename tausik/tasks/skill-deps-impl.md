---
slug: skill-deps-impl
title: "Реализовать механизм зависимостей скиллов"
status: done
epic: skill-deps
story: skill-deps
complexity: complex
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
completed_at: "2026-03-22T12:30:49Z"
---

## Goal

Bootstrap умеет скачивать, версионировать и обновлять внешние скиллы

## Acceptance Criteria

## Plan

[{"step": "\u0421\u043e\u0437\u0434\u0430\u0442\u044c skills.json \u0441 \u0444\u043e\u0440\u043c\u0430\u0442\u043e\u043c \u043c\u0430\u043d\u0438\u0444\u0435\u0441\u0442\u0430", "done": true}, {"step": "\u0421\u043e\u0437\u0434\u0430\u0442\u044c bootstrap_vendor.py \u2014 sync/update \u0437\u0430\u0432\u0438\u0441\u0438\u043c\u043e\u0441\u0442\u0435\u0439 \u0447\u0435\u0440\u0435\u0437 GitHub tarball API", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c bootstrap_copy.py \u2014 vendor \u043a\u0430\u043a fallback source \u0434\u043b\u044f \u0441\u043a\u0438\u043b\u043b\u043e\u0432", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c bootstrap.py \u2014 \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c --sync-deps \u0438 --update-deps \u0444\u043b\u0430\u0433\u0438", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c .frai/vendor/ \u0432 .gitignore", "done": true}, {"step": "\u0422\u0435\u0441\u0442\u044b \u0434\u043b\u044f vendor module", "done": true}, {"step": "\u0418\u043d\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u043e\u043d\u043d\u044b\u0439 \u0442\u0435\u0441\u0442: full bootstrap \u0441 vendor skill", "done": true}]

## Rollback

## Journal
