---
slug: task-quick-slugifier-drops-cyrillic-and-yields-deg
title: "task quick slugifier drops Cyrillic and yields degenerate slugs"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/tausik_utils.py"
  - "scripts/project_cli_task.py"
  - "scripts/service_task_team.py"
  - "tests/test_task_auto_slug.py"
  - "tests/test_firewall_reads_heredoc_as_data.py"
scope_paths:
  - "scripts/tausik_utils.py"
  - "scripts/project_cli_task.py"
  - "scripts/service_task_team.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T21:18:10Z"
---

## Goal

DOGFOODING, смена #238. Две задачи, заведённые подряд русскими заголовками, получили слаги 'gates-json' и 'heredoc' — по одному-двум ASCII-словам, случайно оказавшимся в заголовке. Заголовки были: «Комментарий храповика в gates.json цитирует тест, которого никогда не было» и «Гейт рамок не видит записи, сделанной питоновским скриптом через heredoc».

ПОЧЕМУ ЭТО НЕ КОСМЕТИКА. Слаг есть ПЕРВИЧНЫЙ КЛЮЧ задачи и её адрес во всех командах, журналах, коммитах и доказательствах закрытия. Слаг 'heredoc' не даёт найти задачу и почти наверняка столкнётся со следующей о том же. Проект ведётся по-русски целиком — то есть дефект бьёт по каждой задаче, заведённой быстрым путём, а не по краевому случаю.

ЧТО РАБОТАЕТ СЕГОДНЯ: 'task add' с явным слагом. То есть обход есть и он молчаливый — быстрый путь тихо выдаёт плохой ключ вместо того, чтобы попросить его назвать.

## Acceptance Criteria

AC-1. ЗАМЕР: сколько существующих слагов вырождены (короче N символов или не отражают заголовок) — числом по базе, а не примером.
AC-2. Русский заголовок даёт осмысленный слаг: транслитерация или явный отказ с требованием назвать слаг. Молчаливая выдача плохого ключа запрещена.
AC-3. НЕГАТИВНЫЙ СЦЕНАРИЙ: заголовок, из которого осмысленного слага не получается, приводит к ОТКАЗУ с внятным сообщением, а не к слагу из одного слова. Тест подсовывает такой заголовок и требует отказа.
AC-4. Существующие слаги не переименовываются: они адреса в журналах, коммитах и доказательствах закрытия.

## Plan

## Rollback

git revert; существующие слаги не трогаются

## Journal

- 2026-09-23T20:45:42Z [implementation] — AC-1: ✓ замер выше: 25 из 1117
- 2026-09-23T20:45:42Z [implementation] — Замер (read-only SQL, команды нет): задач 1690, с русскими заголовками 1117, вырожденных слагов (одно слово или короче 12 символов) — 25 (db-indexes, multi-agent, audit-log, ...). Причина: tausik_utils.slugify не транслитерировал и возвращал 'task' при пустом результате, хотя slug_util.transliterate в проекте уже был. Правка: slugify транслитерирует и режет по границе слова; новый task_slug_from_title отказывает при слаге короче 3 символов; task add (_auto_slug) и task quick используют его.
- 2026-09-23T20:45:43Z [implementation] — AC-2: ✓ tests/test_task_auto_slug.py::test_a_title_in_any_script_gives_a_slug_that_reads_like_it
- 2026-09-23T20:45:43Z [implementation] — AC-2: ✓ tests/test_task_auto_slug.py::test_task_quick_uses_the_transliterated_slug
- 2026-09-23T20:45:43Z [implementation] — AC-3: ✓ tests/test_task_auto_slug.py::test_a_title_with_nothing_usable_is_refused_not_stubbed
- 2026-09-23T20:45:44Z [implementation] — AC-4: ✓ существующие слаги не трогаются: правка только в генерации нового слага
- 2026-09-23T20:45:44Z [implementation] — NO-DEAD-END: единственный красный прогон — моя ошибка в ожидаемой транслитерации буквы х
- 2026-09-23T20:47:28Z [implementation] — NO-DEAD-END: красный verify — чужой дефект rag_languages (заведён и исправлен задачей rag-languages-rebuilds-the-config-path-inline)
- 2026-09-23T20:51:15Z [implementation] — Второй красный verify: test_crosscutting_registry — мой тест test_firewall_reads_heredoc_as_data.py (задача firewall-scans-heredoc..., уже закрыта) запускает хук подпроцессом и не объявлял CROSSCUTTING_SCOPE; объявлен ['scripts/hooks/']. NO-DEAD-END: пропуск объявления, исправлено
