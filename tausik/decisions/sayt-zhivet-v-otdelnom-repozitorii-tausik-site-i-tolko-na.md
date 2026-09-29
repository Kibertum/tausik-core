---
slug: sayt-zhivet-v-otdelnom-repozitorii-tausik-site-i-tolko-na
task: lazily-created-table-is-a-second-route-into-the-hybrid-state
date: "2026-09-29"
edges: []
---

## Decision

Сайт живёт в ОТДЕЛЬНОМ репозитории tausik-site и ТОЛЬКО на GitLab. Публикации сайта на GitHub нет. Указание владельца, смена #278. Это сужает решение #368: там сайт жил в tausik/site и вопрос о зеркале оставался открытым; теперь зеркала нет вовсе, и задача пересборки сайта строится из документации ядра по тегу релиза, а выкладка идёт только в GitLab.

## Rationale

Ядро остаётся без следов сайта — эта половина #368 в силе и закреплена tests/test_site_lives_elsewhere.py. Меняется адрес и канал публикации: tausik-site вместо tausik/site, GitLab вместо GitLab плюс GitHub. Следствие для выпуска: гейт публичного снапшота ядра к сайту отношения не имеет, а деплой tausik.tech перестаёт быть актом выкладки в публичное зеркало и становится внутренним.
