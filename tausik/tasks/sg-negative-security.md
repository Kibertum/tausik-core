---
slug: sg-negative-security
title: "Start Gate: negative scenario hard gate + security surface"
status: done
epic: senar-v13-full
story: senar-gaps
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
completed_at: "2026-03-29T11:30:53Z"
---

## Goal

QG-0 блокирует без негативного сценария в AC. Security tasks требуют threat surface.

## Acceptance Criteria

1. task_start блокирует если AC не содержит негативного сценария. 2. task_start предупреждает для security-задач если нет security AC. 3. Негативный сценарий по ключевым словам. 4. Тесты: без negative → blocked. 5. Тесты: с negative → passes.

## Plan

## Rollback

## Journal
