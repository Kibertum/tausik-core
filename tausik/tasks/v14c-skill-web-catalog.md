---
slug: v14c-skill-web-catalog
title: "C3: Web каталог скиллов (static GH Pages)"
status: planning
epic: vscode-extension
story: ext-program
complexity: null
role: developer
stack: python
tier: substantial
call_budget: 100
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Generate static HTML catalog from tausik-skills.json в Kibertum/tausik-skills repo. Hosted на GH Pages. Альтернатива/дополнение к B7 skill catalog CLI.

## Acceptance Criteria

AC1. Принято и зафиксировано через tausik decide решение: генерировать статический веб-каталог ЛИБО закрыть задачу как трижды (1.6/1.7/1.8) не прошедшую отбор приоритета, с уже работающей текстовой командой каталога скиллов как достаточной альтернативой.
AC2. Если реализуется: статический HTML-каталог детерминированно генерируется из tausik-skills.json и публикуется на GH Pages в репо Kibertum/tausik-skills — тест на воспроизводимый вывод из фиксированного входного json.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

## Journal

- 2026-07-20T10:40:43Z [planning] — КАНДИДАТ НА ЗАКРЫТИЕ (решение #153, сессия #120). Отложена из 1.5 и не взята за ТРИ релиза (1.6, 1.7, 1.8). Альтернатива уже работающей текстовой команде каталога скиллов. Держать открытой значит искажать счёт остатка задачами, которые трижды подряд не прошли отбор приоритета.
