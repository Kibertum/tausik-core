---
slug: hooks-pre-tool
title: "PreToolUse hooks: task gate + git push gate + dangerous command firewall"
status: done
epic: frai-v27
story: hooks-enforcement
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
completed_at: "2026-03-29T11:49:23Z"
---

## Goal

Bootstrap генерирует PreToolUse hooks: блокировка Write/Edit без активной задачи, блокировка git push без /ship, firewall для rm -rf и DROP

## Acceptance Criteria

1. PreToolUse Write/Edit: проверяет активную задачу через .frai/frai, exit 2 если нет. 2. PreToolUse Bash(git push): блокирует без явного /ship или /commit, exit 2. 3. PreToolUse Bash(rm -rf, DROP TABLE, git reset --hard): firewall, exit 2. 4. Скрипты хуков в scripts/hooks/. 5. bootstrap_generate.py генерирует hooks в settings.json. 6. Хуки не блокируют в тестовом окружении (FRAI_SKIP_HOOKS). 7. Тесты для каждого хука.

## Plan

## Rollback

## Journal
