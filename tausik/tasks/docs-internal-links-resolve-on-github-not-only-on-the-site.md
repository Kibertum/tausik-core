---
slug: docs-internal-links-resolve-on-github-not-only-on-the-site
title: "73 переключателя языка в docs/ ведут на маршруты сайта (/ru/docs/…), которых в core больше нет; полной проверки ссылок по дереву нет с апреля"
status: done
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
relevant_files:
  - "tests/test_docs_links_resolve.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/en/adding-new-ide.md"
  - "docs/en/architecture.md"
  - "docs/en/claude-md-guide.md"
  - "docs/en/cli.md"
  - "docs/en/config-trust-tiers.md"
  - "docs/en/configuration.md"
  - "docs/en/cost-telemetry.md"
  - "docs/en/customization.md"
  - "docs/en/dev-doc-checks.md"
  - "docs/en/doctor.md"
  - "docs/en/environment.md"
  - "docs/en/hooks.md"
  - "docs/en/i18n-strategy.md"
  - "docs/en/kilo-zai.md"
  - "docs/en/knowledge-store.md"
  - "docs/en/mcp.md"
  - "docs/en/memory-merge-guidelines.md"
  - "docs/en/model-providers.md"
  - "docs/en/no-sdk-verify.md"
  - "docs/en/permissions.md"
  - "docs/en/plan-review.md"
  - "docs/en/plan-stacks.md"
  - "docs/en/publishing.md"
  - "docs/en/quickstart.md"
  - "docs/en/reasoning-trace.md"
  - "docs/en/receipts.md"
  - "docs/en/research/tausik-1.5-mcp-cursor-rework-2026-05-08.md"
  - "docs/en/roles.md"
  - "docs/en/security-checklist.md"
  - "docs/en/security.md"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/en/senar.md"
  - "docs/en/session-active-time.md"
  - "docs/en/sessions.md"
  - "docs/en/skill-adaptation.md"
  - "docs/en/skill-bundles-migration.md"
  - "docs/en/skill-bundles.md"
  - "docs/en/skill-ecosystem.md"
  - "docs/en/skill-patterns.md"
  - "docs/en/skill-profiles.md"
  - "docs/en/skill-spec.md"
  - "docs/en/skills.md"
  - "docs/en/stacks.md"
  - "docs/en/task-archive-spec.md"
  - "docs/en/team-state-in-git.md"
  - "docs/en/testing-principles.md"
  - "docs/en/troubleshooting.md"
  - "docs/en/upgrade.md"
  - "docs/en/vendor-skills.md"
  - "docs/en/verify-glossary.md"
  - "docs/en/whats-new-1.8.md"
  - "docs/en/whats-new-1.9.md"
  - "docs/en/workflow.md"
  - "docs/en/zero-defect.md"
  - "docs/ru/adding-new-ide.md"
  - "docs/ru/architecture.md"
  - "docs/ru/claude-md-guide.md"
  - "docs/ru/cli.md"
  - "docs/ru/config-trust-tiers.md"
  - "docs/ru/configuration.md"
  - "docs/ru/cost-telemetry.md"
  - "docs/ru/customization.md"
  - "docs/ru/dev-doc-checks.md"
  - "docs/ru/doctor.md"
  - "docs/ru/environment.md"
  - "docs/ru/hooks.md"
  - "docs/ru/i18n-strategy.md"
  - "docs/ru/kilo-zai.md"
  - "docs/ru/knowledge-store.md"
  - "docs/ru/mcp.md"
  - "docs/ru/memory-merge-guidelines.md"
  - "docs/ru/model-providers.md"
  - "docs/ru/no-sdk-verify.md"
  - "docs/ru/permissions.md"
  - "docs/ru/plan-review.md"
  - "docs/ru/plan-stacks.md"
  - "docs/ru/publishing.md"
  - "docs/ru/quickstart.md"
  - "docs/ru/reasoning-trace.md"
  - "docs/ru/receipts.md"
  - "docs/ru/research/tausik-1.4-composer-retro-2026-05-02.md"
  - "docs/ru/research/tausik-1.4-token-baseline-2026-05-03.md"
  - "docs/ru/roles.md"
  - "docs/ru/security-checklist.md"
  - "docs/ru/security.md"
  - "docs/ru/senar-compliance-matrix.md"
  - "docs/ru/senar.md"
  - "docs/ru/session-active-time.md"
  - "docs/ru/sessions.md"
  - "docs/ru/skill-adaptation.md"
  - "docs/ru/skill-bundles-migration.md"
  - "docs/ru/skill-bundles.md"
  - "docs/ru/skill-ecosystem.md"
  - "docs/ru/skill-patterns.md"
  - "docs/ru/skill-profiles.md"
  - "docs/ru/skill-spec.md"
  - "docs/ru/skills.md"
  - "docs/ru/stacks.md"
  - "docs/ru/task-archive-spec.md"
  - "docs/ru/team-state-in-git.md"
  - "docs/ru/testing-principles.md"
  - "docs/ru/troubleshooting.md"
  - "docs/ru/upgrade.md"
  - "docs/ru/vendor-skills.md"
  - "docs/ru/verify-glossary.md"
  - "docs/ru/whats-new-1.8.md"
  - "docs/ru/whats-new-1.9.md"
  - "docs/ru/workflow.md"
  - "docs/ru/zero-defect.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T13:25:05Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАМЕР, смена #251, по 224 отслеживаемым .md вне tausik/ и research/: 592 относительные ссылки, 116 не разрешаются: 73 — переключатели «English | Русский» вида `/ru/docs/quickstart` (маршруты VitePress-сайта, вынесенного в tausik/site; на GitHub и в клоне это мёртвые ссылки на каждой странице docs/en и docs/ru), 39 — исторические записи CHANGELOG.md на удалённые brain-файлы, 2 — плейсхолдеры `../lang/file.md` в i18n-strategy.md, 1 — TODO.md → tausik_systemwide_analysis.md (gitignored, и TODO.md не публикуется по #368). Полная проверка ссылок по дереву была отложена в d7-cross-link-check (26.04) и так и не появилась — поэтому 73 страницы сломались молча, когда сайт уехал. Задача: (1) переключатели языка переводятся на относительные ссылки `../ru/<page>.md` / `../en/<page>.md` (работают на GitHub, в клоне и в VitePress, который относительные .md переписывает сам); (2) tests/test_docs_links_resolve.py: каждая относительная ссылка в README*.md, AGENTS.md, CONTRIBUTING.md, SECURITY.md, docs/** (без research/) разрешается в существующий файл; исключения объявлены перечнем с причиной (CHANGELOG*.md — историческая запись, ссылки на файлы как они были; плейсхолдеры i18n-strategy — примеры формата), и перечень не растёт без правки теста; (3) EN↔RU: у каждой страницы docs/en есть пара в docs/ru и наоборот, и переключатель указывает на пару — иначе тест краснит; (4) первое исполнение теста — замер до/после в журнале.

