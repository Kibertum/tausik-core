---
slug: site-tausik-tech-publish-vitepress-gitlab
title: "Promo-site for tausik.tech — VitePress bilingual + Dockerfile + GitLab CI"
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
completed_at: "2026-05-15T12:21:54Z"
---

## Goal

Закоммитить уже подготовленный сайт tausik.tech: VitePress 1.6 (EN+RU) в site/, Dockerfile multi-stage, .gitlab-ci.yml build+deploy на порту 8900, .dockerignore, .gitignore с granular блоком site/*. Сайт деплоится только через GitLab pipeline.

## Acceptance Criteria

(1) site/ закоммичен полностью (VitePress config, scripts/sync-docs.mjs, index.md в обеих локалях, theme, nginx.conf, README, brief, _archive/landing-snapshot.html), без node_modules/, без .vitepress/dist/, без сгенерированных site/{docs,ru/docs}/. (2) Dockerfile, .gitlab-ci.yml, .dockerignore закоммичены. (3) .gitignore содержит granular блок site/* (build artefacts only, source tracked). (4) Атомарный коммит — без CLAUDE.md dynamic, без правок bootstrap/tests которые уже в HEAD~1. (5) Ошибка: коммит не должен затащить site/node_modules/ или site/.vitepress/dist/ — проверено через git diff --cached. (6) Pre-commit гейты (filesize, mypy) проходят зелёным.

## Plan

## Rollback

## Journal

- 2026-05-15T12:21:54Z [implementation] — AC verified: (1) ✓ site/ закоммичен: .vitepress/{config.ts,theme/}, scripts/sync-docs.mjs, index.md, ru/index.md, nginx.conf, README, brief, _archive/landing-snapshot.html, package.json, pnpm-lock.yaml — 13 файлов. (2) ✓ Dockerfile, .gitlab-ci.yml, .dockerignore через 'create mode 100644'. (3) ✓ .gitignore содержит блок site/ с granular ignore (node_modules/, .vitepress/{cache,dist}/, sync-generated docs/, public/uploads/, .zip). (4) ✓ Атомарный коммит 6088ab5: 16 файлов, без CLAUDE.md и без правок из HEAD~1. (5) ✓ git diff --cached проверен — никакого node_modules/dist/cache/sync-output в индексе. (6) ✓ mypy clean (137 source files), filesize гейт прошёл.
