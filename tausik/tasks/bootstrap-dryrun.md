---
slug: bootstrap-dryrun
title: "Bootstrap --dry-run"
status: done
epic: improvements-v2
story: testing-dx
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
completed_at: "2026-03-19T09:46:20Z"
---

## Goal

Добавить флаг --dry-run в bootstrap.py для предпросмотра изменений без записи

## Acceptance Criteria

bootstrap.py --dry-run выводит список действий без записи файлов. Тест покрывает dry-run.

## Plan

[{"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c --dry-run \u0444\u043b\u0430\u0433 \u0432 argparse bootstrap.py", "done": true}, {"step": "\u0420\u0435\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u0442\u044c dry-run \u0440\u0435\u0436\u0438\u043c \u2014 \u0432\u044b\u0432\u043e\u0434 \u0447\u0442\u043e \u0431\u0443\u0434\u0435\u0442 \u0441\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u043d\u043e/\u0441\u043e\u0437\u0434\u0430\u043d\u043e \u0431\u0435\u0437 \u0437\u0430\u043f\u0438\u0441\u0438", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u0442\u0435\u0441\u0442", "done": true}]

## Rollback

## Journal
