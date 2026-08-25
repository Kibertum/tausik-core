---
slug: site-repo-content
title: "Наполнить site-репо файлами (чистый старт)"
status: done
epic: site-standalone-agent-ready
story: extract-site-gitlab
complexity: medium
role: developer
stack: null
tier: moderate
call_budget: 40
defect_of: null
scope: "Новый рабочий каталог standalone-репо (вне core); адаптация scripts/sync-docs.mjs, .vitepress/config.ts (sitemap позже), HomeLanding.vue constants import, package.json, README, .gitignore"
scope_exclude: "core-репо (site/ удаляется отдельной задачей core-remove-site); .gitlab-ci.yml и Dockerfile (отдельная задача site-ci-cd); agent-readiness файлы (отдельные задачи)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-28T13:00:02Z"
---

## Goal

Собрать содержимое нового репо: файлы site/ становятся корнем репо, добавить README, .gitignore, при необходимости поправить sync-docs.mjs под новую структуру (доки приходят извне). Первый коммит и push в tausik/site.

## Acceptance Criteria

1. Standalone-репо tausik/site содержит все файлы сайта в корне (.vitepress/, index.md, ru/, scripts/, package.json, pnpm-lock.yaml, nginx.conf, README, .gitignore). 2. sync-docs.mjs и импорт constants.json адаптированы под новую раскладку: доки фреймворка приходят извне в .docs-src/{en,ru,_generated} (dot-каталог, VitePress не рендерит, gitignored), рендер-каталоги docs/ и ru/docs/ без коллизии. 3. Локальная сборка (с подложенными docs из core) проходит pnpm build без ошибок и dead-links. 4. Первый коммит запушен в origin tausik/site, ветка main. 5. НЕГАТИВНЫЙ сценарий: при отсутствии .docs-src сборка падает (sync-docs FATAL, exit≠0), а не рендерит молча пустой сайт.

## Plan

## Rollback

Новый репо изолирован — откат = удалить запушенную ветку main в tausik/site (git push origin --delete или GitLab API) и рабочий каталог. core не затрагивается.

## Journal

- 2026-06-28T12:59:49Z [implementation] — Standalone-репо собрано и запушено: tausik/site main=a76e64f. Контент в [вычеркнуто: local-path] (commit 64f9be9), TAUSIK инициализирован как отдельный проект (commit a76e64f). Сборка зелёная (EN/RU/docs рендерятся, dead-links enforced), негативный сценарий проверен (sync FATAL exit=1 без .docs-src). AC1-5 выполнены. Дальнейшая работа по сайту ведётся в проекте tausik-site (свой .tausik DB).
- 2026-06-28T13:00:01Z [implementation] — AC verified: 1. ✓ файлы сайта в корне tausik/site (14 файлов, commit 64f9be9). 2. ✓ sync-docs.mjs+constants импорт адаптированы под .docs-src (dot-dir, не рендерится, gitignored). 3. ✓ pnpm build зелёный — dist содержит index.html, ru/index.html, docs/quickstart.html, dead-links enforced. 4. ✓ запушено в origin tausik/site main=a76e64f. 5. ✓ Negative: без .docs-src sync-docs FATAL exit=1 (проверено mv .docs-src). verify run #925 signed.
