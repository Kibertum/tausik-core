---
slug: site-remnants-are-measured-zero-and-held-there
title: "Следы сайта tausik.tech в core и на github/main замерены нулём и удерживаются храповиком"
status: done
epic: release-19-renar-conformance
story: release19-clean-publication-and-onboarding
complexity: simple
role: qa
stack: python
tier: light
call_budget: 20
defect_of: null
scope: "tests/test_site_lives_elsewhere.py (новый), docs/ru/publishing.md, docs/en/publishing.md"
scope_exclude: "Репозиторий tausik/site не трогать; никаких push."
relevant_files:
  - "tests/test_site_lives_elsewhere.py"
  - "docs/ru/publishing.md"
  - "docs/en/publishing.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T13:20:46Z"
resolution: null
resolution_reason: null
---

## Goal

Решение #368, п.1: сайт живёт только в tausik/site (GitLab). Истории extract-site-gitlab и core-github-cleanup закрыты; `git ls-files | grep -iE "^site/|vitepress|package.json|\.vue$"` даёт ноль в core (проверено в смене #251), github/main не проверялся. Задача: замерить оба дерева (core HEAD, github/main через git ls-tree -r; при недоступной сети — SKIP с причиной, не зелёное) на объявленный перечень признаков сайта (каталог site/, docs/.vitepress, *.vue, package.json/package-lock.json/pnpm-lock.yaml, vite.config.*, nginx-конфиги сайта, Dockerfile сайта) и зафиксировать тестом-храповиком tests/test_site_lives_elsewhere.py: возврат любого признака в core краснит; docs/ru/publishing.md называет, где живёт сайт. Ссылки на tausik.tech в README/docs — не след сайта, а ссылка на него, и не запрещаются.

## Acceptance Criteria

AC-1: замер записан в журнал: число совпадений перечня признаков сайта в core HEAD и в github/main (оба ноль или названы файлы). AC-2: tests/test_site_lives_elsewhere.py на core: ноль признаков; НЕГАТИВ: временный репозиторий с одним файлом site/index.html или package.json — тест краснит (мутация доказана). AC-3: проверка github/main пропускается с причиной без сети, а не проходит. AC-4: docs/ru/publishing.md и docs/en/publishing.md называют репозиторий сайта. AC-5: signed verify.

## Plan

## Rollback

git revert; удаляется один тест.

## Journal

- 2026-09-13T13:20:19Z [implementation] — ЗАМЕР: git ls-files (core HEAD) и git ls-tree -r github/main по семи признакам сайта (site/, .vitepress/, *.vue, package(-lock).json/pnpm-lock/yarn.lock, vite.config.*, nginx*.conf, Dockerfile/docker-compose) — 0 и 0 совпадений. Тест tests/test_site_lives_elsewhere.py: core — ноль; github/main — по локальному ref без сетевого вызова, при отсутствии ref — skip с причиной; негатив — site/index.html и package.json ловятся, docs/en/site-notes.md и README.md нет. publishing.md EN/RU — строка tausik/site в таблице «Кто есть кто».
- 2026-09-13T13:20:40Z [implementation] — AC-1 ✓ замер в журнале: 0 совпадений семи признаков сайта в core HEAD (git ls-files) и 0 в github/main (git ls-tree -r). AC-2 ✓ tests/test_site_lives_elsewhere.py::test_core_carries_no_site_build — ноль на core; (НЕГАТИВ) ::test_a_returning_site_file_is_caught — site/index.html и package.json дают ошибку-совпадение, docs/en/site-notes.md и README.md — нет. AC-3 ✓ ::test_the_public_line_carries_no_site_build_or_says_it_was_not_measured — без ref github/main пропуск с причиной, не зелёное; сеть не вызывается. AC-4 ✓ docs/ru/publishing.md и docs/en/publishing.md — строка tausik/site в таблице линий. AC-5 ✓ verify #2591 подписан. Domain: сайт tausik.tech живёт в одном месте, и возврат любого файла сборки в core или на публичную линию красен до того, как уедет тегом.
