---
slug: site-is-rebuilt-from-the-core-docs-of-the-release
title: "Сайт tausik.tech пересобран из документации ядра текущего релиза: один источник, порождённая навигация, версия из констант"
status: blocked
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
resolution: null
resolution_reason: null
tracker_refs:
  - "github#189"
started_model_id: claude-opus-5
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
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

- 2026-09-28T12:30:56Z [implementation] — AC1 замер ДО, репозиторий site доступен локально. Последний коммит e7da518 от 2026-07-06, «update framework to v1.5.8». fetch-docs.mjs берёт ядро тремя путями: CORE_DOCS_SRC (локальный путь), клон CORE_REPO_URL по умолчанию tausik/core.git, и токен CORE_DEPLOY_TOKEN — то есть адрес настраиваемый, не захардкоженный, как предполагала постановка. Навигация в .vitepress/config.ts: 118 строк link/text вручную. Копия .docs-src от 28 июня: 51 ru и 50 en страниц против 64 и 64 в ядре сейчас.
- 2026-09-28T12:31:18Z [implementation] — РЕШЕНИЕ: задача блокируется, а не делается наполовину, по двум причинам из её же критериев. AC2 требует брать ядро ПО ТЕГУ РЕЛИЗА, а тега 1.10 нет — версия 1.9.0, релиз в работе; сборка из ветки противоречила бы собственному критерию. AC6 требует ЗЕЛЁНОГО ДЕПЛОЯ tausik.tech — это публикация наружу на публичный сайт, и права на неё у владельца, а не у автономного прогона. AC3 (навигация из карты) уже разблокирована: карта документации существует и порождается, так что после тега работа сведётся к её подключению.
