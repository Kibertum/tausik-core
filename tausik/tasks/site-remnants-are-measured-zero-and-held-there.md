---
slug: site-remnants-are-measured-zero-and-held-there
title: "Следы сайта tausik.tech в core и на github/main замерены нулём и удерживаются храповиком"
status: planning
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
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Решение #368, п.1: сайт живёт только в tausik/site (GitLab). Истории extract-site-gitlab и core-github-cleanup закрыты; `git ls-files | grep -iE "^site/|vitepress|package.json|\.vue$"` даёт ноль в core (проверено в смене #251), github/main не проверялся. Задача: замерить оба дерева (core HEAD, github/main через git ls-tree -r; при недоступной сети — SKIP с причиной, не зелёное) на объявленный перечень признаков сайта (каталог site/, docs/.vitepress, *.vue, package.json/package-lock.json/pnpm-lock.yaml, vite.config.*, nginx-конфиги сайта, Dockerfile сайта) и зафиксировать тестом-храповиком tests/test_site_lives_elsewhere.py: возврат любого признака в core краснит; docs/ru/publishing.md называет, где живёт сайт. Ссылки на tausik.tech в README/docs — не след сайта, а ссылка на него, и не запрещаются.

## Acceptance Criteria

AC-1: замер записан в журнал: число совпадений перечня признаков сайта в core HEAD и в github/main (оба ноль или названы файлы). AC-2: tests/test_site_lives_elsewhere.py на core: ноль признаков; НЕГАТИВ: временный репозиторий с одним файлом site/index.html или package.json — тест краснит (мутация доказана). AC-3: проверка github/main пропускается с причиной без сети, а не проходит. AC-4: docs/ru/publishing.md и docs/en/publishing.md называют репозиторий сайта. AC-5: signed verify.

## Plan

## Rollback

git revert; удаляется один тест.

## Journal
