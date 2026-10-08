---
slug: remove-force-start
title: "Remove --force from task_start, add gate-bypass audit log"
status: done
epic: senar-final
story: senar-hardening
complexity: simple
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
completed_at: "2026-03-23T13:22:42Z"
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

task_start не принимает --force. Любое использование --force в task_done логируется как gate bypass event

## Acceptance Criteria

1. task_start(force=) убран из парсера и service. 2. task_done --force логирует event с action=gate_bypass. 3. Тесты обновлены.

## Plan

## Rollback

## Journal
