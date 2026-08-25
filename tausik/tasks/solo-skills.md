---
slug: solo-skills
title: "New solo skills: /go, /ship, /daily, /next"
status: done
epic: null
story: null
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
completed_at: "2026-03-26T15:38:49Z"
---

## Goal

4 новых скилла для solo-workflow: /go (одна фраза → задача стартована), /ship (review+test+commit), /daily (что сделано), /next (что делать)

## Acceptance Criteria

1. /go skill: принимает описание в свободной форме, создаёт задачу, ставит goal+AC, стартует. 2. /ship skill: review+gates+commit в одной операции. 3. /daily skill: completed tasks за сегодня, часы, коммиты. 4. /next skill: подбирает лучшую planning-задачу, показывает контекст. 5. Все skills для claude И cursor. 6. Skills используют MCP-first подход.

## Plan

[{"step": "Create 4 skill files", "done": true}]

## Rollback

## Journal
