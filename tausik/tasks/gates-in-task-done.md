---
slug: gates-in-task-done
title: "Integrate gate_runner into task_done (REQ-4)"
status: done
epic: senar-final
story: senar-hardening
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
completed_at: "2026-03-23T13:10:12Z"
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

task_done() calls gate_runner for task-done trigger before completing

## Acceptance Criteria

1. task_done вызывает gate_runner с trigger=task-done. 2. Blocking gate failure предотвращает завершение. 3. Warning gates не блокируют. 4. --force обходит gates (но не AC). 5. Тесты покрывают все сценарии.

## Plan

## Rollback

## Journal
