---
slug: site-is-rebuilt-from-the-core-docs-of-the-release
title: "Сайт tausik.tech пересобран из документации ядра текущего релиза: один источник, порождённая навигация, версия из констант"
status: planning
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: complex
role: docs
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "docs/_generated/*"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - documentation-is-refactored-around-one-map
completed_at: null
---

## Goal

Замер смены #266 по репозиторию tausik/site: последний коммит e7da518 от 06.07.2026 с вендоренным TAUSIK 1.5.8 — сайт показывает документацию четырёхрелизной давности; scripts/fetch-docs.mjs клонирует ядро по адресу [вычеркнуто: internal-host]/tausik/core.git, которого больше нет (ядро живёт в kibertum/clients/kibertum/standards/tausik/core); .vitepress/config.ts несёт 106 ссылок навигации, набранных руками, и расходится с деревом docs/ ядра; .docs-src хранит июльскую копию (60 RU / 51 EN). Решение #368 (1.9): сайт живёт только в tausik/site, в ядре его следов нет — это остаётся. Цель: сайт собирается из документации ядра ТЕКУЩЕГО релиза одной командой, навигация порождается из карты документации (задача documentation-is-refactored-around-one-map), лендинг и агентские артефакты (llms.txt, agent-файлы) берут версию и числа из docs/_generated/constants.json, вендоренный TAUSIK в site обновлён до релиза, деплой зелёный. Работа идёт в репозитории site; задача в ядре держит замеры и доказательства (хеши коммитов site, вывод сборки).

## Acceptance Criteria

1. Замер ДО приложен в журнале: версия вендоренного TAUSIK в site, адрес клона в fetch-docs.mjs, число ссылок навигации, даты копии .docs-src.
2. fetch-docs.mjs берёт ядро по действующему адресу или локальному пути CORE_DOCS_SRC и по тегу релиза (не по main); НЕГАТИВНЫЙ: недоступный источник — сборка падает с текстом, а не собирает июльскую копию.
3. Навигация порождается из карты документации ядра (docs/_generated или файл карты), а не из 106 ручных строк; тест сборки сравнивает число страниц в навигации с числом страниц в дереве; НЕГАТИВНЫЙ: страница без места в карте — ошибка сборки.
4. Лендинг и агентские артефакты (llms.txt, llms-full.txt, agent-файлы) несут версию и счётчики из constants.json ядра; строка «1.5» на сайте отсутствует после сборки (grep по dist).
5. Вендоренный TAUSIK в site обновлён до релиза 1.10 (или последнего тега на момент задачи), bootstrap прошёл.
6. Деплой tausik.tech из main site зелёный; в журнале — хеши коммитов site и адрес пайплайна.
7. В ядре следов сайта не появилось: tests/test_site_lives_elsewhere.py зелёный.

## Plan

## Rollback

git revert коммитов в репозитории site; ядро не меняется, кроме карты документации (её откат — по задаче карты).

## Journal
