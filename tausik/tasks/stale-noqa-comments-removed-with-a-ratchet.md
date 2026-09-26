---
slug: stale-noqa-comments-removed-with-a-ratchet
title: "ruff RUF100: 546 noqa comments suppress nothing"
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

The 546 noqa comments that suppress no active rule are removed in one hygiene change of their own, and RUF100 joins select so a stale suppression cannot accumulate again.

## Acceptance Criteria

## Plan

## Rollback

git revert

## Journal
