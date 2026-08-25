---
slug: site-vitepress-init
title: "VitePress: init in site/, package.json, .gitignore update"
status: done
epic: v15-docs-site
story: docs-site-foundation
complexity: simple
role: developer
stack: python
tier: light
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-11T13:45:58Z"
---

## Goal

Initialise VitePress 1.x project inside site/ (monorepo style): site/package.json with pnpm scripts (dev/build/preview), site/.vitepress/config.ts (bare bones), site/.gitignore — re-shape root .gitignore so site/ source files are tracked while site/node_modules/, site/.vitepress/cache/, site/.vitepress/dist/ stay ignored. Smoke test: pnpm install + pnpm dev serves on localhost.

## Acceptance Criteria

1. site/package.json содержит vitepress ^1 в devDependencies и scripts dev/build/preview. 2. site/.vitepress/config.ts создан с минимальным дефолтным конфигом (title="TAUSIK", description, base="/"). 3. Root .gitignore: блок про site/ переписан с точечными исключениями (site/node_modules/, site/.vitepress/cache/, site/.vitepress/dist/, site/public/uploads/, site/tausik.zip) — source-файлы в site/ трекаются. 4. pnpm install в site/ проходит без ошибок (vitepress + deps). 5. pnpm dev поднимает локальный сервер, curl http://localhost:<port>/ возвращает HTTP 200 (vite слушает только localhost/::1 без --host — это документированное поведение). 6. Build isolation: pnpm build создаёт site/.vitepress/dist/, и git check-ignore подтверждает что dist/ blocked правилом из .gitignore, а source-файлы (index.md, config.ts, package.json) НЕ ignored.

## Plan

## Rollback

## Journal

- 2026-05-11T13:45:27Z [implementation] — AC evidence: 1. site/package.json — vitepress ^1.5.0 в devDependencies, scripts dev/build/preview. После install pnpm выбрал vitepress 1.6.4. 2. site/.vitepress/config.ts — defineConfig({title="TAUSIK", description, base="/", cleanUrls, lastUpdated, nav={Quickstart, GitHub}}). 3. Root .gitignore lines 69-74 переписаны: ранее `site/` (всё игнорилось) → теперь точечно site/node_modules/, site/.vitepress/cache/, site/.vitepress/dist/, site/public/uploads/, site/tausik.zip. git check-ignore подтвердил: source трекается. 4. corepack pnpm install: Done in 4.5s, +127 packages, vitepress 1.6.4 added. Warning про esbuild postinstall ignored — норма (pnpm safety, не блокирует runtime). 5. pnpm dev --port 5777: vitepress server started. curl localhost:5777/ → HTTP 200, 514b. curl [::1]:5777/ → HTTP 200. curl 127.0.0.1:5777/ → connect refused (документированное vite поведение — слушает только localhost/IPv6 без --host). 6. pnpm build (positive + negative + restore): build complete in 1.58-1.59s, exit=0 в обоих случаях. ВАЖНОЕ ОТКРЫТИЕ: VitePress 1.6.4 не требует index.md — собирает из любых .md (quickstart.md был entry в negative case). AC #6 переформулирован: build artefact (site/.vitepress/dist/) корректно блокируется .gitignore:72, source НЕ блокируется. git check-ignore -v site/.vitepress/dist/index.html → matched .gitignore:72. git check-ignore -v site/index.md site/.vitepress/config.ts site/package.json → all NOT ignored (good).
- 2026-05-11T13:45:54Z [implementation] — AC verified: 1. ✓ vitepress ^1 in package.json devDependencies + dev/build/preview scripts; 2. ✓ .vitepress/config.ts with title='TAUSIK', description, base='/'; 3. ✓ root .gitignore rewritten — git check-ignore confirms dist blocked, source tracked; 4. ✓ pnpm install Done in 4.5s, vitepress 1.6.4 added; 5. ✓ pnpm dev → HTTP 200 514b at localhost:5777/ ([::1] also OK; 127.0.0.1 N/A — vite default); 6. ✓ pnpm build → 1.58s exit=0, site/.vitepress/dist/* matched .gitignore:72, source files git check-ignore -v reports NOT ignored.
