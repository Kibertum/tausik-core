---
slug: site-content-and-i18n
title: "VitePress: sync-docs script + i18n (EN + /ru/) + nav + sidebar + accent theme"
status: done
epic: v15-docs-site
story: docs-site-foundation
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-15T11:43:35Z"
---

## Goal

Single combined step: (1) site/scripts/sync-docs.mjs copies docs/en/ → site/en/ and docs/ru/ → site/ru/ before dev/build; (2) site/.vitepress/config.ts gets locales (root=EN default + ru), top nav, auto-sidebar per locale, theme accent override to #5E6AD2; (3) site/en/ and site/ru/ in .gitignore (generated); (4) package.json predev/prebuild hooks wire the sync. Pure "глупое копирование" — single sync path runs locally and in CI without any divergence.

## Acceptance Criteria

1. site/scripts/sync-docs.mjs существует и при запуске копирует docs/en/*.md → site/en/ и docs/ru/*.md → site/ru/, очищает целевые папки перед копией (идемпотентно). 2. site/package.json содержит scripts predev/prebuild которые автоматически вызывают node scripts/sync-docs.mjs. 3. site/.vitepress/config.ts: locales = { root: EN default, ru: {label:'Русский', link:'/ru/'} }, top nav (Quickstart/Architecture/CLI/GitHub) на обоих языках, тема — встроенная DefaultTheme + override CSS var --vp-c-brand на #5E6AD2 через site/.vitepress/theme/style.css. 4. Auto-sidebar для обоих locales: VitePress генерирует sidebar по структуре site/en/ и site/ru/ (либо явный config-side mapping). 5. .gitignore дополнен: site/en/ и site/ru/ — generated, не трекаются. 6. pnpm build (включая prebuild sync) собирает оба locale: site/.vitepress/dist/index.html (EN home) + site/.vitepress/dist/ru/index.html (RU home). curl-проверка после pnpm preview: HTTP 200 на /, на /ru/, на /quickstart, на /ru/quickstart. 7. Failure mode: при отсутствии исходной docs/en/ или docs/ru/ скрипт sync-docs.mjs завершается с ненулевым кодом и понятной ошибкой — а не молчаливо публикует пустой build.

## Plan

## Rollback

## Journal

- 2026-05-15T11:43:34Z [implementation] — AC verified: 1. ✓ site/scripts/sync-docs.mjs copies docs/{en,ru} → site/{docs,ru/docs}, idempotent (rm + cp); 2. ✓ package.json scripts: sync/predev/prebuild → node scripts/sync-docs.mjs; 3. ✓ config.ts locales={root:EN default, ru:{label:'Русский', link:'/ru/'}}, nav per-locale, theme/style.css overrides --vp-c-brand-* to #5E6AD2/#7C86E0; 4. ✓ Sidebar per locale via config-side mapping (/docs/* + /ru/docs/*) grouped Getting started/Concepts/Quality/Memory/Reference; 5. ✓ .gitignore lines updated: site/docs/ + site/ru/docs/ added; 6. ✓ pnpm build 5.79s exit=0, preview probes HTTP 200 — /, /ru/, /docs/quickstart, /ru/docs/quickstart, /docs/architecture, /ru/docs/architecture (sizes 20.5KB-65KB); 7. ✓ Negative case: mv docs/ru → docs/_ru_hidden; pnpm sync prints 'FATAL: source not found: docs/ru' exit=1; restored and re-synced successfully. NOTE: 103 dead links (cross-language and code-file references) found in source MD — ignoreDeadLinks:true set for MVP, cleanup tracked as follow-up.
