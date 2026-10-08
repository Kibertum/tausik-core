---
slug: polnyy-progon-zelenyy-veren-tolko-dlya-m-bystraya-lenta
title: "«Полный прогон зелёный» верен только для -m '': быстрая лента молчит о slow-тестах, и они гнили две смены после удаления Notion"
type: gotcha
tags:
  - ci
  - flake
  - release
  - slow-lane
task: slow-lane-is-red-and-nobody-ran-it
edges: []
---

Смена #253-#255. Журналы называли «полный прогон 10084 passed» — это была быстрая лента (addopts -m 'not slow'). Полная (-m '', джоб tests-full на GitLab) несла 22 падения: 15 в test_caveman_wiring_integration (brain_enabled — параметр, удалённый с Notion), 3 в bootstrap_skills_coverage (ждали навык brain), плюс тесты, читающие живую базу этого проекта. Джоб не исполнялся с 07.09, потому что быстрый перед ним был красным, а локально -m '' никто не гонял. Правило перед релизом: условие 3 (полный прогон) проверяется процедурой CI в свежем shallow-клоне (--depth 50, bootstrap --no-detect --ide all, pytest -m ''), а не словами «полный» в журнале. Второе: три теста (codex_mcp сервер с --project <корень>, symbol CLI, xargs-хук) создавали .tausik/tausik.db в корне репо, и DB-gated контроли просыпались над пустой базой по порядку запуска — тот самый флейк из conftest смены #203, найден поимённо.
