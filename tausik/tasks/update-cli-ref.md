---
slug: update-cli-ref
title: "Дополнить project-cli.md недокументированными командами"
status: done
epic: docs-audit
story: cli-docs
complexity: simple
role: tech-writer
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
completed_at: "2026-03-14T12:46:11Z"
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

Добавить в project-cli.md 7 недокументированных команд: task claim/unclaim, team, metrics, session handoff, session last-handoff, update-claudemd

## Acceptance Criteria

1. Все команды из project_parser.py задокументированы в project-cli.md
2. task claim/unclaim в секции Tasks
3. team как отдельная секция Multi-Agent
4. metrics как отдельная секция
5. session handoff + last-handoff в секции Sessions
6. update-claudemd в новой секции Maintenance
7. Нет ссылок на python scripts/project.py — только .frai/frai

## Plan

## Rollback

## Journal
