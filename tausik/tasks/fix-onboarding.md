---
slug: fix-onboarding
title: "Обновить README.md и INIT.md на актуальные CLI команды"
status: done
epic: docs-audit
story: onboarding-docs
complexity: simple
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - README.md
  - INIT.md
  - "scripts/README.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-14T12:50:41Z"
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

README.md и INIT.md должны использовать .frai/frai вместо python .claude/scripts/project.py

## Acceptance Criteria

1. README.md: все CLI примеры используют .frai/frai
2. INIT.md: все CLI примеры используют .frai/frai
3. Нет ни одного упоминания python .claude/scripts/project.py
4. grep -r 'python.*scripts/project.py' *.md references/ — 0 совпадений

## Plan

## Rollback

## Journal
