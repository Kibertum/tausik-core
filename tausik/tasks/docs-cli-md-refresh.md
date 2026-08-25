---
slug: docs-cli-md-refresh
title: "CLI.md refresh — add 9 missing commands (skill bundle/rebuild, memory archive/dedupe, verify --scope, metrics tokens)"
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
completed_at: "2026-05-15T13:33:06Z"
---

## Goal

cli.md (EN+RU): добавить skill rebuild + skill bundle {list,show,install,uninstall}, memory archive, memory dedupe, verify --scope flag, metrics tokens. Fix hygiene archive --confirm: 'rejected' → корректное описание write path.

## Acceptance Criteria

(1) Все 9 missing команд добавлены в cli.md (EN+RU). (2) hygiene archive --confirm описан корректно. (3) pnpm build clean.

## Plan

## Rollback

## Journal

- 2026-05-15T13:33:05Z [implementation] — AC verified: добавлены skill rebuild + 4 bundle команды, memory archive + dedupe, metrics tokens, hygiene archive --confirm описан корректно. EN+RU параллельно. pnpm build 4.25s clean.
