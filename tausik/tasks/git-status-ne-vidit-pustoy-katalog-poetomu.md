---
slug: git-status-ne-vidit-pustoy-katalog-poetomu
title: "git status не видит пустой каталог, поэтому артефакт оболочки живёт в дереве месяцами"
status: planning
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: simple
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Артефакт оболочки в рабочем дереве обнаруживается проверкой, а не случайной инвентаризацией: пустой каталог и каталог, чьё содержимое целиком игнорируется, невидимы для git status и потому живут месяцами.

## Acceptance Criteria

1. Замер ДО: три артефакта (каталоги с именами неразвёрнутой переменной и двух кусков команды git config), возраст от 24 до 46 дней, ни один не виден git status. 2. Проверка находит каталог, который git не видит: пустой либо со содержимым целиком под .gitignore, и не лежащий в объявленном списке намеренных (worktrees агентов, вендорские репозитории). 3. Имена с метасимволами оболочки называются отдельно от просто пустых: первое есть след сорвавшейся команды, второе бывает законным. 4. НЕГАТИВНЫЙ: намеренный пустой каталог (.claude/worktrees) НЕ попадает в находки, иначе проверку выключат в первую неделю.

## Plan

## Rollback

## Journal
