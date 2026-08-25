---
slug: v142-landing-rework
title: "v1.4.2 landing rework — new slogan, concrete Without/With, lifecycle renamed, stats reframed"
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
completed_at: "2026-05-15T17:11:10Z"
---

## Goal

Полный pass по HomeLanding.vue: новый h1 (AI agents that can't fake 'done'), новый eyebrow (Discipline layer), tightened lede, terminal demo с BLOCKED moment, Without/With rows с конкретными примерами агент-фраз и хук-блоков, '3 messages' секция переименована в 'Task lifecycle', stats reframed (добавить 0 false-'done' claims). EN+RU параллельно. Релиз как v1.4.2.

## Acceptance Criteria

(1) h1 заменён на 'AI agents that can't fake done' (EN+RU). (2) eyebrow Discipline layer. (3) Hero terminal demo показывает enforcement (BLOCKED line). (4) Without/With table — 6 рядов с конкретными агент-фразами + блок-сообщениями. (5) cycle.title переименована Task lifecycle. (6) stats foot/items пересмотрены. (7) Version 1.4.1 → 1.4.2 + CHANGELOG. (8) pnpm build clean. (9) Ошибка: устаревший 'Git for AI workflow' / 'Git для AI разработки' не должен остаться в dist.

## Plan

## Rollback

## Journal

- 2026-05-15T17:11:10Z [implementation] — AC verified: Pipeline #2279 (a127d45) — success, build 19s + deploy 6s. tag v1.4.2 запушен. Live tausik.tech показывает новый h1 'AI agents that can\'t fake \'done\'.' (EN) и 'AI-агенты, которые не врут «готово»' (RU), BLOCKED-line в hero terminal, обновлённый Without/With, переименованную Task lifecycle секцию, reframed stats.
