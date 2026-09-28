---
slug: v14-memory-dedupe-guidelines
title: "Гайд: когда merge memory vs новая запись"
status: done
epic: v14-project-hygiene
story: v14-hygiene-policy
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/memory-merge-guidelines.md"
  - "docs/ru/memory-merge-guidelines.md"
  - "docs/README.md"
  - "docs/en/shared-brain.md"
  - "docs/ru/shared-brain.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T17:33:47Z"
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

Согласование с brain classifier; таблица решений.

## Acceptance Criteria

1. Раздел docs. 2. Примеры. 3. Negative: противоречие с scrubber описано как исключение.

## Plan

## Rollback

## Journal

- 2026-05-01T17:33:42Z [implementation] — AC verified: 1. Разделы docs/en/memory-merge-guidelines.md и docs/ru/memory-merge-guidelines.md + docs/README.md (#17). 2. Примеры в обоих языках (merge / new / scrubber). 3. Negative: scrubber как исключение — секция «Scrubbing wins» / «scrubber важнее», без противоречия classifier; перекрёстные ссылки shared-brain EN/RU.
