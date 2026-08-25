---
slug: tausik-tech-docs-site-vitepress-monorepo-site-source-v
task: promo-site-tausik-tech-open-design-static-site-in-
date: "2026-05-11"
edges: []
---

## Decision

tausik.tech docs site = VitePress + монорепо (site/ source в tausik/core, dist в .gitignore) + GitLab Pages deploy

## Rationale

SSG=VitePress: встроенный i18n (EN default + /ru/), локальный minisearch, MD source без конверсии, dark theme близка к нашему Linear-style landing. Монорепо vs отдельный tausik/site: один PR = доки+код = атомарность (важно для doc-truth, который мы и так строим в v1.4 audit suite); нет двойного push; нет submodule sync; на каждый push CI пересобирает сайт, но docs и так обычно меняются вместе с кодом. Источник docs — прямо docs/en/ + docs/ru/ через VitePress rewrites (без копирования/симлинков). Deploy: GitLab Pages в tausik/core .gitlab-ci.yml (отдельный job pages:), DNS tausik.tech CNAME→pages. Open Design отброшен: UX генератора не зашёл пользователю с первой попытки; Claude Design дал чистый HTML за один промпт — оставлен как hero/home layout нового сайта.
