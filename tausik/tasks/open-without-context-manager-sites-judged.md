---
slug: open-without-context-manager-sites-judged
title: "ruff SIM115: 125 open() calls without a context manager judged for handle leaks"
status: planning
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
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
completed_at: null
resolution: null
resolution_reason: null
---

## Goal

Each of the 125 open() calls SIM115 finds is either put under a context manager or marked deliberate with its reason; the rule joins select once the count is zero.

## Acceptance Criteria

## Plan

## Rollback

git revert

## Journal

- 2026-09-27T10:38:53Z [planning] — ПРЕДВАРИТЕЛЬНЫЙ ЗАМЕР (смена #277, до старта): SIM115 open() без контекстного менеджера — 128, в постановке 125. Расхождение +3 от правок последних смен, а не ошибка постановки.
