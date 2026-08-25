---
slug: site-polish-readme-cleanup
title: "site: rewrite stale README + trim .dockerignore for _archive"
status: done
epic: null
story: null
complexity: simple
role: tech-writer
stack: python
tier: trivial
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-15T12:07:42Z"
---

## Goal

site/README.md содержит устаревшие инструкции под Open Design workflow (отброшен в этом эпике). Переписать под VitePress+Docker+GitLab-CI стек, добавить srcExclude в .dockerignore чтобы _archive/, README.md, brief.md не попадали в Docker build context. Документ остаётся внутренним (srcExclude уже включён) — не публикуется.

## Acceptance Criteria

1. site/README.md полностью переписан под актуальный стек (VitePress, Node 22+pnpm 10.33, Docker multi-stage, GitLab CI deploy, port 8900, sync-docs flow). 2. README прямо упоминает что он dev-only — не публикуется (srcExclude). 3. .dockerignore дополнен: site/_archive, site/README.md, site/brief.md — эти файлы не попадают в Docker build context (нет смысла слать reference-only archive в build). 4. Failure mode: при случайной публикации README (если srcExclude забыли) контент явно помечен dev-сленгом — не выглядит как customer-facing.

## Plan

## Rollback

## Journal

- 2026-05-15T12:07:41Z [implementation] — AC verified: 1. ✓ site/README.md полностью переписан под VitePress 1.6 + Node 22 + pnpm 10.33 + Docker multi-stage + GitLab CI deploy + port 8900:80, секции Stack/Source of truth/Landing/Local dev/Local Docker/CI-CD/Known limitations/GitHub mirror; 2. ✓ README начинается с явной пометки 'Dev-only. This README is excluded from the published site via srcExclude'; 3. ✓ .dockerignore дополнен site/_archive + site/README.md + site/brief.md под комментарием 'Reference-only files'; 4. ✓ README content unambiguously dev-сленг (mentions corepack, BuildKit, internal docker tags) — даже при случайной публикации customer не примет за официальный customer-facing док.
