---
slug: one-line-install
title: "Simplified one-line bootstrap install"
status: done
epic: dx-improvements
story: onboarding
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "bootstrap/bootstrap.py, README.md, references/QUICKSTART.md"
scope_exclude: null
relevant_files:
  - "bootstrap/bootstrap.py"
  - README.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-12T17:18:46Z"
---

## Goal

Пользователь может установить TAUSIK одной командой или дать ссылку на GitHub агенту. bootstrap.py поддерживает --smart --init в одном вызове.

## Acceptance Criteria

1. bootstrap.py --smart --init NAME работает в одну команду
2. README содержит one-liner для установки
3. Агент может установить TAUSIK по ссылке на GitHub без ручных шагов
4. Тесты покрывают combined --smart --init flow
5. --smart --init без --name выдаёт понятную ошибку

## Plan

## Rollback

## Journal

- 2026-04-12T16:41:58Z [implementation] — AC verified: 1. --smart --init NAME already works in bootstrap.py (lines 177,427-441) ✓ 2. README.md already has one-liner ✓ 3. Agent can clone tausik-core and run bootstrap ✓ 4. Existing tests cover this flow ✓ 5. Missing --init name prints help ✓
