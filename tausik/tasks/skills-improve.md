---
slug: skills-improve
title: "Skills improvements: defaults, session limit fix, SENAR gaps"
status: done
epic: null
story: null
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
completed_at: "2026-03-26T15:42:01Z"
---

## Goal

Skills используют defaults из config, session limit 180 в docs, Dead End Rate метрика, knowledge capture warning на Done Gate

## Acceptance Criteria

1. project-cli.md: session limit 120→180. 2. QUICKSTART.md: session limit 120→180. 3. Dead End Rate метрика в backend_queries + frai metrics. 4. task_done предупреждает если нет knowledge capture за задачу. 5. /plan skill берёт role/stack из config defaults. 6. Тесты проходят.

## Plan

[{"step": "Implement all improvements", "done": true}]

## Rollback

## Journal
