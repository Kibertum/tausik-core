---
slug: hooks-post-tool
title: "PostToolUse hooks: auto-format + auto-log changed files"
status: done
epic: frai-v27
story: hooks-enforcement
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
completed_at: "2026-03-29T11:50:57Z"
---

## Goal

PostToolUse hooks: auto-format код после Write/Edit, auto-log изменённые файлы в активную задачу

## Acceptance Criteria

1. PostToolUse Write/Edit: запускает ruff format на файле (если Python). 2. PostToolUse Write/Edit: логирует файл в активную задачу через frai task log. 3. PostToolUse Bash(pytest): записывает результат тестов в task notes. 4. Форматтер определяется по стеку (ruff/prettier/gofmt). 5. Если форматтер не найден — не блокирует (graceful degradation). 6. Тесты.

## Plan

## Rollback

## Journal
