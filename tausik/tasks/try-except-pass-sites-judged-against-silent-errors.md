---
slug: try-except-pass-sites-judged-against-silent-errors
title: "ruff S110/S112: 79 try-except-pass/continue sites judged one by one against the zero-silent-errors principle"
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

Each of the 79 try/except/pass-or-continue sites ruff S110/S112 finds is either given a logged reason, narrowed, or turned into a reported failure; the rules join select once the count is zero.

## Acceptance Criteria

## Plan

## Rollback

git revert

## Journal

- 2026-09-27T10:38:52Z [planning] — ПРЕДВАРИТЕЛЬНЫЙ ЗАМЕР (смена #277, до старта): S110 try-except-pass — 72, S112 try-except-continue — 7, итого 79. Совпадает с числом в постановке.
