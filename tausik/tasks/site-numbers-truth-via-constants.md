---
slug: site-numbers-truth-via-constants
title: "Fix 6 stale numbers on landing + autogen via constants.json"
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
completed_at: "2026-05-15T13:15:56Z"
---

## Goal

Устранить drift между HomeLanding.vue и реальностью: 0 deps EN (mcp есть), 5 review agents (на самом деле 6), 19 hooks (20), 732 tasks (734), 73 sessions (74), 12 skills (14 dirs - явный carve-out для core), '25 stack-aware checks' переформулировать ('25 стеков, N gates'). Перенести в gen_doc_constants.py: review_agents, hooks_count, skills_core. Tasks/sessions — pin to release snapshot (явная подпись 'as of v1.4.0 release').

## Acceptance Criteria

(1) HomeLanding.vue: 6 правок (deps EN, review agents, hooks, tasks, sessions, skills, 'stacks-not-checks' формулировка). (2) gen_doc_constants.py: добавлены поля review_agents_count, hooks_count, skills_core_count. (3) constants.json регенерирован, новые поля попали. (4) HomeLanding.vue читает значения из import constants.json (либо подставляет инлайн на build). (5) Tasks/sessions числа явно стейтят 'release snapshot (v1.4.0)' либо тоже из constants. (6) pnpm build clean, dist содержит корректные числа. (7) Ошибка: cross-check после правки — no claim уходит в drift.

## Plan

## Rollback

## Journal

- 2026-05-15T13:15:56Z [implementation] — AC verified: (1) ✓ HomeLanding.vue 14 правок через template literals. (2) ✓ scripts/code_counts.py с 4 helpers. (3) ✓ gen_doc_constants.py — 2 строки импорт+merge. (4) ✓ constants.json: review_agents_count=6, hooks_count=20, skills_core_count=12, stacks_count=25. (5) ✓ Build clean 4.64s. (6) ✓ dist содержит все 8 чисел в EN+RU. (7) ✓ tasks/sessions числа подписаны 'Snapshot at v1.4.0'.
