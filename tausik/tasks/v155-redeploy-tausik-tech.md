---
slug: v155-redeploy-tausik-tech
title: "Редеплой tausik.tech с показом v1.5.5"
status: done
epic: null
story: null
complexity: simple
role: devops
stack: null
tier: trivial
call_budget: 10
defect_of: null
scope: "Верификация авто-деплоя (push main уже выполнен в релизе). Read-only через gitlab API + curl."
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T11:57:31Z"
---

## Goal

Передеплоить сайт tausik.tech, чтобы витрина отражала релиз v1.5.5 (версия, Kilo Code + z.ai/GLM).

## Acceptance Criteria

1. tausik.tech задеплоен с v1.5.5 контентом. 2. gitlab CI пайплайн на main (commit c61bbb1) прошёл build+deploy success. 3. Живой сайт отдаёт 200 + v1.5.5-эксклюзивную страницу /docs/kilo-zai. 4. Ошибка/abort (негатив): если пайплайн failed ИЛИ сайт не отдаёт 200 ИЛИ kilo-zai отсутствует — задача не закрыта, перезапустить пайплайн/доложить.

## Plan

## Rollback

Откат деплоя — re-run пайплайна на предыдущем коммите через gitlab CI.

## Journal

- 2026-06-19T11:57:31Z [implementation] — AC verified: 1.✓ tausik.tech задеплоен с v1.5.5. 2.✓ gitlab pipeline #3032 (sha c61bbb1, ref main, source push): build success + deploy success @11:01:44Z (curl gitlab API /pipelines + /jobs). 3.✓ live: https://tausik.tech/ HTTP 200; /docs/kilo-zai HTTP 200 (страница существует только в 1.5.5) + /docs/quickstart 200. 4.✓ negative: пайплайн НЕ failed, сайт отдаёт 200, kilo-zai присутствует — abort не нужен. Домен: редеплой произошёл авто при push main в релизе; контент v1.5.5 реально доступен в проде. verify green.
