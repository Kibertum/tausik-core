---
slug: site-locale-parity
title: "Locale parity for docs/ — translate or hide 5 orphan pages"
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
completed_at: "2026-05-15T12:38:28Z"
---

## Goal

EN-only: plan-review, plan-stacks, skill-patterns, skill-spec (4 страницы). RU-only: agent-contract (1 страница). Решение: либо перевести, либо явно скрыть из sidebar до перевода. EN sidebar сейчас не содержит ни одну из 4 EN-only — они sync'ятся но недоступны по навигации.

## Acceptance Criteria

(1) EN sidebar в site/.vitepress/config.ts получает новую секцию 'Internals' с 4 ранее orphan-страницами: plan-review, plan-stacks, skill-patterns, skill-spec. (2) RU agent-contract уже в RU sidebar — оставляем (это и есть 'hide' для EN — orphan не отображается, посетитель его не увидит без прямого URL). (3) pnpm build проходит зелёным, новые ссылки резолвятся (нет deadlinks в этой 4 страницах из EN sidebar). (4) docs/quickstart.html на месте, остальные секции не поломаны. (5) Ошибка: не должно появиться дублирующих ссылок (та же страница в разных секциях) — проверено grep'ом по config.ts. (6) Visual check: новая секция Internals видна только в EN sidebar.

## Plan

## Rollback

## Journal

- 2026-05-15T12:38:27Z [implementation] — AC verified: (1) ✓ config.ts: добавлена секция Internals в EN sidebar после Reference, 4 ссылки (plan-review, plan-stacks, skill-spec, skill-patterns), collapsed:true. (2) ✓ RU agent-contract уже в RU sidebar, не трогали — EN agent-contract orphan-hidden. (3) ✓ pnpm build clean 4.54s. (4) ✓ 4 ссылки в EN sidebar HTML, 0 в RU. (5) ✓ Дубликатов нет. (6) ✓ 4 standalone HTML существуют.
