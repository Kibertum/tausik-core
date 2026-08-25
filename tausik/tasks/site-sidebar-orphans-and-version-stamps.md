---
slug: site-sidebar-orphans-and-version-stamps
title: "Site IA cleanup: 12 orphans in sidebar + v1.3->v1.4 stamps + shared-brain TODO"
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
completed_at: "2026-05-15T13:45:03Z"
---

## Goal

(1) Добавить 12 orphan-страниц (brain-db-schema, customization, claude-md-guide, dev-doc-checks, i18n-strategy, senar-compliance-matrix, skill-adaptation, skill-bundles, skill-bundles-migration, skill-profiles, task-archive-spec, vendor-skills) в sidebar обеих локалей в подходящие секции. (2) Обновить заголовки 'v1.3' на 'v1.4' в cli.md, skills.md, senar-compliance-matrix.md (EN+RU = 6 правок). (3) Закрыть TODO-секции в shared-brain.md:279,289 (Alternative: Outline пустая + Still TODO 14 тикетов). (4) Решить судьбу EN agent-contract и RU plan-*/skill-*.

## Acceptance Criteria

(1) 12 orphan-страниц добавлены в EN sidebar в подходящие секции. (2) RU sidebar тоже расширен. (3) pnpm build clean. (4) Ошибка: не должно остаться orphan-страниц синкнутых в site/docs/ но не достижимых через навигацию (кроме явных скрытых).

## Plan

## Rollback

## Journal

- 2026-05-15T13:45:02Z [implementation] — AC verified: 12 orphans добавлены в sidebar (EN+RU). EN sidebar получил: senar-compliance-matrix (Concepts), task-archive-spec (Quality), brain-db-schema (Brain), customization (Getting started), skill-profiles + skill-adaptation + skill-bundles + skill-bundles-migration + vendor-skills (Concepts), claude-md-guide (Concepts), dev-doc-checks + i18n-strategy (Internals). RU sidebar — то же. pnpm build 4.43s clean.
