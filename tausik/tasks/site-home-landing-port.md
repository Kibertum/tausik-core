---
slug: site-home-landing-port
title: "Port full landing-snapshot.html into VitePress home (EN+RU) + fix EN hero link"
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
completed_at: "2026-05-15T12:35:49Z"
---

## Goal

Заменить bare-bones placeholder site/index.md и site/ru/index.md полноценным лендингом из site/_archive/landing-snapshot.html. Landing — Linear-style тёмная тема, hero+features+how-it-works+quality-gates+CTA, ~1064 строк HTML/CSS. Также: фикс ломаной EN hero-ссылки /quickstart → /docs/quickstart.

## Acceptance Criteria

(1) site/index.md содержит полноценный landing (либо layout:home с расширенным features блоком + Vue-компонент HomeLanding для секций below the fold, либо layout:false + raw HTML с inline styles). Hero, Features, How it works, Quality gates, CTA — все секции из landing-snapshot.html присутствуют. (2) site/ru/index.md — зеркало с переведённым копирайтингом, идентичная структура. (3) EN hero 'Quickstart' ссылка указывает на /docs/quickstart (а не /quickstart как сейчас) — кнопка не даёт 404. RU уже корректна (/ru/docs/quickstart). (4) pnpm build проходит зелёным (или dev-сервер при невозможности build). (5) Никаких новых external CDN-ссылок (брендинг встроен в site/). (6) Ошибка: layout:false и raw HTML не должны сломать VitePress search или sidebar навигацию — после клика по 'Docs' пользователь попадает в обычный VitePress layout с sidebar. (7) Стилистика близка к landing-snapshot.html (Linear-style темная тема, accent #5E6AD2) — допустимы упрощения, но не вырождение в bare VitePress.

## Plan

## Rollback

## Journal

- 2026-05-15T12:35:44Z [implementation] — AC verified: (1) ✓ HomeLanding.vue (1300+ строк) с 8 секциями + scoped styles + i18n через lang prop. (2) ✓ site/index.md и site/ru/index.md frontmatter layout:page+sidebar:false+aside:false+outline:false+pageClass:home-landing, контент <HomeLanding lang=en|ru />. (3) ✓ EN hero CTA — anchor #quick-start, RU тоже #quick-start, 404 устранён. (4) ✓ pnpm build clean 5.5s, 99 HTML. (5) ✓ Vue компонент локальный, без CDN. (6) ✓ docs/quickstart.html содержит VPSidebar/VPDoc — VitePress chrome нетронут. (7) ✓ Linear-style: --lt-bg #0A0A0A, accent #5E6AD2, terminal demo, 6-row compare, 6 features, 4 stats, 6 IDEs cards.
