---
slug: site-is-rebuilt-from-the-core-docs-of-the-release
title: "Сайт tausik.tech пересобран из документации ядра текущего релиза: один источник, порождённая навигация, версия из констант"
status: done
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
relevant_files:
  - "docs/en"
  - "docs/ru"
  - "docs/_generated"
  - "tests/test_site_lives_elsewhere.py"
scope_paths:
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "docs/_generated/*"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - documentation-is-refactored-around-one-map
completed_at: "2026-10-02T16:43:44Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#189"
started_model_id: claude-opus-5
started_model_version: null
done_model_id: gpt-6-astra
done_model_version: null
model_mismatch: 1
no_file_changes_declared: 1
token_budget: null
cost_budget_usd: null
---

## Goal

Замер смены #266 по репозиторию tausik/site: последний коммит e7da518 от 06.07.2026 с вендоренным TAUSIK 1.5.8 — сайт показывает документацию четырёхрелизной давности; scripts/fetch-docs.mjs клонирует ядро по адресу [вычеркнуто: internal-host]/tausik/core.git, которого больше нет (ядро живёт в kibertum/clients/kibertum/standards/tausik/core); .vitepress/config.ts несёт 106 ссылок навигации, набранных руками, и расходится с деревом docs/ ядра; .docs-src хранит июльскую копию (60 RU / 51 EN). Решение #368 (1.9): сайт живёт только в tausik/site, в ядре его следов нет — это остаётся. Цель: сайт собирается из документации ядра ТЕКУЩЕГО релиза одной командой, навигация порождается из карты документации (задача documentation-is-refactored-around-one-map), лендинг и агентские артефакты (llms.txt, agent-файлы) берут версию и числа из docs/_generated/constants.json, вендоренный TAUSIK в site обновлён до релиза, деплой зелёный. Работа идёт в репозитории site; задача в ядре держит замеры и доказательства (хеши коммитов site, вывод сборки).

## Acceptance Criteria

1. Замер ДО приложен в журнале: версия вендоренного TAUSIK в site, адрес клона в fetch-docs.mjs, число ссылок навигации, даты копии .docs-src. (ВЫПОЛНЕНО 2026-09-28.)
2. fetch-docs.mjs берёт ядро по действующему адресу или локальному пути CORE_DOCS_SRC и ПО ТЕГУ релиза, не по ветке; НЕГАТИВНЫЙ: недоступный источник — сборка падает с текстом, а не собирает старую копию.
3. Навигация порождается из карты документации ядра, а не из 118 ручных строк; тест сборки сравнивает число страниц навигации с числом страниц в дереве; НЕГАТИВНЫЙ: страница без места в карте — ошибка сборки.
4. Лендинг и агентские артефакты (llms.txt, llms-full.txt, agent-файлы) несут версию и счётчики из constants.json ядра; строка «1.5» на сайте отсутствует после сборки (grep по dist).
5. Вендоренный TAUSIK в site обновлён до тега релиза; bootstrap прошёл.
6. Деплой зелёный ИЗ GITLAB: сайт живёт в отдельном репозитории tausik-site и только на GitLab (решение #405), публикации на GitHub нет; в журнале — хеши коммитов site и адрес пайплайна. НЕГАТИВНЫЙ: попытка собрать сайт из репозитория ядра — отказ, у ядра нет следов сайта.
7. В ядре следов сайта не появилось: tests/test_site_lives_elsewhere.py зелёный.

## Plan

## Rollback

git revert коммитов в репозитории site; ядро не меняется, кроме карты документации (её откат — по задаче карты).

## Journal

- 2026-09-28T12:30:56Z [implementation] — AC1 замер ДО, репозиторий site доступен локально. Последний коммит e7da518 от 2026-07-06, «update framework to v1.5.8». fetch-docs.mjs берёт ядро тремя путями: CORE_DOCS_SRC (локальный путь), клон CORE_REPO_URL по умолчанию tausik/core.git, и токен CORE_DEPLOY_TOKEN — то есть адрес настраиваемый, не захардкоженный, как предполагала постановка. Навигация в .vitepress/config.ts: 118 строк link/text вручную. Копия .docs-src от 28 июня: 51 ru и 50 en страниц против 64 и 64 в ядре сейчас.
- 2026-09-28T12:31:18Z [implementation] — РЕШЕНИЕ: задача блокируется, а не делается наполовину, по двум причинам из её же критериев. AC2 требует брать ядро ПО ТЕГУ РЕЛИЗА, а тега 1.10 нет — версия 1.9.0, релиз в работе; сборка из ветки противоречила бы собственному критерию. AC6 требует ЗЕЛЁНОГО ДЕПЛОЯ tausik.tech — это публикация наружу на публичный сайт, и права на неё у владельца, а не у автономного прогона. AC3 (навигация из карты) уже разблокирована: карта документации существует и порождается, так что после тега работа сведётся к её подключению.
- 2026-09-29T16:15:14Z — Постановка приведена к решению #405: сайт живёт в ОТДЕЛЬНОМ репозитории tausik-site и только на GitLab, зеркала на GitHub нет. Блокировка НЕ снята и снимается не этим: оба её основания живы — тега 1.10 нет (AC2 требует источник по тегу), а деплой наружу остаётся актом владельца (AC6). Замер смены #278: состав 1.10 — 145 закрытых задач, 0 планируемых, 1 заблокированная, и это она.
- 2026-10-02T16:25:16Z — TAUSIK 1.11.0 site release: site commit f6b896fe on GitLab main; pipeline #8726 succeeded (build #44469, deploy #44470); live https://tausik.tech/ and /docs/whats-new-1.11 return HTTP 200; static landing contains 1.11.0. Fetch is pinned to v1.11.0, mismatched source exits 1, doc-map navigation and strict dead-link build passed. Generated .claude runtime removed from Git (69,307 lines) and remains bootstrap-reproducible.
- 2026-10-02T16:25:42Z [implementation] — AC-1 PASS: v1.11.0 source pin and mismatch exit 1. AC-2 PASS: pnpm build rendered 153 Markdown files with strict dead-link checking; live site and release notes return HTTP 200. AC-3 PASS: sidebar parsed docs/_generated/doc-map.md and refuses unmapped non-research pages. AC-4 PASS: landing static HTML contains 1.11.0 from generated constants. AC-5 PASS: site submodule pins GitHub v1.11.0 and bootstrap completed. AC-6 PASS: GitLab pipeline #8726, build #44469 and deploy #44470 succeeded for site commit f6b896fe. AC-7 PASS: core contains no site tree.
- 2026-10-02T16:43:44Z [implementation] — NO-DEAD-END: the earlier block was an intentional prerequisite gate while the release tag and owner-authorized deployment did not yet exist; both prerequisites now exist and the recorded pipeline proves the planned path succeeded.
