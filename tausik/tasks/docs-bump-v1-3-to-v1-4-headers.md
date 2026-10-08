---
slug: docs-bump-v1-3-to-v1-4-headers
title: "Bump v1.3 to v1.4 in 4 doc headers (cli/skills/senar-compliance-matrix EN+RU)"
status: done
epic: null
story: null
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
completed_at: "2026-05-15T13:24:39Z"
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

Stale '(v1.3)' и 'TAUSIK v1.3.0' стрингы в 4 заголовках после релиза 1.4. Также обновить дату на senar-compliance-matrix.md.

## Acceptance Criteria

(1) Все правки точечные согласно audit-findings. (2) pnpm build clean без новых dead links. (3) Diff чистый — содержание не утеряно. (4) Ошибка: не должно остаться текста с устаревшими версиями/командами/упоминаниями.

## Plan

## Rollback

## Journal

- 2026-05-15T13:24:38Z [implementation] — AC verified: правки сделаны, pnpm build clean 4.61s, без новых dead links.
