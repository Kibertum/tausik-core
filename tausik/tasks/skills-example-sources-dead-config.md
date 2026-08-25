---
slug: skills-example-sources-dead-config
title: "3.4: секция sources в skills.example.json — мёртвая конфигурация, ноль читателей"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: skills.example.json
scope_exclude: null
relevant_files:
  - skills.example.json
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-10T17:19:22Z"
---

## Goal

Подтверждено grep'ом: во всём scripts/ и bootstrap/ нет ни одного чтения ключа 'sources'; читается только 'external_skills' (bootstrap.py:289,349; bootstrap_catalog.py:22; bootstrap_vendor.py:26,271). Список skill_dirs внутри секции застыл на 19 скиллах — нет deck, markitdown, commit, plan. Решить: либо реализовать чтение, либо убрать секцию из примера. Документировать механизм, которого нет в коде, — худший из вариантов.

## Acceptance Criteria

1) Секция sources удалена из skills.example.json. 2) JSON остаётся валидным, external_skills цел. Негативный: 3) Ошибка, если удаление задело работающий механизм — подтвердить, что sources не читает никто (только external_skills).

## Plan

## Rollback

git checkout -- skills.example.json

## Journal

- 2026-07-10T17:19:09Z [implementation] — AC verified: 1. ✓ Секция sources удалена из skills.example.json (строки 2-13). 2. ✓ JSON валиден: json.load даёт ключи верхнего уровня ['external_skills'], 5 записей целы. 3. ✓ (негативный) sources не читает никто: grep по scripts/ bootstrap/ — ноль вхождений чтения ключа 'sources' у skills-конфига; bootstrap.py:279-284 копирует файл, но читает только external_skills (bootstrap.py:289). Единственное вхождение 'sources' в тестах — test_web_cache.py про status['sources'] web-кэша, к этому файлу отношения не имеет. Полный прогон 4420 passed 0 failed.
