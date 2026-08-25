---
slug: rule-on-ruff-016-new-defaults
title: "Принять или отвергнуть новые умолчания ruff 0.16: 1539 находок, по каждому правилу решение"
status: planning
epic: landscape-2026-h2
story: l26-narrative
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - pyproject.toml
  - "scripts/**"
  - "tests/**"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Набор правил ruff — осознанный выбор проекта на 0.16, а не наследство от 0.15: по каждому новоумолчальному правилу принято решение включить или отвергнуть, с записанной причиной.

## Acceptance Criteria

## Plan

## Rollback

git revert правки pyproject; select возвращается к E4,E7,E9,F,BLE001

## Journal
