---
slug: docs-internal-links-resolve-on-github-not-only-on-the-site
title: "73 переключателя языка в docs/ ведут на маршруты сайта (/ru/docs/…), которых в core больше нет; полной проверки ссылок по дереву нет с апреля"
status: planning
epic: release-19-renar-conformance
story: release19-clean-publication-and-onboarding
complexity: medium
role: tech-writer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "docs/en/*.md, docs/ru/*.md (строки переключателей), tests/test_docs_links_resolve.py (новый), CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "Содержание страниц не переписывается; docs/**/research не трогать; CHANGELOG-история не правится."
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕР, смена #251, по 224 отслеживаемым .md вне tausik/ и research/: 592 относительные ссылки, 116 не разрешаются: 73 — переключатели «English | Русский» вида `/ru/docs/quickstart` (маршруты VitePress-сайта, вынесенного в tausik/site; на GitHub и в клоне это мёртвые ссылки на каждой странице docs/en и docs/ru), 39 — исторические записи CHANGELOG.md на удалённые brain-файлы, 2 — плейсхолдеры `../lang/file.md` в i18n-strategy.md, 1 — TODO.md → tausik_systemwide_analysis.md (gitignored, и TODO.md не публикуется по #368). Полная проверка ссылок по дереву была отложена в d7-cross-link-check (26.04) и так и не появилась — поэтому 73 страницы сломались молча, когда сайт уехал. Задача: (1) переключатели языка переводятся на относительные ссылки `../ru/<page>.md` / `../en/<page>.md` (работают на GitHub, в клоне и в VitePress, который относительные .md переписывает сам); (2) tests/test_docs_links_resolve.py: каждая относительная ссылка в README*.md, AGENTS.md, CONTRIBUTING.md, SECURITY.md, docs/** (без research/) разрешается в существующий файл; исключения объявлены перечнем с причиной (CHANGELOG*.md — историческая запись, ссылки на файлы как они были; плейсхолдеры i18n-strategy — примеры формата), и перечень не растёт без правки теста; (3) EN↔RU: у каждой страницы docs/en есть пара в docs/ru и наоборот, и переключатель указывает на пару — иначе тест краснит; (4) первое исполнение теста — замер до/после в журнале.

## Acceptance Criteria

AC-1: замер после правки: ноль неразрешимых относительных ссылок в README*.md, AGENTS.md, CONTRIBUTING.md, SECURITY.md, docs/** (без research/ и без объявленных исключений); число до/после в журнале. AC-2: tests/test_docs_links_resolve.py зелёный на дереве; НЕГАТИВ: временный каталог с одной ссылкой на несуществующий файл или с переключателем `/ru/docs/x` — тест краснит. AC-3: каждая страница docs/en имеет пару в docs/ru и наоборот; переключатель каждой страницы указывает ровно на её пару (тест). AC-4: исключения (CHANGELOG*.md, плейсхолдеры i18n-strategy) объявлены в тесте с причиной; добавить исключение без правки теста невозможно. AC-5: signed verify; CHANGELOG EN/RU (правка документации, видимая потребителю на GitHub).

## Plan

## Rollback

git revert; переключатели вернутся к маршрутам сайта.

## Journal
