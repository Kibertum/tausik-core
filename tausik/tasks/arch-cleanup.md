---
slug: arch-cleanup
title: "Architecture: split project_backend.py, decompose task_done, fix silent exceptions"
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
completed_at: "2026-03-26T15:46:02Z"
---

## Goal

project_backend.py <400 строк, task_done() decomposed, silent exception swallowing fixed

## Acceptance Criteria

1. project_backend.py <400 строк (graph memory вынесен). 2. task_done() разбит на private methods. 3. FTS rebuild и gate_runner import логируют вместо pass. 4. Тесты проходят.

## Plan

[{"step": "Extract graph+exploration to backend_graph.py, decompose task_done, fix silent exceptions", "done": true}]

## Rollback

## Journal
