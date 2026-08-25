---
slug: rag-path-traversal
title: "Path traversal защита в RAG indexer"
status: done
epic: frai-maturity
story: security
complexity: simple
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
completed_at: "2026-03-14T11:47:53Z"
---

## Goal

RAG indexer не проверяет что файлы внутри project_dir. Добавить os.path.commonpath проверку чтобы symlinks/.. не вышли за пределы проекта.

## Acceptance Criteria

## Plan

## Rollback

## Journal