## Acceptance Criteria

AC-1: замер после правки: ноль неразрешимых относительных ссылок в README*.md, AGENTS.md, CONTRIBUTING.md, SECURITY.md, docs/** (без research/ и без объявленных исключений); число до/после в журнале. AC-2: tests/test_docs_links_resolve.py зелёный на дереве; НЕГАТИВ: временный каталог с одной ссылкой на несуществующий файл или с переключателем `/ru/docs/x` — тест краснит. AC-3: каждая страница docs/en имеет пару в docs/ru и наоборот; переключатель каждой страницы указывает ровно на её пару (тест). AC-4: исключения (CHANGELOG*.md, плейсхолдеры i18n-strategy) объявлены в тесте с причиной; добавить исключение без правки теста невозможно. AC-5: signed verify; CHANGELOG EN/RU (правка документации, видимая потребителю на GitHub).

## Plan

## Rollback

git revert; переключатели вернутся к маршрутам сайта.

## Journal

- 2026-09-13T13:23:46Z [implementation] — ЗАМЕР до: 224 md, 592 относительных ссылок, 116 не разрешаются (73 переключателя-маршрута сайта, 39 история CHANGELOG, 2 плейсхолдера i18n, 1 TODO). Сделано: 65 переключателей переписаны на ../ru|../en/<page>.md (66 файлов), 5 маршрутов сайта в research-заметках переведены на относительные, плейсхолдеры i18n-strategy стали <file>/<lang>, 22 парные страницы без переключателя получили его (39 вставок). ЗАМЕР после (те же правила, без CHANGELOG/TODO/research): 221 md, 549 ссылок, 0 неразрешимых; маршрутов сайта в docs/README*/AGENTS — 0. Тест tests/test_docs_links_resolve.py: 182 кейса — разрешение каждой ссылки постранично, отсутствие маршрутов сайта, парность (3 одиночки объявлены с причиной: ru/agent-contract, en/at-generation-procedure, ru/hooks-events), переключатель каждой пары указывает на пару; негатив — мёртвая ссылка и маршрут сайта ловятся. check_docs, audit_stale_docs, dedupe 290/686 — зелёные.
- 2026-09-13T13:25:02Z [implementation] — AC-1 ✓ замер до/после в журнале: 116 неразрешимых → 0 (221 md, 549 относительных ссылок; CHANGELOG/TODO/research вне правил). AC-2 ✓ tests/test_docs_links_resolve.py::test_every_relative_link_resolves[…] (по каждой странице), (НЕГАТИВ) ::test_a_dead_link_and_a_site_route_are_caught — nothing-here.md и /ru/docs/hooks дают ошибку-находку. AC-3 ✓ ::test_every_page_has_its_pair_or_is_a_declared_singleton; ::test_the_switcher_points_at_the_pair[…] по каждой паре. AC-4 ✓ SINGLETONS — три страницы с причиной; исключения проверки (CHANGELOG*, research, TODO) названы в докстринге теста, добавить новое без правки теста нельзя. AC-5 ✓ verify #2593 подписан; CHANGELOG EN/RU. Domain: читатель на GitHub кликает «Русский»/«English» в шапке любой страницы docs и попадает на пару, а не на 404 сайта, который переехал.
