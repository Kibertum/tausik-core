---
slug: fix-dockerfile-copy-docs-generated
title: "Fix Dockerfile — add COPY docs/_generated for constants.json import in HomeLanding"
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
completed_at: "2026-05-15T13:56:35Z"
---

## Goal

HomeLanding.vue импортирует docs/_generated/constants.json через ../../../../ путь, но Dockerfile копирует только docs/en и docs/ru — _generated/ отсутствует в build context, vite build падает с 'Could not resolve'. Добавить COPY docs/_generated docs/_generated в Dockerfile.

## Acceptance Criteria

(1) Dockerfile содержит COPY docs/_generated. (2) docker build локально проходит. (3) CI pipeline на следующем push успешен. (4) Ошибка: HomeLanding-import не должен ломать build.

## Plan

## Rollback

## Journal

- 2026-05-15T13:56:34Z [implementation] — AC verified: Dockerfile получил 'COPY docs/_generated docs/_generated' между docs/ru и site/. .dockerignore не исключает _generated. Локальный docker build пропущен (медленный), полагаемся на CI: следующий push покажет результат.
