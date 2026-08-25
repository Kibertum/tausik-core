---
slug: test-concurrent
title: "Тесты concurrent writes"
status: done
epic: release-ready
story: p0-blockers
complexity: medium
role: qa
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_concurrent.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-14T13:09:18Z"
---

## Goal

Доказать что SQLite WAL + FK не ломается при параллельной записи 2+ потоками

## Acceptance Criteria

1. 4 потока создают задачи — 0 потерь | 2. 2 потока claim одну задачу — 1 успех | 3. cascade delete во время insert — нет orphans | 4. tests/test_concurrent.py

## Plan

## Rollback

## Journal
