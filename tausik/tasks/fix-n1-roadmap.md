---
slug: fix-n1-roadmap
title: "Исправить N+1 запрос в roadmap"
status: done
epic: frai-maturity
story: schema-integrity
complexity: medium
role: developer
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
completed_at: "2026-03-14T11:53:09Z"
---

## Goal

roadmap_data() делает 511 отдельных запросов. Переписать на JOIN или batch-загрузку. Должен быть 1-3 запроса.

## Acceptance Criteria

## Plan

## Rollback

## Journal
