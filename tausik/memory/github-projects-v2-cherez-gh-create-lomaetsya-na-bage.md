---
slug: github-projects-v2-cherez-gh-create-lomaetsya-na-bage
title: "GitHub Projects v2 через gh: create ломается на баге обёртки, views API не создаёт, device-flow нужен для scope project"
type: gotcha
tags:
  - gh
  - github
  - graphql
  - projects
  - roadmap
task: null
edges: []
---

Смена #265. (1) gh project create --owner <org> в gh 2.x падает «Variable $query is used by CreateProjectV2 but not declared» — обходится прямым GraphQL: createProjectV2(input:{ownerId,title}) с id организации из query{organization(login){id}}. (2) Views (Board/Table/Roadmap) через API не создаются — публичной мутации нет; их добавляет владелец руками в UI, README проекта описывает какие. (3) Roadmap-раскладка (таймлайн) требует дат: due date на milestone или date-поле; без дат честнее Board + Table по Milestone. (4) Scope project у токена нет по умолчанию — gh auth refresh -h github.com -s project,read:project печатает одноразовый код, владелец подтверждает в браузере, процесс ждёт до 15 мин; в безголовой сессии запускать в фоне и читать код из файла. (5) Переменные Int! в gh api graphql передаются через -F, не -f. (6) Текст с бэктиками в аргумент bash — только через файл: бэктики выполнились как command substitution и запустили второй device-flow. Проект Kibertum #4 «TAUSIK Roadmap»: id PVT_kwDOBKh_G84BjduL, Status field PVTSSF_lADOBKh_G84BjduLzhiR7WE.
